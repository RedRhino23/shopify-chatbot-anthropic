"""Sheet 1: general arrangement, generated from the 3D model."""
import cadquery as cq

from drawing_lib import Sheet, proj_pt
from rack_model import Params, build, mass_kg

S = 1 / 20.0
DATE = "11/11/2026"
DWG = "RI-RACK-001"


def assembly(parts):
    return cq.Compound.makeCompound([s.val() for lst in parts.values() for s in lst])


def title_block(sh, sheet_no, title2, rev="F"):
    x0, y0, x1, y1 = 215.0, 10.0, 410.0, 50.0
    sh.rect(x0, y0, x1, y1, "TABLE")
    xm = 330.0
    sh.line((xm, y0), (xm, y1)); sh.line((x0, 38.0), (x1, 38.0))
    sh.text("RAVEN INDUSTRIES PTY LTD", (x0 + 3, 44), 3.2, "MLEFT")
    sh.text("UMBRELLA BOX STACKING RACK 15 BOX", (x0 + 3, 31), 2.8, "MLEFT")
    sh.text(title2, (x0 + 3, 25), 2.8, "MLEFT")
    sh.text(f"DWG {DWG}  REV {rev}", (xm + 3, 44), 2.8, "MLEFT")
    sh.text(f"SHEET {sheet_no} OF 2  A3", (xm + 3, 31), 2.5, "MLEFT")
    sh.text(f"DATE {DATE}  mm", (xm + 3, 25), 2.5, "MLEFT")
    sh.text("PROOF OF CONCEPT: GENERATED FROM THE 3D MODEL (rack_model.py), NOT HAND DRAWN", (x0 + 3, 14), 1.8, "MLEFT")


