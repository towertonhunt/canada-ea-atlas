#!/usr/bin/env python3
"""Mirror every document the atlas links to into our own R2 bucket.

Government and proponent hosts retire documents; this makes the copy we link
to permanent. The archive is keyed by the registry's own identifiers so the
key is predictable from the original URL, and a manifest
(data/raw/archive_manifest.json.gz) records what has been fetched, where it
landed, and what failed, so runs are resumable and idempotent.

  python3 scripts/archive_docs.py --budget 18000          # in the lane
  python3 scripts/archive_docs.py --only qc --limit 20     # spot run
  python3 scripts/archive_docs.py --dry-run --only federal # plan only

Credentials come from the environment (R2_ACCOUNT_ID, R2_ACCESS_KEY_ID,
R2_SECRET_ACCESS_KEY, R2_BUCKET, R2_PUBLIC_BASE) and are handed to rclone
through its RCLONE_CONFIG_* variables; nothing is written to disk.

Federal links are landing pages, not files: the page carries an unquoted
href to /050/documents/p<proj>/<doc>.pdf when there is an attachment, and
about 44% are HTML-only notices, in which case the page itself is archived.
IAAC throttles by answering 404 for the whole host after a burst, so that
host is paced hard and canary-checked; see check_links.py.
"""
import argparse
import collections
import glob
import gzip
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_links import CANARY, HostLimiter, SLOW_HOSTS, UA  # noqa: E402

MANIFEST = os.path.join(ROOT, 'data', 'raw', 'archive_manifest.json.gz')
MAX_BYTES = 600 * 1024 * 1024        # skip anything larger; flag for manual
MAX_FAILS = 4                        # give up on a URL after this many tries
IAAC = 'iaac-aeic.gc.ca'
FED_FILE_RX = re.compile(r'href=["\']?(/050/documents/[^"\'\s>]+)', re.I)
FED_DOC_RX = re.compile(r'/050/evaluations/document/(\d+)')
SAFE = re.compile(r'[^A-Za-z0-9._-]+')


def env(name):
    v = os.environ.get(name)
    if not v:
        raise SystemExit(f'{name} is not set')
    return v


def rclone_env():
    """rclone remote 'r2' defined purely through the environment."""
    e = dict(os.environ)
    e.update({
        'RCLONE_CONFIG_R2_TYPE': 's3',
        'RCLONE_CONFIG_R2_PROVIDER': 'Cloudflare',
        'RCLONE_CONFIG_R2_ACCESS_KEY_ID': env('R2_ACCESS_KEY_ID'),
        'RCLONE_CONFIG_R2_SECRET_ACCESS_KEY': env('R2_SECRET_ACCESS_KEY'),
        'RCLONE_CONFIG_R2_ENDPOINT':
            f"https://{env('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com",
        'RCLONE_CONFIG_R2_ACL': 'private',
        'RCLONE_CONFIG_R2_NO_CHECK_BUCKET': 'true',
    })
    return e


def upload_dir(staging, dry_run=False):
    """Push the staging tree to the bucket; keys are the relative paths."""
    if dry_run or not any(os.scandir(staging)):
        return True
    cmd = ['rclone', 'copy', staging, f"r2:{env('R2_BUCKET')}",
           '--transfers', '8', '--s3-no-check-bucket', '--quiet']
    r = subprocess.run(cmd, env=rclone_env(), capture_output=True, text=True)
    if r.returncode != 0:
        print('rclone failed:', r.stderr.strip()[-500:], flush=True)
        return False
    return True


# ── keys ──────────────────────────────────────────────────────────────
def safe(s, n=120):
    return SAFE.sub('_', urllib.parse.unquote(s)).strip('_')[:n] or 'file'


def key_for(jur, project, url, filename=None):
    """Deterministic object key. Mirrors the source's own ids where it has
    them; otherwise the URL's basename, or a hash when there is none."""
    path = urllib.parse.urlsplit(url).path
    q = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
    if jur == 'federal':
        m = FED_DOC_RX.search(url)
        base = filename or (f'{m.group(1)}.pdf' if m else os.path.basename(path))
    elif jur == 'bc':                        # /api/public/document/<id>/download
        m = re.search(r'/document/([0-9a-f]{24})', url)
        base = f'{m.group(1)}.pdf' if m else os.path.basename(path) or 'file'
    elif jur == 'qc':                        # voute.bape.gouv.qc.ca/dl/?id=<n>
        base = f"{q.get('id', ['file'])[0]}.pdf"
    else:
        base = os.path.basename(path)
        if not base or '.' not in base:
            base = hashlib.sha1(url.encode()).hexdigest()[:16] + '.html'
    return f'{jur}/{safe(str(project), 80)}/{safe(base)}'


