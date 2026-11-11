"""Parametric 3D model of the umbrella box stacking rack (15 box), built only from the dimensions on the
two issued sheets (RI-RACK-001 Rev F). All sizes in mm. Axes: X = long side, Y = across, Z = up, foot base at Z=0.

Every drawing number on the sheets comes from here, so the drawing cannot disagree with the model.
Section sizes use the AS/NZS 1163 SHS corner rule (outer radius 2t up to 3 mm wall, 2.5t above).
"""
import math
from dataclasses import dataclass, field

import cadquery as cq

STEEL_KG_MM3 = 7.85e-6          # 7850 kg/m3


@dataclass
class Params:
    # frame
    long_outer: float = 2000.0        # plan, X, over stubs
    wide_outer: float = 1700.0        # plan, Y, over stubs
    stub_sec: tuple = (50, 4)         # item 2: 50x50x4 SHS
    stub_len: float = 250.0
    foot_h: float = 50.0              # item 1 pressed foot height
    foot_size: float = 130.0
    foot_hole: float = 20.0
    foot_t: float = 2.5               # pressed sheet thickness (not on the sheet: chosen to match 0.6 kg)
    post_sec: tuple = (40, 3)         # item 3: 40x40x3 SHS
    post_len: float = 1530.0
    cap_t: float = 5.0                # item 4: 5 PL 40x40, 16.5 hole
    cap_hole: float = 16.5
    pin_d: float = 16.0               # item 5: 16 dia round bar, 25 long, 20 proud of the cap
    pin_len: float = 25.0
    pin_chamfer: float = 1.0
    side_sec: tuple = (50, 2)         # item 6, 7: 50x50x2 SHS
    end_sec: tuple = (50, 2)
    centre_sec: tuple = (50, 3)       # item 8: 50x50x3 SHS
    rail_bottom: float = 150.0        # rails flush top 200 / bottom 150
    rail_top: float = 200.0
    gusset_leg: float = 80.0          # item 9: 4 PL right triangle 80x80, 15 snip
    gusset_t: float = 4.0
    gusset_snip: float = 15.0
    post_hole: float = 13.0           # 13 dia thru at 225 from post bottom / 25 from stub top
    post_hole_from_bottom: float = 225.0
    vent_hole: float = 8.0
    vent_from_top: float = 20.0
    bolt_d: float = 12.0
    bolt_len: float = 70.0
    # use (not geometry)
    box: tuple = (3450.0, 500.0, 270.0)   # max box L x W x H
    boxes_high: int = 5
    boxes_wide: int = 3
    swl_kg: float = 900.0
    min_fork_spread: float = 1200.0
    fork_reach: float = 1070.0

    @property
    def stub_w(self): return self.stub_sec[0]


def corner_radius(t):
    return 2.0 * t if t <= 3.0 else 2.5 * t


def shs(b, t, length):
    """Square hollow section along +Z from z=0, centred on the origin, with catalogue corner radii."""
    ro = corner_radius(t); ri = ro - t
    outer = cq.Workplane("XY").rect(b, b).extrude(length).edges("|Z").fillet(ro)
    inner = cq.Workplane("XY").rect(b - 2 * t, b - 2 * t).extrude(length).edges("|Z").fillet(ri)
    return outer.cut(inner)


def shs_along(b, t, length, axis):
    """SHS of given length with its first end at 0 along `axis` ('x','y','z'), centred on the other two axes."""
    s = shs(b, t, length)
    if axis == "x":
        return s.rotate((0, 0, 0), (0, 1, 0), 90)
    if axis == "y":
        return s.rotate((0, 0, 0), (1, 0, 0), -90)
    return s


def foot(p):
    """Item 1: pressed foot. Flat flange 130x130 at the top (stub and post both bear on it at z = 50), a pot below it
    that sits on the cap of the rack underneath, with the 20 hole in its floor for that rack's locating pin."""
    t = p.foot_t; h = p.foot_h; pot = p.stub_w + 8          # pot outside size: 58 (not on the sheet; chosen so mass matches 0.6 kg)
    flange = cq.Workplane("XY").workplane(offset=h - t).rect(p.foot_size, p.foot_size).extrude(t)
    wall = cq.Workplane("XY").rect(pot, pot).extrude(h - t)
    f = flange.union(wall)
    f = f.cut(cq.Workplane("XY").workplane(offset=t).rect(pot - 2 * t, pot - 2 * t).extrude(h - 2 * t))   # pot cavity
    f = f.cut(cq.Workplane("XY").circle(p.foot_hole / 2).extrude(t))                                          # floor hole
    return f


