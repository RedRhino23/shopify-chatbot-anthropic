"""Parametric 3D model of a rectangular fabric expansion joint with installation rods (BHP / AFJ D17529M-1 style).
All sizes in mm. Axis X = flow. The face view is the Y-Z plane. Bars at x = -t..0 and x = L..L+t.

READ FROM THE ISSUED DRAWING: 950 x 950 outside, 754 x 754 flow opening, 16 x dia 20 holes on an 890 square at 225/220/220/225,
200 between bars, 231 overall, flow liner 760 outside (754 inside), reverse liner 790 outside, overlap 100, gap 5,
BOM quantities (fabric 1, backing bar 2, reverse liner 1, flow liner 1, rods 4, gasket 2, lifting lugs 2, fasteners 32), 130 kg approx.
INFERRED: bar thickness t = (231 - 200) / 2 = 15.5.
ASSUMED (the section on the drawing is N.T.S.): everything else in FParams marked (assumed).
"""
import math
from dataclasses import dataclass

import cadquery as cq

STEEL = 7.98e-6          # 316 S/S
STEEL_ROD = 7.85e-6
PTFE = 2.2e-6
FABRIC = 1.5e-6          # multi layer fabric, kg/mm3 (assumed)


@dataclass
class FParams:
    outer: float = 950.0
    pitch_sq: float = 890.0
    hole_d: float = 20.0
    hole_pos: tuple = (-445.0, -220.0, 0.0, 220.0, 445.0)      # 225/220/220/225 spacing along each edge
    clear_len: float = 200.0
    overall: float = 231.0
    bar_open: float = 810.0          # backing bar opening (assumed: clears the 790 reverse liner and the fabric belt)
    gasket_t: float = 3.0            # PTFE (assumed)
    flow_od: float = 760.0
    flow_id: float = 754.0
    rev_od: float = 790.0
    liner_gap: float = 5.0
    rev_len: float = 100.0
    belt_wall: float = 6.0           # multi layer fabric (assumed)
    belt_clear: float = 6.0          # radial clearance belt to reverse liner (assumed)
    ear_w: float = 70.0              # rod ear on each bar (assumed)
    ear_out: float = 55.0
    rod_d: float = 20.0              # zinc allthread (assumed M20)
    rod_off: float = 30.0            # rod axis outside the 950 edge (assumed)
    rod_len: float = 270.0
    nut_t: float = 16.0
    nut_af: float = 30.0
    eye_od: float = 56.0             # 2 ton eye nut: 56 wide, dia 30 eye (drawing)
    eye_id: float = 30.0
    eye_t: float = 14.0              # assumed
    eye_y: float = 250.0             # eye nut sits this far to the side of the rod on the top edge (assumed)
    bolt_d: float = 20.0
    bolt_len: float = 60.0
    n_fasteners: int = 32
    drawing_weight_kg: float = 130.0

    @property
    def t(self): return (self.overall - self.clear_len) / 2.0       # 15.5
    @property
    def rev_id(self): return self.flow_od + 2 * self.liner_gap
    @property
    def rev_wall(self): return (self.rev_od - self.rev_id) / 2.0    # 10


def frame(outer, inner, x0, t):
    f = cq.Workplane("YZ").workplane(offset=x0).rect(outer, outer).rect(inner, inner).extrude(t)
    return f


def tube(od, id_, x0, length):
    return cq.Workplane("YZ").workplane(offset=x0).rect(od, od).rect(id_, id_).extrude(length)


