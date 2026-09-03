#!/usr/bin/env python3
"""Audit every outbound link the atlas shows, and say which ones actually work.

Two traps make a naive checker useless here:

  * iaac-aeic.gc.ca answers HTTP 200 with a "We couldn't find that Web page"
    body for retired project ids, and 404s outright without a browser
    User-Agent. So bodies are inspected for soft-404 markers, not just codes.
  * The same host throttles by returning 404 rather than 429 -- hammer it and
    every link looks dead. So requests are paced per hostname, and anything
    that fails is re-checked serially at the end before it counts as broken.

  python3 scripts/check_links.py                 # all registry_url values
  python3 scripts/check_links.py --docs          # also every document URL
  python3 scripts/check_links.py --sample 200    # quick spot-check per source
  python3 scripts/check_links.py --only qc_ree

Writes data/link_health.json (per-source rollup + every broken URL) and
checkpoints as it goes, so a long sweep can be re-run to resume.
"""
import argparse
import collections
import concurrent.futures as cf
import glob
import json
import os
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', 'link_health.json')
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120.0 Safari/537.36')

# Bodies that are served with a 2xx but are really "gone".
SOFT_404 = re.compile(
    r"couldn't find that Web page|We're sorry you ended up here"
    r"|resource cannot be found|Page not found|Page introuvable"
    r"|nous ne trouvons pas|n'existe plus|no longer available"
    r"|Site pr.{0,3}sentement en d.{0,3}veloppement",
    re.I)
READ_BYTES = 120_000
# Be a good citizen, and stay under the throttles: at most this many requests
# in flight against one hostname, spaced at least this far apart.
PER_HOST = 2
HOST_INTERVAL = 0.6
SLOW_HOSTS = {'iaac-aeic.gc.ca': 1.2}   # throttles by answering 404

# A control URL per host that is known to exist. If the canary fails, the host
# is refusing us (IAAC blocks by answering 404 for *everything*, including its
# own home page) and every result for that host would be a false negative --
# so we stop checking it rather than record thousands of bogus dead links.
# Hosts that serve a single JavaScript shell for every deep link: the server
# returns a byte-identical 200 whatever the id (including ids that don't
# exist), and the record is fetched client-side. The link works in a browser
# but cannot be verified here, so it is reported as 'js_app' rather than
# counted as either working or broken.
JS_APP_HOSTS = {'www.geologyontario.mines.gov.on.ca'}

# Hosts whose project ids we hold from the registry's OWN search index, so the
# link is valid by construction and probing every one buys nothing but a ban
# (IAAC blocked us after ~50 requests even at 1.2s spacing). Only a small
# sample per host is fetched to confirm the URL *pattern* still works; the
# rest are recorded as 'index_verified'.
INDEX_VERIFIED_HOSTS = {'iaac-aeic.gc.ca': 30}
# Re-run the canary this often (per host) so a host that starts refusing us
# mid-sweep is dropped, not recorded as thousands of dead links.
CANARY_EVERY = 150
NOT_BROKEN = ('ok', 'js_app', 'index_verified', 'skipped')

CANARY = {
    'iaac-aeic.gc.ca': 'https://iaac-aeic.gc.ca/050/evaluations',
    'www.ontario.ca': 'https://www.ontario.ca/page/environmental-assessments',
    'novascotia.ca': 'https://novascotia.ca/nse/ea/',
    'www.gov.nl.ca': 'https://www.gov.nl.ca/eccc/projects/',
    'www.gov.mb.ca': 'https://www.gov.mb.ca/sd/eal/registries/',
    'projects.eao.gov.bc.ca': 'https://projects.eao.gov.bc.ca/',
    'www.ree.environnement.gouv.qc.ca':
        'https://www.ree.environnement.gouv.qc.ca/projet.asp?no_dossier=3211-10-025',
}


class HostLimiter:
    """Bounded concurrency *and* a minimum gap between requests per host."""

    def __init__(self, n, interval):
        self._n, self._interval = n, interval
        self._sem, self._last, self._lock = {}, {}, threading.Lock()

    def _state(self, host):
        with self._lock:
            if host not in self._sem:
                self._sem[host] = threading.Semaphore(self._n)
                self._last[host] = [0.0, threading.Lock()]
            return self._sem[host], self._last[host]

    def acquire(self, host):
        sem, last = self._state(host)
        sem.acquire()
        gap = SLOW_HOSTS.get(host, self._interval)
        with last[1]:
            wait = last[0] + gap - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            last[0] = time.monotonic()
        return sem

    def release(self, host):
        self._state(host)[0].release()


