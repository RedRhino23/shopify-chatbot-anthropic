#!/usr/bin/env python3
"""Overlay check (pipeline step 10): compare a SOURCE drawing with a RESULT drawing, per entity.

    python overlay_check.py source.pdf result.dxf  [--out report_base] [--tol 0.5]

Source and result can each be a vector PDF or a DXF. Both are reduced to line work (mm) and text,
aligned (scale and shift found automatically, or given), then scored:
  recall     share of source line length that the result also has (low = missing geometry)
  precision  share of result line length that the source also has (low = extra geometry)
  numbers    every number on the source must be on the result, and vice versa (dimension values)
Outputs: <out>_overlay.png (grey = matched, red = in source only, blue = in result only),
         <out>_report.json, and a short summary on screen. Exit 1 if below the thresholds.

Needs: pip install ezdxf pdfplumber numpy scipy matplotlib   (all permissive licences; no PyMuPDF/AGPL)
Limits: dashed lines are matched as continuous lines (so a missing dash pattern is not caught); hatch fill is skipped on DXF, so use --mask for
hatched areas that are drawn as lines in the PDF. Raster-only PDFs are not read (step 3, later).
"""
import argparse
import json
import math
import re
import sys
from collections import Counter

import numpy as np
from scipy.ndimage import binary_dilation, label
from scipy.spatial import cKDTree

PT = 25.4 / 72.0  # PDF point to mm
NUM = re.compile(r"(?<![\w.])\d+(?:\.\d+)?(?![\w])")


class Geo:
    def __init__(self, name):
        self.name = name
        self.segs = []   # (x1, y1, x2, y2) mm, y up
        self.dashed = []  # dashed / centre lines as continuous lines: only used so the other side's dashes can match
        self.texts = []  # (string, x, y)
        self.skipped_dashed = 0
        self.hatches = []  # (polygon Nx2, pattern angle deg) for patterned (non-solid) hatches

    def seg_array(self):
        return np.array(self.segs, float).reshape(-1, 4)


def _bez(p0, p1, p2, p3, n=10):
    t = np.linspace(0, 1, n + 1)[:, None]
    pts = ((1 - t) ** 3) * p0 + 3 * ((1 - t) ** 2) * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3
    return pts


