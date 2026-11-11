"""Sheet for the rubber expansion joint: axial section (cut from the 3D model), end view, BOM, notes, title block."""
import math

import cadquery as cq
from OCP.BRepTools import BRepTools_WireExplorer

from drawing_lib import Sheet
from joint_model import JParams, build, masses
from parts_sheet import table


def wire_points(wire, n_arc=20):
    """Ordered (x, z) points around a wire, arcs and circles discretised."""
    pts = []
    exp = BRepTools_WireExplorer(wire.wrapped)
    while exp.More():
        e = cq.Edge(exp.Current())
        if e.geomType() == "LINE":
            seg = [e.startPoint(), e.endPoint()]
        else:
            seg = [e.positionAt(i / n_arc) for i in range(n_arc + 1)]
        q = [(v.x, v.z) for v in seg]
        if pts and math.dist(pts[-1], q[0]) > math.dist(pts[-1], q[-1]):
            q.reverse()
        pts.extend(q if not pts else q[1:])
        exp.Next()
    return pts


def section_faces(parts):
    """Cut every solid by the plane y = 0 (keep y <= 0) and return {item: [face, ...]} of the planar cut faces."""
    half = cq.Solid.makeBox(2000, 1000, 1000, cq.Vector(-1000, -1000, -400))
    out = {}
    for k, lst in parts.items():
        for s in lst:
            cut = s.val().intersect(half)
            for f in cut.Faces():
                if f.geomType() == "PLANE" and abs(f.Center().y) < 1e-4 and abs(f.normalAt().y) > 0.99:
                    out.setdefault(k, []).append(f)
    return out


def generic_title_block(sh, job, sheet_label="GENERAL ARRANGEMENT"):
    x0, y0, x1, y1 = 215.0, 10.0, 410.0, 50.0
    sh.rect(x0, y0, x1, y1, "TABLE")
    xm = 335.0
    sh.line((xm, y0), (xm, y1)); sh.line((x0, 38.0), (x1, 38.0))
    sh.text(job["company"], (x0 + 3, 44), 2.8, "MLEFT")
    for i, ln in enumerate(job["title_lines"]):
        sh.text(ln, (x0 + 3, 34.5 - i * 4.3), 2.2, "MLEFT")
    sh.text(f"NUMBER  {job['drawing_no']}", (xm + 3, 44), 2.4, "MLEFT")
    sh.text(f"REV  {job['rev']}", (xm + 3, 33), 2.4, "MLEFT")
    sh.text(f"DATE  {job['date']}", (xm + 3, 27), 2.2, "MLEFT")
    sh.text("SCALE  N.T.S", (xm + 3, 21), 2.2, "MLEFT")
    sh.text(job["doc_no"], (x1 - 3, 54), 3.0, "RIGHT")
    sh.text("PROOF OF CONCEPT: GENERATED FROM THE 3D MODEL (joint_model.py)", (x0 + 3, 13), 1.6, "MLEFT")