def targets(args):
    """(url, source, label) for everything the map or a sidebar can link to."""
    geo = json.load(open(os.path.join(ROOT, 'data', 'projects_canada.geojson')))
    seen, out = set(), []
    for f in geo['features']:
        p = f['properties']
        u = p.get('registry_url')
        if not u or u in seen:
            continue
        seen.add(u)
        out.append((u, p.get('source') or 'unknown', p.get('name') or ''))
    if args.docs:
        for path in sorted(glob.glob(os.path.join(ROOT, 'data', 'docs', '*', '*.json'))):
            jur = os.path.basename(os.path.dirname(path))
            try:
                cat = json.load(open(path))
            except (ValueError, OSError):
                continue
            for d in cat.get('docs') or []:
                u = d.get('url')
                if not u or u in seen:
                    continue
                seen.add(u)
                out.append((u, f'docs:{jur}', d.get('title') or ''))
    if args.only:
        keep = set(args.only.split(','))
        out = [t for t in out if t[1] in keep]
    if args.sample:
        by = collections.defaultdict(list)
        for t in out:
            by[t[1]].append(t)
        out = [t for ts in by.values() for t in ts[:args.sample]]
    return out


def probe(url, limiter, timeout=40):
    """-> (verdict, http_code, detail). verdict: ok | soft404 | http_error | error"""
    try:
        host = urllib.parse.urlsplit(url).hostname or ''
    except ValueError:
        return 'error', None, 'unparseable url'
    if not url.lower().startswith(('http://', 'https://')):
        return 'error', None, 'not an absolute http(s) url'
    if host in JS_APP_HOSTS:
        return 'js_app', None, 'client-rendered deep link; not server-verifiable'
    limiter.acquire(host)
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': UA,
            'Accept': 'text/html,application/xhtml+xml,application/pdf,*/*',
            'Accept-Language': 'en-CA,en;q=0.9,fr-CA;q=0.8',
        })
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                ctype = (r.headers.get('Content-Type') or '').lower()
                if 'html' not in ctype and 'xml' not in ctype:
                    return 'ok', r.status, ctype.split(';')[0]  # PDF etc.
                body = r.read(READ_BYTES).decode('utf-8', 'replace')
                if SOFT_404.search(body):
                    return 'soft404', r.status, '200 but body says page is gone'
                return 'ok', r.status, f'{len(body)}b'
        except urllib.error.HTTPError as e:
            return 'http_error', e.code, f'HTTP {e.code}'
        except Exception as e:                              # noqa: BLE001
            return 'error', None, f'{type(e).__name__}: {e}'[:120]
    finally:
        limiter.release(host)