def build(p: FParams = None):
    p = p or FParams()
    L, t = p.clear_len, p.t
    pts = [(y, z) for y in p.hole_pos for z in p.hole_pos if abs(y) == max(p.hole_pos) or abs(z) == max(p.hole_pos)]
    assert len(pts) == 16
    def holes(x0, th):
        return cq.Workplane("YZ").workplane(offset=x0 - 1).pushPoints(pts).circle(p.hole_d / 2).extrude(th + 2)
    def bar(x0):
        b = frame(p.outer, p.bar_open, x0, t)
        for sgn in (1, -1):                                   # four ears carrying the rod holes
            for ax in (0, 1):
                cy_, cz_ = (0, sgn * (p.outer / 2 + p.ear_out / 2)) if ax == 0 else (sgn * (p.outer / 2 + p.ear_out / 2), 0)
                w, d = (p.ear_w, p.ear_out) if ax == 0 else (p.ear_out, p.ear_w)
                ear = cq.Workplane("YZ").workplane(offset=x0).center(cy_, cz_).rect(w, d).extrude(t)
                rz = sgn * (p.outer / 2 + p.rod_off)
                hole = cq.Workplane("YZ").workplane(offset=x0 - 1).center(0 if ax == 0 else rz, rz if ax == 0 else 0).circle(11).extrude(t + 2)
                b = b.union(ear.cut(hole))
        return b.cut(holes(x0, t))
    def gasket(x0):
        return frame(p.outer, p.bar_open, x0, p.gasket_t).cut(holes(x0, p.gasket_t))
    bar1, bar2 = bar(-t), bar(L)
    g1, g2 = gasket(-t - p.gasket_t), gasket(L + t)
    flow = tube(p.flow_od, p.flow_id, 0, L)
    rev = tube(p.rev_od, p.rev_id, L - p.rev_len, p.rev_len)
    belt_id = p.rev_od + 2 * p.belt_clear
    belt = tube(belt_id + 2 * p.belt_wall, belt_id, 0, L)
    rods = []
    for sgn in (1, -1):
        rz = sgn * (p.outer / 2 + p.rod_off)
        rods.append(cq.Workplane("YZ").workplane(offset=-t - 20).center(0, rz).circle(p.rod_d / 2).extrude(p.rod_len))
        rods.append(cq.Workplane("YZ").workplane(offset=-t - 20).center(rz, 0).circle(p.rod_d / 2).extrude(p.rod_len))
    eyes = []
    for xc in (-t / 2, L + t / 2):
        z0 = p.outer / 2
        ring = cq.Workplane("XZ").workplane(offset=-p.eye_t / 2 - p.eye_y).center(xc, z0 + 25 + p.eye_od / 2).circle(p.eye_od / 2).circle(p.eye_id / 2).extrude(p.eye_t)
        shank = cq.Workplane("XY").workplane(offset=z0).center(xc, p.eye_y).circle(10).extrude(27)
        eyes.append(ring.union(shank))
    parts = {1: [belt], 2: [bar1, bar2], 3: [rev], 4: [flow], 5: rods, 6: [g1, g2], 7: eyes}
    return p, parts


def bolt_mass(p):
    shank = math.pi / 4 * p.bolt_d ** 2 * p.bolt_len * STEEL_ROD
    area_hex = math.sqrt(3) / 2 * 30 ** 2
    return shank + area_hex * 13 * STEEL_ROD + (area_hex - math.pi / 4 * p.bolt_d ** 2) * 18 * STEEL_ROD


def masses(p, parts):
    v = lambda k: sum(s.val().Volume() for s in parts[k])
    m = {"fabric belt": v(1) * FABRIC, "backing bars": v(2) * STEEL, "reverse liner": v(3) * STEEL, "flow liner": v(4) * STEEL,
         "rods": v(5) * STEEL_ROD + 4 * 2 * 2 * (math.sqrt(3) / 2 * p.nut_af ** 2 - math.pi / 4 * p.rod_d ** 2) * p.nut_t * STEEL_ROD,
         "gaskets": v(6) * PTFE, "eye nuts": v(7) * STEEL_ROD, "fasteners": p.n_fasteners * bolt_mass(p)}
    m["total"] = sum(m.values())
    return m


if __name__ == "__main__":
    p, parts = build()
    m = masses(p, parts)
    for k, v in m.items():
        print(f"{k:14s} {v:7.2f} kg")
    print("t =", p.t, " rev wall", p.rev_wall, " drawing", p.drawing_weight_kg, "kg")
    bb = cq.Compound.makeCompound([s.val() for l in parts.values() for s in l]).BoundingBox()
    print("bbox x", round(bb.xmin, 1), round(bb.xmax, 1), "y", round(bb.ymin), round(bb.ymax), "z", round(bb.zmin), round(bb.zmax))
    print("valid:", all(s.val().isValid() for l in parts.values() for s in l))
