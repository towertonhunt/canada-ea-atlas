#!/usr/bin/env python3
"""Harvest Ontario's provincial EA project pages on ontario.ca.

The category listing gives us only a name and a URL, which is why Ontario
projects had no proponent, no status, no coordinates and no documents. Each
project page carries all four: a definition-list style body (Proponent /
Location / Type / Reference number), a "Project history" block of decision
dates, and a "Project documentation" sidebar linking the notices of approval,
ministry review and terms of reference -- the actual EA record.

  python3 scripts/fetch_on_ea_pages.py            # full refresh
  python3 scripts/fetch_on_ea_pages.py --limit 5  # smoke test

Writes data/raw/on_ea_project_pages.json, consumed by
build_national_geojson.py and split_doc_catalogues.py.
"""
import argparse
import concurrent.futures as cf
import html as htmllib
import json
import os
import re
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, 'data', 'raw')
OUT = os.path.join(RAW, 'on_ea_project_pages.json')
BASE = 'https://www.ontario.ca'
INDEX = BASE + '/page/environmental-assessment-projects-category'
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120.0 Safari/537.36')
SECTIONS = ['Electricity', 'Mining', 'Forestry', 'Municipal infrastructure',
            'Waste management', 'Transit', 'Transportation', 'Other']


def get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=45) as r:
                return r.read().decode('utf-8', 'replace')
        except Exception:                                    # noqa: BLE001
            if i == tries - 1:
                raise
            time.sleep(2 * (i + 1))


def text(frag):
    frag = re.sub(r'<br\s*/?>|</p>|</li>|</h[1-6]>', '\n', frag)
    frag = re.sub(r'<[^>]+>', '', frag)
    return re.sub(r'[ \t]+', ' ',
                  htmllib.unescape(frag).replace('\xa0', ' ')).strip()


def parse_index(h):
    """-> [(sector, name, url)] from the by-category listing."""
    out = []
    for part in re.split(r'<h2[^>]*>', h):
        m = re.match(r'\s*([^<]+)</h2>(.*)', part, re.S)
        if not m or m.group(1).strip() not in SECTIONS:
            continue
        sector = m.group(1).strip()
        for u, t in re.findall(r'<a href="([^"]+)"[^>]*>(.*?)</a>', m.group(2), re.S):
            name = text(t)
            if (not name or 'back to top' in name.lower()
                    or name.lower().startswith(
                        ('guide', 'environmental assessment requirement'))):
                continue
            out.append((sector, name, BASE + u if u.startswith('/') else u))
    return out


# "Approximately 185 kilometres northeast of Cochrane" -> Cochrane; the
# gazetteer pass in build_national_geojson.py geocodes off this.
_LOC_TAIL = re.compile(
    r'\b(?:of|near|in|at|adjacent to|outside|within)\s+'
    r'(?:the\s+)?((?:[A-Z][\w.\'’-]*)(?:[ -](?:of|the|de|St\.?|Ste\.?)?[ ]?'
    r'[A-Z][\w.\'’-]*){0,3})\s*[,.]?\s*$')


def municipality(loc):
    """Best single place name in a free-text Location, or None.

    Wrong beats missing here: the gazetteer pass turns this into a map pin,
    so a corridor like "Kincardine to Milton" resolves to its first endpoint
    and anything ambiguous returns None rather than guessing.
    """
    if not loc:
        return None
    first = re.sub(r'\([^)]*\)', ' ', loc)              # drop parentheticals
    first = re.split(r'[;\n]', first)[0]
    first = re.sub(r'^\s*(?:between|from|along|near|within)\s+', '', first,
                   flags=re.I)
    # corridors and pairs: take the first endpoint
    first = re.split(r'\s+(?:to|and|&)\s+', first)[0].strip().rstrip('.,')
    m = _LOC_TAIL.search(first)
    cand = (m.group(1) if m else first).strip()
    cand = re.sub(r'^(?:the\s+)?(?:City|Town|Township|Municipality|County|'
                  r'Region(?:al Municipality)?|District|Village)\s+of\s+', '',
                  cand, flags=re.I).strip(" .,'’-")
    if not cand or len(cand) < 3 or len(cand.split()) > 3:
        return None
    return cand if re.match(r"^[A-Z][A-Za-zÀ-ÿ.'’ -]+$", cand) else None


