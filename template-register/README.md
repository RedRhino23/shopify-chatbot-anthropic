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

## Building templates from the drawing collection (template_miner.py)

Templates are not drawn by hand. They are mined from the whole drawing collection, which the drawing database can list, then approved by a person.

    python template_miner.py DXF_FOLDER --out MINED --manifest drawings.csv [--register ROOT --rev-owner client --projection first]

- Input: DXF files (convert DWG first: AutoCAD, Open CAD Studio `--export`, or ODA File Converter) and optionally a CSV export from the drawing database with `path` (or `file`), `client`, `drawing_no`, `rev`. Without the CSV, the client is the parent folder name.
- It finds each sheet border, measures everything from the border corner (so drawings placed anywhere line up), and groups a client's drawings that share a sheet, border size and title block line work. Stray drawing lines in the title block area do not split a group.
- Per group of `--min-count` or more drawings, it keeps only what at least `--threshold` (90%) of them share: border, title block lines, fixed labels. Text in the same place whose value changes (drawing no., revision, title) becomes a field (ATTDEF).
- Writes `MINED/clusters.json` (every group, its example drawings, its fields, what was skipped) and `MINED/drafts/<cluster>.dxf`. With `--register` each draft is added to the register as DRAFT. Nothing is approved by the miner; a person approves, which locks it.
- Groups smaller than `--min-count` get no draft; they are listed for a person to look at. Drawings with no sheet-sized border are skipped and listed.

Limits (so far)
- Tested only on synthetic drawings, not on the real collection.
- Arcs and circles in a title block (logos) are listed as shared but not written into drafts yet.
- Blocks (INSERT) are matched but their contents are not copied into drafts; client logos and symbols usually arrive that way.
- Border detection needs a closed rectangle on the sheet size. Borders drawn as four separate lines, or inside a block, are skipped for now.
- Mined output holds client data: keep MINED on the NAS, not in git.

## Getting the drawing list (14/11/2026)
The drawing register (repo `drawing-register`) already scans the legacy roots and builds `scratch/legacy-package/package.jsonl` on QD, with each drawing's customer matched. `manifest_from_package.py` turns that package into the miner's manifest CSV. DWG to DXF: ODA File Converter is not installed on QD; AutoCAD Mechanical 2026's console (`accoreconsole /product ACM`) is the route that works there. Known border sources: `Q:\ACAD\COM\SUPPORT\AFJ 2D template.dwt`, `Q:\8606M-1 Nov 24\D8606m-1 New Boarder.dwg`, the BHP border in `Q:\Information\STANDARDS`, Roy Hill A1 borders, and `G:\Files\Borders`.

## Converting DWG to DXF (dwg_to_dxf_batch.ps1, verify_dxf.py)
`dwg_to_dxf_batch.ps1` (PowerShell 5.1, on QD) reads the manifest, copies each DWG into `C:\dr-staging\dwg-copy`, converts the copy to DXF in `C:\dr-staging\dxf`, and logs each file to `convert-log.csv`. It refuses any output path under Q:, S:, G:, H:, T: or the NAS, skips files already done, and has `-TestOne`, `-Limit`, `-Client` and `-WhatIf`. Tool `autocad` uses AutoCAD Mechanical's console (`accoreconsole /product ACM`, ADR-0010's route while the licence lasts); tool `libredwg` uses `dwg2dxf` as a separate command line (GPL, run only as its own program). ODA stays blocked (ADR-0010). It has NOT been run on QD yet. The AutoCAD DXFOUT answers are written from memory of the command's prompts, so run `-TestOne` and open the result first. `verify_dxf.py DXF_FOLDER` then checks the output reads, has a sheet-sized border, and fails the ADR-0010 gate if more than 10% are unreadable.
