# AS 1100 profile (pipeline step 0)

Method (changed 13/11/2026): Ross's masters are NOT to AS 1100. The profile is built from the standard only. The masters are measured against it to list deviations, each for Ross to rule on. `profile_extract.py` is the measuring tool, not the source.

Files: `items_201.json` (AS 1100.201 items, each with its clause, status DRAFT until Ross confirms), `as1100_201_checks.py` (text checks that run on a DXF today), `TODO-TICKLIST.html` (open tasks to tick off).

Rule: nothing in the profile is "AS 1100" until a person has matched it to a clause in the copy of AS 1100.101, AS 1100.201 or HB 47 on file and set it to CONFIRMED. Nothing is written from memory.

Status values: UNVERIFIED (observed in a master, no clause yet), CONFIRMED (clause cited), REJECTED (master differs from the standard; do not copy it).

Part 1 (done): `profile_extract.py master.dxf [more.dxf] --out profile_draft.json` records layers, linetypes, text styles and heights, dimension styles, extents and title block text, and lists each as an UNVERIFIED item with an empty `clause`.

Standard on file, as received 13/11/2026 (checked, nothing copied into this repo)
- AS 1100.201-1992 full (79 pages) and its Amdt 1-1994: SUPPLIED.
- AS 1100.101-1992 Amdt 1-1994: SUPPLIED, but it is the 5-page amendment only. The body of AS 1100.101 is NOT supplied.
- Also supplied 13/11/2026: AS 1101.3-1987 (welding symbols, not yet read), a second scanned copy of AS 1100.201, a second copy of the AS 1100.101 amendment (filed as AS ISO 128.1-2005, same 6 pages), and AS 1100.301-2008 with Amdt 1-2011 (architectural, not needed).
- HB 47: not supplied.
- AS 1100.201 defers to AS 1100.101 for line types (cl 2.2.1), line thickness (2.2.2), scales (2.4), symbols (2.3), and the units and methods of dimensioning and tolerancing (2.1.1). So the step 0 template (linetypes, line weights, dimension style, scales, sheet and title block, lettering) cannot be confirmed until the 101 body is supplied.
- Licence: the PDFs are Ross Edgar's 1-user personal licence ("copying, storage, distribution or use on network prohibited"). They stay out of git, out of the repo and off the QD worker. The profile holds clause numbers and our own parameter values only, no standard text.

Needed from Ross
- AS 1100.101-1992 (full body, not just the amendment). HB 47 if you hold it.
- Two or three real masters as DXF: a clean A3 master and a dimension-heavy drawing. Keep them out of git.

Next (after the standard is supplied)
- Part 2: for each UNVERIFIED item, quote the clause, set status, and write the CONFIRMED items out as the template DXF (layers, linetypes, dimstyle, text style, border and title block).
- Part 3: `as1100_lint.py`, checking a DXF against CONFIRMED items only. Each finding cites its clause.

## Weld symbol geometry check (14/11/2026)
- `weld_symbols.py` draws weld symbols to AS 1101.3 Appendix B as DXF blocks (`add_library(doc)`): fillet, V-butt, bevel-butt, square-butt, J-butt, U-butt, plug or slot, spot, weld-all-around, field flag. It is the start of the symbol library for the step 0 template. J and U shapes are drawn by eye from the figures with the labelled sizes.
- `weld_symbol_check.py drawing.dxf` checks weld symbol blocks against Appendix B (sizes and angles, plus or minus 1 mm or 1 degree). A simple one-symbol block is recognised by SHAPE first (Appendix B sizes differ by only 1 mm, the tolerance, so size alone cannot tell symbols apart) and then measured. A library block with many overlapped symbols gets a PRIMITIVE AUDIT: every line, circle and arc must sit within tolerance of some Appendix B size and angle. It lists insert scales too. It does not check which weld a symbol is used for, which side of the line it is on, or the perpendicular-leg-left rule.
- `test_weld_symbols.py` is the self-test (perfect library passes; an 8 mm fillet, a 37 degree V arm and a dia 8.4 spot are caught).
- First real result, on the AFJ border's `Weld Symbols - Metric` block (AutoCAD Mechanical library, inch-based sizes): 36 of 38 primitives are within tolerance of an Appendix B size. Two 45 degree lines of 8.98 mm are 1.02 mm from the nearest size (10) and are listed for Ross to look at; they may belong to a symbol that is not in Appendix B. Sizes are Appendix B read by eye: confirm against the printed page.
