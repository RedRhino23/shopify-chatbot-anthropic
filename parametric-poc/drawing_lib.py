"""Helpers: hidden-line projection of a CadQuery shape into 2D edges, and placing them on a DXF sheet (paper mm)."""
import math

import cadquery as cq
import ezdxf
from ezdxf import ARROWS
from ezdxf.enums import TextEntityAlignment
from OCP.BRepLib import BRepLib
from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt
from OCP.HLRAlgo import HLRAlgo_Projector
from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape

A, B, C = 1, 2, 3


def project(shape, direction, xdir=None):
    """Hidden-line projection. Returns (visible_edges, hidden_edges), each a list of cq Edge in 2D (x right, y up)."""
    hlr = HLRBRep_Algo()
    hlr.Add(shape.wrapped)
    ax = gp_Ax2(gp_Pnt(), gp_Dir(*direction), gp_Dir(*xdir)) if xdir else gp_Ax2(gp_Pnt(), gp_Dir(*direction))
    hlr.Projector(HLRAlgo_Projector(ax))
    hlr.Update()
    hlr.Hide()
    h = HLRBRep_HLRToShape(hlr)
    vis = [c for c in (h.VCompound(), h.Rg1LineVCompound(), h.OutLineVCompound()) if not c.IsNull()]
    hid = [c for c in (h.HCompound(), h.OutLineHCompound()) if not c.IsNull()]
    for c in vis + hid:
        BRepLib.BuildCurves3d_s(c, 1e-6)
    edges = lambda cs: [e for c in cs for e in cq.Shape.cast(c).Edges()]
    return edges(vis), edges(hid)


def view_axes(direction, xdir=None):
    """2D axes used by project(): returns (xvec, yvec) in world coordinates, for projecting points."""
    d = _unit(direction)
    if xdir is None:
        # same rule OCCT uses is not documented; callers pass xdir whenever they need to project points
        raise ValueError("pass xdir to project points")
    x = _unit(xdir)
    y = _cross(d, x)
    return x, y


def _unit(v):
    n = math.sqrt(sum(c * c for c in v)); return tuple(c / n for c in v)


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def proj_pt(p, direction, xdir):
    x, y = view_axes(direction, xdir)
    return (sum(a * b for a, b in zip(p, x)), sum(a * b for a, b in zip(p, y)))


def edges_to_prims(edges):
    """2D edges -> primitives: ('L', p, q), ('C', cx, cy, r), ('P', [pts])."""
    out = []
    for e in edges:
        t = e.geomType()
        if t == "LINE":
            p, q = e.startPoint(), e.endPoint()
            if abs(p.x - q.x) + abs(p.y - q.y) < 1e-6:
                continue
            out.append(("L", (p.x, p.y), (q.x, q.y)))
        elif t == "CIRCLE" and e.IsClosed():
            c = e.arcCenter()
            out.append(("C", c.x, c.y, e.radius()))
        else:
            pts = [e.positionAt(i / 32) for i in range(33)]
            out.append(("P", [(q.x, q.y) for q in pts]))
    return out


def clip_prims(prims, keep, gap_shift):
    """Keep only the parts of lines/circles inside the x-ranges in `keep` (list of (x0, x1)); shift each kept range left
    so the removed middle closes up. gap_shift[i] is the shift applied to range i. Polylines are kept if fully inside."""
    out = []
    for pr in prims:
        for (a, b), sh in zip(keep, gap_shift):
            if pr[0] == "L":
                (x0, y0), (x1, y1) = pr[1], pr[2]
                lo, hi = min(x0, x1), max(x0, x1)
                if hi < a - 1e-9 or lo > b + 1e-9:
                    continue
                if abs(x1 - x0) < 1e-9:
                    if a - 1e-9 <= x0 <= b + 1e-9:
                        out.append(("L", (x0 - sh, y0), (x1 - sh, y1)))
                    continue
                t0 = max(0.0, (a - x0) / (x1 - x0)) if x1 > x0 else max(0.0, (b - x0) / (x1 - x0))
                t1 = min(1.0, (b - x0) / (x1 - x0)) if x1 > x0 else min(1.0, (a - x0) / (x1 - x0))
                if t1 <= t0:
                    continue
                px, py = x0 + t0 * (x1 - x0), y0 + t0 * (y1 - y0)
                qx, qy = x0 + t1 * (x1 - x0), y0 + t1 * (y1 - y0)
                out.append(("L", (px - sh, py), (qx - sh, qy)))
            elif pr[0] == "C":
                if a <= pr[1] <= b:
                    out.append(("C", pr[1] - sh, pr[2], pr[3]))
            else:
                if all(a - 1e-9 <= q[0] <= b + 1e-9 for q in pr[1]):
                    out.append(("P", [(q[0] - sh, q[1]) for q in pr[1]]))
    return out