def build_joint_sheet(p, parts, job, out):
    sh = Sheet()
    sh.rect(10, 10, 410, 287, "BORDER")
    L, R, Ri = p.length, p.flange_od / 2, p.bore / 2
    m = masses(p, parts)
    S = 1 / 2.5
    # ------------------------------------------------------------ axial section (axis horizontal, flow left to right)
    cx, cy = 120.0, 130.0
    ox = cx - L / 2 * S
    sec = lambda x, z: (ox + z * S, cy + x * S)
    faces = section_faces(parts)
    for k, fl in faces.items():
        for f in fl:
            loops = [wire_points(f.outerWire())] + [wire_points(w) for w in f.innerWires()]
            h = sh.msp.add_hatch(color=7, dxfattribs={"layer": "THIN"})
            h.set_pattern_fill("ANSI31" if k == 2 else "ANSI37", scale=0.5 if k == 2 else 0.35)
            for i, lp in enumerate(loops):
                h.paths.add_polyline_path([sec(*q) for q in lp], is_closed=True, flags=1 if i == 0 else 16)
            for lp in loops:
                sh.msp.add_lwpolyline([sec(*q) for q in lp], close=True, dxfattribs={"layer": "OUTLINE"})
    sh.line((ox - 8, cy), (ox + L * S + 8, cy), "CENTRE")
    sh.text("SECTION THROUGH AXIS 1:2.5", (cx, cy - R * S - 30), 3.0, "CENTER")
    xr = ox + L * S
    sh.dim((ox, cy + R * S), (xr, cy + R * S), (ox, cy + R * S + 12), lfac=2.5)                   # 150
    sh.dim((xr, cy - R * S), (xr, cy + R * S), (xr + 14, cy), angle=90, text="<> O.D", lfac=2.5)    # 343 O.D
    sh.dim((ox, cy - Ri * S), (ox, cy + Ri * S), (ox - 14, cy), angle=90, text="DN<>", lfac=2.5)   # DN200
    t0, t1 = p.flange_face_t, p.flange_face_t + p.ring_t
    sh.dim((ox + t0 * S, cy + R * S), (ox + t1 * S, cy + R * S), (ox, cy + R * S + 5), lfac=2.5)   # 12
    hx = ox + (p.flange_face_t + p.ring_t) * S / 2
    sh.text(f"{p.holes} HOLES Ø{p.hole_d}", (ox - 31, cy), 2.6, "CENTER", rot=90)
    sh.text(f"ON {p.pcd} PCD", (ox - 26.5, cy), 2.6, "CENTER", rot=90)
    sh.line((ox - 6, cy + p.pcd / 2 * S), (ox + t1 * S + 4, cy + p.pcd / 2 * S), "CENTRE")
    sh.line((ox - 6, cy - p.pcd / 2 * S), (ox + t1 * S + 4, cy - p.pcd / 2 * S), "CENTRE")
    zc = L / 2
    arch_bot = (ox + zc * S, cy - (Ri + p.tube_wall + p.arch_h) * S)
    sh.balloon((arch_bot[0] - 6, arch_bot[1] - 16), 1, arch_bot)
    sh.text("UNFILLED ARCH", (arch_bot[0] + 1, arch_bot[1] - 16), 2.4, "MLEFT")
    sh.balloon((ox - 12, cy - R * S - 10), 2, (ox + 14 * S, cy - R * S + 2))
    sh.balloon((xr + 28, cy - p.pcd / 2 * S), 3, (xr - 1, cy - p.pcd / 2 * S))
    # FLOW arrow
    fy = cy - R * S - 42
    sh.text("FLOW", (cx - 26, fy), 5.0, "MLEFT")
    sh.line((cx - 5, fy), (cx + 28, fy), "OUTLINE")
    sh.msp.add_solid([(cx + 12, fy + 3.2), (cx + 28, fy), (cx + 12, fy - 3.2)], dxfattribs={"layer": "OUTLINE"})
    # ------------------------------------------------------------ end view (looking at the z = 0 face)
    ex, ey = 290.0, 135.0
    emap = lambda x, y: (ex + x * S, ey + y * S)
    sh.view(cq.Compound.makeCompound([s.val() for lst in parts.values() for s in lst]), (0, 0, -1), (1, 0, 0), emap)
    sh.msp.add_circle((ex, ey), p.pcd / 2 * S, dxfattribs={"layer": "CENTRE"})
    sh.line((ex - R * S - 6, ey), (ex + R * S + 6, ey), "CENTRE"); sh.line((ex, ey - R * S - 6), (ex, ey + R * S + 6), "CENTRE")
    sh.text("END VIEW 1:2.5", (ex, ey - R * S - 8), 3.0, "CENTER")
    a = math.radians(45)
    sh.text(f"{p.pcd} PCD", (ex + 6, ey + p.pcd / 2 * S + 3), 2.0, "MLEFT")
    # ------------------------------------------------------------ BOM
    rows = [[3, "FASTENERS", "ASTM A193 B16 / ASTM A194 2H", p.n_fasteners],
            [2, "BACKING BARS", "316 S.S", len(parts[2])],
            [1, "RUBBER EXPANSION JOINT", "REINFORCED BUTYL RUBBER", 1]]
    ybot = table(sh, 225, 283, [12, 52, 72, 14], ["ITEM", "DESCRIPTION", "MATERIAL", "QTY"], rows[::-1][::-1], rowh=5.4, hh=5.4, th=2.0)
    # ------------------------------------------------------------ notes (job words) with the weight from the model
    notes = list(job["notes"]) + [f"TOTAL WEIGHT: APPROXIMATE {m['total']:.0f} Kg"]
    y = ybot - 8
    sh.text("NOTES:", (225, y), 2.4, "MLEFT")
    for i, ln in enumerate(notes):
        sh.text(f"{i + 1}.  {ln}", (225, y - 4.4 * (i + 1)), 2.2, "MLEFT")
    generic_title_block(sh, job)
    sh.save(out)
    return m


if __name__ == "__main__":
    import json, sys
    job = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "joint_job.example.json"))
    p, parts = build()
    print(build_joint_sheet(p, parts, job, "out_joint"))
