#!/usr/bin/env python3
"""Check weld symbol blocks in a DXF against AS 1101.3-1987 Appendix B (sizes and angles, tolerance +/- 1 mm or 1 degree).

    python weld_symbol_check.py drawing.dxf [--block NAME ...] [--scale 1.0] [--json out.json]

Looks at blocks whose name contains "weld" (or --block). For each block it tries two things.
1. SHAPE CHECK, for a block that holds one simple symbol (up to 4 pieces): it recognises the shape first (fillet, V-butt, bevel-butt,
   square-butt, plug or slot, J-butt, U-butt, spot, weld-all-around), then measures the sizes and angles against Appendix B.
   Shape first, because Appendix B sizes differ by only 1 mm (the tolerance), so size alone cannot tell neighbouring symbols apart.
2. PRIMITIVE AUDIT, for a library block holding many symbols overlapped: every line, circle and arc must lie within tolerance of
   some Appendix B size and angle. It lists the ones that do not, and the worst deviation of those that do.
It also lists where each block is inserted and at what scale: a symbol inserted at scale 14 is 14 times the standard's size on paper
unless the sheet is scaled the same. --scale is the model-to-paper factor for the sheet (1 = drawn at paper size).
It reads geometry only. It cannot tell whether the right symbol is used for the right weld, which side of the reference line it sits
on, or whether the perpendicular leg is on the left (cl 2.3.11, see the 1101-2.3.11 item). Exit 1 if anything is OFF.
Values are Appendix B read by eye from page images: confirm against the printed page.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import ezdxf

ITEMS = json.load(open(Path(__file__).with_name("items_1101_3.json")))["items"]
P = next(i for i in ITEMS if i["id"] == "1101-AppB")["params"]
TOL, TOLA = P["tolerance_mm"], P["tolerance_deg"]
S2 = math.sqrt(2)
SNAP = 0.15

LINE_NOMINALS = sorted({P["B2_square_butt"]["height"], P["B2_square_butt"]["gap"], P["B3_bevel_butt"]["height"], P["B3_bevel_butt"]["height"] * S2,
                        P["B5_V_butt"]["height"] * S2, P["B6_fillet"]["height"], P["B6_fillet"]["height"] * S2, P["B4_J_butt"]["height"],
                        P["B7_U_butt"]["height"], P["B10_plug_or_slot"]["height"], P["B10_plug_or_slot"]["width"], P["B15_seam"]["length"],
                        P["B22_backing"]["width"], P["B22_backing"]["height"], 25.0, P["B4_J_butt"]["offset"], P["B18_field_weld"]["pole_height"]})
ANGLES = [0, 45, 90, 135]
RADII = sorted({P["B4_J_butt"]["radius"], P["B7_U_butt"]["radius"], P["B16_complete_penetration_one_side"]["radius"], 10.0,
                P["B14_spot_or_projection"]["diameter"] / 2, P["B17_weld_all_around"]["circle_diameter"] / 2})


def angdiff(a, b):
    d = abs(a - b) % 180
    return min(d, 180 - d)


def prims(block, scale):
    out = []
    for e in block:
        t = e.dxftype()
        if t == "LINE":
            s, f = e.dxf.start, e.dxf.end
            out.append({"k": "line", "p0": (s.x * scale, s.y * scale), "p1": (f.x * scale, f.y * scale)})
        elif t == "LWPOLYLINE":
            pts = [(p[0] * scale, p[1] * scale) for p in e.get_points("xy")]
            for a, b in zip(pts, pts[1:] + ([pts[0]] if e.closed else [])):
                out.append({"k": "line", "p0": a, "p1": b})
        elif t == "CIRCLE":
            out.append({"k": "circle", "c": (e.dxf.center.x * scale, e.dxf.center.y * scale), "r": e.dxf.radius * scale})
        elif t == "ARC":
            out.append({"k": "arc", "c": (e.dxf.center.x * scale, e.dxf.center.y * scale), "r": e.dxf.radius * scale})
    for p in out:
        if p["k"] == "line":
            dx, dy = p["p1"][0] - p["p0"][0], p["p1"][1] - p["p0"][1]
            p["len"], p["ang"] = math.hypot(dx, dy), math.degrees(math.atan2(dy, dx)) % 180
    return out


def near(a, b):
    return math.dist(a, b) <= SNAP


def vertical(l):
    return angdiff(l["ang"], 90) <= 5


def diag(l):
    return angdiff(l["ang"], 45) <= 5 or angdiff(l["ang"], 135) <= 5


def nominal(x, values):
    return min(values, key=lambda v: abs(v - x))


def measure(label, actual, nom, unit="mm"):
    dev = abs(actual - nom)
    return {"what": label, "actual": round(actual, 2), "nominal": round(nom, 2), "dev": round(dev, 2), "unit": unit,
            "ok": dev <= (TOL if unit == "mm" else TOLA) + 1e-6}


def classify(ps):
    """Return (symbol name, [measurements]) for one simple symbol, else None."""
    lines = [p for p in ps if p["k"] == "line"]
    circ = [p for p in ps if p["k"] == "circle"]
    arcs = [p for p in ps if p["k"] == "arc"]
    if len(ps) == 1 and len(circ) == 1:
        d = circ[0]["r"] * 2
        sp, wa = P["B14_spot_or_projection"]["diameter"], P["B17_weld_all_around"]["circle_diameter"]
        name, nom = ("spot or projection (B14)", sp) if abs(d - sp) <= abs(d - wa) else ("weld-all-around (B17)", wa)
        return name, [measure("diameter", d, nom)], "spot dia 6 and weld-all-around dia 5 differ by the 1 mm tolerance; classed by the nearer"
    if arcs and len(lines) in (1, 2) and len(arcs) in (1, 2) and len(ps) <= 4:
        # J-butt: one vertical line + one arc; U-butt: two verticals + two arcs
        if len(lines) == 1 and len(arcs) == 1 and vertical(lines[0]):
            return "J-butt (B4)", [measure("height", lines[0]["len"], P["B4_J_butt"]["height"]), measure("radius", arcs[0]["r"], P["B4_J_butt"]["radius"])], ""
        if len(lines) == 2 and len(arcs) == 2 and all(vertical(l) for l in lines):
            return "U-butt (B7)", [measure("height", lines[0]["len"], P["B7_U_butt"]["height"]), measure("radius", arcs[0]["r"], P["B7_U_butt"]["radius"])], ""
        return None
    if len(lines) == 3 and len(ps) == 3:
        v = [l for l in lines if vertical(l)]
        h = [l for l in lines if angdiff(l["ang"], 0) <= 5]
        if len(v) == 2 and len(h) == 1:
            return "plug or slot (B10)", [measure("height", v[0]["len"], P["B10_plug_or_slot"]["height"]), measure("width", h[0]["len"], P["B10_plug_or_slot"]["width"])], ""
        return None
    if len(lines) == 2 and len(ps) == 2:
        a, b = lines
        if vertical(a) and vertical(b):
            gap = abs(a["p0"][0] - b["p0"][0])
            return "square-butt (B2)", [measure("height", a["len"], P["B2_square_butt"]["height"]), measure("gap", gap, P["B2_square_butt"]["gap"])], ""
        v, d = (a, b) if vertical(a) else (b, a)
        if vertical(v) and diag(d):
            vt = max(v["p0"], v["p1"], key=lambda q: q[1]); vb = min(v["p0"], v["p1"], key=lambda q: q[1])
            ends = [d["p0"], d["p1"]]
            if any(near(e, vt) for e in ends):         # diagonal starts at the top of the vertical, runs down to the base line: fillet
                far = [e for e in ends if not near(e, vt)][0]
                ok_base = abs(far[1] - vb[1]) <= SNAP * 2
                name = "fillet (B6)" if ok_base else None
                if name:
                    return name, [measure("vertical leg", v["len"], P["B6_fillet"]["height"]), measure("angle", min(d["ang"], 180 - d["ang"]), 45, "deg"),
                                  measure("diagonal", d["len"], v["len"] * S2)], ""
            if any(near(e, vb) for e in ends):         # diagonal starts at the foot of the vertical, runs up: bevel-butt
                return "bevel-butt (B3)", [measure("vertical leg", v["len"], P["B3_bevel_butt"]["height"]), measure("angle", min(d["ang"], 180 - d["ang"]), 45, "deg"),
                                           measure("diagonal", d["len"], P["B3_bevel_butt"]["height"] * S2)], ""
        if diag(a) and diag(b):
            sh = [(x, y) for x in (a["p0"], a["p1"]) for y in (b["p0"], b["p1"]) if near(x, y)]
            if sh:
                h = a["len"] / S2
                return "V-butt (B5)", [measure("height", h, P["B5_V_butt"]["height"]), measure("angle a", min(a["ang"], 180 - a["ang"]), 45, "deg"),
                                       measure("angle b", min(b["ang"], 180 - b["ang"]), 45, "deg"), measure("legs equal", b["len"], a["len"])], ""
    return None


def audit(ps):
    """Each primitive must lie within tolerance of some Appendix B size and angle. Returns (outliers, worst deviation of the passing ones)."""
    out, worst = [], 0.0
    for p in ps:
        if p["k"] == "line":
            n = nominal(p["len"], LINE_NOMINALS); d = abs(p["len"] - n)
            a_dev, a_ref = min((angdiff(p["ang"], a), a) for a in ANGLES)
            problems = []
            if d > TOL + 1e-6:
                problems.append(f"nearest Appendix B size {n:.2f} ({d:.2f} off)")
            if TOLA + 1e-6 < a_dev <= 10:
                problems.append(f"angle is {a_dev:.1f} deg off {a_ref} (limit {TOLA})")
            if problems:
                out.append(f"line {p['len']:.2f} mm at {p['ang']:.0f} deg: " + "; ".join(problems))
            else:
                worst = max(worst, d)
        else:
            n = nominal(p["r"], RADII); d = abs(p["r"] - n) * (2 if p["k"] == "circle" else 1)
            if d <= TOL + 1e-6:
                worst = max(worst, d)
            else:
                out.append(f"{p['k']} radius {p['r']:.2f} mm: nearest Appendix B radius {n:.2f} ({d:.2f} off)")
    return out, worst


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dxf"); ap.add_argument("--block", action="append", default=[]); ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--json")
    a = ap.parse_args()
    doc = ezdxf.readfile(a.dxf)
    names = a.block or [b.name for b in doc.blocks if "weld" in b.name.lower() and not b.name.startswith("*")]
    if not names:
        print("no block with 'weld' in its name; pass --block NAME"); sys.exit(0)
    uses = {}
    for lay in [doc.modelspace()] + [doc.layouts.get(n) for n in doc.layout_names() if n != "Model"]:
        for e in lay.query("INSERT"):
            uses.setdefault(e.dxf.name, []).append(round(e.dxf.xscale, 3))
    bad, report = 0, []
    for n in names:
        ps = prims(doc.blocks.get(n), a.scale)
        ins = uses.get(n, [])
        print(f"block '{n}': {len(ps)} primitives; inserted {len(ins)} time(s)" + (f" at scale {sorted(set(ins))}" if ins else ""))
        res = classify(ps) if len(ps) <= 4 else None
        if res:
            name, ms, note = res
            ok = all(m["ok"] for m in ms)
            print(f"  {'CONFORMS' if ok else 'OFF':<9} {name}: " + "; ".join(f"{m['what']} {m['actual']} (std {m['nominal']}, off {m['dev']} {m['unit']})" + ("" if m["ok"] else " <-- OUT") for m in ms))
            if note:
                print(f"            note: {note}")
            report.append({"block": n, "mode": "shape", "symbol": name, "ok": ok, "measures": ms})
            bad += not ok
        else:
            out, worst = audit(ps)
            print(f"  {'AUDIT OK' if not out else 'AUDIT: ' + str(len(out)) + ' outside'}: {len(ps) - len(out)} of {len(ps)} primitives within +/-{TOL} mm / {TOLA} deg of an Appendix B size (worst passing {worst:.2f} mm)")
            for o in out:
                print("     -", o)
            report.append({"block": n, "mode": "audit", "outliers": out, "worst_passing_mm": round(worst, 2)})
            bad += bool(out)
    if a.json:
        json.dump(report, open(a.json, "w"), indent=1)
    print(f"\n{bad} block(s) with something outside Appendix B (tolerance +/- {TOL} mm, {TOLA} deg).")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
