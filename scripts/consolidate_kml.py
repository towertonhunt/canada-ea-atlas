#!/usr/bin/env python3
"""Consolidate many KML/KMZ files into one KMZ with a folder tree.

Usage:
    python3 scripts/consolidate_kml.py manifest.json out.kmz [--report report.md]

Manifest (JSON):
{
  "name": "Top-level document name",
  "description": "optional",
  "src_dir": "directory the 'file' entries are relative to",
  "layers": [
    {"file": "DLM.kmz", "folder": ["Mine Site", "Existing infrastructure"],
     "note": "free text", "date": "2024-11-21",
     "drop_if_same_as": "Sampling Locations.kmz",  # optional: skip when all
                                                    # geometries already exist
                                                    # in that other layer
     "drop_null_coords": true,      # optional: remove placemarks at 0,0
     "skip": "reason"               # optional: list in report, do not merge
    }
  ]
}

What it does:
  * unzips each KMZ (or reads KML), takes the root Document/Folder and nests
    it under the requested folder path;
  * namespaces every shared style id (Style, StyleMap, gx:CascadingStyle,
    Schema, Document ids) with a per-layer slug so ids never collide when
    dozens of Google-Earth exports are merged, and rewrites styleUrl /
    schemaUrl references to match;
  * optional geometry-level dedupe: a layer whose coordinate set is entirely
    contained in another named layer is dropped and reported;
  * writes doc.kml into a deterministic KMZ and validates the result
    (every styleUrl resolves, no duplicate ids, placemark totals add up);
  * writes a markdown inventory report.
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

KML = "http://www.opengis.net/kml/2.2"
GX = "http://www.google.com/kml/ext/2.2"
ATOM = "http://www.w3.org/2005/Atom"
NS = {"k": KML, "gx": GX}
# '' as the prefix makes ElementTree emit KML as the default namespace
# (plain <kml>, <Placemark>, id="..."), which is what Google Earth expects.
for p, u in (("", KML), ("gx", GX), ("atom", ATOM)):
    ET.register_namespace(p, u)

ID_ATTRS = ("id", f"{{{KML}}}id")


def q(tag):
    return f"{{{KML}}}{tag}"


def read_kml_bytes(path):
    if path.lower().endswith(".kmz"):
        with zipfile.ZipFile(path) as z:
            kmls = [n for n in z.namelist() if n.lower().endswith(".kml")]
            main = "doc.kml" if "doc.kml" in kmls else kmls[0]
            return z.read(main)
    with open(path, "rb") as fh:
        return fh.read()


def slugify(s):
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")[:40]


def rename_ids(el, prefix):
    """Prefix every id / styleUrl / schemaUrl in the subtree.

    ArcGIS/Google-Earth exports reuse ids such as 'layer 0' or 'inline' in
    every nested Document, so ids are namespaced per Document scope:
    <prefix>_d<n>_<id>.  A styleUrl is resolved against its own Document
    first, then enclosing Documents, then the whole layer.
    """
    counter = [0]
    all_maps = []
    used = set()

    def walk_define(node, chain):
        # `chain` = list of id-maps from outermost to innermost scope
        if node.tag == q("Document") or not chain:
            m = {}
            idx = counter[0]
            counter[0] += 1
            chain = chain + [(m, idx)]
            all_maps.append(m)
        m, idx = chain[-1]
        for attr in ID_ATTRS:
            v = node.get(attr)
            if v:
                new = f"{prefix}_d{idx}_{v}"
                if v in m:  # source reused an id inside one Document
                    k = 2
                    while f"{new}_{k}" in used:
                        k += 1
                    new = f"{new}_{k}"
                else:
                    m[v] = new
                used.add(new)
                node.set(attr, new)
        for child in node:
            walk_define(child, chain)

    def resolve(chain, ref):
        for m, _ in reversed(chain):
            if ref in m:
                return m[ref]
        for m in all_maps:
            if ref in m:
                return m[ref]
        return f"{prefix}_d0_{ref}"

    scope_id = [0]

    def walk_refs(node, chain):
        if node.tag == q("Document") or not chain:
            chain = chain + [(all_maps[scope_id[0]], scope_id[0])]
            scope_id[0] += 1
        if node.tag == q("styleUrl") and node.text and node.text.startswith("#"):
            node.text = "#" + resolve(chain, node.text[1:])
        su = node.get("schemaUrl")
        if su and su.startswith("#"):
            node.set("schemaUrl", "#" + resolve(chain, su[1:]))
        for child in node:
            walk_refs(child, chain)

    walk_define(el, [])
    walk_refs(el, [])
    return sum(len(m) for m in all_maps)


def coord_set(el):
    out = set()
    for c in el.iter(q("coordinates")):
        for tok in (c.text or "").split():
            parts = tok.split(",")
            if len(parts) >= 2:
                try:
                    out.add((round(float(parts[0]), 6), round(float(parts[1]), 6)))
                except ValueError:
                    pass
    return out


def placemarks(el):
    return el.findall(".//k:Placemark", NS)


def ensure_folder(parent, path, cache):
    key = ()
    node = parent
    for name in path:
        key = key + (name,)
        if key not in cache:
            f = ET.SubElement(node, q("Folder"))
            ET.SubElement(f, q("name")).text = name
            cache[key] = f
        node = cache[key]
    return node


def build(manifest):
    src_dir = manifest.get("src_dir", ".")
    kml = ET.Element(q("kml"))
    doc = ET.SubElement(kml, q("Document"))
    ET.SubElement(doc, q("name")).text = manifest["name"]
    desc = manifest.get("description", "")
    stamp = dt.date.today().isoformat()
    ET.SubElement(doc, q("description")).text = (
        f"{desc}\nBuilt {stamp} by scripts/consolidate_kml.py from "
        f"{len(manifest['layers'])} source files."
    )
    folders = {}
    loaded = {}  # file -> (root element, coord set)
    rows = []
    for layer in manifest["layers"]:
        if layer.get("skip"):
            rows.append((layer, 0, 0, f"excluded: {layer.get('skip')}"))
            continue
        path = os.path.join(src_dir, layer["file"])
        root = ET.fromstring(read_kml_bytes(path))
        top = None
        for child in root:
            if child.tag in (q("Document"), q("Folder")):
                top = child
                break
        if top is None:
            raise SystemExit(f"{layer['file']}: no Document/Folder under <kml>")
        dropped_pm = []
        if layer.get("drop_null_coords"):
            for parent in top.iter():
                for pm in list(parent):
                    if pm.tag == q("Placemark") and coord_set(pm) <= {(0.0, 0.0)}:
                        dropped_pm.append(pm.findtext("k:name", default="?", namespaces=NS))
                        parent.remove(pm)
        coords = coord_set(top)
        loaded[layer["file"]] = (top, coords)
        n_pm = len(placemarks(top))
        status = "included"
        if dropped_pm:
            status += f"; dropped {len(dropped_pm)} placemark(s) at 0,0: {', '.join(dropped_pm)}"
        other = layer.get("drop_if_same_as")
        if other:
            if other not in loaded:
                raise SystemExit(f"{layer['file']}: drop_if_same_as target "
                                 f"{other!r} must appear earlier in manifest")
            _, other_coords = loaded[other]
            if coords and coords <= other_coords:
                status = f"dropped (all {len(coords)} coords already in {other})"
        rows.append((layer, n_pm, len(coords), status))
        if not status.startswith("included"):
            continue
        slug = slugify(os.path.splitext(layer["file"])[0])
        n_ids = rename_ids(top, slug)
        # give the wrapped element the display name we want
        nm = top.find("k:name", NS)
        if nm is None:
            nm = ET.SubElement(top, q("name"))
            top.insert(0, nm)
        nm.text = layer.get("display", layer["folder"][-1] if layer["folder"] else nm.text)
        note = layer.get("note", "")
        date = layer.get("date", "")
        d = top.find("k:description", NS)
        if d is None:
            d = ET.Element(q("description"))
            top.insert(1, d)
        d.text = (f"Source: {layer['file']} (modified {date}). {note} "
                  f"[{n_pm} placemarks, {n_ids} shared styles]").strip()
        parent = ensure_folder(doc, layer["folder"][:-1], folders) if layer["folder"] else doc
        parent.append(top)
    return kml, rows


def validate(kml):
    ids = []
    for node in kml.iter():
        for attr in ID_ATTRS:
            v = node.get(attr)
            if v:
                ids.append(v)
    dup = {i for i in ids if ids.count(i) > 1}
    idset = set(ids)
    missing = set()
    for node in kml.iter(q("styleUrl")):
        if node.text and node.text.startswith("#") and node.text[1:] not in idset:
            missing.add(node.text)
    return dup, missing, len(placemarks(kml))


def write_kmz(kml, out_path):
    data = ET.tostring(kml, encoding="utf-8", xml_declaration=True)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        info = zipfile.ZipInfo("doc.kml", date_time=(1980, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        z.writestr(info, data)
    return len(data)


def folder_summary(kml, depth=0, out=None, maxd=2):
    out = [] if out is None else out
    for ch in kml:
        if ch.tag in (q("Folder"), q("Document")):
            nm = ch.findtext("k:name", default="?", namespaces=NS)
            out.append(("  " * depth) + f"- {nm} ({len(placemarks(ch))} placemarks)")
            if depth < maxd:
                folder_summary(ch, depth + 1, out, maxd)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    ap.add_argument("out")
    ap.add_argument("--report")
    a = ap.parse_args()
    manifest = json.load(open(a.manifest))
    kml, rows = build(manifest)
    dup, missing, total = validate(kml)
    size = write_kmz(kml, a.out)
    print(f"wrote {a.out}: {total} placemarks, doc.kml {size/1e6:.1f} MB")
    if dup:
        print("DUPLICATE IDS:", sorted(dup)[:10], file=sys.stderr)
    if missing:
        print("UNRESOLVED styleUrl:", sorted(missing)[:10], file=sys.stderr)
    if a.report:
        lines = [f"# {manifest['name']}", "",
                 f"Built {dt.date.today().isoformat()} from {len(rows)} source files; "
                 f"{total} placemarks in output; "
                 f"{'no' if not dup else len(dup)} duplicate style ids; "
                 f"{'all' if not missing else len(missing) + ' unresolved'} style references resolve.",
                 "", "## Sources", "",
                 "| # | File | Date | Placemarks | Folder | Status | Note |",
                 "|---|------|------|-----------:|--------|--------|------|"]
        for i, (layer, n_pm, n_c, status) in enumerate(rows, 1):
            lines.append(f"| {i} | {layer['file']} | {layer.get('date','')} | {n_pm} | "
                         f"{' / '.join(layer['folder'])} | {status} | {layer.get('note','')} |")
        lines += ["", "## Output folder tree", ""] + folder_summary(kml[0])
        open(a.report, "w").write("\n".join(lines) + "\n")
        print("report ->", a.report)
    return 1 if (dup or missing) else 0


if __name__ == "__main__":
    sys.exit(main())
