# Template register (borders and title blocks, per client)

Many templates, one or more per client. This tool keeps them in a register with versions, an approval step, and a lookup the pipeline uses (step 9b).

Where things live
- The register (`register.json`) and the template files (`files/`) live on the NAS. They carry client names, so they are NEVER in git. `.gitignore` here blocks `register.json`, `files/` and `*.dxf`.
- Git holds only this tool.

Each entry records: template id (TPL-<client code>-<sheet>-<number>), client code (full name optional), version, sheet size and orientation (guessed from the DXF extents if not given), projection (first or third: the template carries it, step 8 only checks views match), who owns the revision system (client or AFJ; BHP's belongs to BHP), default purpose (sales, manufacture or both, for the R-009 N.T.S. check), title block field tags (ATTDEF tags found in the file), layers, text heights, file hash, status (DRAFT or APPROVED), who approved and when, source, notes, and a place for the AS 1100 deviations list.

Rules
- Nothing is overwritten. Adding the same client, sheet and name again makes the next version; old files stay.
- `find` returns only APPROVED templates, newest version, and fails when there are none. Nothing is guessed. A person picks if more than one matches.
- `check` confirms every file exists and its hash still matches.

    python template_register.py --root \\WHY4RSNAS\...\templates add border.dxf --client MIM --name "MIM A3 landscape" --projection first --rev-owner client
    python template_register.py --root ... list --client MIM
    python template_register.py --root ... approve TPL-MIM-A3-001 --by "Ross"
    python template_register.py --root ... find --client MIM --sheet A3
    python template_register.py --root ... check

Later
- Import the register into the drawing register (portal) so a job picks its template by client.
- Fill `as1100_deviations` from the AS 1100 profile once AS 1100.101 is on file.
- Title block positions for files that have no ATTDEF fields (plain text only).
