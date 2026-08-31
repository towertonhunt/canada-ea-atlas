#!/usr/bin/env python3
"""Build a SQLite FTS5 full-text index over the document corpus.

Reads data/corpus/<jur>/index.json + the gzipped text files it references,
and writes data/corpus_search.sqlite3.gz — a self-contained FTS5 database
the static wiki.html page loads in-browser (via sql.js) for full-text
search with ranked snippets. No server component.

Run after any corpus update: python3 scripts/build_corpus_search.py
"""
import gzip
import html
import io
import json
import os
import re
import sqlite3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(ROOT, 'data', 'corpus')
OUT = os.path.join(ROOT, 'data', 'corpus_search.sqlite3')

JURISDICTIONS = ('bc', 'federal', 'ontario')
JUR_LABEL = {'bc': 'British Columbia', 'federal': 'Federal',
             'ontario': 'Ontario'}

# nav/boilerplate that leads many scraped pages — trimmed so bm25 ranking
# and snippets aren't dominated by chrome. Light touch; FTS handles the rest.
NAV = re.compile(r'^.*?(?:Skip to main content|Passer au contenu principal)',
                 re.I | re.S)


def clean(text):
    text = NAV.sub('', text, count=1)
    text = html.unescape(text)
    return re.sub(r'\s+', ' ', text).strip()


def main():
    if os.path.exists(OUT):
        os.remove(OUT)
    db = sqlite3.connect(OUT)
    db.execute('PRAGMA page_size=4096')
    db.execute('PRAGMA journal_mode=OFF')
    # tokenize with unicode61 + porter stemming so "monitoring" matches
    # "monitor"; UNINDEXED columns are stored for retrieval but not searched
    db.execute("""
        CREATE VIRTUAL TABLE docs USING fts5(
            jurisdiction UNINDEXED, project, title, category UNINDEXED,
            url UNINDEXED, source_path UNINDEXED, body,
            tokenize = 'porter unicode61'
        )""")

    n = 0
    for jur in JURISDICTIONS:
        idx_path = os.path.join(CORPUS, jur, 'index.json')
        if not os.path.exists(idx_path):
            print(f'skip {jur}: no index.json')
            continue
        index = json.load(open(idx_path))
        for e in index:
            doc_id = e.get('doc_id')
            fpath = os.path.join(CORPUS, jur, f'{doc_id}.txt.gz')
            if not os.path.exists(fpath):
                continue
            try:
                body = clean(gzip.open(fpath, 'rt', errors='replace').read())
            except Exception as ex:
                print(f'read fail {fpath}: {ex}')
                continue
            if len(body) < 40:
                continue
            src = (f'https://iaac-aeic.gc.ca/050/evaluations/document/{doc_id}'
                   if jur == 'federal' else e.get('url'))
            db.execute(
                'INSERT INTO docs (jurisdiction, project, title, category, '
                'url, source_path, body) VALUES (?,?,?,?,?,?,?)',
                (JUR_LABEL[jur], e.get('project') or '', e.get('title') or '',
                 e.get('category') or '', src or '',
                 f'data/corpus/{jur}/{doc_id}.txt.gz', body))
            n += 1
    # compact the FTS index and the file
    db.execute("INSERT INTO docs(docs) VALUES('optimize')")
    db.commit()
    db.execute('VACUUM')
    db.commit()
    db.close()

    raw = open(OUT, 'rb').read()
    gz = gzip.compress(raw, mtime=0)
    open(OUT + '.gz', 'wb').write(gz)
    os.remove(OUT)   # ship only the gzipped DB; page inflates client-side
    print(f'{n} documents indexed')
    print(f'db {len(raw)/1e6:.1f} MB  ->  gz {len(gz)/1e6:.1f} MB  ->  '
          f'{OUT}.gz')


if __name__ == '__main__':
    main()
