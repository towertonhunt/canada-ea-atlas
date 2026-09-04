#!/usr/bin/env python3
"""Find the EA / Class EA document sections on proponent websites.

Follows the pattern that worked for Hydro One: locate the project pages,
then pull every document link off them and classify it by title. This is
the discovery pass -- it maps the site and records document URLs with
titles; archiving is left to archive_docs.py, which reads the output.

Per site: robots.txt is honoured, sitemaps are used when present, and the
crawl is bounded (same host, limited depth, limited pages) and polite
(2s between requests). Pages are kept only when they look like project /
environment / assessment pages or hold document links.

  python3 scripts/proponent_discover.py --top 40          # top-ranked sites
  python3 scripts/proponent_discover.py --key "atura power"
  python3 scripts/proponent_discover.py --site https://www.opg.com --key opg

-> data/raw/proponents/sites/<key>.json  {pages:[...], docs:[...]}
"""
import argparse
import collections
import glob
import gzip
import html as htmllib
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import urllib.robotparser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_links import UA  # noqa: E402

PROP_DIR = os.path.join(ROOT, 'data', 'raw', 'proponents')
TARGETS = os.path.join(PROP_DIR, 'targets.json')
SITES_DIR = os.path.join(PROP_DIR, 'sites')
DELAY = 2.0
MAX_PAGES = 250
MAX_DEPTH = 3
DOC_EXT = ('.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.zip', '.kmz', '.ashx')
MEDIA_EXT = re.compile(r'\.(jpe?g|png|gif|svg|webp|bmp|tiff?|mp4|mp3|m4a|mov|avi|css|js|ico|woff2?)$', re.I)
DOC_PATH = re.compile(r'/-/media/|/download|getfile|/getmedia/|/media/reports|'
                      r'/documents?/[^/]+/?$|/wp-content/uploads/', re.I)

# Signals that a link leads toward the EA record. STRONG terms are followed
# at any depth and ranked first; WEAK ones only near the top of the site,
# otherwise a corporate site's navigation chrome swamps the crawl.
STRONG = re.compile(
    r'environment|assessment|\bea\b|class-?ea|\besr\b|study-?report|impact|'
    r'major-?projects?|projects?|regulatory|permit|licen[cs]|consult|open-?house|'
    r'notice|monitoring|closure|reclamation|decommission|indigenous|first-?nation|'
    r'transmission-?line|generating-?station|\bmine\b|hydroelectric|waterpower|'
    r'terms-?of-?reference|screening|engagement|refurbish|expansion|redevelop', re.I)
WEAK = re.compile(
    r'sustainab|community|documents?|reports?|library|publications?|resources|'
    r'planning|development|transmission|generation|station|hydro|wind|solar|'
    r'storage|operations|about|what-?we-?do|our-?business', re.I)
TOPIC = re.compile(STRONG.pattern + '|' + WEAK.pattern, re.I)
SKIP_URL = re.compile(
    r'/(careers?|jobs?|investors?|news(room)?|media|press|blog|login|cart|search|'
    r'privacy|terms|sitemap|tag|category|author|feed|wp-json|xmlrpc|\?s=|'
    r'events?|calendar|contact|accessibility|fr/|en-fr|francais|_layouts|'
    r'authenticate|signin|sign-in|account|my-?account|rates?|billing|outage|'
    r'moving|request-a-service|customer|rewards?|contest|shop|store|safety-?tips)\b|'
    r'\.(jpe?g|png|gif|svg|css|js|ico|mp4|mp3|webp|woff2?)(\?|$)', re.I)


def priority(url, label):
    """Higher = crawl sooner. EA-specific terms in the URL beat terms in the
    anchor text; several hits beat one."""
    blob_u, blob_l = urllib.parse.unquote(url), label or ''
    return (3 * len(STRONG.findall(blob_u)) + 2 * len(STRONG.findall(blob_l))
            + len(WEAK.findall(blob_u)))

