#!/usr/bin/env python3
"""Classify and date every Ontario REA instrument the map links to.

The Access Environment instrument PDFs (accessenvironment.ene.gov.on.ca/
instruments/<id>.pdf) are all harvested as document_type='application' with
the bare title "Renewable Energy Approval", so a project with an approval and
four amendments shows five identical links. Page one of each PDF carries the
instrument heading ("RENEWABLE ENERGY APPROVAL" / "AMENDMENT TO RENEWABLE
ENERGY APPROVAL" / "NOTICE OF REVOCATION ..."), the approval NUMBER and the
"Issue Date:". This script fetches each PDF once (cached under
pipeline/data/raw/rea/instruments/), parses those fields and writes
data/raw/rea_instruments.json keyed by URL:

  {url: {instrument, host, kind, title, heading, issue_date, rea_number,
         amends_number, amends_date, status}}

kind:  approval | amendment | revocation | other
title: the display title the naming convention prescribes (no date; the UI
       prefixes the formatted issue_date).

Usage:  python3 scripts/fetch_rea_instruments.py [--limit N] [--force]
                                               [--workers N]
Downloads run on a small thread pool (default 5); Access Environment
answers slowly (~30 s/PDF) so a serial pass over 557 instruments takes
hours. Parsing stays serial - it is cheap and keeps output ordered.
Reads URLs from the enviro_permits DB when available, else from
projects.geojson. Idempotent; re-runs only parse what is missing.
"""
import json
import os
import re
import hashlib
import subprocess
import sys
import time
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', 'raw', 'rea_instruments.json')
CACHE = os.path.join(os.path.dirname(ROOT), 'pipeline', 'data', 'raw', 'rea', 'instruments')
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')
PACE = 0.7  # seconds between fetches (ontario.ca is not IAAC, but be polite)
FORCE = '--force' in sys.argv
LIMIT = int(sys.argv[sys.argv.index('--limit') + 1]) if '--limit' in sys.argv else None
WORKERS = int(sys.argv[sys.argv.index('--workers') + 1]) if '--workers' in sys.argv else 5

MONTHS = {m: i for i, m in enumerate(
    ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august',
     'september', 'october', 'november', 'december'], 1)}

KIND_TITLES = {
    'approval':   'Renewable Energy Approval',
    'amendment':  'Renewable Energy Approval Amendment',
    'revocation': 'Renewable Energy Approval Revocation',
}


ACCESS_ENV = 'accessenvironment.ene.gov.on.ca/instruments/'
# Proponent sites republish the same instruments under their own names
# ("2.0_PDN-REA-Amendment1.pdf", "REA NUMBER 0558-9GUJ8T.pdf"). Any PDF on
# an REA project whose title or filename says REA is worth a look; parse()
# only classifies a document as an instrument when page one carries the
# heading and an issue date, so applications, reports and notices that
# merely mention the REA fall through untouched.
REA_HINT = re.compile(r'\bREA\b|renewable energy approval', re.I)


def instrument_urls():
    urls = []
    try:
        import psycopg2
        conn = psycopg2.connect('dbname=enviro_permits')
        cur = conn.cursor()
        cur.execute("""SELECT DISTINCT document_url FROM rea_documents
                       WHERE document_url LIKE '%%accessenvironment.ene.gov.on.ca/instruments/%%'
                       ORDER BY 1""")
        urls = [r[0] for r in cur.fetchall()]
        conn.close()
    except Exception as e:  # noqa: BLE001
        print(f'DB unavailable ({e}); falling back to projects.geojson')
    seen = set(urls)
    g = json.load(open(os.path.join(ROOT, 'projects.geojson')))
    for f in g['features']:
        for s in f['properties'].get('doc_sections') or []:
            for d in s.get('docs') or []:
                u = d.get('url') or ''
                if u in seen:
                    continue
                base = urllib.parse.unquote(u.rsplit('/', 1)[-1])
                hosted = ACCESS_ENV in u
                copy = (base.lower().endswith('.pdf')
                        and (REA_HINT.search(base) or REA_HINT.search(d.get('title') or '')))
                if hosted or copy:
                    seen.add(u)
                    urls.append(u)
    return urls


def fetch(url, dest):
    for attempt in range(3):
        r = subprocess.run(['curl', '-sSL', '-A', UA, '--max-time', '120',
                            '-o', dest, '-w', '%{http_code} %{content_type}', url],
                           capture_output=True, text=True)
        code, _, ctype = r.stdout.partition(' ')
        if code == '200' and 'pdf' in ctype.lower() and cached_ok(dest):
            return 'ok'
        if code in ('404', '410'):
            return f'http_{code}'
        time.sleep(3 * (attempt + 1))
    return f'fail_{code or "curl"}'


def page1_text(path):
    try:
        import fitz  # pymupdf
        with fitz.open(path) as doc:
            return '\n'.join(doc[i].get_text() for i in range(min(2, len(doc))))
    except Exception:  # noqa: BLE001
        r = subprocess.run(['pdftotext', '-l', '2', '-layout', path, '-'],
                           capture_output=True, text=True)
        return r.stdout


def parse_date(s):
    m = re.match(r'([A-Za-z]+)\.?\s+(\d{1,2}),?\s+(\d{4})', s.strip())
    if not m or m.group(1).lower() not in MONTHS:
        return None
    return f'{int(m.group(3)):04d}-{MONTHS[m.group(1).lower()]:02d}-{int(m.group(2)):02d}'


