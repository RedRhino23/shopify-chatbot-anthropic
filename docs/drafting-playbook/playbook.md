# Playbook

Status 08/11/2026. Rules R-001 to R-008 come from Ross's reviews of the Mount Isa Mines RHF 2 RevB set (02/11/2026). The other headings are empty for Ross to fill. Fields per rule are in `rule-template.md`.

## 1. Editing drawings (changing dimensions, lines and hatches)

### R-001 Remove lines a changed dimension no longer needs
- **Rule:** when a dimension changes, deal with every line it measured to. A line that only existed for the old dimension is removed in the same edit.
- **Why:** a leftover line stays on the issued drawing and the client sees it.
- **Check:** auto, `dr_check.py` flags isolated lines (both ends free); Ross checks the area around each changed dimension.
- **Fail example:** D17428M-1 joint 1, a vertical line left under the 1200 I.D arrow after the dimension went to full width. Ross found it.
- **Source:** MIM RHF 2 RevB, 02/11/2026.
- **Status:** auto (partial)

### R-002 Compare each drawing with its sister drawings
- **Rule:** compare each drawing with its sisters (e.g. joints 1, 2, 3). Any line on one and not the others needs a reason, or it goes.
- **Why:** a line on one drawing only is usually a leftover.
- **Check:** auto, `dr_check.py --sisters`; a reason is written in the job notes for anything left in.
- **Source:** MIM RHF 2 RevB, 02/11/2026.
- **Status:** auto (partial)

### R-003 No stray lines, correct dimension targets
- **Rule:** before hand-back, check for stray, orphan or half-trimmed lines, and that every dimension measures to the right lines. Ross must never be the one to find them.
- **Why:** a draftsman-level hand-back means no leftovers; every miss costs Ross's trust.
- **Check:** auto, `dr_check.py` (orphans, free ends, dimension points on no geometry); visual check of the render at 400%.
- **Source:** MIM RHF 2 RevB, 02/11/2026.
- **Status:** auto (partial)

### R-004 Follow the scan, not the summary
- **Rule:** every red mark on the client's scan is a change, dimension arrows included. Follow the scan literally, not the written summary.
- **Why:** the written summary leaves out marks.
- **Check:** manual, a marks list built from the scan, each mark ticked off against the drawing; later, a visual check of each marked area.
- **Source:** MIM RHF 2 RevB, 02/11/2026.
- **Status:** manual

### R-005 Associative dimensions
- **Rule:** DIMDISASSOCIATE before editing associative dimension points, or AutoCAD silently reverts the change. Verify in a DXF export. (OCS also has DIMDISASSOCIATE and DIMREASSOCIATE; Ross's checklist tests it.)
- **Why:** the edit looks done on screen and is not saved.
- **Check:** auto, compare dimension values before and after (`dr_check.py --before`); the DXF diff.
- **Source:** MIM RHF 2 RevB, 02/11/2026.
- **Status:** auto (partial)

### R-006 Hatches and STRETCH
- **Rule:** STRETCH skips non-associative hatches. Move hatch boundaries explicitly.
- **Why:** the hatch stays behind when the part moves.
- **Check:** manual and visual; hatch boundary against the outline in the render.
- **Source:** MIM RHF 2 RevB, 02/11/2026.
- **Status:** manual

## 2. Title block and notes

### R-007 Title block centring and revision row
- **Rule:** title-block values are centred in their cells. A new revision row pushes the notes block down one row. Text "under a view" goes under the view, not in the notes list.
- **Why:** the layout looks wrong, and notes get lost.
- **Check:** visual (render the title block at 200%); later, an auto check of cell centring.
- **Source:** MIM RHF 2 RevB, 02/11/2026.
- **Status:** manual

### Not yet written (Ross to fill in)
- File name against drawing number
- File revision against the title block revision
- Revision log entries (wording, date format DD/MM/YYYY)
- Notes block rules

## 3. Plotting

### R-008 Plot like RevA
- **Rule:** DWG To PDF.pc3, ISO full bleed A4 landscape, window fit, centred, monochrome.ctb, no lineweights. Compare with anti-aliasing off so hairlines show.
- **Why:** the issued PDF must look like the earlier revision.
- **Check:** visual and auto, plot settings read from the job record; side-by-side compare against the RevA PDF.
- **Source:** MIM RHF 2 RevB, 02/11/2026.
- **Status:** manual

## 4. Standards (Ross to fill in)
- AS 1100: which points apply to which drawing type (the worker flags 2 on the test claim)
- ASME B16.5: use EXACT flange values, not the rounded OneSteel chart
- Scale: see R-009. Still to fill in: what N.T.S. changes when editing.

### R-009 N.T.S. masters (house rule, draft)
- **Rule:** masters may be drawn N.T.S. instead of true scale, and the sheet says N.T.S. Dimensions govern, never scaled-off measurements.
- **Why (Ross, 13/11/2026):** (1) true scale loses detail, for example a small feature on a large diameter; (2) a similar drawing can be reused by changing only the dimension values; (3) if the drawing is for sales and not for manufacture, scale does not matter.
- **Check:** auto, advisory only: `as1100_201_checks.py --purpose manufacture|sales`. Sales: no finding. Manufacture: advisory, because AS 1100.201 cl 2.4 sends scales to AS 1100.101, whose body is not on file yet. Unknown purpose: advisory asks.
- **Consequence for the pipeline:** on an N.T.S. drawing a dimension is allowed to disagree with the drawn length. The step 4 cross-check (dimension against solved geometry) cannot use absolute size there. It can only check shape and proportion, and a person decides the rest.
- **Source:** Ross, 13/11/2026.
- **Status:** draft (Ross to confirm the manufacture case against AS 1100.101 when supplied)

## 5. Product families (Ross to fill in, one block per register family code)
- Family code (must match the register's product family codes and `families.json` keys)
- What changes between sizes
- What must never change
- Typical client changes and where they land on the drawing

## 6. End clients and senders (Ross to fill in)
Conventions belong to the END CLIENT (the owner whose title block and revision system the drawing uses), not to whoever emails the job. One sender can send jobs for several end clients, so keep the two apart.
- Use codes or short names only, no contact names or personal details.

### End client: BHP (Olympic Dam), from one job on 09/11/2026. Ross to confirm and correct.
- **Revision system:** Rev A = ISSUED FOR APPROVAL; Rev 0-0 = ISSUED FOR CONSTRUCTION. Numeric style (0-0, 1-0).
- **Dates:** DD.MM.YY (for example 05.11.26).
- **Drawn-by initials in the revision row:** "RED".
- **Client drawing number:** BHP's own number (form ODE4371-2-0404) is added to the title block as a reference.
- **Title block revision field** changes with the revision row (A to 0-0).
- Not yet known: other revision steps after 0-0, checker/approver fields, what the "populate" note on the revision table row means.
- **How their markups arrive:** PDF with digital annotations (replacement text boxes, strike-outs, sticky notes). Ignore the "AutoCAD SHX Text" annotations that AutoCAD's PDF export adds.

### Senders (who emails us)
- AFJ: sends jobs for end clients including BHP. Note here anything specific to how AFJ sends requests (file names, sets of drawings per scan), separate from the end client's rules.

## 7. When to stop and ask Ross
- List the situations where the agent must not guess (unclear mark, missing value, conflicting values, a rule that doesn't fit).