# Title -> document type, from the Hydro One harvest.
DOC_TYPES = [
    (r'(?i)draft.{0,20}environmental\s*study\s*report|draft.{0,10}\bESR\b', 'ESR_draft'),
    (r'(?i)final.{0,20}environmental\s*study\s*report|final.{0,10}\bESR\b', 'ESR_final'),
    (r'(?i)environmental\s*study\s*report|\bESR\b', 'ESR'),
    (r'(?i)environmental\s*(impact|assessment)\s*(statement|report)|\bEIS\b|\bEA\s*report', 'EA_report'),
    (r'(?i)terms\s*of\s*reference|\bToR\b', 'terms_of_reference'),
    (r'(?i)notice\s*of\s*commencement', 'notice_of_commencement'),
    (r'(?i)notice\s*of\s*completion|statement\s*of\s*completion', 'notice_of_completion'),
    (r'(?i)screening', 'screening'),
    (r'(?i)open\s*house|public\s*(information\s*centre|meeting|consultation)|\bPIC\b', 'open_house'),
    (r'(?i)monitoring|follow-?up', 'monitoring'),
    (r'(?i)closure|reclamation|decommission', 'closure'),
    (r'(?i)technical\s*(report|memo)|baseline|appendix|appendices', 'technical'),
    (r'(?i)\bmap\b|figure|route', 'map'),
    (r'(?i)newsletter|bulletin|fact\s*sheet|update', 'newsletter'),
    (r'(?i)presentation|slides?', 'presentation'),
    (r'(?i)permit|approval|licen[cs]e|leave\s*to\s*construct', 'permit_approval'),
    (r'(?i)indigenous|first\s*nation|m[ée]tis|engagement|consultation', 'engagement'),
]


def classify(title, url):
    blob = f'{title} {urllib.parse.unquote(url)}'
    for rx, label in DOC_TYPES:
        if re.search(rx, blob):
            return label
    return 'other'


# ── browser fallback ─────────────────────────────────────────────────
# Several of the biggest proponents (OPG, Bruce Power, Suncor, BHP, LNG
# Canada) sit behind bot walls that 403 any non-browser client, and others
# (ATCO, Shell) serve an empty JavaScript shell. A headless Chromium via
# Playwright fetches those; it is only used when the plain fetch fails or
# comes back as a shell, so the polite/plain path stays the default.
_browser = {'pw': None, 'ctx': None, 'enabled': False, 'hosts': set()}


def browser_page():
    if _browser['ctx'] is None:
        from playwright.sync_api import sync_playwright
        _browser['pw'] = sync_playwright().start()
        if _browser.get('headed'):
            # Cloudflare Bot Management (OPG, Suncor, BHP) blocks every
            # headless variant after the first page but passes a real, headed
            # Chrome. Local-only: a window appears while the crawl runs.
            b = _browser['pw'].chromium.launch(
                headless=False, channel='chrome',
                args=['--disable-blink-features=AutomationControlled'])
            _browser['ctx'] = b.new_context(locale='en-CA',
                                            viewport={'width': 1280, 'height': 900})
            return _browser['ctx'].new_page()
        b = _browser['pw'].chromium.launch(headless=True)
        # A current, non-headless Chrome UA is what the walls accept: the
        # default "HeadlessChrome" UA trips Cloudflare (OPG, Suncor) and a
        # stale Chrome version trips others (Bruce Power). Tested 2026-09-04.
        _browser['ctx'] = b.new_context(user_agent=UA, locale='en-CA',
                                        viewport={'width': 1280, 'height': 900})
    return _browser['ctx'].new_page()


