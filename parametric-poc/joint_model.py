"""Parametric 3D model of a single-arch rubber expansion joint (unfilled arch), with backing rings and bolt sets.
All sizes in mm. Axis = Z, face to face along Z, flow from z = 0 to z = L.

Stated on the issued drawing (D17530M-1 style): face to face 150, bore DN200, flange OD 343, 8 holes dia 22.4 on 298.5 PCD,
backing bar 12 thick, 16 fasteners, reinforced butyl rubber, 316 S.S backing bars, approx weight 16 kg.
Assumed (the drawing is N.T.S., radial sizes are not to scale): tube wall, arch width/height, rubber flange thickness,
backing ring inside diameter, rubber density, bolt size. They are all in Params so they can be changed in one place.
"""
import math
from dataclasses import dataclass

import cadquery as cq

STEEL_316 = 7.98e-6      # kg/mm3
STEEL_BOLT = 7.85e-6


@dataclass
class JParams:
    length: float = 150.0          # face to face   (drawing)
    bore: float = 200.0            # DN200          (drawing)
    flange_od: float = 343.0       # 343 O.D        (drawing)
    pcd: float = 298.5             #                (drawing)
    holes: int = 8                 #                (drawing)
    hole_d: float = 22.4           #                (drawing)
    hole_offset_deg: float = 22.5  # holes straddle the centrelines (ASME B16.5); the drawing does not show the angle (assumed)
    ring_t: float = 12.0           # backing bar thickness (drawing, item 2)
    flange_face_t: float = 8.0     # rubber flange face thickness (assumed: 20 total flange, less the 12 ring)
    ring_id: float = 230.0         # backing ring inside diameter (assumed)
    tube_wall: float = 10.0        # tube and arch wall (assumed; matches the drawn arch wall at true axial scale)
    arch_w: float = 37.0           # arch outside width, axial (measured on the drawing, axial scale is true)
    arch_cavity_w: float = 17.0    # arch inside width (measured)
    arch_h: float = 30.0           # arch height above the tube outside (assumed)
    rubber_density: float = 1.25e-6   # kg/mm3, reinforced butyl (assumed)
    bolt_d: float = 20.0           # M20 for dia 22.4 holes (assumed)
    bolt_len: float = 70.0
    bolt_head_af: float = 30.0
    bolt_head_t: float = 13.0
    nut_t: float = 18.0
    n_fasteners: int = 16          # drawing
    drawing_weight_kg: float = 16.0   # "approx 16 kg" on the drawing


def build(p: JParams = None):
    p = p or JParams()
    Ri = p.bore / 2; Ro = Ri + p.tube_wall; R = p.flange_od / 2; Rb = p.ring_id / 2
    L = p.length; tf = p.flange_face_t; tr = p.ring_t; fl = tf + tr
    zc = L / 2; ro = p.arch_w / 2; ri = p.arch_cavity_w / 2
    rc = Ro + p.arch_h - ro                                   # arch centre radius
    prof = (cq.Workplane("XZ").moveTo(Ri, 0).lineTo(R, 0).lineTo(R, tf).lineTo(Rb, tf).lineTo(Rb, fl).lineTo(Ro, fl)
            .lineTo(Ro, zc - ro).lineTo(rc, zc - ro).threePointArc((rc + ro, zc), (rc, zc + ro)).lineTo(Ro, zc + ro)
            .lineTo(Ro, L - fl).lineTo(Rb, L - fl).lineTo(Rb, L - tf).lineTo(R, L - tf).lineTo(R, L).lineTo(Ri, L)
            .lineTo(Ri, zc + ri).lineTo(rc, zc + ri).threePointArc((rc + ri, zc), (rc, zc - ri)).lineTo(Ri, zc - ri).close())
    rubber = prof.revolve(360, (0, 0, 0), (0, 1, 0))
    ring = cq.Workplane("XZ").moveTo(Rb, tf).lineTo(R, tf).lineTo(R, fl).lineTo(Rb, fl).close().revolve(360, (0, 0, 0), (0, 1, 0))
    ring_a, ring_b = ring, ring.mirror("XY").translate((0, 0, L))
    ring_b = ring_b.translate((0, 0, 0))
    off = math.radians(p.hole_offset_deg)
    pts = [(p.pcd / 2 * math.cos(off + 2 * math.pi * k / p.holes), p.pcd / 2 * math.sin(off + 2 * math.pi * k / p.holes)) for k in range(p.holes)]
    holes_a = cq.Workplane("XY").workplane(offset=-1).pushPoints(pts).circle(p.hole_d / 2).extrude(fl + 2)
    holes_b = cq.Workplane("XY").workplane(offset=L - fl - 1).pushPoints(pts).circle(p.hole_d / 2).extrude(fl + 2)
    holes = holes_a.union(holes_b)
    rubber = rubber.cut(holes); ring_a = ring_a.cut(holes_a); ring_b = ring_b.cut(holes_b)
    parts = {1: [rubber], 2: [ring_a, ring_b]}
    return p, parts


def fastener_mass(p: JParams):
    shank = math.pi / 4 * p.bolt_d ** 2 * p.bolt_len * STEEL_BOLT
    area_hex = math.sqrt(3) / 2 * p.bolt_head_af ** 2
    head = area_hex * p.bolt_head_t * STEEL_BOLT
    nut = (area_hex - math.pi / 4 * p.bolt_d ** 2) * p.nut_t * STEEL_BOLT
    return shank + head + nut


def masses(p, parts):
    rub = parts[1][0].val().Volume() * p.rubber_density
    rings = [s.val().Volume() * STEEL_316 for s in parts[2]]
    fas = fastener_mass(p) * p.n_fasteners
    return {"rubber": rub, "ring_each": rings[0], "rings": sum(rings), "fasteners": fas, "total": rub + sum(rings) + fas}


if __name__ == "__main__":
    p, parts = build()
    m = masses(p, parts)
    for k, v in m.items():
        print(f"{k:10s} {v:7.2f} kg")
    print("drawing says approx", p.drawing_weight_kg, "kg;  bbox", [round(x, 1) for x in (parts[1][0].val().BoundingBox().zmax, parts[1][0].val().BoundingBox().xmax)])
    print("rubber valid:", parts[1][0].val().isValid(), " ring valid:", parts[2][0].val().isValid())