def parse(text):
    t = re.sub(r'[ \t]+', ' ', text)
    flat = ' '.join(t.split())
    rec = {'heading': None, 'kind': 'other', 'issue_date': None, 'rea_number': None,
           'amends_number': None, 'amends_date': None}
    head = re.search(r'((?:AMENDMENT TO|NOTICE OF (?:AN? )?\w+ (?:OF|TO)|NOTICE OF \w+)\s+'
                     r'(?:RENEWABLE ENERGY APPROVAL|APPROVAL)|RENEWABLE ENERGY APPROVAL'
                     r'(?:\s+AMENDMENT)?|NOTICE OF REVOCATION[A-Z ]*)', flat)
    if head:
        rec['heading'] = head.group(1).strip()
        h = rec['heading']
        if 'REVOCATION' in h:
            rec['kind'] = 'revocation'
        elif 'AMENDMENT' in h:
            rec['kind'] = 'amendment'
        elif h.startswith('RENEWABLE ENERGY APPROVAL'):
            rec['kind'] = 'approval'
    m = re.search(r'NUMBER\s+([0-9]{4}-[0-9A-Z]{6})', flat)
    if m:
        rec['rea_number'] = m.group(1)
    m = re.search(r'Issue Date:?\s*([A-Za-z]+\.?\s+\d{1,2},?\s+\d{4})', flat)
    if m:
        rec['issue_date'] = parse_date(m.group(1))
    m = re.search(r'amended (?:Renewable Energy )?Approval (?:No\.?|Number)\s*([0-9]{4}-[0-9A-Z]{6})'
                  r'(?:,? issued on ([A-Za-z]+\.?\s+\d{1,2},?\s+\d{4}))?', flat, re.I)
    if m:
        rec['amends_number'] = m.group(1)
        rec['amends_date'] = parse_date(m.group(2)) if m.group(2) else None
        if rec['kind'] == 'other':
            rec['kind'] = 'amendment'
    # A document whose body says "hereby notified that I have amended" is an
    # amendment even when the heading was not captured cleanly.
    if rec['kind'] == 'other' and re.search(r'notified that I have amended', flat, re.I):
        rec['kind'] = 'amendment'
    if rec['kind'] == 'other' and re.search(r'notified that I have revoked', flat, re.I):
        rec['kind'] = 'revocation'
    rec['title'] = KIND_TITLES.get(rec['kind'], 'Renewable Energy Approval (unclassified)')
    return rec


def cache_path(url):
    inst = urllib.parse.unquote(url.rsplit('/', 1)[-1])
    inst = re.sub(r'\.pdf$', '', inst, flags=re.I)
    if ACCESS_ENV not in url:
        # "REA_Amendment.pdf" exists on several proponent sites; key by URL
        inst = hashlib.sha1(url.encode()).hexdigest()[:10] + '_' + re.sub(r'[^\w.-]+', '_', inst)[:80]
    return inst, os.path.join(CACHE, inst + '.pdf')


def cached_ok(path):
    """A cache hit must be a whole PDF. A run killed mid-download leaves a
    truncated file that still passes a size check but parses to nothing, so
    require the header and a trailer near the end of the file."""
    try:
        if os.path.getsize(path) < 1000:
            return False
        with open(path, 'rb') as fh:
            if fh.read(5) != b'%PDF-':
                return False
            fh.seek(-2048, os.SEEK_END)
            return b'%%EOF' in fh.read()
    except OSError:
        return False


def main():
    os.makedirs(CACHE, exist_ok=True)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    out = json.load(open(OUT)) if os.path.exists(OUT) and not FORCE else {}
    urls = instrument_urls()
    if LIMIT:
        urls = urls[:LIMIT]
    todo = [u for u in urls
            if FORCE or not (out.get(u) or {}).get('status') == 'ok']
    print(f'{len(urls)} instrument URLs; {len(out)} already parsed; {len(todo)} to do')

    # ── fetch stage (parallel; the server is the bottleneck, not us) ──
    missing = [u for u in todo if not cached_ok(cache_path(u)[1])]
    fetched = {}
    if missing:
        import concurrent.futures
        import threading
        lock = threading.Lock()
        done = [0]

        def grab(url):
            inst, dest = cache_path(url)
            st = fetch(url, dest)
            time.sleep(PACE)
            with lock:
                done[0] += 1
                if done[0] % 25 == 0 or done[0] == len(missing):
                    print(f'  fetched {done[0]}/{len(missing)}  last: {inst} {st}',
                          flush=True)
            return url, st

        print(f'fetching {len(missing)} PDFs on {WORKERS} workers')
        with concurrent.futures.ThreadPoolExecutor(WORKERS) as ex:
            for url, st in ex.map(grab, missing):
                fetched[url] = st

    # ── parse stage (serial, cheap) ──
    for i, url in enumerate(todo, 1):
        inst, dest = cache_path(url)
        status = fetched.get(url, 'ok')
        rec = {'instrument': inst, 'status': status,
               'host': 'access_environment' if ACCESS_ENV in url else 'proponent'}
        if status == 'ok':
            rec.update(parse(page1_text(dest)))
        out[url] = rec
        if i % 100 == 0:
            json.dump(out, open(OUT, 'w'), indent=1, ensure_ascii=False)
            print(f'  parsed {i}/{len(todo)}', flush=True)
    json.dump(out, open(OUT, 'w'), indent=1, ensure_ascii=False)
    from collections import Counter
    print('kinds:', Counter(r.get('kind') for r in out.values()))
    print('status:', Counter(r.get('status') for r in out.values()))
    print('undated:', sum(1 for r in out.values() if r.get('status') == 'ok' and not r.get('issue_date')))


if __name__ == '__main__':
    main()
