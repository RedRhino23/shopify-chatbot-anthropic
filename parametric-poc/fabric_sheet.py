"""Sheet for the fabric expansion joint with installation rods: section, face view, BOM, notes, title block."""
import json
import sys

import cadquery as cq

from drawing_lib import Sheet
from fabric_model import FParams, build, masses
from joint_sheet import generic_title_block, wire_points
from parts_sheet import table

TEXT = {8: ("FASTENERS", "ASTM A193 B16 / ASTM A194 2H"), 7: ("LIFTING LUGS", "2 TON VRM-STARPOINT EYE NUT"), 6: ("GASKET", "PTFE"),
        5: ("INSTALLATION RODS", "ZINC ALLTHREAD"), 4: ("FLOW LINER", "316 S/S"), 3: ("REVERSE LINER", "316 S/S"),
        2: ("BACKING BAR", "316 S/S"), 1: ("FABRIC EXPANSION JOINT", "MULTI LAYER FABRIC")}


def cut_faces(parts, zmin=-2000):
    half = cq.Solid.makeBox(4000, 2000, 4000 - zmin - 2000 + 2000, cq.Vector(-2000, -2000, zmin))      # keeps y <= 0, z >= zmin
    out = {}
    for k, lst in parts.items():
        for s in lst:
            for f in s.val().intersect(half).Faces():
                if f.geomType() == "PLANE" and abs(f.Center().y) < 1e-4 and abs(f.normalAt().y) > 0.99:
                    out.setdefault(k, []).append(f)
    return out


