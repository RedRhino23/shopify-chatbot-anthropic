# Review: PDF to AS 1100 drawing pipeline

Reviewer note, 13/11/2026. Scope: the pipeline diagram "PDF -> AS 1100 drawing pipeline". Do not let this delay M0 / M0b.

## Verdict
Sound structure. Read the true geometry, solve it, re-draft it, measure every stage. Keep it.

## Good
- Vector-only MVP first (step 2).
- Overlay diff with DOF = 0 (step 10) is a real, checkable test.
- Parts catalogue (5b): exact standard values (EN 1092-1, ASME B16.5) give correct dimensions without reading them.
- Per-stage metrics and a frozen held-out set.

## Concerns
1. Step 3 (raster vectorise) is a research project. Park it until the vector path works on real jobs.
2. Step 4 (vision model reads dimensions) is the biggest risk. A misread 1200 as 1250 gives a wrong part with a clean drawing. Cross-check every dimension against solved geometry; disagreements go to a person.
3. Step 8 (first to third angle) cannot be done reliably from 2D alone. Swapping existing views is fine; redrawing projections that were never shown is not.
4. Step 6 will meet over-constrained sketches (PDF geometry is only drawn to scale). Decide the rule: OCR'd dimension wins, conflict flagged.
5. No human sign-off gate before hand-back. Add one.
6. Title block, drawing number and revision handling are missing. BHP revision system belongs to BHP, not AFJ. Waiting on Ross's answers on the three BHP revision-table / file-naming points.

## Risks outside the drawing work
- Licences: PyMuPDF is AGPL (or commercial). Fine internal, a problem if exposed through the website. Check eDOCr2, DeepLSD, SegFormer weights. FreeCAD, planegcs, OCCT are LGPL.
- Client privacy: sending client drawings to a hosted vision model is Ross's decision, needed before step 4.
- Where it runs: heavy work on the QD worker. The website plugin (PHP, 30 s limit) only queues the job and fetches the result.

## Suggested order
1. Build step 10 first: overlay diff plus `dr_check.py`. Useful on every job with no automation upstream.
2. Then steps 1, 2 and 9 on clean vector PDFs.
3. Golden set: the email index already pairs client request with issued drawing (about 200 jobs since 2024). Keep a frozen held-out part. No client data in git.
