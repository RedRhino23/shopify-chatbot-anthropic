# Template register (2D borders / title blocks and 3D model templates)

Many templates, set in stone once approved. Two kinds: 2d (border and title block, DXF/DWG) and 3d (model template: STEP, Inventor, SolidWorks, Fusion or a parametric script). Two scopes: client templates sit under that client's account (own folder `clients/<CODE>/`, so NAS permissions can follow the client), and house templates (Drafting Central's own, `house/`). This tool keeps them in a register with versions, an approval step, and a lookup the pipeline uses (step 9b).

Where things live
- The register (`register.json`) and the template files (`files/`) live on the NAS. They carry client names, so they are NEVER in git. `.gitignore` here blocks `register.json`, `files/` and `*.dxf`.
- Git holds only this tool.

Each entry records (3d entries record units and the register product family code instead of sheet and projection): template id (TPL-<client code>-<sheet>-<number>), client code (full name optional), version, sheet size and orientation (guessed from the DXF extents if not given), projection (first or third: the template carries it, step 8 only checks views match), who owns the revision system (client or AFJ; BHP's belongs to BHP), default purpose (sales, manufacture or both, for the R-009 N.T.S. check), title block field tags (ATTDEF tags found in the file), layers, text heights, file hash, status (DRAFT or APPROVED), who approved and when, source, notes, and a place for the AS 1100 deviations list.

Rules
- Set in stone: approving a template makes its file read-only and records its hash. There is no edit command. A change is a new version; old versions are kept and can be retired, never deleted. `check` flags a missing, changed or writable approved file.
- Client templates need a client code and can carry the client's portal account id (`--client-account-id`, filled in when the portal link is built).
- `find` looks only under the client's account. House templates are used only if `--house` is passed.
- Nothing is overwritten. Adding the same client, sheet and name again makes the next version; old files stay.
- `find` returns only APPROVED templates, newest version, and fails when there are none. Nothing is guessed. A person picks if more than one matches.
- `check` confirms every file exists and its hash still matches.

    python template_register.py --root \\WHY4RSNAS\...\templates add border.dxf --client MIM --name "MIM A3 landscape" --projection first --rev-owner client
    python template_register.py --root ... list --client MIM
    python template_register.py --root ... approve TPL-MIM-A3-001 --by "Ross"
    python template_register.py --root ... find --client MIM --sheet A3
    python template_register.py --root ... check

Later
- Link `client_account_id` to the portal's client accounts (needs the portal code; not on this machine).
- 3D templates for the parametric models (rack, rubber joint, bellows, fabric joint, tied joint) as house or per-client entries.
- Import the register into the drawing register (portal) so a job picks its template by client.
- Fill `as1100_deviations` from the AS 1100 profile once AS 1100.101 is on file.
- Title block positions for files that have no ATTDEF fields (plain text only).
