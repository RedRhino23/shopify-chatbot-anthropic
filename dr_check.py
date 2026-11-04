#!/usr/bin/env python3
"""Pre-handback check for DXF drawings. No AutoCAD needed (needs: pip install ezdxf).

Covers Ross's rules of 02/11/2026:
  1  orphan lines left behind when a dimension changed
  2  lines on one sister drawing and not the others
  3  stray / half-trimmed lines, dimensions not measuring to geometry
  5  dimension points that did not move (compare against a pre-edit DXF)

Usage:
  dr_check.py D17428M-1.dxf                          rules 3 (one drawing)
  dr_check.py J1.dxf J2.dxf J3.dxf --sisters         adds rule 2
  dr_check.py new.dxf --before old.dxf               adds rule 5
Options: --tol 0.5 (drawing units)  --ignore-layers DEFPOINTS,BORDER
Exit code 1 if any ERROR, so the drawing code can stop hand-back.
"""
import argparse
import math
import sys
from collections import Counter

import ezdxf


def segments(msp, ignore):
    """Yield (handle, layer, (x1, y1), (x2, y2)) for LINEs and polyline edges."""
    for e in msp:
        layer = e.dxf.layer
        if layer.upper() in ignore:
            continue
        t = e.dxftype()
        if t == "LINE":
            s, f = e.dxf.start, e.dxf.end
            yield e.dxf.handle, layer, (s.x, s.y), (f.x, f.y)
        elif t == "LWPOLYLINE":
            pts = [(p[0], p[1]) for p in e.get_points("xy")]
            if e.closed and pts:
                pts.append(pts[0])
            for a, b in zip(pts, pts[1:]):
                yield e.dxf.handle, layer, a, b


def dist_pt_seg(p, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    if L2 == 0:
        return math.hypot(p[0] - ax, p[1] - ay)
    t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2))
    return math.hypot(p[0] - (ax + t * dx), p[1] - (ay + t * dy))


def other_geometry(msp, ignore):
    """Points and segments from everything that is not a LINE/LWPOLYLINE, so lines that
    end on an arc, circle, hatch edge or block count as touching something."""
    pts = []
    for e in msp:
        if e.dxf.layer.upper() in ignore:
            continue
        t = e.dxftype()
        try:
            if t in ("ARC", "CIRCLE"):
                c, r = e.dxf.center, e.dxf.radius
                for k in range(0, 360, 5):
                    pts.append((c.x + r * math.cos(math.radians(k)), c.y + r * math.sin(math.radians(k))))
            elif t == "INSERT":
                pts.append((e.dxf.insert.x, e.dxf.insert.y))
            elif t in ("ELLIPSE", "SPLINE"):
                pts.extend((p.x, p.y) for p in e.flattening(1.0))
        except Exception:
            pass
    return pts


def check_lines(doc, tol, ignore, out):
    msp = doc.modelspace()
    segs = list(segments(msp, ignore))
    extra = other_geometry(msp, ignore)
    dims = dimension_points(msp)
    for h, layer, a, b in segs:
        if math.dist(a, b) < tol:
            out.append(("WARN", h, f"zero-length line on {layer}"))
            continue
        free = []
        for end in (a, b):
            touched = any(
                h2 != h and dist_pt_seg(end, a2, b2) <= tol for h2, _, a2, b2 in segs
            ) or any(math.dist(end, p) <= tol for p in extra)
            # an end that carries a dimension point is doing a job
            if not touched and any(math.dist(end, p) <= tol for p in dims):
                touched = True
            if not touched:
                free.append(end)
        if len(free) == 2:
            out.append(("ERROR", h, f"isolated line on {layer}, both ends free: "
                                    f"({a[0]:.2f},{a[1]:.2f})-({b[0]:.2f},{b[1]:.2f}). Orphan? (rule 1/3)"))
        elif len(free) == 1:
            p = free[0]
            out.append(("WARN", h, f"half-trimmed? one free end at ({p[0]:.2f},{p[1]:.2f}) on {layer} (rule 3)"))
    return segs


def dimension_points(msp):
    pts = []
    for d in msp.query("DIMENSION"):
        for attr in ("defpoint2", "defpoint3", "defpoint4"):
            if d.dxf.hasattr(attr):
                v = d.dxf.get(attr)
                pts.append((v.x, v.y))
    return pts


