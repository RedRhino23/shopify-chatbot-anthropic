"""Parametric 3D model of a flanged metallic bellows expansion joint (single bellows, U-shaped convolutions, internal liner).
All sizes in mm. Axis = Z. Flange faces at z = -flange_t (inlet) and z = bellows length + flange_t (outlet).

Built from the standard construction (U-shaped convolutions, root and crown radius = pitch / 4, parallel sidewalls),
NOT from a specific AFJ drawing: every size below is an assumption to be replaced by the real design.
Section and end flange follow ASME B16.5 class 150, NPS 8 (343 OD, 298.5 PCD, 8 holes dia 22.4 as on the BHP rubber joint).
"""
import math
from dataclasses import dataclass

import cadquery as cq

STEEL_SS = 7.98e-6       # 316L
STEEL_CS = 7.85e-6       # A105 flange


@dataclass
class BParams:
    bore: float = 200.0          # inside diameter at the ends (DN200)
    n_conv: int = 6              # number of convolutions
    pitch: float = 36.0          # convolution pitch q (root and crown radius = q / 4)
    height: float = 40.0         # convolution height w (neutral root to neutral crown)
    plies: int = 2
    ply_t: float = 0.8           # thickness per ply (plies are modelled as one solid of plies x ply_t)
    tangent: float = 25.0        # end tangent length each end
    flange_od: float = 343.0     # B16.5 150 NPS 8
    pcd: float = 298.5
    holes: int = 8
    hole_d: float = 22.4
    hole_offset_deg: float = 22.5
    flange_t: float = 24.0
    liner_t: float = 2.0
    liner_gap: float = 2.0       # radial clearance liner to bellows root
    liner_short: float = 20.0    # liner stops this far short of the far flange
    bellows_mat: str = "316L"
    flange_mat: str = "A105"

    @property
    def T(self): return self.plies * self.ply_t
    @property
    def length(self): return self.n_conv * self.pitch + 2 * self.tangent        # bellows element, tangent to tangent
    @property
    def face_to_face(self): return self.length + 2 * self.flange_t


def _rot90(v): return (-v[1], v[0])
def _unit(v):
    n = math.hypot(*v); return (v[0] / n, v[1] / n)


def neutral_path(p: BParams):
    """Neutral line of the bellows in (r, z). Elements: ('L', a, b) or ('A', a, mid, b, centre, cw)."""
    rm = p.pitch / 4.0
    Rr = p.bore / 2 + p.T / 2                 # root neutral radius (inside surface = bore/2)
    Rc = Rr + p.height                        # crown neutral radius
    tl = p.tangent
    el = [("L", (Rr, 0.0), (Rr, tl))]
    c = (Rr + rm, tl)
    el.append(("A", (Rr, tl), (c[0] - rm * math.cos(math.pi / 4), c[1] + rm * math.sin(math.pi / 4)), (Rr + rm, tl + rm), c, True))
    z = tl + rm
    for i in range(p.n_conv):
        el.append(("L", (Rr + rm, z), (Rc - rm, z)))
        c = (Rc - rm, z + rm)
        el.append(("A", (Rc - rm, z), (Rc, z + rm), (Rc - rm, z + 2 * rm), c, False))      # crown, turns left
        z += 2 * rm
        el.append(("L", (Rc - rm, z), (Rr + rm, z)))
        if i < p.n_conv - 1:
            c = (Rr + rm, z + rm)
            el.append(("A", (Rr + rm, z), (Rr, z + rm), (Rr + rm, z + 2 * rm), c, True))   # root, turns right
            z += 2 * rm
    c = (Rr + rm, z + rm)
    el.append(("A", (Rr + rm, z), (c[0] - rm * math.cos(math.pi / 4), c[1] - rm * math.sin(math.pi / 4)), (Rr, z + rm), c, True))
    z += rm
    el.append(("L", (Rr, z), (Rr, z + tl)))
    return el


def _left_normal(el, point):
    if el[0] == "L":
        t = _unit((el[2][0] - el[1][0], el[2][1] - el[1][1]))
    else:
        c, cw = el[4], el[5]
        d = (point[0] - c[0], point[1] - c[1])
        t = _unit(_rot90(d)) if not cw else _unit((-_rot90(d)[0], -_rot90(d)[1]))
    return _rot90(t)


def offset_path(el_list, s):
    out = []
    for el in el_list:
        pts = [el[1], el[2]] if el[0] == "L" else [el[1], el[2], el[3]]
        o = [(q[0] + s * _left_normal(el, q)[0], q[1] + s * _left_normal(el, q)[1]) for q in pts]
        out.append((el[0], o))
    return out


def bellows_solid(p: BParams):
    el = neutral_path(p)
    Lp, Rp = offset_path(el, p.T / 2), offset_path(el, -p.T / 2)
    w = cq.Workplane("XZ").moveTo(*Lp[0][1][0])
    for kind, pts in Lp:
        w = w.lineTo(*pts[1]) if kind == "L" else w.threePointArc(pts[1], pts[2])
    w = w.lineTo(*Rp[-1][1][-1])
    for kind, pts in reversed(Rp):
        w = w.lineTo(*pts[0]) if kind == "L" else w.threePointArc(pts[1], pts[0])
    return w.close().revolve(360, (0, 0, 0), (0, 1, 0))


def build(p: BParams = None):
    p = p or BParams()
    L, tf, Ri, R = p.length, p.flange_t, p.bore / 2, p.flange_od / 2
    bellows = bellows_solid(p)
    off = math.radians(p.hole_offset_deg)
    pts = [(p.pcd / 2 * math.cos(off + 2 * math.pi * k / p.holes), p.pcd / 2 * math.sin(off + 2 * math.pi * k / p.holes)) for k in range(p.holes)]
    def flange(z0):
        f = cq.Workplane("XY").workplane(offset=z0).circle(R).circle(Ri).extrude(tf)
        return f.cut(cq.Workplane("XY").workplane(offset=z0 - 1).pushPoints(pts).circle(p.hole_d / 2).extrude(tf + 2))
    f1, f2 = flange(-tf), flange(L)
    ro = Ri - p.liner_gap
    liner = cq.Workplane("XY").workplane(offset=-tf).circle(ro).circle(ro - p.liner_t).extrude(tf + L - p.liner_short)
    return p, {1: [bellows], 2: [f1, f2], 3: [liner]}


def masses(p, parts):
    b = parts[1][0].val().Volume() * STEEL_SS
    f = [s.val().Volume() * STEEL_CS for s in parts[2]]
    l = parts[3][0].val().Volume() * STEEL_SS
    return {"bellows": b, "flange_each": f[0], "flanges": sum(f), "liner": l, "total": b + sum(f) + l}


if __name__ == "__main__":
    p, parts = build()
    m = masses(p, parts)
    for k, v in m.items():
        print(f"{k:12s} {v:7.2f} kg")
    bb = parts[1][0].val().BoundingBox()
    print("bellows z", round(bb.zmin, 2), round(bb.zmax, 2), " crown OD", round(2 * bb.xmax, 1), " valid", parts[1][0].val().isValid(), parts[2][0].val().isValid(), parts[3][0].val().isValid())
    print("length", p.length, "face to face", p.face_to_face)
    thrust_area = math.pi / 4 * (p.bore + p.height) ** 2
    print("effective area (mean dia) mm2", round(thrust_area))
