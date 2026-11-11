"""Sheet for the tied metal expansion joint: section through the rods, end view, BOM, notes, title block."""
import json
import sys

import cadquery as cq

from drawing_lib import Sheet
from fabric_sheet import cut_faces
from joint_sheet import generic_title_block, wire_points
from parts_sheet import table
from tied_model import TParams, build, masses


def build_tied_sheet(p, parts, job, out):
    sh = Sheet()
    sh.rect(10, 10, 410, 287, "BORDER")
    S = 1 / 2.5
    Lo, c, ct = p.Lo, p.c, p.collar_t
    m = masses(p, parts)
    cy, ox = 150.0, 40.0
    sec = lambda x, z: (ox + z * S, cy + x * S)
    for k, fl in cut_faces(parts).items():
        for f in fl:
            loops = [wire_points(f.outerWire())] + [wire_points(w) for w in f.innerWires()]
            h = sh.msp.add_hatch(color=7, dxfattribs={"layer": "THIN"})
            if k == 1:
                h.set_solid_fill()
            else:
                h.set_pattern_fill("ANSI31", scale=0.45)
            for i, lp in enumerate(loops):
                h.paths.add_polyline_path([sec(*q) for q in lp], is_closed=True, flags=1 if i == 0 else 16)
            for lp in loops:
                sh.msp.add_lwpolyline([sec(*q) for q in lp], close=True, dxfattribs={"layer": "OUTLINE"})
    sh.line((ox - 40 * S - 4, cy), (ox + (Lo + 40) * S + 4, cy), "CENTRE")
    top = cy + p.B / 2 * S
    zc = p.tangent_outer + p.n_conv * p.pitch / 2
    B2 = p.B / 2
    sh.dim(sec(B2, 0), sec(B2, Lo), (ox, top + 9), lfac=2.5)                                                   # Lo
    sh.dim(sec(B2, zc), sec(B2, Lo - zc), (ox, top + 17), lfac=2.5, text="<> (BELLOWS CENTRES)")              # l*
    for z in (zc, Lo - zc):
        sh.line(sec(B2 + 2, z), sec(100, z), "CENTRE")
    sh.dim(sec(-B2, Lo + p.rod_ext), sec(B2, Lo + p.rod_ext), (ox + (Lo + p.rod_ext + 18) * S, cy), angle=90, lfac=2.5)   # B
    sh.dim(sec(-p.d1 / 2, 0), sec(p.d1 / 2, 0), (ox - 14, cy), angle=90, lfac=2.5, text="<> (d1)")             # OFD
    sh.dim(sec(-B2, ct), sec(-B2, ct + c), (ox, cy - B2 * S - 8), lfac=2.5)                                    # c
    sh.text("SECTION THROUGH THE TIE RODS 1:2.5", (ox + Lo * S / 2, cy - p.B / 2 * S - 22), 3.0, "CENTER")
    tg = [(1, (zc, -122), (+14, +24)), (2, (Lo / 2, -105), (0, -26)), (3, (2, 118), (-12, 22)), (4, (ct + c / 2, 160), (-8, 24)), (5, (Lo / 2, p.rod_r), (0, -22))]
    for n, (z, x), (dx, dy) in tg:
        px, py = sec(x, z)
        sh.balloon((px + dx, py + dy), n, (px, py))
    fy = cy - p.B / 2 * S - 36
    sh.text("FLOW", (ox + Lo * S / 2 - 24, fy), 5.0, "MLEFT")
    sh.line((ox + Lo * S / 2 - 4, fy), (ox + Lo * S / 2 + 28, fy), "OUTLINE")
    sh.msp.add_solid([(ox + Lo * S / 2 + 12, fy + 3.2), (ox + Lo * S / 2 + 28, fy), (ox + Lo * S / 2 + 12, fy - 3.2)], dxfattribs={"layer": "OUTLINE"})
    # ---------------------------------------------------------------- end view (looking at the inlet collar face)
    SE = 1 / 4.0
    ex, ey = 352.0, 160.0
    emap = lambda x, y: (ex + x * SE, ey + y * SE)
    sh.view(cq.Compound.makeCompound([s.val() for l in parts.values() for s in l]), (0, 0, -1), (1, 0, 0), emap)
    sh.msp.add_circle((ex, ey), p.pcd / 2 * SE, dxfattribs={"layer": "CENTRE"})
    sh.line((ex - p.B / 2 * SE - 6, ey), (ex + p.B / 2 * SE + 6, ey), "CENTRE"); sh.line((ex, ey - p.flange_od / 2 * SE - 6), (ex, ey + p.flange_od / 2 * SE + 6), "CENTRE")
    sh.text("END VIEW 1:4", (ex, ey - p.flange_od / 2 * SE - 8), 3.0, "CENTER")
    sh.dim(emap(-p.B / 2, -p.flange_od / 2), emap(p.B / 2, -p.flange_od / 2), (ex, ey - p.flange_od / 2 * SE - 16), lfac=4, text="<> OVER RODS")
    sh.text(f"{p.holes} HOLES DIA {p.hole_d:.0f} ON {p.pcd:.0f} PCD", (ex, ey + p.flange_od / 2 * SE + 9), 2.4, "CENTER")
    sh.text("EN 1092-1 PN10 DN200", (ex, ey + p.flange_od / 2 * SE + 4.5), 2.4, "CENTER")
    # ---------------------------------------------------------------- BOM and notes
    rows = [[5, "TIE RODS", f"M{p.rod_d:.0f} ALLTHREAD, 2 NUTS PER END", p.n_rods],
            [4, "LOOSE FLANGES", "CARBON STEEL, EN 1092-1 PN10", 2],
            [3, "STUB END COLLARS", "CARBON STEEL", 2],
            [2, "MIDDLE PIPE", f"DN200 SCH 40 ({p.pipe_wall} WALL)", 1],
            [1, "BELLOWS", f"316L, {p.plies} PLY x {p.ply_t}, {p.n_conv} CONV.", 2]]
    ybot = table(sh, 215, 283, [12, 50, 82, 14], ["ITEM", "DESCRIPTION", "MATERIAL", "QTY"], rows, rowh=5.2, hh=5.2, th=1.9)
    notes = list(job["notes"]) + [f"TOTAL WEIGHT APPROXIMATE: {m['total']:.0f} Kg"]
    y = 281
    sh.text("NOTES:", (15, y), 2.4, "MLEFT")
    for i, ln in enumerate(notes):
        sh.text(f"{i + 1}.  {ln}", (15, y - 4.2 * (i + 1)), 2.0, "MLEFT")
    generic_title_block(sh, job, "tied_model.py")
    sh.save(out)
    return m


if __name__ == "__main__":
    job = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "tied_job.example.json", encoding="utf-8"))
    p, parts = build()
    print(build_tied_sheet(p, parts, job, "out_tied"))