def build(p: Params = None):
    p = p or Params()
    L, W, sw = p.long_outer, p.wide_outer, p.stub_w
    cx = [sw / 2, L - sw / 2]; cy = [sw / 2, W - sw / 2]
    parts = {}            # item number -> list of (name, workplane/shape, placement)

    def add(item, shape, name=None):
        parts.setdefault(item, []).append(shape)

    for x in cx:
        for y in cy:
            # 1 foot
            add(1, foot(p).translate((x, y, 0)))
            # 2 stub (sits on the foot floor? stub bottom at foot_h)
            stub = shs(p.stub_sec[0], p.stub_sec[1], p.stub_len).translate((0, 0, 0))
            stub = stub.cut(cq.Workplane("XZ").workplane(offset=-50).center(0, p.stub_len - 25).circle(p.post_hole / 2).extrude(100))
            add(2, stub.translate((x, y, p.foot_h)))
            # 3 telescopic post: bears on the foot flange, same level as the stub bottom (sheet: 50 + 1530 + 5 = 1585 top of cap)
            z0 = p.foot_h
            post = shs(p.post_sec[0], p.post_sec[1], p.post_len)
            post = post.cut(cq.Workplane("XZ").workplane(offset=-50).center(0, p.post_hole_from_bottom).circle(p.post_hole / 2).extrude(100))
            post = post.cut(cq.Workplane("XZ").workplane(offset=-50).center(0, p.post_len - p.vent_from_top).circle(p.vent_hole / 2).extrude(100))
            add(3, post.translate((x, y, z0)))
            ztop = z0 + p.post_len
            # 4 cap
            cap = cq.Workplane("XY").rect(p.post_sec[0], p.post_sec[0]).extrude(p.cap_t)
            cap = cap.cut(cq.Workplane("XY").circle(p.cap_hole / 2).extrude(p.cap_t))
            add(4, cap.translate((x, y, ztop)))
            # 5 locating pin: through the cap, 20 proud
            pin = cq.Workplane("XY").circle(p.pin_d / 2).extrude(p.pin_len).faces(">Z").chamfer(p.pin_chamfer)
            add(5, pin.translate((x, y, ztop)))
            # 10 retainer bolt through stub and post, axis Y, at the hole height
            zb = p.foot_h + p.stub_len - 25
            bolt = (cq.Workplane("XZ").circle(p.bolt_d / 2).extrude(-p.bolt_len)).translate((0, -p.bolt_len / 2, 0))
            head = cq.Workplane("XZ").polygon(6, 19 / math.cos(math.radians(30))).extrude(7.5).translate((0, -p.bolt_len / 2, 0))
            add(10, bolt.union(head).translate((x, y, zb)))
    ztop_cap = p.foot_t + p.post_len + p.cap_t
    zb_, zt_ = p.rail_bottom, p.rail_top
    rh = zt_ - zb_
    # 6 side rails (long sides), between stubs
    for y in cy:
        r = shs_along(p.side_sec[0], p.side_sec[1], L - 2 * sw, "x").translate((sw, y, zb_ + rh / 2))
        add(6, r)
    # 7 end bearers, between stubs
    for x in cx:
        r = shs_along(p.end_sec[0], p.end_sec[1], W - 2 * sw, "y").translate((x, sw, zb_ + rh / 2))
        add(7, r)
    # 8 centre rail, between the end bearers
    r = shs_along(p.centre_sec[0], p.centre_sec[1], L - 2 * sw, "x").translate((sw, W / 2, zb_ + rh / 2))
    add(8, r)
    # 9 corner gussets: right triangle, right angle at the stub's inside corner (snipped), top face flush with rail underside
    g, t, s = p.gusset_leg, p.gusset_t, p.gusset_snip
    tri = [(s, 0), (g, 0), (0, g), (0, s)]
    base = cq.Workplane("XY").polyline(tri).close().extrude(t)
    for ix, x in enumerate(cx):
        for iy, y in enumerate(cy):
            gx = sw if ix == 0 else L - sw
            gy = sw if iy == 0 else W - sw
            m = base
            if ix == 1: m = m.mirror("YZ")
            if iy == 1: m = m.mirror("XZ")
            add(9, m.translate((gx, gy, zb_ - t)))
    return p, parts


def solid_of(shapes):
    c = cq.Compound.makeCompound([s.val() if hasattr(s, "val") else s for s in shapes])
    return c


def mass_kg(shape):
    return shape.Volume() * STEEL_KG_MM3


if __name__ == "__main__":
    p, parts = build()
    names = {1: "Pallet foot", 2: "Corner stub", 3: "Telescopic post", 4: "Post cap", 5: "Locating pin", 6: "Side rail",
             7: "End bearer", 8: "Centre rail", 9: "Corner gusset", 10: "Retainer bolt"}
    listed = {1: 0.6, 2: 1.34, 3: 5.05, 4: 0.06, 5: 0.04, 6: 5.57, 7: 4.69, 8: 8.08, 9: 0.10}
    tot = 0
    for k in sorted(parts):
        sh = parts[k]; qty = len(sh)
        m = mass_kg(sh[0].val()) if hasattr(sh[0], "val") else mass_kg(sh[0])
        tot += sum(mass_kg(s.val() if hasattr(s, "val") else s) for s in sh)
        print(f"{k:2d} {names[k]:16s} qty {qty}  model {m:7.3f} kg ea   sheet {listed.get(k, '-')}")
    print("rack total", round(tot, 2), "kg   (sheet: approx 58)")