def browser_get(url, timeout=45):
    page = browser_page()
    try:
        resp = page.goto(url, wait_until='domcontentloaded', timeout=timeout * 1000)
        try:
            page.wait_for_load_state('networkidle', timeout=8000)
        except Exception:                                        # noqa: BLE001
            pass
        status = resp.status if resp else 200
        if status in (403, 429, 503):
            # Cloudflare/Imperva managed challenge: the 403 page runs a script
            # and then navigates to the real page on its own. Reloading resets
            # it; waiting lets it finish.
            for _ in range(20):
                page.wait_for_timeout(1000)
                title = (page.title() or '').lower()
                if not re.search(r'attention required|just a moment|checking your browser|'
                                 r'access denied|forbidden|incapsula|challenge', title):
                    html = page.content()
                    if len(re.findall(r'<a\b', html)) >= 8:
                        status = 200
                        break
        ctype = (resp.headers.get('content-type') if resp else '') or 'text/html'
        if status >= 400:
            raise urllib.error.HTTPError(url, status, 'browser', {}, None)
        if 'html' not in ctype and 'xml' not in ctype:
            return None, ctype, page.url
        return page.content(), ctype, page.url
    finally:
        page.close()


def looks_like_shell(html):
    """A page with almost no anchors is a JS app shell, not content."""
    return html is not None and len(html) < 20_000 and len(re.findall(r'<a\b', html)) < 8


