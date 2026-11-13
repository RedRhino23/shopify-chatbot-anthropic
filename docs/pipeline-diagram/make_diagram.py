"""Builds the PDF -> AS 1100 drawing pipeline diagram (SVG, PNG, PDF). Edit the REVS list and boxes, rerun.
    python make_diagram.py            writes pipeline_diagram.svg / .png / .pdf (needs playwright for png/pdf)
"""
from html import escape

W, H = 1240, 1190
INK, MUTED = "#1f2328", "#5b6470"
GREY, GREYLINE = "#d9d9d9", "#9aa0a6"
MVP = "#c4533b"
BLUE, BLUELINE = "#6aa8ee", "#2f6fc0"
GREEN = "#2a9d5c"

REV = "C"
DATE = "13/11/2026"
REVS = [
    ("A", "13/11/2026", "First diagram, as received: steps 0 to 10, build order, testing row."),
    ("B", "13/11/2026", "Overlay check first, frozen real test set, local models only, NAS reference catalogue, decisions still open."),
    ("C", "13/11/2026", "Reviewer items: human sign-off (11), title block / drawing no. / revision step (9b), step 4 cross-check, step 8 limit, licences in open decisions. Title block added."),
]

out = []
add = out.append


def text(x, y, s, size=12, weight=400, fill=INK, anchor="start", style=""):
    add(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}" {style}>{escape(s)}</text>')


def box(x, y, w, h, title, lines, kind="later", badge=None):
    fill, stroke, sw, dash = {"later": (GREY, GREYLINE, 1, ""), "mvp": (GREY, MVP, 2.5, ""), "blue": (BLUE, GREYLINE, 1, ""),
                              "bluemvp": (BLUE, MVP, 2.5, ""), "new": (GREY, GREEN, 2, "5 3"), "newmvp": (GREY, MVP, 2.5, "")}[kind]
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="7" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"' + (f' stroke-dasharray="{dash}"' if dash else "") + "/>")
    text(x + w / 2, y + 20, title, min(13, round((w - 16) / (0.62 * len(title)), 1)), 700, anchor="middle")
    for i, ln in enumerate(lines):
        text(x + w / 2, y + 38 + i * 14.5, ln, 10.5, 400, "#333", "middle")
    if badge:
        bw = 8 + 6.4 * len(badge)
        add(f'<rect x="{x + w - bw - 6}" y="{y - 8}" width="{bw}" height="16" rx="8" fill="{GREEN}"/>')
        text(x + w - bw / 2 - 6, y + 3.5, badge, 10, 700, "#fff", "middle")


def arrow(pts, dashed=False, label=None, lx=None, ly=None):
    d = "M" + " L".join(f"{x},{y}" for x, y in pts)
    add(f'<path d="{d}" fill="none" stroke="#333" stroke-width="1.4"' + (' stroke-dasharray="5 4"' if dashed else "") + ' marker-end="url(#ah)"/>')
    if label:
        tw = 6 * len(label) + 8
        add(f'<rect x="{lx - tw / 2}" y="{ly - 10}" width="{tw}" height="14" fill="#fff"/>')
        text(lx, ly, label, 10, 400, "#333", "middle")


def panel(x, y, w, h, title):
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="#fafafa" stroke="#d0d0d0"/>')
    text(x + 14, y + 22, title, 13, 400, MUTED)


add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Helvetica, Arial, sans-serif">')
add('<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#333"/></marker></defs>')
add(f'<rect width="{W}" height="{H}" fill="#fff"/>')
text(30, 44, "PDF → AS 1100 drawing pipeline", 28, 700)
text(30, 68, f"Read the true geometry, then re-draft it to AS 1100.   Rev {REV}, {DATE}", 14, 400, MUTED)
# legend
lx = 800
for i, (k, lab) in enumerate((("mvp", "MVP step"), ("blue", "supporting / data"), ("later", "later"))):
    fx = {"mvp": (GREY, MVP, 2.5), "blue": (BLUE, GREYLINE, 1), "later": (GREY, GREYLINE, 1)}[k]
    add(f'<rect x="{lx + i * 130}" y="34" width="26" height="14" rx="3" fill="{fx[0]}" stroke="{fx[1]}" stroke-width="{fx[2]}"/>')
    text(lx + i * 130 + 32, 45, lab, 11, 400)
add(f'<rect x="{lx}" y="56" width="22" height="13" rx="6" fill="{GREEN}"/>')
text(lx + 11, 66, "B", 9, 700, "#fff", "middle")
text(lx + 28, 66, "badge = revision that added or changed the box", 11, 400)

