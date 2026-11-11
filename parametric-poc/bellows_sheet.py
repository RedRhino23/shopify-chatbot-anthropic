"""Sheet for the metallic bellows: axial section (cut from the 3D model), end view, BOM, bellows data, notes, title block."""
import json
import math
import sys

import cadquery as cq

from bellows_model import BParams, build, masses
from drawing_lib import Sheet
from joint_sheet import generic_title_block, section_faces, wire_points
from parts_sheet import table


def build_bellows_sheet(p, parts, job, out):
    sh = Sheet()
    sh.rect(10, 10, 410, 287, "BORDER")
    S = 1 / 2.5
    tf, L = p.flange_t, p.length
    R, Ri = p.flange_od / 2, p.bore / 2
    m = masses(p, parts)
    cx, cy = 125.0, 135.0
    ox = cx - p.face_to_face / 2 * S
    sec = lambda x, z: (ox + (z + tf) * S, cy + x * S)
    for k, fl in section_faces(parts).items():
        for f in fl:
            loops = [wire_points(f.outerWire())] + [wire_points(w) for w in f.innerWires()]
            h = sh.msp.add_hatch(color=7, dxfattribs={"layer": "THIN"})
            if k == 2:
                h.set_pattern_fill("ANSI31", scale=0.5)
            else:
                h.set_solid_fill()
            for i, lp in enumerate(loops):
                h.paths.add_polyline_path([sec(*q) for q in lp], is_closed=True, flags=1 if i == 0 else 16)
            for lp in loops:
                sh.msp.add_lwpolyline([sec(*q) for q in lp], close=True, dxfattribs={"layer": "OUTLINE"})
    xr = ox + p.face_to_face * S
    sh.line((ox - 8, cy), (xr + 8, cy), "CENTRE")
    sh.text("SECTION THROUGH AXIS 1:2.5", (cx, cy - R * S - 28), 3.0, "CENTER")
    # dimensions (all measured from the model)
    sh.dim((ox, cy + R * S), (xr, cy + R * S), (ox, cy + R * S + 18), lfac=2.5)                          # face to face
    sh.dim((ox + tf * S, cy + Ri * S), (xr - tf * S, cy + Ri * S), (ox, cy + R * S + 8), lfac=2.5, text="<> BELLOWS")
    sh.dim((xr, cy - R * S), (xr, cy + R * S), (xr + 14, cy), angle=90, text="<> O.D", lfac=2.5)
    sh.dim((ox, cy - Ri * S), (ox, cy + Ri * S), (ox - 14, cy), angle=90, text="DN<>", lfac=2.5)
    crown_r = Ri + p.T / 2 + p.height + p.T / 2
    sh.dim((xr - 4, cy - crown_r * S), (xr - 4, cy + crown_r * S), (xr - 22, cy), angle=90, text="<> O.D BELLOWS", lfac=2.5)
    sh.text(f"{p.holes} HOLES Ø{p.hole_d}", (ox - 31, cy), 2.6, "CENTER", rot=90)
    sh.text(f"ON {p.pcd} PCD", (ox - 26.5, cy), 2.6, "CENTER", rot=90)
    sh.line((ox - 6, cy + p.pcd / 2 * S), (ox + tf * S + 4, cy + p.pcd / 2 * S), "CENTRE")
    sh.line((ox - 6, cy - p.pcd / 2 * S), (ox + tf * S + 4, cy - p.pcd / 2 * S), "CENTRE")
    # balloons
    zc = p.tangent + 2 * (p.pitch / 4)
    sh.balloon((ox + (zc + tf) * S, cy - crown_r * S - 16), 1, (ox + (zc + tf) * S, cy - crown_r * S))
    sh.balloon((ox + 2, cy - R * S - 12), 2, (ox + tf * S / 2, cy - R * S + 3))
    zl = ox + (tf + L * 0.35) * S
    sh.balloon((zl, cy - (Ri - p.liner_gap) * S + 14), 3, (zl, cy - (Ri - p.liner_gap - p.liner_t / 2) * S))
    fy = cy - R * S - 40
    sh.text("FLOW", (cx - 26, fy), 5.0, "MLEFT")
    sh.line((cx - 5, fy), (cx + 28, fy), "OUTLINE")
    sh.msp.add_solid([(cx + 12, fy + 3.2), (cx + 28, fy), (cx + 12, fy - 3.2)], dxfattribs={"layer": "OUTLINE"})
    # end view
    ex, ey = 290.0, 135.0
    emap = lambda x, y: (ex + x * S, ey + y * S)
    sh.view(cq.Compound.makeCompound([s.val() for l in parts.values() for s in l]), (0, 0, -1), (1, 0, 0), emap)
    sh.msp.add_circle((ex, ey), p.pcd / 2 * S, dxfattribs={"layer": "CENTRE"})
    sh.line((ex - R * S - 6, ey), (ex + R * S + 6, ey), "CENTRE"); sh.line((ex, ey - R * S - 6), (ex, ey + R * S + 6), "CENTRE")
    sh.text("END VIEW 1:2.5", (ex, ey - R * S - 8), 3.0, "CENTER")
    sh.text(f"{p.pcd} PCD", (ex + 6, ey + p.pcd / 2 * S + 3), 2.0, "MLEFT")
    # BOM
    rows = [[1, "METALLIC BELLOWS", f"{p.bellows_mat}, {p.plies} PLY x {p.ply_t}", 1],
            [2, "FLANGES", f"ASME B16.5 CL150 {p.flange_mat}", len(parts[2])],
            [3, "INTERNAL LINER", p.bellows_mat, 1]]
    ybot = table(sh, 225, 283, [12, 52, 72, 14], ["ITEM", "DESCRIPTION", "MATERIAL", "QTY"], rows[::-1], rowh=5.4, hh=5.4, th=2.0)
    y = ybot - 8
    data = [f"BELLOWS: {p.n_conv} CONVOLUTIONS, PITCH {p.pitch:.0f}, HEIGHT {p.height:.0f}", f"WALL: {p.plies} PLY x {p.ply_t} {p.bellows_mat}",
            f"FREE LENGTH (BELLOWS) {p.length:.0f}, FACE TO FACE {p.face_to_face:.0f}",
            f"EFFECTIVE AREA {math.pi / 4 * (p.bore + p.height) ** 2 / 100:.0f} cm2 (MEAN DIA {p.bore + p.height:.0f})"]
    notes = list(job["notes"]) + data + [f"TOTAL WEIGHT: APPROXIMATE {m['total']:.0f} Kg"]
    sh.text("NOTES:", (225, y), 2.4, "MLEFT")
    for i, ln in enumerate(notes):
        sh.text(f"{i + 1}.  {ln}", (225, y - 4.2 * (i + 1)), 2.1, "MLEFT")
    generic_title_block(sh, job, "bellows_model.py")
    sh.save(out)
    return m


if __name__ == "__main__":
    job = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "bellows_job.example.json", encoding="utf-8"))
    p, parts = build()
    print(build_bellows_sheet(p, parts, job, "out_bellows"))