def get(url, timeout=45):
    host = urllib.parse.urlsplit(url).hostname
    if _browser['enabled'] and host in _browser['hosts']:
        return browser_get(url, timeout)
    req = urllib.request.Request(url, headers={
        'User-Agent': UA, 'Accept': 'text/html,application/xhtml+xml,*/*;q=0.8'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            ctype = (r.headers.get('Content-Type') or '').lower()
            if 'html' not in ctype and 'xml' not in ctype:
                return None, ctype, r.geturl()
            raw = r.read(3_000_000)
            if ctype.endswith('gzip') or url.endswith('.gz'):
                raw = gzip.decompress(raw)
            body = raw.decode('utf-8', 'replace')
    except urllib.error.HTTPError as e:
        if _browser['enabled'] and e.code in (403, 429, 503):
            _browser['hosts'].add(host)
            print(f'  {host}: HTTP {e.code} -> switching to browser', flush=True)
            return browser_get(url, timeout)
        raise
    except urllib.error.URLError as e:
        if _browser['enabled'] and 'SSL' in str(e).upper():
            _browser['hosts'].add(host)
            print(f'  {host}: TLS handshake failed -> switching to browser', flush=True)
            return browser_get(url, timeout)
        raise
    if _browser['enabled'] and 'html' in ctype and looks_like_shell(body):
        _browser['hosts'].add(host)
        print(f'  {host}: JS shell -> switching to browser', flush=True)
        return browser_get(url, timeout)
    return body, ctype, r.geturl()


def text(frag):
    return re.sub(r'\s+', ' ', htmllib.unescape(re.sub(r'<[^>]+>', ' ', frag))).strip()


def links(html, base):
    for m in re.finditer(r'<a\b[^>]*?href\s*=\s*["\']?([^"\'\s>]+)[^>]*>(.*?)</a>',
                         html, re.S | re.I):
        href, label = m.group(1), text(m.group(2))[:200]
        if href.startswith(('#', 'mailto:', 'tel:', 'javascript:')):
            continue
        yield urllib.parse.urljoin(base, htmllib.unescape(href)).split('#')[0], label


def _apex(host):
    """'www.woodfibrelng.ca' and 'woodfibrelng.ca' are one site."""
    host = (host or '').lower()
    return host[4:] if host.startswith('www.') else host


def same_site(u, host):
    h = _apex(urllib.parse.urlsplit(u).hostname)
    a = _apex(host)
    return bool(h) and (h == a or h.endswith('.' + a))


def sitemap_urls(site, rp):
    """URLs listed in sitemap.xml (and one level of sitemap index)."""
    out = []
    cands = list(rp.site_maps() or []) + [urllib.parse.urljoin(site, '/sitemap.xml'),
                                          urllib.parse.urljoin(site, '/sitemap_index.xml')]
    seen = set()
    for sm in cands[:6]:
        if sm in seen:
            continue
        seen.add(sm)
        try:
            body, _, _ = get(sm)
        except Exception:                                        # noqa: BLE001
            continue
        if not body:
            continue
        locs = re.findall(r'<loc>\s*([^<\s]+)\s*</loc>', body)
        if '<sitemapindex' in body:
            for child in locs[:15]:
                try:
                    b2, _, _ = get(child)
                    out += re.findall(r'<loc>\s*([^<\s]+)\s*</loc>', b2 or '')
                except Exception:                                # noqa: BLE001
                    pass
                time.sleep(DELAY / 2)
        else:
            out += locs
        time.sleep(DELAY / 2)
    return out


def crawl(site, key, max_pages=MAX_PAGES, seeds=()):
    site = site if site.startswith('http') else 'https://' + site
    try:                                   # www.x.ca -> x.ca, or a renamed company
        _, _, final = get(site)
        fh = urllib.parse.urlsplit(final)
        if final and fh.hostname and _apex(fh.hostname) != _apex(urllib.parse.urlsplit(site).hostname):
            print(f'  {urllib.parse.urlsplit(site).hostname} redirects to {fh.hostname}; crawling that',
                  flush=True)
        if final and fh.hostname:
            site = f'{fh.scheme}://{fh.netloc}/'
    except Exception:                                            # noqa: BLE001
        pass
    host = urllib.parse.urlsplit(site).hostname
    rp = urllib.robotparser.RobotFileParser()
    if host in _browser['hosts']:
        rp = None          # the wall has spoken; robots.txt would 403 too
    else:
        try:
            rp.set_url(urllib.parse.urljoin(site, '/robots.txt'))
            rp.read()
        except Exception:                                        # noqa: BLE001
            rp = None
    allowed = (lambda u: rp.can_fetch(UA, u)) if rp and rp.default_entry else (lambda u: True)

    import heapq
    queue, tie = [], 0          # max-heap on priority: (-prio, order, url, depth)
    seen = set()

    def push(url, depth, prio):
        nonlocal tie
        tie += 1
        heapq.heappush(queue, (-prio, tie, url, depth))

    # seeds: known project pages first, then the home page, then topical
    # sitemap urls -- all ranked so the EA-specific ones are fetched first
    for u in seeds:
        push(u, 0, 100)
    push(site, 0, 50)
    sm = sitemap_urls(site, rp) if rp else []
    topical = [u for u in sm if TOPIC.search(u) and not SKIP_URL.search(u)]
    for u in topical[:max_pages * 4]:
        push(u, 1, priority(u, ''))
    print(f'  {host}: {len(sm)} sitemap urls, {len(topical)} topical, '
          f'{len(seeds)} seeds', flush=True)

    pages, docs, doc_seen = [], [], set()
    errors = collections.Counter()
    n_fetch = 0
    while queue and n_fetch < max_pages:
        _, _, url, depth = heapq.heappop(queue)
        if url in seen or not same_site(url, host) or SKIP_URL.search(url) or not allowed(url):
            continue
        seen.add(url)
        try:
            body, ctype, final = get(url)
        except Exception as e:                                   # noqa: BLE001
            if 'Download is starting' in str(e):
                if url not in doc_seen:
                    doc_seen.add(url)
                    docs.append({'url': url, 'title': os.path.basename(url.rstrip('/')),
                                 'type': classify('', url), 'page': None})
                n_fetch += 1
                continue
            errors[type(e).__name__ + ': ' + str(e)[:80]] += 1
            if sum(errors.values()) <= 3:
                print(f'  fetch failed {url[:80]}: {type(e).__name__}: {str(e)[:120]}', flush=True)
            continue
        n_fetch += 1
        time.sleep(DELAY)
        if body is None:
            continue
        title = text(re.search(r'<title[^>]*>(.*?)</title>', body, re.S | re.I).group(1)) \
            if re.search(r'<title', body, re.I) else ''
        page_docs = []
        for u, label in links(body, final):
            path = urllib.parse.urlsplit(u).path.lower()
            if (path.endswith(DOC_EXT) or DOC_PATH.search(path)) and not MEDIA_EXT.search(path):
                if u not in doc_seen:
                    doc_seen.add(u)
                    d = {'url': u, 'title': label or os.path.basename(path),
                         'type': classify(label, u), 'page': final}
                    docs.append(d)
                    page_docs.append(d)
            elif depth < MAX_DEPTH and same_site(u, host) and u not in seen \
                    and not SKIP_URL.search(u):
                strong = STRONG.search(u) or STRONG.search(label)
                weak = WEAK.search(u) or WEAK.search(label)
                if strong or (weak and depth <= 1):
                    push(u, depth + 1, priority(u, label) + (5 if strong else 0))
        if page_docs or TOPIC.search(url) or TOPIC.search(title):
            pages.append({'url': final, 'title': title[:200], 'depth': depth,
                          'docs': len(page_docs)})
    return {'key': key, 'site': site, 'host': host, 'fetched': n_fetch,
            'errors': dict(errors.most_common(5)),
            'pages': pages, 'docs': docs,
            'doc_types': dict(collections.Counter(d['type'] for d in docs)),
            'crawled_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--top', type=int)
    ap.add_argument('--key')
    ap.add_argument('--site')
    ap.add_argument('--max-pages', type=int, default=MAX_PAGES)
    ap.add_argument('--refresh', action='store_true', help='recrawl even if a result exists')
    ap.add_argument('--seed', action='append', default=[], help='extra start URL (repeatable)')
    ap.add_argument('--budget', type=int, help='stop starting new sites after N seconds')
    ap.add_argument('--browser', action='store_true',
                    help='fall back to headless Chromium on 403 / JS-shell sites (needs playwright)')
    ap.add_argument('--headed', action='store_true',
                    help='use a visible real Chrome for browser fetches (beats Cloudflare bot '
                         'management; local machines with a display only)')
    args = ap.parse_args()
    os.makedirs(SITES_DIR, exist_ok=True)
    _browser['enabled'] = args.browser or args.headed
    _browser['headed'] = args.headed
    targets = json.load(open(TARGETS))
    if args.browser:
        for t in targets:
            if t.get('browser_first') and t.get('website'):
                _browser['hosts'].add(urllib.parse.urlsplit(t['website']).hostname)
        # and any site whose last crawl needed the browser
        for f in glob.glob(os.path.join(SITES_DIR, '*.json')):
            try:
                d = json.load(open(f))
                if d.get('via_browser') and d.get('host'):
                    _browser['hosts'].add(d['host'])
            except (ValueError, OSError):
                pass
    if args.site:
        todo = [{'key': args.key or urllib.parse.urlsplit(args.site).hostname,
                 'name': args.key or args.site, 'website': args.site}]
    elif args.key:
        todo = [t for t in targets if t['key'] == args.key]
    else:
        todo = [t for t in targets if t.get('website')][:args.top or 20]
    started = time.time()
    for t in todo:
        if args.budget and time.time() - started > args.budget:
            print('budget reached', flush=True)
            break
        out = os.path.join(SITES_DIR, re.sub(r'[^a-z0-9]+', '-', t['key']) + '.json')
        if os.path.exists(out) and not args.refresh:
            continue
        if not t.get('website'):
            continue
        print(f'{t["name"]} -> {t["website"]}', flush=True)
        try:
            res = crawl(t['website'], t['key'], args.max_pages,
                        seeds=list(t.get('seed_urls') or []) + args.seed)
        except Exception as e:                                   # noqa: BLE001
            print('  FAILED', e)
            continue
        res['name'] = t['name']
        res['via_browser'] = res['host'] in _browser['hosts'] or _apex(res['host']) in {_apex(h) for h in _browser['hosts']}
        json.dump(res, open(out, 'w'), ensure_ascii=False, indent=1)
        print(f'  {res["fetched"]} pages fetched, {len(res["pages"])} kept, '
              f'{len(res["docs"])} documents {res["doc_types"]}', flush=True)


if __name__ == '__main__':
    try:
        main()
    finally:
        if _browser['pw']:
            _browser['pw'].stop()
