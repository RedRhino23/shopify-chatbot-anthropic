# AS 1100 profile (pipeline step 0)

Rule: nothing in the profile is "AS 1100" until a person has matched it to a clause in the copy of AS 1100.101, AS 1100.201 or HB 47 on file and set it to CONFIRMED. Nothing is written from memory.

Status values: UNVERIFIED (observed in a master, no clause yet), CONFIRMED (clause cited), REJECTED (master differs from the standard; do not copy it).

Part 1 (done): `profile_extract.py master.dxf [more.dxf] --out profile_draft.json` records layers, linetypes, text styles and heights, dimension styles, extents and title block text, and lists each as an UNVERIFIED item with an empty `clause`.

Needed from Ross
- The AS 1100 / HB 47 file(s) as PDF (not on this machine; path on the NAS is enough if the QD worker can read it).
- Two or three real masters as DXF: a clean A3 master and a dimension-heavy drawing. Keep them out of git.

Next (after the standard is supplied)
- Part 2: for each UNVERIFIED item, quote the clause, set status, and write the CONFIRMED items out as the template DXF (layers, linetypes, dimstyle, text style, border and title block).
- Part 3: `as1100_lint.py`, checking a DXF against CONFIRMED items only. Each finding cites its clause.
