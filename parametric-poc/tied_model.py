"""Parametric 3D model of a tied metal expansion joint: two bellows, a middle pipe, loose flanges with rod ears, tie rods.
Modelled on the public Belman catalogue entry LA2BT (lateral expansion joint with loose flanges and tie rods), DN200 PN10,
ID no. 81.164.20, built-in length Lo = 525, movement 2lN = 101.

FROM THE CATALOGUE (inputs): Lo 525, width over rods B 426, flange thickness c 27, outside face diameter d1 258,
centre distance of the bellows l* 364, weight 42.2 kg, flange drilling EN 1092-1 PN10 DN200 (OD 340, PCD 295, 8 x dia 22).
ASSUMED (the catalogue gives no section): bellows convolutions (5 x 10.2 pitch, 12 high, 1 ply of 1.0), middle pipe wall,
tie rod diameter and nuts, collar thickness, material grades. All in TParams.
Axis = Z; collar face of the inlet at z = 0, outlet at z = Lo.
"""
import math
from dataclasses import dataclass

import cadquery as cq

from bellows_model import BParams, bellows_solid

SS = 7.98e-6
CS = 7.85e-6


@dataclass
class TParams:
    Lo: float = 525.0
    B: float = 426.0
    c: float = 27.0
    d1: float = 258.0
    l_star: float = 364.0
    catalogue_weight_kg: float = 42.2
    flange_od: float = 340.0
    pcd: float = 295.0
    holes: int = 8
    hole_d: float = 22.0
    flange_bore: float = 222.0       # loose flange bore (assumed: clears the 219.1 tangent)
    collar_t: float = 4.0            # stub end collar thickness (assumed)
    pipe_od: float = 219.1           # DN200 pipe OD
    pipe_wall: float = 8.18          # middle pipe wall: DN200 schedule 40 (assumed; the catalogue does not say)
    n_conv: int = 5
    pitch: float = 10.2
    height: float = 12.0
    ply_t: float = 1.0
    plies: int = 1
    tangent_inner: float = 10.0
    rod_d: float = 20.0              # tie rods (assumed M20)
    n_rods: int = 2
    nut_af: float = 30.0
    nut_t: float = 16.0
    ear_w: float = 60.0
    rod_ext: float = 30.0            # rod length beyond each flange outer face
    ear_edge: float = 22.0           # rod axis to the outer edge of the ear (the width over rods B ends at the ear edge)

    @property
    def rod_r(self): return self.B / 2 - self.ear_edge                              # rod axis radius from the width over rods
    @property
    def tangent_outer(self): return (self.Lo - self.l_star) / 2 - self.n_conv * self.pitch / 2   # so the bellows centres are l* apart
    @property
    def bellows(self):
        return BParams(bore=self.pipe_od - 2 * self.plies * self.ply_t, n_conv=self.n_conv, pitch=self.pitch, height=self.height,
                       plies=self.plies, ply_t=self.ply_t, tangent=self.tangent_outer, tangent_b=self.tangent_inner)


def build(p: TParams = None):
    p = p or TParams()
    Lo, c, ct = p.Lo, p.c, p.collar_t
    bp = p.bellows
    b1 = bellows_solid(bp)                                                     # inlet bellows from z = 0
    b2 = bellows_solid(bp).mirror("XY").translate((0, 0, Lo))                  # outlet bellows, mirrored
    zin = bp.length                                                            # where the middle pipe starts
    pipe = cq.Workplane("XY").workplane(offset=zin).circle(p.pipe_od / 2).circle(p.pipe_od / 2 - p.pipe_wall).extrude(Lo - 2 * zin)
    def collar(z0):
        return cq.Workplane("XY").workplane(offset=z0).circle(p.d1 / 2).circle(p.pipe_od / 2).extrude(ct)
    col1, col2 = collar(0), collar(Lo - ct)
    off = math.radians(22.5)
    pts = [(p.pcd / 2 * math.cos(off + 2 * math.pi * k / p.holes), p.pcd / 2 * math.sin(off + 2 * math.pi * k / p.holes)) for k in range(p.holes)]
    def flange(z0):
        f = cq.Workplane("XY").workplane(offset=z0).circle(p.flange_od / 2).circle(p.flange_bore / 2).extrude(c)
        r_in, r_out = p.flange_od / 2 - 5, p.B / 2                              # ear runs from just inside the flange edge to B / 2
        for sgn in (1, -1):
            ear = cq.Workplane("XY").workplane(offset=z0).center(sgn * (r_in + r_out) / 2, 0).rect(r_out - r_in, p.ear_w).extrude(c)
            f = f.union(ear)
        f = f.cut(cq.Workplane("XY").workplane(offset=z0 - 1).pushPoints(pts).circle(p.hole_d / 2).extrude(c + 2))
        f = f.cut(cq.Workplane("XY").workplane(offset=z0 - 1).pushPoints([(p.rod_r, 0), (-p.rod_r, 0)]).circle(p.rod_d / 2 + 1).extrude(c + 2))
        return f
    fl1, fl2 = flange(ct), flange(Lo - ct - c)
    rods = [cq.Workplane("XY").workplane(offset=-p.rod_ext).center(sgn * p.rod_r, 0).circle(p.rod_d / 2).extrude(Lo + 2 * p.rod_ext) for sgn in (1, -1)][:p.n_rods]
    return p, {1: [b1, b2], 2: [pipe], 3: [col1, col2], 4: [fl1, fl2], 5: rods}


def masses(p, parts):
    v = lambda k: sum(s.val().Volume() for s in parts[k])
    nuts = p.n_rods * 4 * (math.sqrt(3) / 2 * p.nut_af ** 2 - math.pi / 4 * p.rod_d ** 2) * p.nut_t * CS
    m = {"bellows (2)": v(1) * SS, "middle pipe": v(2) * CS, "collars (2)": v(3) * CS, "loose flanges (2)": v(4) * CS,
         "tie rods": v(5) * CS, "rod nuts": nuts}
    m["total"] = sum(m.values())
    return m


if __name__ == "__main__":
    p, parts = build()
    m = masses(p, parts)
    for k, v in m.items():
        print(f"{k:18s} {v:7.2f} kg")
    comp = cq.Compound.makeCompound([s.val() for l in parts.values() for s in l]); bb = comp.BoundingBox()
    print("catalogue", p.catalogue_weight_kg, "kg   rod_r", p.rod_r, " tangent_outer", p.tangent_outer)
    print("z", round(bb.zmin, 1), round(bb.zmax, 1), " x", round(bb.xmin, 1), round(bb.xmax, 1), " valid", all(s.val().isValid() for l in parts.values() for s in l))
    print("bellows length", p.bellows.length, " bellows centre", p.tangent_outer + p.n_conv * p.pitch / 2, "->  l* =", p.Lo - 2 * (p.tangent_outer + p.n_conv * p.pitch / 2))