def build_fabric_sheet(p, parts, job, out):
    sh = Sheet()
    sh.rect(10, 10, 410, 287, "BORDER")
    S = 1 / 7.0
    L, t = p.clear_len, p.t
    m = masses(p, parts)
    qty = {1: 1, 2: 2, 3: 1, 4: 1, 5: 4, 6: 2, 7: 2, 8: p.n_fasteners}
    # ---------------------------------------------------------------- section through the axis: whole joint, 1:7 (context)
    def draw_section(zmin, mapper):
        for k, fl in cut_faces(parts, zmin).items():
            for f in fl:
                loops = [wire_points(f.outerWire())] + [wire_points(w) for w in f.innerWires()]
                h = sh.msp.add_hatch(color=7, dxfattribs={"layer": "THIN"})
                if k in (5, 6, 7):
                    h.set_solid_fill()
                elif k == 1:
                    h.set_pattern_fill("ANSI37", scale=0.35)
                else:
                    h.set_pattern_fill("ANSI31", scale=0.45)
                for i, lp in enumerate(loops):
                    h.paths.add_polyline_path([mapper(*q) for q in lp], is_closed=True, flags=1 if i == 0 else 16)
                for lp in loops:
                    sh.msp.add_lwpolyline([mapper(*q) for q in lp], close=True, dxfattribs={"layer": "OUTLINE"})
    cy, ox = 118.0, 50.0
    sec = lambda x, z: (ox + x * S, cy + z * S)
    draw_section(-2000, sec)
    sh.line((ox - 14, cy), (ox + (L + t + 22) * S, cy), "CENTRE")
    sh.text("SECTION THROUGH AXIS 1:7", (ox + 20, cy - 560 * S - 10), 2.8, "CENTER")
    sh.dim(sec(-t, -p.outer / 2), sec(-t, p.outer / 2), (ox - 12, cy), angle=90, lfac=7)                                  # 950
    sh.dim(sec(L + t, -p.rev_od / 2), sec(L + t, p.rev_od / 2), (ox + (L + t) * S + 8, cy), angle=90, lfac=7)             # 790
    sh.dim(sec(L + t, -p.flow_od / 2), sec(L + t, p.flow_od / 2), (ox + (L + t) * S + 16, cy), angle=90, lfac=7)          # 760
    fy = cy - 560 * S - 24
    sh.text("FLOW", (ox - 8, fy), 4.5, "MLEFT")
    sh.line((ox + 12, fy), (ox + 40, fy), "OUTLINE")
    sh.msp.add_solid([(ox + 27, fy + 3.0), (ox + 40, fy), (ox + 27, fy - 3.0)], dxfattribs={"layer": "OUTLINE"})
    # ---------------------------------------------------------------- top edge detail 1:2 (where the rods, bars, gasket and liners are)
    D2 = 1 / 3.0
    dx0, dy0, zmin = 126.0, 104.0, 330.0
    dmap = lambda x, z: (dx0 + (x + t) * D2, dy0 + (z - zmin) * D2)
    draw_section(zmin, dmap)
    zt = dy0 + (560 - zmin) * D2
    sh.text("SECTION THROUGH AXIS, TOP EDGE 1:3", (dx0 + (L + 2 * t) * D2 / 2, dy0 - 10), 2.8, "CENTER")
    sh.dim(dmap(-t, 470), dmap(L + t, 470), (dx0, zt + 6), lfac=3)                                        # 231
    sh.dim(dmap(0, 470), dmap(L, 470), (dx0, zt + 14), lfac=3)                                            # 200
    sh.dim(dmap(L - p.rev_len, 340), dmap(L, 340), (dx0, dy0 - 3), lfac=3)                                # 100
    sh.dim(dmap(-t, 340), dmap(0, 340), (dx0, dy0 - 3), lfac=3, text="<>")                                 # bar thickness (inferred)
    tg = [(5, (100, 505), (+0, +12)), (2, (-t / 2, 442), (-14, +6)), (6, (-t - 1.5, 400), (-14, -8)),
          (1, (100, 404), (+8, +10)), (3, (170, 390), (+10, -14)), (4, (40, 379), (-10, -14))]
    for n, (x, z), (dx, dy) in tg:
        px, py = dmap(x, z)
        sh.balloon((px + dx, py + dy), n, (px, py))
    # ---------------------------------------------------------------- face view from the inlet (X toward the viewer)
    SP = 1 / 8.0
    ex, ey = 315.0, 135.0
    D, XD = (-1, 0, 0), (0, -1, 0)
    emap = lambda x, y: (ex + x * SP, ey + y * SP)
    sh.view(cq.Compound.makeCompound([s.val() for l in parts.values() for s in l]), D, XD, emap)
    hp = list(p.hole_pos)
    ps = p.pitch_sq / 2
    sh.msp.add_lwpolyline([emap(-ps, -ps), emap(ps, -ps), emap(ps, ps), emap(-ps, ps)], close=True, dxfattribs={"layer": "CENTRE"})
    sh.text("FACE VIEW FROM INLET 1:8", (ex, ey - 560 * SP - 5), 2.8, "CENTER")
    ytop = ey + 556 * SP
    xs = [emap(-h_, 0)[0] for h_ in reversed(hp)]                       # hole centres along the top edge (symmetrical)
    for a, b in zip(xs, xs[1:]):
        sh.dim((a, ey + ps * SP), (b, ey + ps * SP), (a, ytop + 7), lfac=8)
    sh.dim(emap(-p.outer / 2, p.outer / 2), emap(p.outer / 2, p.outer / 2), (ex, ytop + 16), lfac=8)                  # 950
    sh.dim(emap(p.outer / 2, -p.outer / 2), emap(p.outer / 2, p.outer / 2), (ex + 540 * SP + 6, ey), angle=90, lfac=8)
    sh.dim(emap(-p.flow_id / 2, 0), emap(p.flow_id / 2, 0), (ex, ey - 120 * SP), lfac=8)                                # 754
    sh.dim(emap(0, -p.flow_id / 2), emap(0, p.flow_id / 2), (ex - 140 * SP, ey), angle=90, lfac=8)
    sh.text("16 x \u00d8" + f"{p.hole_d:.0f}", (ex + 38, ey - 505 * SP - 12), 2.8, "MLEFT")
    sh.line(emap(-hp[1], -ps), (ex + 37, ey - 505 * SP - 10.5), "THIN")
    sh.balloon((ex + 560 * SP + 12, ey + 520 * SP), 7, emap(-p.eye_y, 540))
    # ---------------------------------------------------------------- BOM and notes
    rows = [[k, TEXT[k][0], TEXT[k][1], qty[k]] for k in range(8, 0, -1)]
    ybot = table(sh, 225, 283, [12, 52, 72, 14], ["ITEM", "DESCRIPTION", "MATERIAL", "QTY"], rows, rowh=5.2, hh=5.2, th=2.0)
    notes = list(job["notes"]) + [f"TOTAL WEIGHT APPROXIMATE: {m['total']:.0f}Kg"]
    sh.text("NOTES:", (15, 281), 2.4, "MLEFT")
    for i, ln in enumerate(notes):
        sh.text(f"{i + 1}.  {ln}", (15, 281 - 4.4 * (i + 1)), 2.2, "MLEFT")
    sh.text("INSTALLATION RODS TO BE REMOVED", (15, 233), 2.6, "MLEFT")
    sh.text("AFTER EXPANSION JOINT IS INSTALLED", (15, 228.5), 2.6, "MLEFT")
    generic_title_block(sh, job, "fabric_model.py")
    sh.save(out)
    return m


if __name__ == "__main__":
    job = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "fabric_job.example.json", encoding="utf-8"))
    p, parts = build()
    print(build_fabric_sheet(p, parts, job, "out_fabric"))
