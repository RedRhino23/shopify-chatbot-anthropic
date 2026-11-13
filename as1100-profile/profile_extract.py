#!/usr/bin/env python3
"""Step 0, part 1: read one or more DXF masters and record what they ACTUALLY do (layers, linetypes, text
styles and heights, dimension styles, sheet size, title block text). Describes only. It makes no claim about
AS 1100. Each observed item goes into the profile as status UNVERIFIED with an empty "clause" field.
A person fills "clause" from the copy of AS 1100 / HB 47 on file and sets status to CONFIRMED or REJECTED.

    python profile_extract.py master1.dxf master2.dxf --out profile_draft.json
"""
import argparse
import json
from collections import Counter, defaultdict

import ezdxf


def observe(path):
    doc = ezdxf.readfile(path)
    msp = doc.modelspace()
    o = {"file": path.replace("\\", "/").split("/")[-1], "units": doc.header.get("$INSUNITS"), "layers": {}, "linetypes": [], "text_styles": {},
         "dimstyles": {}, "text_heights": Counter(), "entity_counts": Counter(), "extents": None}
    for l in doc.layers:
        o["layers"][l.dxf.name] = {"color": l.dxf.color, "linetype": l.dxf.linetype, "lineweight": l.dxf.get("lineweight", -3)}
    o["linetypes"] = sorted(lt.dxf.name for lt in doc.linetypes)
    for s in doc.styles:
        o["text_styles"][s.dxf.name] = {"font": s.dxf.font, "fixed_height": s.dxf.height, "width": s.dxf.width}
    for d in doc.dimstyles:
        o["dimstyles"][d.dxf.name] = {k: d.dxf.get(k) for k in ("dimtxt", "dimasz", "dimexo", "dimexe", "dimgap", "dimdec", "dimtxsty", "dimclrd", "dimlfac", "dimscale", "dimtad", "dimzin") if d.dxf.hasattr(k)}
    per_layer = defaultdict(Counter)
    for e in msp:
        t = e.dxftype()
        o["entity_counts"][t] += 1
        per_layer[e.dxf.layer][t] += 1
        if t == "TEXT":
            o["text_heights"][round(e.dxf.height, 2)] += 1
        elif t == "MTEXT":
            o["text_heights"][round(e.dxf.char_height, 2)] += 1
    o["entities_by_layer"] = {k: dict(v) for k, v in per_layer.items()}
    o["text_heights"] = {str(k): v for k, v in sorted(o["text_heights"].items())}
    o["entity_counts"] = dict(o["entity_counts"])
    o["dim_overrides"] = Counter(e.dxf.dimstyle for e in msp.query("DIMENSION"))
    o["dim_overrides"] = dict(o["dim_overrides"])
    try:
        from ezdxf import bbox
        b = bbox.extents(msp)
        o["extents"] = [round(b.extmin.x, 1), round(b.extmin.y, 1), round(b.extmax.x, 1), round(b.extmax.y, 1)]
    except Exception:
        pass
    o["title_block_text"] = sorted({(e.plain_text() if e.dxftype() == "MTEXT" else e.dxf.text).strip()[:60] for e in msp if e.dxftype() in ("TEXT", "MTEXT")})[:60]
    return o


def to_profile(observations):
    items = []
    def add(kind, key, value, seen):
        items.append({"id": f"{kind}:{key}", "observed": value, "seen_in": seen, "status": "UNVERIFIED", "clause": "", "note": ""})
    layers = defaultdict(list)
    for ob in observations:
        for n, v in ob["layers"].items():
            layers[(n, json.dumps(v, sort_keys=True))].append(ob["file"])
    for (n, v), files in sorted(layers.items()):
        add("layer", n, json.loads(v), files)
    heights = defaultdict(list)
    for ob in observations:
        for h in ob["text_heights"]:
            heights[h].append(ob["file"])
    for h, files in sorted(heights.items(), key=lambda t: float(t[0])):
        add("text_height_mm", h, h, files)
    ds = defaultdict(list)
    for ob in observations:
        for n, v in ob["dimstyles"].items():
            ds[(n, json.dumps(v, sort_keys=True))].append(ob["file"])
    for (n, v), files in sorted(ds.items()):
        add("dimstyle", n, json.loads(v), files)
    return {"purpose": "Draft AS 1100 profile built from AFJ/Drafting Central masters. Nothing here is a claim about the standard until clause is filled and status is CONFIRMED.",
            "standard_on_file": "NOT YET SUPPLIED (AS 1100.101, AS 1100.201, HB 47). Needed before any item can be confirmed.",
            "items": items}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dxf", nargs="+")
    ap.add_argument("--out", default="profile_draft.json")
    a = ap.parse_args()
    obs = [observe(p) for p in a.dxf]
    prof = to_profile(obs)
    prof["observations"] = obs
    json.dump(prof, open(a.out, "w", encoding="utf-8"), indent=1, default=str)
    print(f"{len(obs)} file(s), {len(prof['items'])} items, all UNVERIFIED -> {a.out}")
    for ob in obs:
        print(f"  {ob['file']}: {len(ob['layers'])} layers, text heights {list(ob['text_heights'])}, dimstyles {list(ob['dimstyles'])}, extents {ob['extents']}")


if __name__ == "__main__":
    main()
