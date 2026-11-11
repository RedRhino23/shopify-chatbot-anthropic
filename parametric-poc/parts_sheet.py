"""Sheet 2: cut list, stock order, part details and joint details, generated from the 3D model."""
import math

import cadquery as cq

from drawing_lib import Sheet, clip_prims, edges_to_prims, proj_pt, project
from ga_sheet import assembly, title_block
from rack_model import build, mass_kg

TEXT = {   # words on the issued sheet that are not geometry (material, operations)
    1: ("Pallet foot", "Pressed galv 130x130x50, 20 hole", "Purchased. Weld flange-up under item 2 (see Detail B)."),
    2: ("Corner stub", "50x50x4 SHS C350L0", "Square cut. Drill 13 dia thru at 25 from top (one axis)."),
    3: ("Telescopic post", "40x40x3 SHS C350L0", "Square cut. Drill 13 dia thru at 225 from bottom. 8 dia vent at 20 from top."),
    4: ("Post cap", "5 PL 250 grade", "Laser cut, 16.5 dia centre hole. Weld to post top."),
    5: ("Locating pin", "16 dia round bar", "Saw cut, chamfer 1x45 top. Plug weld into item 4, 20 proud."),
    6: ("Side rail", "50x50x2 SHS C350L0", "Square cut both ends."),
    7: ("End bearer", "50x50x2 SHS C350L0", "Square cut both ends."),
    8: ("Centre rail", "50x50x3 SHS C350L0", "Square cut both ends. Top flush with items 6/7."),
    9: ("Corner gusset", "4 PL 250 grade", "Laser cut right triangle, 15 snip. Weld to underside of rail corners."),
    10: ("Retainer bolt", "M12 x 70 grade 8.8 galv + nylok", "Fit through items 2 and 3 after assembly."),
}
NOTES = ["1. Material: SHS/RHS C350L0 to AS/NZS 1163. Plate 250 grade to AS/NZS 3678.",
         "2. Weld: 3 mm fillet all round unless noted. 2.5 mm to 2 mm wall. GMAW.",
         "3. Rails 6, 7, 8 all 50 deep, flush top 200 / bottom 150. Welded between stubs.",
         "4. Post 3 slides in stub 2 and bears on foot 1. Check post slides freely after galv.",
         "5. Hot dip galvanise after fab. Vent holes per galvaniser, max 8 dia visible.",
         "6. Gussets 9 on underside so box seat stays flat. Tolerance +/-2 overall.",
         "7. Forklift: forks min 1200 apart. One rack at a time. Check capacity plate."]


def dims_of(shape):
    bb = shape.BoundingBox()
    return bb.xlen, bb.ylen, bb.zlen


def cut_len(k, shape):
    x, y, z = dims_of(shape)
    if k in (1, 10):
        return "-"
    if k in (4, 9):
        return f"{x:.0f}x{y:.0f}"
    return f"{max(x, y, z):.0f}"


def table(sh, x0, ytop, colw, head, rows, rowh=6.2, hh=6.5, th=2.1):
    xs = [x0]
    for w in colw:
        xs.append(xs[-1] + w)
    ybot = ytop - hh - rowh * len(rows)
    sh.rect(xs[0], ybot, xs[-1], ytop, "TABLE")
    for x in xs[1:-1]:
        sh.line((x, ytop), (x, ybot))
    sh.line((xs[0], ytop - hh), (xs[-1], ytop - hh))
    for i in range(1, len(rows)):
        sh.line((xs[0], ytop - hh - i * rowh), (xs[-1], ytop - hh - i * rowh))
    for j, h in enumerate(head):
        sh.text(h, ((xs[j] + xs[j + 1]) / 2, ytop - hh / 2), th, "CENTER")
    for i, r in enumerate(rows):
        yc = ytop - hh - rowh * (i + 0.5)
        for j, c in enumerate(r):
            if j in (1, 2, 6):
                sh.text(str(c), (xs[j] + 1.5, yc), th, "MLEFT")
            else:
                sh.text(str(c), ((xs[j] + xs[j + 1]) / 2, yc), th, "CENTER")
    return ybot