def read_pdf(path, page=0):
    import pdfplumber
    g = Geo(path)
    with pdfplumber.open(path) as pdf:
        pg = pdf.pages[page]
        H = float(pg.height)
        flip = lambda x, y: (x * PT, (H - y) * PT)  # pdfplumber coordinates are top-origin
        for kind in ("lines", "curves", "rects"):
            for o in getattr(pg, kind):
                is_dashed = bool(o.get("dash") and o["dash"][0])
                if not o.get("stroke", True):
                    continue  # fills (page background, solid areas) are not line work
                path_cmds = o.get("path")
                polylines = []
                if path_cmds:
                    cur, start = None, None
                    for cmd in path_cmds:
                        c = cmd[0]
                        if c == "m":
                            cur = start = np.array(cmd[1], float); polylines.append([cur])
                        elif c == "l" and cur is not None:
                            cur = np.array(cmd[1], float); polylines[-1].append(cur)
                        elif c == "c" and cur is not None:
                            b = _bez(cur, np.array(cmd[1], float), np.array(cmd[2], float), np.array(cmd[3], float))
                            polylines[-1].extend(list(b[1:])); cur = np.array(cmd[3], float)
                        elif c == "h" and start is not None:
                            polylines[-1].append(start); cur = start
                        elif c == "re":
                            x, y, w, h = cmd[1:5]
                            polylines.append([np.array(q, float) for q in ((x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y))])
                else:
                    pts = o.get("pts") or []
                    if pts:
                        polylines.append([np.array(q, float) for q in pts] + ([np.array(pts[0], float)] if kind == "rects" else []))
                for pl in polylines:
                    for a, b in zip(pl, pl[1:]):
                        (g.dashed if is_dashed else g.segs).append((*flip(a[0], a[1]), *flip(b[0], b[1])))
        # Text: group characters by baseline direction and line, so vertical and rotated dimension text reads right
        # (pdfplumber's own word grouping scrambles rotated text).
        by_th = {}
        for ch in pg.chars:
            m = ch["matrix"]
            th = round(math.degrees(math.atan2(m[1], m[0])) % 360, 0)
            x, y = m[4], m[5]  # origin of the character, PDF points, y up
            c, sn = math.cos(math.radians(th)), math.sin(math.radians(th))
            by_th.setdefault(th, []).append((-x * sn + y * c, x * c + y * sn, ch["text"], x, y, ch["size"]))
        groups = {}
        for th, L in by_th.items():
            L.sort()
            line_id, last_v = 0, None
            for v, u, tx, x, y, size in L:
                if last_v is not None and v - last_v > size * 0.3:
                    line_id += 1
                last_v = v
                groups.setdefault((th, line_id), []).append((u, tx, x, y, size))
        words = []
        for (th, _), chs in groups.items():
            chs.sort()
            cur = []
            for item in chs + [None]:
                brk = item is None or item[1].isspace() or (cur and item[0] - cur[-1][0] > 1.6 * max(cur[-1][4], item[4]))
                if brk and cur:
                    words.append((th, cur)); cur = []
                if item is not None and not item[1].isspace():
                    cur.append(item)
        by_line = {}
        for th, cur in words:
            by_line.setdefault((th, round(((-(cur[0][2]) * math.sin(math.radians(th)) + cur[0][3] * math.cos(math.radians(th)))) / 3)), []).append(cur)
        for (th, _), line in by_line.items():
            line.sort(key=lambda w: w[0][0])
            for i, w in enumerate(line):
                size = w[0][4]
                gap_prev = (w[0][0] - (line[i - 1][-1][0] + line[i - 1][-1][4] * 0.6)) if i else 99
                gap_next = (line[i + 1][0][0] - (w[-1][0] + w[-1][4] * 0.6)) if i + 1 < len(line) else 99
                alone = gap_prev > 8 and gap_next > 8
                text = "".join(c[1] for c in w)
                cx = sum(c[2] for c in w) / len(w) + math.cos(math.radians(th)) * size * 0.3
                cy = sum(c[3] for c in w) / len(w) + math.sin(math.radians(th)) * size * 0.3
                g.texts.append((text, cx * PT, cy * PT, alone))
    return g


def read_dxf(path, ignore_layers=()):
    import ezdxf
    from ezdxf import disassemble
    from ezdxf.path import make_path
    g = Geo(path)
    doc = ezdxf.readfile(path)
    msp = doc.modelspace()
    ign = {x.upper() for x in ignore_layers}
    from ezdxf.path import from_hatch
    for h in msp.query("HATCH"):
        if h.dxf.solid_fill or h.dxf.layer.upper() in ign:
            continue
        try:
            ang = float(h.dxf.pattern_angle)
            base = [float(l.angle) for l in h.pattern.lines] if h.pattern else [45.0]
            for p in from_hatch(h):
                poly = np.array([(v.x, v.y) for v in p.flattening(0.1)])
                if len(poly) > 2:
                    g.hatches.append((poly, [(ang + b) % 180 for b in base]))
        except Exception:
            pass
    for e in disassemble.recursive_decompose(msp):
        t = e.dxftype()
        if e.dxf.hasattr("layer") and e.dxf.layer.upper() in ign:
            continue
        if t in ("TEXT", "MTEXT"):
            if t == "TEXT":
                raw, hgt = e.dxf.text, float(e.dxf.height)
                h_al = int(e.dxf.get("halign", 0))
                p = e.dxf.align_point if (h_al or int(e.dxf.get("valign", 0))) and e.dxf.hasattr("align_point") else e.dxf.insert
                frac = {0: 0.0, 1: 0.5, 2: 1.0, 4: 0.5}.get(h_al, 0.0)
            else:
                raw, hgt = e.plain_text(), float(e.dxf.char_height)
                p = e.dxf.insert
                frac = {1: 0.0, 2: 0.5, 3: 1.0}[((int(e.dxf.attachment_point) - 1) % 3) + 1]
            cw = 0.6 * hgt  # rough character width, only used to place each word along its line
            for line in raw.replace("\\P", "\n").split("\n"):
                width = len(line) * cw
                left = p.x - frac * width
                toks = list(re.finditer(r"\S+", line))
                for m in toks:
                    g.texts.append((m.group(), left + (m.start() + len(m.group()) / 2) * cw, p.y, len(toks) == 1))
            continue
        if t in ("LINE", "ARC", "CIRCLE", "ELLIPSE", "SPLINE", "LWPOLYLINE", "POLYLINE"):
            lt = e.dxf.linetype.upper() if e.dxf.hasattr("linetype") else "BYLAYER"
            if lt in ("BYLAYER", "BYBLOCK") and e.dxf.hasattr("layer") and e.dxf.layer in doc.layers:
                lt = doc.layers.get(e.dxf.layer).dxf.linetype.upper()
            dashed = lt not in ("BYLAYER", "BYBLOCK", "CONTINUOUS")
            try:
                pts = [(v.x, v.y) for v in make_path(e).flattening(0.05)]
            except Exception:
                continue
            for a, b in zip(pts, pts[1:]):
                (g.dashed if dashed else g.segs).append((a[0], a[1], b[0], b[1]))
    return g