def build_ga(p, parts, out):
    sh = Sheet()
    sh.rect(10, 10, 410, 287, "BORDER")
    asm = assembly(parts)
    L, W = p.long_outer, p.wide_outer
    bb = assembly(parts).BoundingBox()                    # heights are read from the model, not typed in
    pin_top = bb.zmax                                     # top of the locating pin
    top_cap = pin_top - (p.pin_len - p.cap_t)             # top of the cap plate
    # ------------------------------------------------ FRONT VIEW (long side)
    fx, fy = 62.0, 168.0
    fmap = lambda x, y: (fx + x * S, fy + y * S)
    D_FRONT, X_FRONT = (0, -1, 0), (1, 0, 0)
    sh.view(asm, D_FRONT, X_FRONT, fmap)
    bx0, bx1 = (L - p.box[0]) / 2, (L + p.box[0]) / 2
    z0, z1 = p.rail_top, p.rail_top + p.boxes_high * p.box[2]
    sh.msp.add_lwpolyline([fmap(bx0, z0), fmap(bx1, z0), fmap(bx1, z1), fmap(bx0, z1)], close=True, dxfattribs={"layer": "PHANTOM"})
    for k in range(1, p.boxes_high):
        sh.line(fmap(bx0, z0 + k * p.box[2]), fmap(bx1, z0 + k * p.box[2]), "PHANTOM")
    sh.text("FRONT VIEW (LONG SIDE) 1:20", (fx + L * S / 2, fy - 20), 3.0, "CENTER")
    sh.text(f"{p.boxes_high * p.boxes_wide} x boxes, max {p.box[0]:.0f} x {p.box[1]:.0f} x {p.box[2]:.0f} (phantom)", (fx + L * S / 2, fy + 40), 2.2, "CENTER")
    sh.text(f"{p.boxes_high} high x {p.boxes_wide} wide, {p.swl_kg:.0f} kg", (fx + L * S / 2, fy + 36), 2.2, "CENTER")
    sh.dim(fmap(bx0, 0), fmap(0, 0), (fx, fy - 9))
    sh.dim(fmap(0, 0), fmap(L, 0), (fx, fy - 9))
    sh.dim(fmap(L, 0), fmap(bx1, 0), (fx, fy - 9))
    for z, off in ((p.rail_bottom, 12), (p.rail_top, 22), (p.foot_h + p.stub_len, 32)):
        sh.dim(fmap(0, 0), fmap(0, z), (fx - off, fy), angle=90)
    sh.dim(fmap(L, 0), fmap(L, top_cap), (fx + (bx1 + 130) * S, fy), angle=90, text="<> TOP OF CAP")
    for n, tgt, bal in ((1, (70, 48.5), (-300, 220)), (2, (25, 270), (-150, 330)), (3, (25, 800), (-200, 780)), (6, (1000, 175), (1300, -250)), ):
        sh.balloon(fmap(*bal), n, fmap(*tgt))
    # ------------------------------------------------ PLAN VIEW
    px, py = 255.0, 178.0
    pmap = lambda x, y: (px + x * S, py + y * S)
    sh.view(asm, (0, 0, 1), (1, 0, 0), pmap)
    by0 = (W - p.boxes_wide * p.box[1]) / 2
    by1 = by0 + p.boxes_wide * p.box[1]
    sh.msp.add_lwpolyline([pmap(bx0, by0), pmap(bx1, by0), pmap(bx1, by1), pmap(bx0, by1)], close=True, dxfattribs={"layer": "PHANTOM"})
    for k in range(1, p.boxes_wide):
        sh.line(pmap(bx0, by0 + k * p.box[1]), pmap(bx1, by0 + k * p.box[1]), "PHANTOM")
    for cxm in (L / 2 - p.min_fork_spread / 2, L / 2 + p.min_fork_spread / 2):         # fork tines, entry from the long side
        sh.msp.add_lwpolyline([pmap(cxm - 75, -0), pmap(cxm + 75, 0), pmap(cxm + 75, p.fork_reach), pmap(cxm - 75, p.fork_reach)], close=True, dxfattribs={"layer": "PHANTOM"})
    sh.text("PLAN VIEW 1:20", (px + L * S / 2, py - 30), 3.0, "CENTER")
    sh.dim(pmap(0, W), pmap(L, W), (px, py + W * S + 6))
    sh.dim(pmap(bx0, W), pmap(bx1, W), (px, py + W * S + 14), text="<> MAX BOX")
    sh.dim(pmap(L, 0), pmap(L, W), (px + L * S + 4, py), angle=90)
    sh.dim(pmap(L, 0), pmap(L, W / 2), (px + L * S + 12, py), angle=90)
    sh.dim(pmap(L / 2 - p.min_fork_spread / 2, -10), pmap(L / 2 + p.min_fork_spread / 2, -10), (px, py - 12), text="<> MIN SPREAD")
    sh.dim(pmap(bx0 - 30, 0), pmap(bx0 - 30, p.fork_reach), (px + bx0 * S - 6, py), angle=90, text="<> FORK")
    sh.text("FORK ENTRY, LONG SIDE ONLY", (px + 4, py - 20), 2.0, "MLEFT")
    for n, tgt, bal in ((9, (75, 75), (-500, 1450)), (5, (25, 25), (-300, 100)), (4, (L - 25, W - 25), (2300, 1450)), (8, (1000, W / 2), (1000, 1280))):
        sh.balloon(pmap(*bal), n, pmap(*tgt))
    # ------------------------------------------------ END VIEW
    ex, ey = 62.0, 44.0
    emap = lambda x, y: (ex + x * S, ey + y * S)
    sh.view(asm, (1, 0, 0), (0, 1, 0), emap)
    ey0 = by0
    sh.msp.add_lwpolyline([emap(by0, z0), emap(by1, z0), emap(by1, z1), emap(by0, z1)], close=True, dxfattribs={"layer": "PHANTOM"})
    for k in range(1, p.boxes_high):
        sh.line(emap(by0, z0 + k * p.box[2]), emap(by1, z0 + k * p.box[2]), "PHANTOM")
    for k in range(1, p.boxes_wide):
        sh.line(emap(by0 + k * p.box[1], z0), emap(by0 + k * p.box[1], z1), "PHANTOM")
    sh.text("END VIEW 1:20", (ex + W * S / 2, ey - 22), 3.0, "CENTER")
    sh.dim(emap(0, 0), emap(W, 0), (ex, ey - 9))
    sh.balloon(emap(W + 200, 700), 7, emap(W - 120, 175))
    # ------------------------------------------------ ISOMETRIC (NTS)
    ISO_D, ISO_X = (1, -1, 1), (1, 1, 0)
    iso_s = 1 / 40.0
    cx0, cy0 = proj_pt((L / 2, W / 2, 0), ISO_D, ISO_X)
    imap = lambda x, y: (335 + (x - cx0) * iso_s, 100 + (y - cy0) * iso_s)
    sh.view(asm, ISO_D, ISO_X, imap)
    sh.text("ISOMETRIC NTS", (335, 58), 3.0, "CENTER")
    ip = lambda P: imap(*proj_pt(P, ISO_D, ISO_X))
    # balloons placed by a paper offset (mm) from the part they point to, so they stay clear of the drawing
    for n, P, off in ((1, (25, 25, 45), (-17, -6)), (2, (25, 25, 250), (-17, 6)), (3, (25, 25, 800), (-14, 16)),
                      (6, (1000, 25, 200), (-4, -12)), (7, (L - 25, 800, 200), (9, 16))):
        tx, ty = ip(P)
        sh.balloon((tx + off[0], ty + off[1]), n, (tx, ty))
    # ------------------------------------------------ GENERAL notes (values come from the model)
    total = sum(mass_kg(s.val()) for lst in parts.values() for s in lst)
    stack3 = 3 * top_cap
    lines = ["GENERAL",
             f"SWL {p.swl_kg:.0f} kg ({p.boxes_high * p.boxes_wide} boxes @ {p.swl_kg / (p.boxes_high * p.boxes_wide):.0f} kg). Rack approx {total:.0f} kg.",
             f"Stack max 3 high (approx {stack3 / 1000:.1f} m) on level slab only.",
             f"Fork entry long side only. Forks min {p.min_fork_spread:.0f} apart,",
             "lifting on centre rail (item 8).",
             f"Load centre approx {W / 2:.0f}: check forklift capacity plate.",
             "Lift one rack at a time. See sheet 2 for cut list and details."]
    for i, s in enumerate(lines):
        sh.text(s, (170, 108 - i * 4.4), 3.0 if i == 0 else 2.3, "MLEFT")
    title_block(sh, 1, "GENERAL ARRANGEMENT")
    sh.save(out)
    return total, stack3


if __name__ == "__main__":
    p, parts = build()
    print(build_ga(p, parts, "out_ga"))