# ---------------------------------------------------------------- read the drawing
panel(20, 90, 1200, 215, "Read the drawing")
box(40, 150, 150, 90, "1 Triage", ["Vector or raster;", "set scale in mm"], "later")
box(230, 118, 150, 78, "2 Vector extract", ["pdfplumber paths + text", "→ JSON sketch"], "mvp")
box(230, 204, 150, 78, "3 Raster vectorize", ["SegFormer + DeepLSD", "+ arc fits"], "later")
box(420, 130, 190, 126, "4 Read annotations", ["eDOCr2 / VLM: dims,", "GD&T, title block", "(local models only)", "Every dimension read is", "checked against step 6;", "disagreement → a person"], "new", "C")
box(650, 150, 140, 90, "5 Understand", ["Graph model: roles,", "links, constraints,", "views"], "later")
box(830, 150, 150, 90, "5b Components", ["Spot, match and size", "standard parts from", "the catalogue"], "later")
box(1020, 150, 160, 90, "6 Param. solve", ["FreeCAD / planegcs;", "OCR dims drive;", "conflicts flagged"], "mvp")
arrow([(190, 195), (210, 195), (210, 157), (230, 157)]); arrow([(190, 195), (210, 195), (210, 243), (230, 243)])
arrow([(380, 157), (400, 157), (400, 180), (420, 180)]); arrow([(380, 243), (400, 243), (400, 215), (420, 215)])
arrow([(610, 195), (650, 195)]); arrow([(790, 195), (830, 195)]); arrow([(980, 195), (1020, 195)])
# 4 <-> 6 cross-check
arrow([(1100, 150), (1100, 106), (515, 106), (515, 130)], dashed=True, label="solved geometry checks each dimension read", lx=800, ly=110)

# ---------------------------------------------------------------- re-draft
panel(20, 340, 1200, 190, "Re-draft to AS 1100")
box(40, 395, 130, 100, "7 Geometry clean-up", ["OCCT: trim, join,", "close profiles;", "check vs NAS values"], "mvp")
box(195, 395, 130, 100, "8 View normalisation", ["Swap / realign views", "that exist. Never invent", "a projection the", "source did not show"], "later", "C")
box(350, 395, 130, 100, "9 Re-draft to AS 1100", ["Model + drafting layer", "→ DXF: dims, blocks,", "parts list, balloons"], "mvp")
box(505, 395, 140, 100, "9b Title block, no., rev", ["Client's own rev system", "kept (BHP's is BHP's).", "File name = drawing no.;", "file rev = title block rev"], "newmvp", "C")
box(670, 395, 130, 100, "10 Check & review", ["Overlay diff, DOF = 0.", "Edits → model (6) or", "drafting layer (9)"], "bluemvp", "1st")
box(825, 395, 130, 100, "11 Human sign-off", ["A drafter checks the", "overlay report and every", "flagged item. Nothing", "issues unchecked."], "newmvp", "C")
box(985, 395, 215, 100, "Outputs", ["DXF · PDF · BOM (parts list,", "CSV/XLSX) · JSON/FCStd · STEP"], "mvp")
arrow([(1100, 240), (1100, 318), (105, 318), (105, 395)])
arrow([(170, 445), (195, 445)]); arrow([(325, 445), (350, 445)]); arrow([(480, 445), (505, 445)])
arrow([(645, 445), (670, 445)]); arrow([(800, 445), (825, 445)]); arrow([(955, 445), (985, 445)])

# ---------------------------------------------------------------- supporting
panel(20, 565, 1200, 150, "Supporting tracks")
box(40, 600, 215, 100, "NAS reference catalogue", ["Known sizes, scales, part dims", "from past jobs. SQLite, read-only.", "Final issued rev only. Hints, not", "truth. No client names. Crawler: todo"], "blue", "B")
box(300, 600, 210, 100, "0 AS 1100 profile", [".101, .201 + HB 47 as a DXF", "template: layers, linetypes,", "dim style, sheets, projection", "symbol"], "bluemvp")
box(555, 600, 215, 100, "Synthetic data", ["build123d/OCCT parts → HLR", "views → AS 1100 / ISO / ASME", "→ PDF/PNG. Trains steps 3–5"], "blue")
box(880, 600, 200, 100, "Parts catalogue", ["Parametric templates +", "BOM data: fasteners,", "flanges, bearings, sections"], "blue")
arrow([(105, 600), (105, 495)], label="known dims / scale check", lx=105, ly=548)
arrow([(415, 600), (415, 495)], label="style rules", lx=415, ly=548)
arrow([(730, 600), (730, 495)], dashed=True, label="corrections", lx=730, ly=548)
arrow([(970, 600), (970, 497)])
arrow([(970, 497), (970, 240)], label="templates", lx=970, ly=300)