def read_any(path, args):
    return read_pdf(path) if path.lower().endswith(".pdf") else read_dxf(path, args.ignore_layers.split(",") if args.ignore_layers else ())


def sample(segs, step):
    pts, sid = [], []
    for i, (x1, y1, x2, y2) in enumerate(segs):
        L = math.hypot(x2 - x1, y2 - y1)
        n = max(1, int(math.ceil(L / step)))
        for k in range(n):
            f = (k + 0.5) / n
            pts.append((x1 + f * (x2 - x1), y1 + f * (y2 - y1))); sid.append(i)
    return np.array(pts).reshape(-1, 2), np.array(sid, int)


def apply_masks(g, masks):
    if not masks:
        return
    keep = []
    for s in g.segs:
        mx, my = (s[0] + s[2]) / 2, (s[1] + s[3]) / 2
        if not any(x0 <= mx <= x1 and y0 <= my <= y1 for x0, y0, x1, y1 in masks):
            keep.append(s)
    g.segs = keep
    g.dashed = [x for x in g.dashed if not any(x0 <= (x[0] + x[2]) / 2 <= x1 and y0 <= (x[1] + x[3]) / 2 <= y1 for x0, y0, x1, y1 in masks)]
    g.texts = [t for t in g.texts if not any(x0 <= t[1] <= x1 and y0 <= t[2] <= y1 for x0, y0, x1, y1 in masks)]


def drop_hatch_lines(g, hatches, ang_tol=3.0):
    """Remove segments of g that lie inside a patterned hatch and run along its pattern angle
    (hatch lines drawn as plain lines in a PDF)."""
    if not hatches:
        return 0
    from matplotlib.path import Path
    keep, n = [], 0
    mids = np.array([((s[0] + s[2]) / 2, (s[1] + s[3]) / 2) for s in g.segs])
    angs = np.array([math.degrees(math.atan2(s[3] - s[1], s[2] - s[0])) % 180 for s in g.segs])
    drop = np.zeros(len(g.segs), bool)
    for poly, pangs in hatches:
        inside = Path(poly).contains_points(mids, radius=-0.3)
        for pa in pangs:
            d = np.abs((angs - pa + 90) % 180 - 90)
            drop |= inside & (d < ang_tol)
    g.segs = [s for s, dr in zip(g.segs, drop) if not dr]
    return int(drop.sum())


def bbox(a):
    return a[:, [0, 2]].min(), a[:, [1, 3]].min(), a[:, [0, 2]].max(), a[:, [1, 3]].max()


def transform(g, s, dx, dy):
    f = lambda L: [(x1 * s + dx, y1 * s + dy, x2 * s + dx, y2 * s + dy) for x1, y1, x2, y2 in L]
    g.segs, g.dashed = f(g.segs), f(g.dashed)
    g.texts = [(t, x * s + dx, y * s + dy, al) for t, x, y, al in g.texts]


def score_shift(src_pts, res_tree, s, dx, dy, tol):
    d, _ = res_tree.query(src_pts * s + np.array([dx, dy]), distance_upper_bound=tol)
    return np.isfinite(d).mean()


def _fit_bbox(sb, rb):
    sw, sh, rw, rh = sb[2] - sb[0], sb[3] - sb[1], rb[2] - rb[0], rb[3] - rb[1]
    s = (rw / sw + rh / sh) / 2 if sw and sh else 1.0
    return s, (rb[0] + rb[2]) / 2 - s * (sb[0] + sb[2]) / 2, (rb[1] + rb[3]) / 2 - s * (sb[1] + sb[3]) / 2