class Sheet:
    def __init__(self, width=420.0, height=297.0):
        self.doc = ezdxf.new("R2010", setup=True)
        self.doc.units = ezdxf.units.MM
        self.msp = self.doc.modelspace()
        self.w, self.h = width, height
        d = self.doc
        for name, lt, lw in (("OUTLINE", "CONTINUOUS", 35), ("THIN", "CONTINUOUS", 18), ("HIDDEN", "HIDDEN", 18),
                             ("PHANTOM", "PHANTOM2", 13), ("CENTRE", "CENTER2", 13), ("DIM", "CONTINUOUS", 13),
                             ("TEXT", "CONTINUOUS", 13), ("BORDER", "CONTINUOUS", 50), ("TABLE", "CONTINUOUS", 25),
                             ("BALLOON", "CONTINUOUS", 25)):
            d.layers.add(name, linetype=lt, lineweight=lw)
        d.styles.add("RACK", font="arial.ttf")
        st = d.dimstyles.duplicate_entry("EZDXF", "RACK")
        st.dxf.dimtxsty = "RACK"
        st.dxf.dimtxt = 2.5
        st.dxf.dimasz = 2.5
        st.dxf.dimexe = 1.5
        st.dxf.dimexo = 1.0
        st.dxf.dimgap = 0.8
        st.dxf.dimdec = 0
        st.dxf.dimzin = 8
        st.dxf.dimtad = 1
        st.dxf.dimdle = 0
        st.dxf.dimlfac = 20.0
        st.set_arrows(blk=ARROWS.closed_filled)
        st.dxf.dimtsz = 0

    # ---- projected geometry
    def draw_edges(self, edges, mapper, layer="OUTLINE"):
        self.draw_prims(edges_to_prims(edges), mapper, layer)

    def draw_prims(self, prims, mapper, layer="OUTLINE"):
        sc = mapper(1, 0)[0] - mapper(0, 0)[0]
        for pr in prims:
            if pr[0] == "L":
                self.msp.add_line(mapper(*pr[1]), mapper(*pr[2]), dxfattribs={"layer": layer})
            elif pr[0] == "C":
                self.msp.add_circle(mapper(pr[1], pr[2]), abs(pr[3] * sc), dxfattribs={"layer": layer})
            else:
                self.msp.add_lwpolyline([mapper(*q) for q in pr[1]], dxfattribs={"layer": layer})

    def view(self, shape, direction, xdir, mapper, hidden=False):
        vis, hid = project(shape, direction, xdir)
        self.draw_edges(vis, mapper, "OUTLINE")
        if hidden:
            self.draw_edges(hid, mapper, "HIDDEN")

    # ---- annotation
    def text(self, s, p, h=2.5, align="LEFT", layer="TEXT", rot=0.0):
        al = {"LEFT": TextEntityAlignment.LEFT, "CENTER": TextEntityAlignment.MIDDLE_CENTER,
              "RIGHT": TextEntityAlignment.RIGHT, "MLEFT": TextEntityAlignment.MIDDLE_LEFT}[align]
        t = self.msp.add_text(s, height=h, rotation=rot, dxfattribs={"layer": layer, "style": "RACK"})
        t.set_placement(p, align=al)
        return t

    def dim(self, p1, p2, base, angle=0, text="<>", lfac=None):
        ov = {"dimlfac": lfac} if lfac else {}
        d = self.msp.add_linear_dim(base=base, p1=p1, p2=p2, angle=angle, text=text, dimstyle="RACK",
                                    override=ov, dxfattribs={"layer": "DIM"})
        d.render()

    def balloon(self, centre, num, target, r=4.0):
        cx, cy = centre
        self.msp.add_circle(centre, r, dxfattribs={"layer": "BALLOON"})
        self.text(str(num), centre, 3.0, "CENTER", "BALLOON")
        dx, dy = target[0] - cx, target[1] - cy
        n = math.hypot(dx, dy) or 1
        self.msp.add_line((cx + dx / n * r, cy + dy / n * r), target, dxfattribs={"layer": "BALLOON"})
        self.msp.add_circle(target, 0.5, dxfattribs={"layer": "BALLOON"})
        h = self.msp.add_hatch(color=7, dxfattribs={"layer": "BALLOON"})
        h.paths.add_polyline_path([(target[0] + 0.5 * math.cos(a / 8 * 2 * math.pi), target[1] + 0.5 * math.sin(a / 8 * 2 * math.pi)) for a in range(8)], is_closed=True)

    def rect(self, x0, y0, x1, y1, layer="BORDER"):
        self.msp.add_lwpolyline([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], close=True, dxfattribs={"layer": layer})

    def line(self, p, q, layer="TABLE"):
        self.msp.add_line(p, q, dxfattribs={"layer": layer})

    # ---- output
    def save(self, base):
        self.doc.saveas(base + ".dxf")
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from ezdxf.addons.drawing import Frontend, RenderContext
        from ezdxf.addons.drawing.config import BackgroundPolicy, ColorPolicy, Configuration
        from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
        fig = plt.figure(figsize=(self.w / 25.4, self.h / 25.4))
        ax = fig.add_axes([0, 0, 1, 1])
        cfg = Configuration(background_policy=BackgroundPolicy.WHITE, color_policy=ColorPolicy.BLACK, lineweight_scaling=1.0, min_lineweight=0.3)
        Frontend(RenderContext(self.doc), MatplotlibBackend(ax), config=cfg).draw_layout(self.msp, finalize=False)
        ax.set_xlim(0, self.w); ax.set_ylim(0, self.h); ax.set_aspect("equal"); ax.axis("off")
        fig.savefig(base + ".pdf")
        fig.savefig(base + ".png", dpi=130)
        plt.close(fig)