def canary_check(hosts, limiter):
    """-> set of hosts that are refusing us and must be skipped."""
    blocked = set()
    for host in sorted(hosts):
        url = CANARY.get(host)
        if not url:
            continue
        verdict, code, detail = probe(url, limiter)
        if verdict != 'ok':
            blocked.add(host)
            print(f'  CANARY FAIL {host}: {detail} -- skipping this host',
                  flush=True)
    return blocked


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--docs', action='store_true', help='also check document URLs')
    ap.add_argument('--sample', type=int, help='check only N URLs per source')
    ap.add_argument('--only', help='comma-separated source filter')
    ap.add_argument('--workers', type=int, default=6)
    ap.add_argument('--resume', action='store_true',
                    help='skip URLs already recorded in data/link_health.json')
    args = ap.parse_args()

    todo = targets(args)
    prior = {}
    if args.resume and os.path.exists(OUT):
        prior = {r['url']: r for r in json.load(open(OUT)).get('results', [])}
        todo = [t for t in todo if t[0] not in prior]
    print(f'checking {len(todo)} urls ({len(prior)} already done)', flush=True)

    limiter = HostLimiter(PER_HOST, HOST_INTERVAL)
    hosts = {urllib.parse.urlsplit(u).hostname for u, _, _ in todo}
    blocked = canary_check(hosts - {None}, limiter)
    if blocked:
        skipped = [t for t in todo if urllib.parse.urlsplit(t[0]).hostname in blocked]
        todo = [t for t in todo if urllib.parse.urlsplit(t[0]).hostname not in blocked]
        print(f'skipping {len(skipped)} urls on {len(blocked)} blocked host(s); '
              f'{len(todo)} to check', flush=True)

    # Sample the index-verified hosts instead of sweeping them.
    per_host_seen, sampled_out = collections.Counter(), []
    kept = []
    for t in todo:
        host = urllib.parse.urlsplit(t[0]).hostname
        cap = INDEX_VERIFIED_HOSTS.get(host)
        if cap is not None and per_host_seen[host] >= cap:
            sampled_out.append(t)
        else:
            per_host_seen[host] += 1
            kept.append(t)
    if sampled_out:
        print(f'{len(sampled_out)} urls on index-verified hosts recorded without '
              f'fetching (sampling {dict(INDEX_VERIFIED_HOSTS)} each)', flush=True)
    todo = kept

    results, lock, started = list(prior.values()), threading.Lock(), time.time()
    for url, source, label in sampled_out:
        results.append({'url': url, 'source': source, 'name': label[:120],
                        'verdict': 'index_verified', 'code': None,
                        'detail': 'id comes from the registry search index; '
                                  'pattern spot-checked, not fetched'})
    host_hits, dead_hosts = collections.Counter(), set(blocked)

    def run(t):
        url, source, label = t
        host = urllib.parse.urlsplit(url).hostname
        with lock:
            if host in dead_hosts:
                return None
            host_hits[host] += 1
            recheck = host_hits[host] % CANARY_EVERY == 0 and host in CANARY
        if recheck and probe(CANARY[host], limiter)[0] != 'ok':
            with lock:
                dead_hosts.add(host)
            print(f'  CANARY FAIL mid-sweep {host} -- dropping host', flush=True)
            return None
        verdict, code, detail = probe(url, limiter)
        rec = {'url': url, 'source': source, 'name': label[:120],
               'verdict': verdict, 'code': code, 'detail': detail}
        with lock:
            results.append(rec)
            n = len(results)
            if n % 250 == 0:
                bad = sum(1 for r in results if r['verdict'] not in NOT_BROKEN)
                rate = n / max(time.time() - started, 1)
                print(f'{n}/{len(todo) + len(prior)} checked, {bad} broken, '
                      f'{rate:.1f}/s', flush=True)
                write(results)
        return rec

    with cf.ThreadPoolExecutor(args.workers) as ex:
        list(ex.map(run, todo))
    if dead_hosts - set(blocked):
        # results gathered from a host that turned out to be refusing us are
        # not evidence of anything; replace them with 'skipped'
        results = [r for r in results
                   if urllib.parse.urlsplit(r['url']).hostname not in dead_hosts
                   or r['verdict'] in ('ok', 'index_verified', 'js_app')]
        have = {r['url'] for r in results}
        for url, source, label in todo:
            if url not in have and urllib.parse.urlsplit(url).hostname in dead_hosts:
                results.append({'url': url, 'source': source, 'name': label[:120],
                                'verdict': 'skipped', 'code': None,
                                'detail': 'host refused us mid-sweep; not checked'})
    write(results)

    # Confirmation pass. A throttled host answers 404, so a single failure
    # proves nothing -- re-check serially and slowly, and let anything that
    # recovers count as working.
    suspect = [r for r in results if r['verdict'] not in NOT_BROKEN
               and r['detail'] != 'not an absolute http(s) url']
    if suspect:
        print(f'\nre-checking {len(suspect)} failures serially...', flush=True)
        calm = HostLimiter(1, 2.0)
        still_blocked = canary_check(
            {urllib.parse.urlsplit(r['url']).hostname for r in suspect} - {None},
            calm)
        suspect = [r for r in suspect
                   if urllib.parse.urlsplit(r['url']).hostname not in still_blocked]
        recovered = 0
        for i, r in enumerate(suspect, 1):
            verdict, code, detail = probe(r['url'], calm)
            if verdict == 'ok':
                recovered += 1
            r.update(verdict=verdict, code=code, detail=detail,
                     confirmed=verdict != 'ok')
            if i % 100 == 0:
                print(f'  {i}/{len(suspect)} ({recovered} recovered)', flush=True)
        print(f'  {recovered}/{len(suspect)} recovered on retry')
        write(results)

    roll = collections.defaultdict(collections.Counter)
    for r in results:
        roll[r['source']][r['verdict']] += 1
    print(f"\n{'source':22}{'ok':>7}{'soft404':>9}{'http_err':>10}{'error':>7}"
          f"{'js_app':>8}{'idx_ver':>9}{'skipped':>9}")
    for s in sorted(roll):
        c = roll[s]
        print(f"{s:22}{c['ok']:>7}{c['soft404']:>9}{c['http_error']:>10}"
              f"{c['error']:>7}{c['js_app']:>8}{c['index_verified']:>9}{c['skipped']:>9}")
    broken = sum(1 for r in results if r['verdict'] not in NOT_BROKEN)
    print(f'\n{broken}/{len(results)} broken -> {OUT}')


def write(results):
    roll = collections.defaultdict(collections.Counter)
    for r in results:
        roll[r['source']][r['verdict']] += 1
    json.dump({
        'checked_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'total': len(results),
        'broken': sum(1 for r in results if r['verdict'] not in NOT_BROKEN),
        'by_source': {s: dict(c) for s, c in sorted(roll.items())},
        'results': sorted(results,
                          key=lambda r: (r['verdict'] in NOT_BROKEN, r['source'])),
    }, open(OUT, 'w'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
