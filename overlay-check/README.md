# Overlay check (pipeline step 10, built first)

Compares a SOURCE drawing with a RESULT drawing and says what differs. No AutoCAD needed.

    pip install ezdxf pdfplumber numpy scipy matplotlib reportlab
    python overlay_check.py client.pdf our_drawing.dxf --out check_J1234

- Source and result can each be a vector PDF or a DXF.
- It finds the scale and shift itself (identity, bounding boxes, then fine fit). `--scale S --offset DX DY` to force it.
- Scores line work both ways: recall (is everything on the source in the result?) and precision (is everything in the result on the source?).
- Reads every number on both sides, including vertical dimension text. Missing, extra and moved numbers fail.
- Writes `<out>_overlay.png` (grey matched, red source only, blue result only) and `<out>_report.json`.
- Exit code 1 if any missing or extra stretch of line is 5 mm or longer (`--min-region`), any number differs, or recall/precision is under 95%.

Limits (by design, for now)
- Dashed and centre lines are matched as continuous lines, so a wrong dash pattern is not caught.
- Hatch on the DXF side is not drawn as lines. Source lines inside a patterned hatch, along its angle, are ignored. For anything else use `--mask x0,y0,x1,y1` (source mm).
- Raster-only PDFs are not read (pipeline step 3, later).
- Text is compared as numbers, not words. Wording and fonts are not checked.
- Numbers in the middle of a longer line of text are counted but their position is not checked.
- It tells you where the two differ. It does not know which is right. A person decides.

Licences: ezdxf (MIT), pdfplumber (MIT), numpy/scipy/matplotlib (BSD), reportlab (BSD). No PyMuPDF, so no AGPL.

Self-test (builds PDFs from any DXF with known faults: missing line, extra line, wrong number, moved number, shifted and scaled copy):

    python tests/run_tests.py some_drawing.dxf

Passes on the tied bellows, rubber joint, fabric joint, bellows and rack drawings.

Real jobs: keep client PDFs and reports out of git.
