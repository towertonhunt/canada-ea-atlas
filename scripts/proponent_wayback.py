#!/usr/bin/env python3
"""Discover a proponent's documents through the Wayback Machine's index.

The CDX API lists every URL the Internet Archive has ever captured on a
host, with MIME type and timestamp. Asking it for PDFs and Office files on
a proponent's domain gives, at zero load on the proponent and with no bot
wall in the way, the full historical document inventory -- including files
the site has since removed, which is exactly what the archive is for.

Complements proponent_discover.py (live crawl). Where the live site blocks
us (OPG, Suncor, BHP behind Cloudflare bot management) this is the primary
route; elsewhere it fills in history.

  python3 scripts/proponent_wayback.py --key "ontario power generation"
  python3 scripts/proponent_wayback.py --top 60

-> data/raw/proponents/wayback/<key>.json
   {docs: [{url, wayback_url, timestamp, bytes, type}], ...}
"""
import argparse
import collections
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from proponent_discover import classify, TARGETS  # noqa: E402

OUT_DIR = os.path.join(ROOT, 'data', 'raw', 'proponents', 'wayback')
CDX = 'http://web.archive.org/cdx/search/cdx'
UA = {'User-Agent': 'CanadaEAAtlas/1.0 (https://canadaeaatlas.towerton.ca; archive research)'}
MIMES = ('application/pdf', 'application/msword',
         'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
         'application/zip')
# URL words that mark obvious non-EA material; everything else is kept and
# classified, and the reviewer decides.
NOISE = re.compile(r'annual[-_ ]?report|financial|investor|quarterly|proxy|circular|'
                   r'press[-_ ]?release|newsletter|brochure|career|recipe|menu|'
                   r'/fr/|_fr\.|french|-fr\.pdf', re.I)


def cdx(host, mime, timeout=600, tries=4):
    """One query per host and MIME type. The CDX server is slow and
    rate-limited (503/504 under load), so: a single large request, a long
    timeout, and exponential backoff rather than many small pages."""
    q = urllib.parse.urlencode({
        'url': f'{host}/*', 'filter': f'mimetype:{mime}', 'collapse': 'urlkey',
        'fl': 'original,timestamp,length,statuscode', 'output': 'json',
        'limit': 60000})
    req = urllib.request.Request(f'{CDX}?{q}', headers=UA)
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                rows = json.load(r)
            return rows[1:] if rows else []
        except urllib.error.HTTPError as e:
            if e.code in (429, 503, 504) and attempt < tries - 1:
                time.sleep(20 * (attempt + 1))
                continue
            raise
        except Exception:                                        # noqa: BLE001
            if attempt < tries - 1:
                time.sleep(20 * (attempt + 1))
                continue
            raise


def apex(host):
    host = (host or '').lower()
    return host[4:] if host.startswith('www.') else host


def harvest(host):
    docs, seen = [], set()
    host = apex(host)
    for mime in MIMES:
        try:
            rows = cdx(host, mime)
        except Exception as e:                                   # noqa: BLE001
            print(f'  cdx {mime.split("/")[-1]}: {str(e)[:60]}', flush=True)
            rows = []
        if True:
            for original, ts, length, status in rows:
                if status not in ('200', '-') or original in seen:
                    continue
                seen.add(original)
                docs.append({
                    'url': original, 'timestamp': ts,
                    'wayback_url': f'https://web.archive.org/web/{ts}id_/{original}',
                    'bytes': int(length) if str(length).isdigit() else None,
                    'title': urllib.parse.unquote(os.path.basename(
                        urllib.parse.urlsplit(original).path)),
                    'type': classify('', original),
                    'noise': bool(NOISE.search(original)),
                })
            time.sleep(3.0)
    return docs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--key')
    ap.add_argument('--top', type=int)
    ap.add_argument('--refresh', action='store_true')
    args = ap.parse_args()
    os.makedirs(OUT_DIR, exist_ok=True)
    targets = json.load(open(TARGETS))
    if args.key:
        todo = [t for t in targets if t['key'] == args.key]
    else:
        todo = [t for t in targets if t.get('website')][:args.top or 20]
    for t in todo:
        if not t.get('website'):
            continue
        out = os.path.join(OUT_DIR, re.sub(r'[^a-z0-9]+', '-', t['key']) + '.json')
        if os.path.exists(out) and not args.refresh:
            continue
        host = urllib.parse.urlsplit(t['website']).hostname
        print(f'{t["name"]} -> {apex(host)}', flush=True)
        docs = harvest(host)
        kinds = collections.Counter(d['type'] for d in docs if not d['noise'])
        json.dump({'key': t['key'], 'name': t['name'], 'host': apex(host),
                   'harvested_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                   'docs': docs, 'doc_types': dict(kinds)},
                  open(out, 'w'), ensure_ascii=False, indent=1)
        print(f'  {len(docs)} files in the Wayback index, '
              f'{sum(1 for d in docs if not d["noise"])} after noise filter, '
              f'types {dict(kinds.most_common(6))}', flush=True)


if __name__ == '__main__':
    main()