def auto_align(src, res, tol, step):
    """Try several starting transforms (identity, full bounding boxes, trimmed bounding boxes), then
    refine the best one by shift and scale, coarse to fine."""
    sp, _ = sample(src.segs, step * 2)
    rp, _ = sample(res.segs, step)
    tree = cKDTree(rp)
    sa, ra = src.seg_array(), res.seg_array()
    sb, rb = bbox(sa), bbox(ra)
    q = lambda p: (np.percentile(p[:, 0], 1), np.percentile(p[:, 1], 1), np.percentile(p[:, 0], 99), np.percentile(p[:, 1], 99))
    cands = [(1.0, 0.0, 0.0), _fit_bbox(sb, rb), _fit_bbox(q(sp), q(rp))]
    aspect = abs(((rb[2] - rb[0]) / (sb[2] - sb[0])) / ((rb[3] - rb[1]) / (sb[3] - sb[1])) - 1)
    best_c, best = None, -1
    for c in cands:
        v = score_shift(sp, tree, *c, 3.0)
        if v > best:
            best, best_c = v, c
    s, dx, dy = best_c
    for t in (3.0, 1.5, tol):
        cur = score_shift(sp, tree, s, dx, dy, t)
        stepsz = 4.0 * t / 3.0
        while stepsz > 0.05:
            improved = True
            while improved:
                improved = False
                for ds, ddx, ddy in ((0, stepsz, 0), (0, -stepsz, 0), (0, 0, stepsz), (0, 0, -stepsz),
                                     (s * 0.002 * stepsz, 0, 0), (-s * 0.002 * stepsz, 0, 0)):
                    v = score_shift(sp, tree, s + ds, dx + ddx, dy + ddy, t)
                    if v > cur + 1e-6:
                        cur, s, dx, dy, improved = v, s + ds, dx + ddx, dy + ddy, True
            stepsz /= 2
    return s, dx, dy, aspect, score_shift(sp, tree, s, dx, dy, tol)


def cluster_regions(pts, flags, cell=3.0, min_len=0.0, step=0.25):
    bad = pts[flags]
    if len(bad) == 0:
        return []
    mn = pts.min(0)
    ij = np.floor((bad - mn) / cell).astype(int)
    grid = np.zeros(ij.max(0) + 3, bool)
    grid[ij[:, 0] + 1, ij[:, 1] + 1] = True
    lab, n = label(binary_dilation(grid, iterations=1))
    out = []
    for k in range(1, n + 1):
        sel = lab[ij[:, 0] + 1, ij[:, 1] + 1] == k
        if not sel.any():
            continue
        p = bad[sel]
        length = len(p) * step
        if length >= min_len:
            out.append({"x0": float(p[:, 0].min()), "y0": float(p[:, 1].min()), "x1": float(p[:, 0].max()), "y1": float(p[:, 1].max()), "length_mm": round(length, 1)})
    return sorted(out, key=lambda r: -r["length_mm"])


def numbers(g):
    """(number string, x, y, standalone). Position is only trusted for standalone numbers (dimension values)."""
    out = []
    for t, x, y, al in g.texts:
        for m in NUM.findall(t.replace(",", ".") if re.fullmatch(r"\d+,\d+", t) else t):
            out.append((m, x, y, al and m == t))
    return out


def compare_numbers(src, res, move_mm):
    sn, rn = numbers(src), numbers(res)
    cs, cr = Counter(n for n, *_ in sn), Counter(n for n, *_ in rn)
    missing = {k: v - cr[k] for k, v in cs.items() if v > cr[k]}
    extra = {k: v - cs[k] for k, v in cr.items() if v > cs[k]}
    moved = []
    pool = {}
    for m, rx, ry, al in rn:
        if al:
            pool.setdefault(m, []).append((rx, ry))
    for n, x, y, al in sorted(sn, key=lambda t: t[0]):
        if not al:
            continue
        cands = pool.get(n)
        if not cands:
            continue
        i = min(range(len(cands)), key=lambda k: math.hypot(x - cands[k][0], y - cands[k][1]))
        d = math.hypot(x - cands[i][0], y - cands[i][1])
        cands.pop(i)
        if d > move_mm:
            moved.append({"value": n, "at": [round(x, 1), round(y, 1)], "nearest_in_result_mm": round(d, 1)})
    return {"source_count": len(sn), "result_count": len(rn), "missing_in_result": missing, "extra_in_result": extra, "moved": moved[:50]}


