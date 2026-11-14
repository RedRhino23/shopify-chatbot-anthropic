# Template register import for the drawing register: spec for the register chat

Written 14/11/2026 by the auto-draft review chat at Ross's request. This is a PROPOSAL, not code in the register repo. The register's own rules say a new feature needs a requirement (REQUIREMENTS.md), an ADR where it adds structure, Ross's OK, and the milestone gate; and that code and requirements that disagree stop for Ross. So the side I can own is done (the export package, below, tested); the register side is specified here for its own team to build under its own workflow. It must not delay M0/M0b.

## What exists (in the shopify-chatbot-anthropic repo, branch claude/sweet-johnson-x81bzn, `template-register/`)
- `template_register.py`: the register of 2D (border / title block) and 3D (model) templates, with client scope (under the client's account folder) and house scope, versions, approval that LOCKS the file (read-only, hash recorded), retire, check.
- `template_miner.py` builds draft templates from the drawing collection.
- NEW: `template_register.py --root R export-package OUT [--approved-only]` writes `OUT/templates.jsonl` and `OUT/manifest.json`. One JSON line per template version, sorted keys and order, so the same register gives a byte-identical package (tested). It refuses to write if any file is missing or differs from its recorded hash. File bytes are NOT in the package: each record has the file's path under the register root and its sha256.

## Fit with the register's rules
- FR-42 / section 5.10: borders and block libraries "don't get drawing numbers". Templates are NOT drawings: no DC number, no revision row, no transmittal. They are their own records, referenced by drawings ("Border used", autodraft-handoff section 1; `border` in the REQUIREMENTS 482 schema sketch).
- Golden rule 1 (append-only): an approved template version is never updated or deleted. Superseding or retiring is a new state or a new version.
- Golden rule 4/6: files private, signed URLs only, every download logged. Templates are STAFF-ONLY. Never shown to customers unless Ross decides otherwise.
- Golden rule 5: client templates are tenant-scoped by customer (the client's account). House templates have no customer.
- Golden rule 8: no new framework; no AGPL. The import is a Django management command like `legacy_import`.

## Proposed requirement (number to be assigned by the register chat, for Ross to approve)
> **FR-1xx (S) Template register.** The register holds drawing templates (2D border and title block, 3D model template). Each template version records: template id and version, kind (2d, 3d), scope (customer, house), customer, client account id, name, sheet size, orientation, projection (first or third), who owns the revision system (client or AFJ), default purpose (sales, manufacture, both), title block field tags, layers, file (hash-checked), status (draft, approved, retired), who approved it and when, and the AS 1100 deviations list. An approved version is read-only for ever. Drawings can name the template they used ("Border used"). Templates are staff-only.

## Data model (sketch; the database-engineer decides)
- `Template(template_id, kind, scope, customer FK null, client_account_id, family FK null for 3d, name, created_by)` one row per template.
- `TemplateVersion(template FK, version, sheet, orientation, projection, units, rev_owner, purpose_default, title_block_tags JSON, layers JSON, text_heights JSON, file FK, sha256, status, approved_by, approved_on, locked_on, source, notes, as1100_deviations, source_key unique)` append-only after approval.
- `Drawing.border_template` (FK to TemplateVersion, null) replaces the free-text "Border used".
- Status changes are audit rows (record()), like every other register change.

## The import (management command, same shape as `legacy_import`)
    uv run python manage.py template_import load <package folder> --dry-run --by ross@example.com
    uv run python manage.py template_import apply <package folder> --by ross@example.com
    uv run python manage.py template_import attach <package folder> --by ross@example.com
- `load --dry-run`: read `templates.jsonl` and `manifest.json`; check the manifest's package_sha256; write only a reconciliation report and review items. Creates nothing.
- Idempotent by `key` (`template:<template_id>:v<n>`): run again, it adds only what it has not seen.
- Customer matching: the record's `client_code` goes through the existing `tools/legacy/customers.py` rules (AFJ, AF, New Folder...). No match gives a `template_customer` review item; it is not guessed. `scope: house` needs no customer.
- Append-only: an imported version that is APPROVED is never changed by a later import. A later package that disagrees about an approved version (different sha256, different fields) is a conflict review item, not an overwrite. A version that arrives APPROVED or RETIRED is stored with its own approver and dates as given; a DRAFT can be replaced by a later package until approved on the register side.
- `attach`: copy each template file from the NAS to private storage, checking every byte against `sha256` (like `legacy_import attach`); staff-only; pending the virus scan.
- Never writes under the NAS template folder; reads only.

## Tests (qa-test-engineer)
1. Dry run creates nothing; real run creates the expected versions; run twice, second run creates nothing.
2. Byte-identical package gives identical results.
3. An approved version is never changed; a conflicting package makes a review item.
4. A client template is invisible to another customer and to the customer portal; staff see it.
5. Unmatched client code gives a review item and no template under a guessed customer.
6. `attach` refuses a file whose hash differs; downloads need a signed URL and are logged.
7. Licence check still passes (no new dependency).
8. A template has no DC number and appears in no drawing list.

## Out of scope for the first cut
- Editing templates in the register (they are built and approved with the template tools, then imported).
- A customer-facing template view.
- The miner, DWG to DXF conversion, and the AS 1100 deviations measurement (separate tools).

## Questions for Ross
1. Milestone: which phase does this belong in? (Not before the Phase 1 gate; it must not delay M0/M0b.)
2. Customer-facing or staff-only? Spec says staff-only.
3. Should a drawing's "Border used" become a required link, or stay optional?
4. Who approves templates: Ross only, or a drafter too? (The approval name is recorded either way.)