def stock_lines(parts, stock=8000.0):
    """Stock lengths per section for 10 racks. A mixed set (several lengths) takes one stock length per rack if it fits."""
    by = {}
    for k in (2, 3, 6, 7, 8):
        sec = TEXT[k][1].split(" SHS")[0]
        for s in parts[k]:
            x, y, z = dims_of(s.val())
            by.setdefault(sec, {}).setdefault(k, []).append(max(x, y, z))
    out = []
    for sec, ks in by.items():
        items = sorted(ks)
        cuts = [l for k in ks for l in ks[k]]
        per_rack_m = sum(cuts) / 1000
        if len(set(cuts)) > 1 and sum(cuts) <= stock:
            n = 10
            note = "1 per rack: " + " + ".join(f"{len([c for c in cuts if c == v])} x {v:.0f}" for v in sorted(set(cuts), reverse=True))
        else:
            L = cuts[0]
            per = int(stock // L)
            n = math.ceil(10 * len(cuts) / per)
            note = f"{per} x {L:.0f} / length"
        out.append((f"{sec} SHS (item{'s' if len(items) > 1 else ''} {', '.join(map(str, items))})", f"{per_rack_m:.2f} m", f"{n} lengths  ({note})"))
    return out


def zig(sh, x, y0, y1, mapper):
    pts = [(x, y0), (x + 12, y0 + (y1 - y0) * 0.33), (x - 12, y0 + (y1 - y0) * 0.66), (x, y1)]
    sh.msp.add_lwpolyline([mapper(*q) for q in pts], dxfattribs={"layer": "THIN"})


def local(shape, shift, rot=None):
    s = shape.translate(cq.Vector(*shift))
    if rot:
        s = s.rotate(cq.Vector(0, 0, 0), cq.Vector(*rot[0]), rot[1])
    return s


def build_parts_sheet(p, parts, out):
    sh = Sheet()
    sh.rect(10, 10, 410, 287, "BORDER")
    asm = assembly(parts)
    # ---------------------------------------------------------------- cut list
    rows = []
    for k in range(1, 11):
        shp = parts[k][0].val()
        n = len(parts[k])
        kg = "-" if k == 10 else f"{mass_kg(shp):.2f}"
        rows.append([k, TEXT[k][0], TEXT[k][1], cut_len(k, shp), n, n * 10, TEXT[k][2], kg])
    colw = [12, 30, 60, 17, 11, 15, 210, 15]
    ybot = table(sh, 15, 282, colw, ["ITEM", "PART", "SECTION / MATERIAL", "CUT LEN", "QTY", "QTY x10", "OPERATIONS", "kg EA"], rows)
    sh.text("MATERIALS", (15 + 195, 284.2), 2.4, "CENTER")
    # ---------------------------------------------------------------- stock order
    y = ybot - 8
    sh.text("STOCK ORDER (8.0 m lengths)", (15, y), 2.6, "MLEFT"); sh.text("PER RACK", (92, y), 2.4, "MLEFT"); sh.text("PER 10 RACKS", (112, y), 2.4, "MLEFT")
    for i, (a, b, c) in enumerate(stock_lines(parts)):
        yy = y - 5.2 * (i + 1)
        sh.text(a, (15, yy), 2.2, "MLEFT"); sh.text(b, (92, yy), 2.2, "MLEFT"); sh.text(c, (112, yy), 2.2, "MLEFT")
    sh.text("FABRICATION NOTES", (235, y), 2.6, "MLEFT")
    for i, s in enumerate(NOTES):
        sh.text(s, (235, y - 4.6 * (i + 1)), 2.1, "MLEFT")
    # ---------------------------------------------------------------- part details (NTS)
    sh.text("PART DETAILS (NTS, dims mm)", (15, 169), 2.8, "MLEFT")
    yc, ytitle = 141, 162
    FRONT, XF = (0, -1, 0), (1, 0, 0)
    TOP, XT = (0, 0, 1), (1, 0, 0)

    # item 2: stub lying along X, hole near the top (right) end
    st = local(parts[2][0].val(), (-25, -25, -50), ((0, 1, 0), 90))
    sc = 1 / 2.5; ox = 20
    m = lambda x, y: (ox + x * sc, yc + y * sc)
    sh.view(st, FRONT, XF, m)
    L2 = dims_of(parts[2][0].val())[2]
    sh.text("ITEM 2  50x50x4", (ox, ytitle), 2.4, "MLEFT")
    sh.dim(m(0, -25), m(L2, -25), (ox, yc - 21), text=f"{L2:.0f}")
    sh.dim(m(L2 - 25, -25), m(L2, -25), (ox, yc - 29), text="25")
    # item 3: post, broken
    po = local(parts[3][0].val(), (-25, -25, -p.foot_h), ((0, 1, 0), 90))
    sc = 1 / 5; ox = 135
    L3 = dims_of(parts[3][0].val())[2]
    keep = [(0, 300), (L3 - 100, L3)]; gap = 60
    shifts = [0, (L3 - 100) - (300 + gap)]
    vis, _ = project(po, FRONT, XF)
    m = lambda x, y: (ox + x * sc, yc + y * sc)
    sh.draw_prims(clip_prims(edges_to_prims(vis), keep, shifts), m)
    zig(sh, 300, -20, 20, m); zig(sh, 300 + gap, -20, 20, m)
    sh.text("ITEM 3  40x40x3", (ox, ytitle), 2.4, "MLEFT")
    sh.dim(m(0, -20), m(300 + gap + 100, -20), (ox, yc - 13), text=f"{L3:.0f}")
    sh.dim(m(0, -20), m(p.post_hole_from_bottom, -20), (ox, yc - 21), text=f"{p.post_hole_from_bottom:.0f}")
    sh.dim(m(300 + gap + 100 - p.vent_from_top, -20), m(300 + gap + 100, -20), (ox, yc - 21), text=f"{p.vent_from_top:.0f}")
    # item 4: cap plate, top view and edge view beside it
    cp = local(parts[4][0].val(), (-25, -25, -(p.foot_h + p.post_len)))
    ox, oy = 258, 136
    m = lambda x, y: (ox + x, oy + y)
    sh.view(cp, TOP, XT, m)
    sh.view(cp, (1, 0, 0), (0, 1, 0), lambda x, y: (ox + 34 + x, oy - 20 + y + 20 - 2.5))
    sh.text("ITEM 4  5 PL", (ox - 20, ytitle), 2.4, "MLEFT")
    sh.dim(m(-20, -20), m(20, -20), (ox, oy - 25), text="40")
    sh.text(f"{p.cap_hole} DIA HOLE", (ox - 10, oy - 14.5), 1.8, "MLEFT")
    # item 5: locating pin
    pn = local(parts[5][0].val(), (-25, -25, -(p.foot_h + p.post_len)))
    ox, oy = 322, 126
    m = lambda x, y: (ox + x, oy + y)
    sh.view(pn, FRONT, XF, m)
    sh.text("ITEM 5  16 RD", (ox - 12, ytitle), 2.4, "MLEFT")
    sh.dim(m(8, 0), m(8, p.pin_len), (ox + 17, oy), angle=90, text=f"{p.pin_len:.0f}")
    sh.dim(m(-8, p.pin_len), m(8, p.pin_len), (ox, oy + p.pin_len + 5), text=f"{p.pin_d:.0f}")
    # item 9: gusset
    g = local(parts[9][0].val(), (-p.stub_w, -p.stub_w, -(p.rail_bottom - p.gusset_t)))
    sc = 1 / 2.5; ox, oy = 358, 122
    m = lambda x, y: (ox + x * sc, oy + y * sc)
    sh.view(g, TOP, XT, m)
    sh.text("ITEM 9  4 PL (1:2.5)", (ox - 6, ytitle), 2.4, "MLEFT")
    sh.dim(m(0, 0), m(p.gusset_leg, 0), (ox, oy - 6), text=f"{p.gusset_leg:.0f}")
    sh.dim(m(0, 0), m(0, p.gusset_leg), (ox - 6, oy), angle=90, text=f"{p.gusset_leg:.0f}")
    sh.text(f"{p.gusset_snip:.0f} SNIP", (ox + 10, oy + 6), 1.8, "MLEFT")
    # rails: items 6, 7, 8 (broken); title, then dimension, then the rail
    for i, (k, lab) in enumerate(((6, "ITEM 6  SIDE RAIL 50x50x2"), (7, "ITEM 7  END BEARER 50x50x2"), (8, "ITEM 8  CENTRE RAIL 50x50x3"))):
        s0 = parts[k][0].val()
        if k == 7:
            s0 = s0.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), -90)       # lay it along X like the others
        bb = s0.BoundingBox()
        rs = s0.translate(cq.Vector(-bb.xmin, -(bb.ymin + bb.ymax) / 2, -(p.rail_bottom + 25)))
        Lr = bb.xlen
        vis, _ = project(rs, FRONT, XF)
        keep = [(0, 250), (Lr - 250, Lr)]; shifts = [0, (Lr - 250) - (250 + 60)]
        ycr = 94.5 - 20 * i; ox = 232; sc = 1 / 6
        m = lambda x, y, ycr=ycr, ox=ox, sc=sc: (ox + x * sc, ycr + y * sc)
        sh.draw_prims(clip_prims(edges_to_prims(vis), keep, shifts), m)
        zig(sh, 250, -25, 25, m); zig(sh, 250 + 60, -25, 25, m)
        sh.text(lab, (ox, ycr + 13.5), 2.4, "MLEFT")
        sh.dim(m(0, 25), m(250 + 60 + 250, 25), (ox, ycr + 6.5), text=f"{Lr:.0f}")
    # ---------------------------------------------------------------- Detail B: corner, 1:5
    top_cap = p.foot_h + p.post_len + p.cap_t
    win = cq.Solid.makeBox(260, 260, 380, cq.Vector(-60, -60, -1))
    corner = asm.intersect(win)
    sc = 1 / 5; ox, oy = 146, 28
    m = lambda x, y: (ox + x * sc, oy + y * sc)
    sh.view(corner, FRONT, XF, m)
    sh.text("DETAIL B  CORNER 1:5", (ox + 30, oy - 12), 2.8, "CENTER")
    for z, off in ((p.rail_bottom, 12), (p.rail_top, 20), (p.foot_h + p.stub_len, 28)):
        sh.dim(m(-60, 0), m(-60, z), (ox - 60 * sc - off + 12, oy), angle=90, text=f"{z:.0f}")
    sh.text("ITEM 1", (ox + 50, oy + 2), 2.0, "MLEFT"); sh.line(m(95, 25), (ox + 49, oy + 3), "THIN")
    sh.text("ITEM 6 / 7", (ox + 50, oy + 30), 2.0, "MLEFT"); sh.line(m(150, 175), (ox + 49, oy + 31), "THIN")
    sh.text("M12 (ITEM 10)", (ox + 50, oy + 55), 2.0, "MLEFT"); sh.line(m(25, 275), (ox + 49, oy + 56), "THIN")
    # ---------------------------------------------------------------- Detail A: stacking joint, 1:5
    lowx = cq.Solid.makeBox(160, 160, 200, cq.Vector(-60, -60, top_cap - 140))
    upx = cq.Solid.makeBox(160, 160, 200, cq.Vector(-60, -60, top_cap - 1))
    low = asm.intersect(lowx)
    up = asm.translate(cq.Vector(0, 0, top_cap)).intersect(upx)
    both = cq.Compound.makeCompound([low, up])
    ox, oy = 38, 28; z0 = top_cap - 140
    m = lambda x, y: (ox + x * sc, oy + (y - z0) * sc)
    sh.view(both, FRONT, XF, m, hidden=True)
    sh.text("DETAIL A  STACKING JOINT 1:5", (ox + 12, oy - 12), 2.8, "CENTER")
    for t, zz, dx in (("UPPER RACK ITEMS 2 + 3", top_cap + 180, 25), ("ITEM 1 FOOT (UPPER RACK)", top_cap + 25, 60), ("ITEMS 4 + 5", top_cap + 2, 30), ("ITEM 3 LOWER RACK", top_cap - 90, 25)):
        sh.text(t, (ox + 34, oy + (zz - z0) * sc), 1.9, "MLEFT"); sh.line((ox + 33, oy + (zz - z0) * sc), m(dx, zz), "THIN")
    title_block(sh, 2, "CUT LIST AND PART DETAILS")
    sh.save(out)


if __name__ == "__main__":
    p, parts = build()
    build_parts_sheet(p, parts, "out_parts")
