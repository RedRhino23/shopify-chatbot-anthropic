"""Build synthetic 'client PDFs' from a DXF (real text, plain vector lines, no hatch) with optional faults,
so overlay_check.py can be tested against known differences.
    python tests/make_synthetic.py in.dxf outdir
Writes: ok.pdf, missing_line.pdf, wrong_number.pdf, moved_number.pdf, extra_line.pdf, offset_scaled.pdf
"""
import re
import sys
from pathlib import Path

import ezdxf
from ezdxf import disassemble
from ezdxf.path import make_path
from reportlab.pdfgen import canvas

MM = 72 / 25.4


def collect(dxf):
    doc = ezdxf.readfile(dxf)
    lines, texts = [], []
    for e in disassemble.recursive_decompose(doc.modelspace()):
        t = e.dxftype()
        if t in ("TEXT", "MTEXT"):
            s = e.dxf.text if t == "TEXT" else e.plain_text()
            p = e.dxf.insert
            rot = float(e.dxf.get("rotation", 0.0)) if t == "TEXT" else (float(e.dxf.rotation) if e.dxf.hasattr("rotation") else __import__("math").degrees(__import__("math").atan2(e.dxf.text_direction.y, e.dxf.text_direction.x)) if e.dxf.hasattr("text_direction") else 0.0)
            texts.append([s.strip(), p.x, p.y, float(e.dxf.char_height if t == "MTEXT" else e.dxf.height), rot])
        elif t in ("LINE", "ARC", "CIRCLE", "ELLIPSE", "SPLINE", "LWPOLYLINE", "POLYLINE"):
            lay = doc.layers.get(e.dxf.layer) if e.dxf.layer in doc.layers else None
            dashed = lay is not None and lay.dxf.linetype.upper() != "CONTINUOUS"
            pts = [(v.x, v.y) for v in make_path(e).flattening(0.05)]
            lines.append((dashed, pts))
    return lines, texts


def write(path, lines, texts, w=420, h=297, scale=1.0, dx=0.0, dy=0.0):
    c = canvas.Canvas(str(path), pagesize=(w * MM, h * MM))
    for dashed, pts in lines:
        c.setDash(*( ([6, 2, 1, 2], 0) if dashed else ([], 0))) if dashed else c.setDash([], 0)
        c.setLineWidth(0.3)
        p = c.beginPath()
        p.moveTo((pts[0][0] * scale + dx) * MM, (pts[0][1] * scale + dy) * MM)
        for q in pts[1:]:
            p.lineTo((q[0] * scale + dx) * MM, (q[1] * scale + dy) * MM)
        c.drawPath(p, stroke=1, fill=0)
    for s, x, y, hh, rot in texts:
        c.saveState()
        c.translate((x * scale + dx) * MM, (y * scale + dy) * MM)
        c.rotate(rot)
        c.setFont("Helvetica", max(hh * scale, 1.5) * MM)
        c.drawString(0, 0, s)
        c.restoreState()
    c.save()


def main(dxf, out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    lines, texts = collect(dxf)
    write(out / "ok.pdf", lines, texts)
    # 1. drop the longest vertical solid line away from the border (a dimension line or similar)
    def length(pl):
        return sum(((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5 for a, b in zip(pl, pl[1:]))
    cand = sorted((l for l in lines if not l[0] and len(l[1]) == 2 and 40 < length(l[1]) < 250), key=lambda l: -length(l[1]))
    drop = cand[0]
    write(out / "missing_line.pdf", [l for l in lines if l is not drop], texts)
    # 2. wrong number: a standalone number + 7
    t2 = [list(t) for t in texts]
    standalone = lambda t, L: re.fullmatch(r"\d{2,4}", t[0]) and not any(o is not t and abs(o[2] - t[2]) < 3 and abs(o[1] - t[1]) < 25 for o in L)
    pick2 = next(t for t in t2 if standalone(t, t2))
    pick2[0] = str(int(pick2[0]) + 7)
    write(out / "wrong_number.pdf", lines, t2)
    # 3. moved number: a standalone number moved 40 mm
    t3 = [list(t) for t in texts]
    pick = next(t for t in t3 if standalone(t, t3))
    pick[1] += 40
    write(out / "moved_number.pdf", lines, t3)
    # 4. extra line
    write(out / "extra_line.pdf", lines + [(False, [(100, 120), (180, 120)])], texts)
    # 5. correct drawing, but scaled 0.5 and shifted (alignment test)
    write(out / "offset_scaled.pdf", lines, texts, w=420, h=297, scale=0.5, dx=60, dy=40)
    print("dropped line:", drop[1][0], "->", drop[1][-1])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
