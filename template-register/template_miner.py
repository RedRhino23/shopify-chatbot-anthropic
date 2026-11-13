#!/usr/bin/env python3
"""Mine draft templates from the drawing collection (2D borders and title blocks).

    python template_miner.py DXF_FOLDER --out MINED [--manifest drawings.csv] [--min-count 3] [--threshold 0.9]
                             [--register ROOT --rev-owner client --projection first]

How it works
1. Every DXF is reduced to its sheet border (the largest rectangle that fits a sheet size) and the title block region
   (bottom-right of the border). Positions are measured from the border corner, so drawings in different places line up.
2. Drawings of one client with the same sheet and border size, and alike title block line work (--similarity), form a cluster (one cluster = one candidate template).
3. For each cluster, only what is shared survives: entities present at the same place in at least --threshold of the drawings.
   Text that sits in the same place but changes (job no., title, date, revision) becomes a field (ATTDEF) in the draft.
4. Writes MINED/clusters.json (report), MINED/drafts/<cluster>.dxf (the draft template) and, with --register, adds each
   as a DRAFT to the template register. Nothing is approved here; a person approves.

--manifest is a CSV export from the drawing database: columns path (or file), client, drawing_no, rev. Without it the client is
the name of the drawing's parent folder. Only DXF is read. For DWG, convert first (AutoCAD, Open CAD Studio --export, or ODA File
Converter) and point this at the DXF folder. Outputs carry client data: keep MINED on the NAS, not in git.
"""
import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import ezdxf

SIZES = {"A4": (297, 210), "A3": (420, 297), "A2": (594, 420), "A1": (841, 594), "A0": (1189, 841)}
R = 0.5  # rounding, mm


def rd(v):
    return round(v / R) * R


def rects(msp):
    out = []
    for e in msp:
        if e.dxftype() == "LWPOLYLINE":
            pts = [(p[0], p[1]) for p in e.get_points("xy")]
            if len(pts) >= 4 and (e.closed or (len(pts) == 5 and pts[0] == pts[-1])):
                xs, ys = [p[0] for p in pts], [p[1] for p in pts]
                x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
                if all((abs(p[0] - x0) < 0.01 or abs(p[0] - x1) < 0.01) and (abs(p[1] - y0) < 0.01 or abs(p[1] - y1) < 0.01) for p in pts):
                    out.append((x0, y0, x1, y1))
    return out


def find_border(msp):
    best = None
    for x0, y0, x1, y1 in rects(msp):
        w, h = x1 - x0, y1 - y0
        L, S = max(w, h), min(w, h)
        for k, (a, b) in SIZES.items():
            if a * 0.85 <= L <= a * 1.02 and b * 0.85 <= S <= b * 1.02:
                if best is None or w * h > best[2] * best[3]:
                    best = (x0, y0, w, h, k)
    return best


def entities(msp, ox, oy):
    """Keyed entities relative to the border corner. key = what it is and where; text carries its string separately."""
    out = []
    for e in msp:
        t = e.dxftype()
        try:
            if t == "LINE":
                a, b = e.dxf.start, e.dxf.end
                p = sorted([(rd(a.x - ox), rd(a.y - oy)), (rd(b.x - ox), rd(b.y - oy))])
                out.append((("LINE", e.dxf.layer, tuple(p)), None))
            elif t == "LWPOLYLINE":
                pts = tuple((rd(p[0] - ox), rd(p[1] - oy)) for p in e.get_points("xy"))
                out.append((("POLY", e.dxf.layer, pts, bool(e.closed)), None))
            elif t in ("ARC", "CIRCLE"):
                c = e.dxf.center
                out.append(((t, e.dxf.layer, rd(c.x - ox), rd(c.y - oy), rd(e.dxf.radius)), None))
            elif t == "TEXT":
                p = e.dxf.insert
                out.append((("TEXT", e.dxf.layer, rd(p.x - ox), rd(p.y - oy), round(e.dxf.height, 1)), e.dxf.text.strip()))
            elif t == "MTEXT":
                p = e.dxf.insert
                out.append((("MTEXT", e.dxf.layer, rd(p.x - ox), rd(p.y - oy), round(e.dxf.char_height, 1)), e.plain_text().strip()))
            elif t == "INSERT":
                p = e.dxf.insert
                out.append((("INSERT", e.dxf.layer, e.dxf.name, rd(p.x - ox), rd(p.y - oy)), None))
        except Exception:
            pass
    return out


def in_title_region(key, w, h):
    """Bottom-right of the border: right 45 percent, bottom 35 percent."""
    def pts():
        if key[0] == "LINE":
            return list(key[2])
        if key[0] == "POLY":
            return list(key[2])
        if key[0] in ("TEXT", "MTEXT"):
            return [(key[2], key[3])]
        if key[0] == "INSERT":
            return [(key[3], key[4])]
        return [(key[2], key[3])]
    return all(x >= w * 0.55 and y <= h * 0.35 for x, y in pts())


def region_lines(ents, border):
    """Set of title block line work: lines and polylines in the bottom-right region."""
    x0, y0, w, h, sheet = border
    return frozenset(k for k, _ in ents if k[0] in ("LINE", "POLY") and in_title_region(k, w, h))


def jaccard(a, b):
    return len(a & b) / len(a | b) if a | b else 1.0