def check_dimensions(doc, segs, tol, out):
    msp = doc.modelspace()
    for d in msp.query("DIMENSION"):
        for attr in ("defpoint2", "defpoint3"):
            if not d.dxf.hasattr(attr):
                continue
            v = d.dxf.get(attr)
            p = (v.x, v.y)
            if not any(dist_pt_seg(p, a, b) <= tol for _, _, a, b in segs):
                out.append(("ERROR", d.dxf.handle,
                            f"dimension {attr} ({p[0]:.2f},{p[1]:.2f}) measures to nothing (rule 3)"))


def signature(segs, round_to=1.0):
    """Layer + orientation + rounded length, ignoring position, for sister comparison."""
    sig = Counter()
    for _, layer, a, b in segs:
        ang = round(math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 180, 0)
        sig[(layer, ang, round(math.dist(a, b) / round_to) * round_to)] += 1
    return sig


def compare_sisters(named, out):
    sigs = {n: signature(s) for n, s in named.items()}
    for n, sig in sigs.items():
        for key, cnt in sig.items():
            missing = [m for m, s in sigs.items() if m != n and s[key] < cnt]
            if missing and len(missing) == len(sigs) - 1:
                layer, ang, ln = key
                out.append(("WARN", n, f"only on this drawing: {layer} line {ln:g} long at {ang:g} deg "
                                       f"(x{cnt}). Needs a reason or it goes (rule 2)"))


def _measure(d):
    try:
        return round(float(d.get_measurement()), 2)
    except Exception:
        return None


def compare_before(new, old, tol, out):
    """Rule 5: list each dimension's measured length before and after, so the drawing code
    can confirm every intended change really landed (AutoCAD silently reverts associative edits)."""
    def meas(doc):
        return {d.dxf.handle: (d.dxf.get("text", ""), _measure(d),
                               [(round(p.x, 2), round(p.y, 2)) for p in
                                (d.dxf.get(k) for k in ("defpoint2", "defpoint3") if d.dxf.hasattr(k))])
                for d in doc.modelspace().query("DIMENSION")}
    n, o = meas(new), meas(old)
    changed = same = 0
    for h, (txt, m, pts) in n.items():
        if h not in o:
            out.append(("INFO", h, f"new dimension, measures {m}"))
        elif o[h][2] != pts or o[h][1] != m:
            changed += 1
            out.append(("INFO", h, f"changed: {o[h][1]} -> {m}"))
        else:
            same += 1
    for h in o:
        if h not in n:
            out.append(("INFO", h, "dimension removed"))
    out.append(("INFO", "-", f"{changed} dimension(s) changed, {same} unchanged. Every dimension the scan marks "
                             "must be in the changed list; if not, the edit was reverted (rule 5)."))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dxf", nargs="+")
    ap.add_argument("--sisters", action="store_true", help="compare the given files as sister drawings")
    ap.add_argument("--before", help="pre-edit DXF of the (single) drawing")
    ap.add_argument("--tol", type=float, default=0.5)
    ap.add_argument("--ignore-layers", default="DEFPOINTS")
    a = ap.parse_args()
    ignore = {x.strip().upper() for x in a.ignore_layers.split(",") if x.strip()}

    out, named = [], {}
    for path in a.dxf:
        res = []
        doc = ezdxf.readfile(path)
        segs = check_lines(doc, a.tol, ignore, res)
        check_dimensions(doc, segs, a.tol, res)
        named[path] = segs
        if a.before and len(a.dxf) == 1:
            compare_before(doc, ezdxf.readfile(a.before), a.tol, res)
        out += [(lvl, f"{path}:{h}", msg) for lvl, h, msg in res]
    if a.sisters and len(a.dxf) > 1:
        sis = []
        compare_sisters(named, sis)
        out += sis

    order = {"ERROR": 0, "WARN": 1, "INFO": 2}
    for lvl, where, msg in sorted(out, key=lambda r: order[r[0]]):
        print(f"{lvl:5} {where}  {msg}")
    errs = sum(1 for r in out if r[0] == "ERROR")
    print(f"\n{errs} error(s), {sum(1 for r in out if r[0] == 'WARN')} warning(s). "
          + ("NOT ready for hand-back." if errs else "Review warnings, then hand back."))
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