def parse_page(h, url):
    main = re.search(r'<main.*?</main>', h, re.S)
    main = main.group(0) if main else h
    body = re.search(r'<div class="body-field">(.*?)</div>\s*</div>', main, re.S)
    body = body.group(1) if body else main

    rec = {'url': url}

    st = re.search(r'<h2[^>]*>\s*Current status\s*</h2>(.*?)(?=<h2|</div>)', main, re.S)
    if st:
        # keep the status sentence; drop the "Get details on..." call to action
        lines = [l for l in text(st.group(1)).split('\n') if l.strip()]
        if lines:
            rec['status'] = lines[0].strip()

    # <h3>Field</h3><p>value</p> pairs
    for label, key in (('Proponent', 'proponent'), ('Location', 'location'),
                       ('Type', 'ea_sector'), ('Reference number', 'reference_number')):
        m = re.search(rf'<h[23][^>]*>\s*{label}\s*</h[23]>\s*(<p>.*?</p>)', body, re.S)
        if m:
            v = text(m.group(1))
            if v:
                rec[key] = v
    rec['municipality'] = municipality(rec.get('location'))

    hist = re.search(r'<h2[^>]*>\s*Project history\s*</h2>(.*?)(?=<h2|\Z)', body, re.S)
    if hist:
        lines = [l.strip() for l in text(hist.group(1)).split('\n') if l.strip()]
        rec['history'] = lines[:40]
        for l in lines:
            m = re.match(r'Decision date:\s*(.+)', l)
            if m and 'decision_date' not in rec:
                rec['decision_date'] = m.group(1).strip()

    # "Project documentation" sidebar -- the actual EA record
    docs, seen = [], set()
    aside = re.search(r'<aside[^>]*sidebar[^>]*>(.*?)</aside>', main, re.S)
    for u, t in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
                           aside.group(1) if aside else '', re.S):
        title = text(t)
        if not title or u.startswith(('#', 'tel:', 'mailto:')):
            continue
        full = BASE + u if u.startswith('/') else u
        if full in seen:
            continue
        seen.add(full)
        docs.append({'title': title, 'url': full})
    rec['docs'] = docs

    ext = [u for u in re.findall(r'<a[^>]+href="(https?://[^"]+)"', body)
           if 'ontario.ca' not in u and 'signin.ontario' not in u]
    if ext:
        rec['proponent_url'] = ext[0]

    upd = re.search(r'Updated:\s*([^<]+)<', main)
    if upd:
        rec['page_updated'] = upd.group(1).strip()
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int)
    ap.add_argument('--workers', type=int, default=5)
    args = ap.parse_args()

    index_html = get(INDEX)
    open(os.path.join(RAW, 'on_ea_projects_category.html'), 'w',
         encoding='utf-8').write(index_html)
    entries = parse_index(index_html)
    # a project can be listed under more than one sector; keep the first
    uniq = {}
    for sector, name, url in entries:
        uniq.setdefault(url, (sector, name, url))
    todo = list(uniq.values())[:args.limit] if args.limit else list(uniq.values())
    print(f'{len(todo)} project pages', flush=True)

    out, fails = [], []

    def one(t):
        sector, name, url = t
        try:
            rec = parse_page(get(url), url)
        except Exception as e:                               # noqa: BLE001
            fails.append((url, str(e)[:80]))
            return None
        rec['name'], rec['sector'] = name, sector
        rec['slug'] = url.rstrip('/').rsplit('/', 1)[-1]
        time.sleep(0.3)
        return rec

    with cf.ThreadPoolExecutor(args.workers) as ex:
        for i, rec in enumerate(ex.map(one, todo), 1):
            if rec:
                out.append(rec)
            if i % 25 == 0:
                print(f'  {i}/{len(todo)}', flush=True)

    json.dump(out, open(OUT, 'w'), ensure_ascii=False, indent=1)
    have = lambda k: sum(1 for r in out if r.get(k))
    print(f'\n{len(out)} pages -> {OUT}  ({len(fails)} failed)')
    print(f'  proponent {have("proponent")}  status {have("status")}  '
          f'location {have("location")}  municipality {have("municipality")}  '
          f'docs {sum(len(r["docs"]) for r in out)} across {have("docs")} projects')
    for u, e in fails[:10]:
        print('  FAIL', u, e)


if __name__ == '__main__':
    main()