def load_manifest(p):
    m = {}
    if p:
        for r in csv.DictReader(open(p, encoding="utf-8-sig")):
            path = r.get("path") or r.get("file") or ""
            m[Path(path).name.lower()] = r
    return m


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder"); ap.add_argument("--out", required=True); ap.add_argument("--manifest")
    ap.add_argument("--min-count", type=int, default=3, help="smallest cluster that becomes a draft")
    ap.add_argument("--threshold", type=float, default=0.9, help="share of drawings an entity must appear in to count as shared")
    ap.add_argument("--similarity", type=float, default=0.8, help="title block line work must overlap this much (Jaccard) to be one template")
    ap.add_argument("--register"); ap.add_argument("--rev-owner", choices=["client", "afj"]); ap.add_argument("--projection", choices=["first", "third"])
    a = ap.parse_args()
    man = load_manifest(a.manifest)
    out = Path(a.out); (out / "drafts").mkdir(parents=True, exist_ok=True)
    clusters = {}; groups = defaultdict(list); skipped = []
    files = sorted(Path(a.folder).rglob("*.dxf"))
    for f in files:
        try:
            doc = ezdxf.readfile(f)
        except Exception as e:
            skipped.append((str(f), f"unreadable: {e}")); continue
        msp = doc.modelspace()
        b = find_border(msp)
        if not b:
            skipped.append((str(f), "no sheet-sized border rectangle found")); continue
        ents = entities(msp, b[0], b[1])
        client = (man.get(f.name.lower(), {}).get("client") or f.parent.name).upper()
        groups[(client, b[4], rd(b[2]), rd(b[3]))].append({"file": str(f), "border": b, "ents": ents, "client": client, "region": region_lines(ents, b)})
    # within a client + sheet + border size, join drawings whose title block line work is alike (a stray drawing line does not split them)
    for (client, sheet, bw, bh), members in groups.items():
        freq = Counter(k for m in members for k in m["region"])
        keep = {k for k, c in freq.items() if c >= max(2, 0.3 * len(members))}   # structure: lines many drawings share; stray drawing lines drop out
        for m in members:
            m["core"] = m["region"] & keep
        cl = []
        for m in members:
            for c in cl:
                if jaccard(m["core"], c[0]["core"]) >= a.similarity:
                    c.append(m); break
            else:
                cl.append([m])
        for i, c in enumerate(cl, 1):
            clusters[(client, f"{sheet}-{i:02d}")] = c
    report = []
    for (client, sig), members in sorted(clusters.items(), key=lambda kv: -len(kv[1])):
        n = len(members)
        cid = f"{client}-{sig}"
        row = {"cluster": cid, "client": client, "sheet": members[0]["border"][4], "drawings": n, "examples": [m["file"] for m in members[:3]], "draft": None, "fields": [], "shared_entities": 0}
        if n >= a.min_count:
            cnt = Counter(); texts = defaultdict(list)
            for m in members:
                seen = set()
                for k, s in m["ents"]:
                    if k[0] in ("TEXT", "MTEXT"):
                        texts[k].append(s)
                    if k not in seen:
                        seen.add(k); cnt[k] += 1
            need = a.threshold * n
            shared = [k for k, c in cnt.items() if c >= need]
            d = ezdxf.new("R2010"); m2 = d.modelspace(); ox = oy = 0.0; blk = d.blocks.new("TITLE_FIELDS"); fields = []
            for k in shared:
                kind = k[0]
                if kind in ("TEXT", "MTEXT"):
                    vals = Counter(texts[k])
                    if len(vals) > 1 and vals.most_common(1)[0][1] < need:   # same place, changing value: a field
                        tag = f"FIELD_{len(fields) + 1}"
                        blk.add_attdef(tag, (k[2], k[3]), dxfattribs={"height": k[4], "layer": k[1]})
                        fields.append({"tag": tag, "x": k[2], "y": k[3], "height": k[4], "examples": [v for v, _ in vals.most_common(3)]})
                    else:
                        m2.add_text(vals.most_common(1)[0][0], height=k[4], dxfattribs={"layer": k[1]}).set_placement((k[2], k[3]))
                elif kind == "LINE":
                    m2.add_line(k[2][0], k[2][1], dxfattribs={"layer": k[1]})
                elif kind == "POLY":
                    m2.add_lwpolyline(list(k[2]), close=k[3], dxfattribs={"layer": k[1]})
                elif kind in ("ARC", "CIRCLE"):
                    pass  # arcs lose angles in the key; left out of drafts, shown for review in the report
            if fields:
                m2.add_blockref("TITLE_FIELDS", (0, 0))
            draft = out / "drafts" / f"{cid}.dxf"
            d.saveas(draft)
            row.update(draft=str(draft), fields=fields, shared_entities=len(shared))
            if a.register:
                if not (a.rev_owner and a.projection):
                    sys.exit("--register needs --rev-owner and --projection")
                import subprocess
                subprocess.run([sys.executable, str(Path(__file__).with_name("template_register.py")), "--root", a.register, "add", str(draft), "--client", client,
                                "--name", f"mined {cid}", "--projection", a.projection, "--rev-owner", a.rev_owner, "--sheet", row["sheet"],
                                "--source", f"mined from {n} drawings"], check=True)
        report.append(row)
    json.dump({"drawings_read": len(files), "skipped": skipped, "clusters": report}, open(out / "clusters.json", "w", encoding="utf-8"), indent=1)
    print(f"{len(files)} DXF read, {sum(r['drawings'] for r in report)} clustered, {len(skipped)} skipped, {len(report)} cluster(s)")
    for r in report:
        print(f"  {r['cluster']:<34} {r['drawings']:>4} drawings  fields {len(r['fields'])}  " + ("DRAFT written" if r["draft"] else f"under --min-count {a.min_count}, no draft"))
    for s, why in skipped[:10]:
        print(f"  skipped {s}: {why}")


if __name__ == "__main__":
    main()