# ── fetch ─────────────────────────────────────────────────────────────
def fetch(url, limiter, timeout=120):
    host = urllib.parse.urlsplit(url).hostname or ''
    limiter.acquire(host)
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': UA, 'Accept': '*/*',
            'Accept-Language': 'en-CA,en;q=0.9,fr-CA;q=0.8'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            ctype = (r.headers.get('Content-Type') or '').split(';')[0].strip()
            clen = r.headers.get('Content-Length')
            if clen and int(clen) > MAX_BYTES:
                return None, ctype, f'too large ({int(clen) // 1_000_000} MB)'
            data = r.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                return None, ctype, 'too large (streamed)'
            disp = r.headers.get('Content-Disposition') or ''
            return data, ctype, disp
    finally:
        limiter.release(host)


def resolve_federal(url, html):
    """Landing page -> (file url or None). None means HTML-only notice."""
    m = FED_FILE_RX.search(html)
    if not m:
        return None
    return urllib.parse.urljoin(url, m.group(1))


def ext_for(ctype, disp, fallback):
    m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)', disp or '', re.I)
    if m:
        e = os.path.splitext(urllib.parse.unquote(m.group(1)))[1].lower()
        if e:
            return e
    return {'application/pdf': '.pdf', 'text/html': '.html',
            'application/msword': '.doc', 'application/zip': '.zip',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
            'application/vnd.ms-excel': '.xls'}.get(ctype, fallback)


# ── work list ────────────────────────────────────────────────────────
def targets(only=None):
    out, seen = [], set()
    for path in sorted(glob.glob(os.path.join(ROOT, 'data', 'docs', '*', '*.json'))):
        jur = os.path.basename(os.path.dirname(path))
        if only and jur not in only:
            continue
        project = os.path.splitext(os.path.basename(path))[0]
        try:
            docs = json.load(open(path)).get('docs') or []
        except (ValueError, OSError):
            continue
        for d in docs:
            u = d.get('url')
            if not u or u in seen or not u.startswith(('http://', 'https://')):
                continue
            seen.add(u)
            out.append((u, jur, project, d.get('title') or ''))
    return out


def load_manifest():
    if os.path.exists(MANIFEST):
        return json.load(gzip.open(MANIFEST, 'rt'))
    return {}


def save_manifest(m):
    tmp = MANIFEST + '.tmp'
    with gzip.open(tmp, 'wt') as f:
        json.dump(m, f, ensure_ascii=False)
    os.replace(tmp, MANIFEST)


# ── main ─────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--budget', type=int, default=3600, help='seconds')
    ap.add_argument('--only', help='comma-separated jurisdictions')
    ap.add_argument('--limit', type=int)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--flush-every', type=int, default=200)
    args = ap.parse_args()

    public = os.environ.get('R2_PUBLIC_BASE', '').rstrip('/')
    if not args.dry_run:
        env('R2_BUCKET')
        if not public:
            raise SystemExit('R2_PUBLIC_BASE is not set')

    manifest = load_manifest()
    todo = [t for t in targets(set(args.only.split(',')) if args.only else None)
            if not manifest.get(t[0], {}).get('key')
            and manifest.get(t[0], {}).get('fails', 0) < MAX_FAILS]
    # round-robin across hosts so the slow one doesn't serialise the run
    by_host = collections.defaultdict(collections.deque)
    for t in todo:
        by_host[urllib.parse.urlsplit(t[0]).hostname].append(t)
    order = []
    while any(by_host.values()):
        for h in list(by_host):
            if by_host[h]:
                order.append(by_host[h].popleft())
    todo = order[:args.limit] if args.limit else order
    done_before = sum(1 for v in manifest.values() if v.get('key'))
    print(f'{len(todo)} to fetch, {done_before} already archived, '
          f'{len(manifest) - done_before} pending/failed', flush=True)
    if args.dry_run:
        for u, jur, proj, _ in todo[:15]:
            print('  ', key_for(jur, proj, u), '<-', u[:90])
        return

    limiter = HostLimiter(2, 0.6)
    dead = set()
    for host in {urllib.parse.urlsplit(t[0]).hostname for t in todo}:
        if host in CANARY:
            try:
                fetch(CANARY[host], limiter)
            except Exception as e:                            # noqa: BLE001
                dead.add(host)
                print(f'  canary FAIL {host}: {e} -- skipping host', flush=True)

    staging = tempfile.mkdtemp(prefix='ea-archive-')
    started, n_ok, n_fail, n_bytes = time.time(), 0, 0, 0
    host_hits = collections.Counter()
    staged = []          # urls written to staging but not yet uploaded

    def flush():
        """Upload what is staged; only then does the manifest get to claim it."""
        if not staged:
            save_manifest(manifest)
            return True
        if upload_dir(staging):
            save_manifest(manifest)
            shutil.rmtree(staging)
            os.makedirs(staging)
            staged.clear()
            return True
        return False

    try:
        for url, jur, project, title in todo:
            if time.time() - started > args.budget:
                print('budget reached', flush=True)
                break
            host = urllib.parse.urlsplit(url).hostname
            if host in dead:
                continue
            rec = manifest.setdefault(url, {'jur': jur, 'project': project})
            rec['title'] = title[:200]
            try:
                # periodic canary on the throttling host
                host_hits[host] += 1
                if host == IAAC and host_hits[host] % 100 == 0:
                    fetch(CANARY[IAAC], limiter)

                data, ctype, disp = fetch(url, limiter)
                if data is None:
                    raise RuntimeError(disp)
                file_url, kind = url, 'file'
                if jur == 'federal' and 'html' in ctype:
                    fu = resolve_federal(url, data.decode('utf-8', 'replace'))
                    if fu:
                        data2, ctype2, disp2 = fetch(fu, limiter)
                        if data2 is None:
                            raise RuntimeError(disp2)
                        data, ctype, disp, file_url = data2, ctype2, disp2, fu
                    else:
                        kind = 'html_notice'
                if 'html' in ctype and jur != 'federal' and jur != 'on':
                    # a registry answering HTML where a file was expected is
                    # a soft failure (login page, error page); don't archive it
                    raise RuntimeError(f'got html from {host}')
                ext = ext_for(ctype, disp, os.path.splitext(
                    urllib.parse.urlsplit(file_url).path)[1] or '.bin')
                key = key_for(jur, project, url)
                if not key.endswith(ext):
                    key = os.path.splitext(key)[0] + ext
                dest = os.path.join(staging, key)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                open(dest, 'wb').write(data)
                rec.update(key=key, archive_url=f'{public}/{key}',
                           bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                           content_type=ctype, kind=kind, file_url=file_url,
                           fetched_at=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
                rec.pop('error', None)
                n_ok += 1
                n_bytes += len(data)
                staged.append(url)
            except urllib.error.HTTPError as e:
                rec['fails'] = rec.get('fails', 0) + 1
                rec['error'] = f'HTTP {e.code}'
                n_fail += 1
                if host == IAAC and e.code == 404:
                    # could be a throttle, not a dead link: verify with the canary
                    try:
                        fetch(CANARY[IAAC], limiter)
                    except Exception:                          # noqa: BLE001
                        dead.add(host)
                        rec['fails'] -= 1          # not the URL's fault
                        print('  IAAC is refusing us -- dropping host for this run', flush=True)
            except Exception as e:                            # noqa: BLE001
                rec['fails'] = rec.get('fails', 0) + 1
                rec['error'] = str(e)[:160]
                n_fail += 1
            if staged and len(staged) % args.flush_every == 0:
                if not flush():
                    print('upload failing; stopping to avoid losing work', flush=True)
                    break
                print(f'  {n_ok} archived ({n_bytes / 1e9:.2f} GB), {n_fail} failed, '
                      f'{(time.time() - started) / 60:.0f} min', flush=True)
    finally:
        if not flush():
            # never let the manifest claim objects that aren't in the bucket
            print(f'FINAL UPLOAD FAILED -- {len(staged)} staged files will be '
                  f'refetched next run', flush=True)
            for url in staged:
                for k in ('key', 'archive_url', 'bytes', 'sha256',
                          'content_type', 'kind', 'file_url', 'fetched_at'):
                    manifest[url].pop(k, None)
            save_manifest(manifest)
        shutil.rmtree(staging, ignore_errors=True)

    total = sum(1 for v in manifest.values() if v.get('key'))
    gb = sum(v.get('bytes', 0) for v in manifest.values()) / 1e9
    print(f'\nthis run: {n_ok} archived, {n_fail} failed, {n_bytes / 1e9:.2f} GB')
    print(f'archive total: {total} objects, {gb:.1f} GB -> {MANIFEST}')


if __name__ == '__main__':
    main()