# ---------------------------------------------------------------- testing
panel(20, 750, 1200, 125, "Testing")
box(40, 785, 270, 80, "Overlay check (built)", ["Render result over source; per-entity", "scores; numbers must match.", "overlay-check/ in the repo; self-test passes"], "blue", "B")
box(330, 785, 270, 80, "Synthetic round trip", ["DXF → render → pipeline → compare,", "at rising degradation"], "later")
box(620, 785, 270, 80, "Frozen real test set", ["Past jobs from the NAS, redrawn by a", "drafter. Never used for training."], "new", "B")
box(910, 785, 290, 80, "Metrics + CI gate", ["F1, CER, DOF; dimension satisfaction,", "fix count. AS 1100 linter, DXF opens", "in ODA / LibreCAD"], "later")

# ---------------------------------------------------------------- build order / decisions / title block
text(30, 908, "Build order", 14, 700)
for i, s in enumerate(["0. Overlay check (step 10 diff) + frozen test set of past jobs. Overlay check built.",
                       "1. MVP: clean vector PDFs, rules only (terracotta steps: 0, 2, 6, 7, 9, 9b, 10, 11, outputs)",
                       "2. Synthetic data generator",
                       "3. Graph model replaces rules in step 5",
                       "4. Parts catalogue + step 5b (~10 families)",
                       "5. Raster path (step 3)",
                       "6. GD&T and multi-view"]):
    text(30, 930 + i * 18, s, 11)
text(30, 1070, "Decisions still open", 14, 700)
dec = ["Hosted AI vision model for client drawings? Assume NO: local models only until decided.",
       "Three BHP revision / file-naming questions: not yet received; add when available.",
       "NAS: where the crawler runs, what is on it, and whether any content is confidential.",
       "Licences: PyMuPDF is AGPL (the overlay check uses pdfplumber instead). Check the",
       "   eDOCr2, DeepLSD and SegFormer weights before they go into the worker."]
for i, s in enumerate(dec):
    text(30, 1092 + i * 17, s, 11)

# title block (bottom right)
tx, ty, tw = 810, 905, 410
rows_h = [22, 22] + [max(34, 17 * (1 + len(r[2]) // 52)) for r in REVS]
add(f'<rect x="{tx}" y="{ty}" width="{tw}" height="{sum(rows_h) + 20}" fill="#fff" stroke="{INK}" stroke-width="1.5"/>')
y = ty
add(f'<line x1="{tx}" y1="{y + 22}" x2="{tx + tw}" y2="{y + 22}" stroke="{INK}"/>')
text(tx + 8, y + 16, "PDF → AS 1100 DRAWING PIPELINE", 12, 700)
text(tx + tw - 8, y + 16, f"REV {REV}", 12, 700, anchor="end")
y += 22
add(f'<line x1="{tx}" y1="{y + 22}" x2="{tx + tw}" y2="{y + 22}" stroke="{INK}"/>')
text(tx + 8, y + 16, f"DATE  {DATE}", 11)
text(tx + 150, y + 16, "SCALE  N.T.S", 11)
text(tx + 250, y + 16, "DWG NO.  DC-AUTO-PIPE", 11)
y += 22
add(f'<line x1="{tx + 38}" y1="{y}" x2="{tx + 38}" y2="{y + sum(rows_h[2:]) + 2}" stroke="{INK}"/>')
add(f'<line x1="{tx + 108}" y1="{y}" x2="{tx + 108}" y2="{y + sum(rows_h[2:]) + 2}" stroke="{INK}"/>')
text(tx + 19, y + 14, "REV", 10, 700, anchor="middle"); text(tx + 73, y + 14, "DATE", 10, 700, anchor="middle"); text(tx + 114, y + 14, "WHAT CHANGED", 10, 700)
add(f'<line x1="{tx}" y1="{y + 20}" x2="{tx + tw}" y2="{y + 20}" stroke="{INK}"/>')
y += 20
import textwrap
for (r, d, c), rh in zip(REVS, rows_h[2:]):
    text(tx + 19, y + 15, r, 11, 700, anchor="middle"); text(tx + 73, y + 15, d, 10, anchor="middle")
    for i, ln in enumerate(textwrap.wrap(c, 58)):
        text(tx + 114, y + 15 + i * 13, ln, 10)
    add(f'<line x1="{tx}" y1="{y + rh}" x2="{tx + tw}" y2="{y + rh}" stroke="#888" stroke-width="0.6"/>')
    y += rh
add("</svg>")
svg = "\n".join(out)
open("pipeline_diagram.svg", "w", encoding="utf-8").write(svg)

try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=2)
        pg.set_content(f'<html><body style="margin:0">{svg}</body></html>')
        pg.screenshot(path="pipeline_diagram.png")
        pg.pdf(path="pipeline_diagram.pdf", width=f"{W}px", height=f"{H}px", print_background=True)
        b.close()
    print("wrote svg, png, pdf")
except Exception as e:
    print("wrote svg only:", e)