def draw(src_pts, src_ok, res_pts, res_ok, regions_s, regions_r, texts_bad, base, bounds):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(16.5, 11.7))
    ax.scatter(*src_pts[src_ok].T, s=0.6, c="#9a9a9a", linewidths=0)
    ax.scatter(*src_pts[~src_ok].T, s=3.0, c="#d62728", linewidths=0, label="in source, not in result")
    ax.scatter(*res_pts[~res_ok].T, s=3.0, c="#1f5fd6", linewidths=0, label="in result, not in source")
    for r in regions_s[:15]:
        ax.add_patch(plt.Rectangle((r["x0"] - 2, r["y0"] - 2), r["x1"] - r["x0"] + 4, r["y1"] - r["y0"] + 4, fill=False, ec="#d62728", lw=0.8))
    for r in regions_r[:15]:
        ax.add_patch(plt.Rectangle((r["x0"] - 2, r["y0"] - 2), r["x1"] - r["x0"] + 4, r["y1"] - r["y0"] + 4, fill=False, ec="#1f5fd6", lw=0.8))
    for label_, x, y, col in texts_bad:
        ax.annotate(label_, (x, y), color=col, fontsize=8, weight="bold")
    ax.set_aspect("equal"); ax.set_xlim(bounds[0] - 10, bounds[2] + 10); ax.set_ylim(bounds[1] - 10, bounds[3] + 10)
    ax.legend(loc="lower left"); ax.axis("off")
    fig.savefig(base + "_overlay.png", dpi=110, bbox_inches="tight")
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source"); ap.add_argument("result")
    ap.add_argument("--out", default="overlay")
    ap.add_argument("--tol", type=float, default=0.5, help="match distance in mm on the result frame")
    ap.add_argument("--step", type=float, default=0.25, help="sample spacing in mm")
    ap.add_argument("--scale", type=float, help="fixed scale source->result (skips auto align)")
    ap.add_argument("--offset", type=float, nargs=2, metavar=("DX", "DY"))
    ap.add_argument("--mask", action="append", default=[], help="x0,y0,x1,y1 in source mm to ignore (hatch, logo); repeatable")
    ap.add_argument("--ignore-layers", default="DEFPOINTS", help="DXF layers to ignore")
    ap.add_argument("--min-region", type=float, default=5.0, help="any missing or extra stretch of line this long (mm) fails, whatever the percentages")
    ap.add_argument("--min-recall", type=float, default=0.95)
    ap.add_argument("--min-precision", type=float, default=0.95)
    ap.add_argument("--move-mm", type=float, default=15.0, help="a number found this far from its source position is reported as moved")
    a = ap.parse_args()

    src, res = read_any(a.source, a), read_any(a.result, a)
    if not src.segs or not res.segs:
        sys.exit(f"no line work read (source {len(src.segs)}, result {len(res.segs)}). Raster-only PDF?")
    masks_src = [tuple(float(v) for v in m.split(",")) for m in a.mask]
    apply_masks(src, masks_src)
    if a.scale is not None:
        s, dx, dy, aspect = a.scale, (a.offset or (0, 0))[0], (a.offset or (0, 0))[1], 0.0
        transform(src, s, dx, dy)
        fit = None
    else:
        s, dx, dy, aspect, fit = auto_align(src, res, a.tol, a.step)
        transform(src, s, dx, dy)
    dropped = drop_hatch_lines(src, res.hatches) if src.name.lower().endswith(".pdf") else 0
    if dropped:
        print(f"hatch: ignored {dropped} source lines inside patterned hatches of the result")
        if a.scale is None:
            s2, dx2, dy2, aspect, fit = auto_align(src, res, a.tol, a.step)
            transform(src, s2, dx2, dy2)
            s, dx, dy = s * s2, dx * s2 + dx2, dy * s2 + dy2
    apply_masks(res, [(x0 * s + dx, y0 * s + dy, x1 * s + dx, y1 * s + dy) for x0, y0, x1, y1 in masks_src])

    sp, _ = sample(src.segs, a.step)
    rp, _ = sample(res.segs, a.step)
    # dashes are matched against the other side's dash line as a continuous line (phase never agrees)
    spd = np.vstack([sp, sample(src.dashed, a.step)[0]]) if src.dashed else sp
    rpd = np.vstack([rp, sample(res.dashed, a.step)[0]]) if res.dashed else rp
    sp_n, rp_n = len(sp), len(rp)
    ts, tr = cKDTree(spd), cKDTree(rpd)
    s_ok = np.isfinite(tr.query(sp, distance_upper_bound=a.tol)[0])
    r_ok = np.isfinite(ts.query(rp, distance_upper_bound=a.tol)[0])
    recall, precision = s_ok.mean(), r_ok.mean()
    f1 = 2 * recall * precision / (recall + precision) if recall + precision else 0.0
    reg_s = cluster_regions(sp, ~s_ok, step=a.step, min_len=2.0)
    reg_r = cluster_regions(rp, ~r_ok, step=a.step, min_len=2.0)
    nums = compare_numbers(src, res, a.move_mm)
    bad_txt = [(f"missing {k}", 0, 0, "#d62728") for k in nums["missing_in_result"]]
    # place number flags at their source position
    flags = []
    for t, x, y, _ in numbers(src):
        if t in nums["missing_in_result"]:
            flags.append((f"? {t}", x, y, "#d62728"))
    for t, x, y, _ in numbers(res):
        if t in nums["extra_in_result"]:
            flags.append((f"? {t}", x, y, "#1f5fd6"))
    b = bbox(np.vstack([src.seg_array(), res.seg_array()]))
    draw(sp, s_ok, rp, r_ok, reg_s, reg_r, flags, a.out, b)

    rep = {"source": a.source, "result": a.result, "align": {"scale": round(s, 5), "dx": round(dx, 2), "dy": round(dy, 2), "aspect_mismatch": round(aspect, 4), "initial_fit": None if fit is None else round(float(fit), 4)},
           "recall": round(float(recall), 4), "precision": round(float(precision), 4), "f1": round(float(f1), 4),
           "source_length_mm": round(len(sp) * a.step, 1), "result_length_mm": round(len(rp) * a.step, 1),
           "dashed_segments": {"source": len(src.dashed), "result": len(res.dashed)},
           "missing_regions": reg_s[:30], "extra_regions": reg_r[:30], "numbers": nums}
    json.dump(rep, open(a.out + "_report.json", "w"), indent=1)

    print(f"align: scale {s:.4f}, shift ({dx:.1f}, {dy:.1f}) mm" + ("" if recall >= 0.6 else f"  WARNING: poor alignment (recall {recall:.0%}). Different drawing, or give --scale/--offset"))
    print(f"recall {recall:.1%} (source geometry found in result)   precision {precision:.1%} (result geometry found in source)   F1 {f1:.1%}")
    for r in reg_s[:8]:
        print(f"  MISSING in result : {r['length_mm']:6.1f} mm of line near ({(r['x0'] + r['x1']) / 2:.0f}, {(r['y0'] + r['y1']) / 2:.0f}) mm")
    for r in reg_r[:8]:
        print(f"  EXTRA in result   : {r['length_mm']:6.1f} mm of line near ({(r['x0'] + r['x1']) / 2:.0f}, {(r['y0'] + r['y1']) / 2:.0f}) mm")
    print(f"numbers: source {nums['source_count']}, result {nums['result_count']}")
    if nums["missing_in_result"]:
        print("  numbers on source, not on result :", ", ".join(f"{k} x{v}" for k, v in nums["missing_in_result"].items()))
    if nums["extra_in_result"]:
        print("  numbers on result, not on source :", ", ".join(f"{k} x{v}" for k, v in nums["extra_in_result"].items()))
    for m in nums["moved"][:5]:
        print(f"  moved: {m['value']} is {m['nearest_in_result_mm']} mm from its source position")
    big = [r for r in reg_s + reg_r if r["length_mm"] >= a.min_region]
    fail = bool(big) or bool(nums["moved"]) or recall < a.min_recall or precision < a.min_precision or bool(nums["missing_in_result"]) or bool(nums["extra_in_result"])
    print("PASS" if not fail else "FAIL: do not hand back until each item above is explained or fixed.")
    print(f"wrote {a.out}_overlay.png, {a.out}_report.json")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
