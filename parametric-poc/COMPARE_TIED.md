# Tied metal expansion joint: model v catalogue (Belman LA2BT, DN200 PN10, ID 81.164.20)

Source: Belman public datasheet LA2BT (lateral tied joint, EN 14917). Proof of concept only. Not for issue.

| Item | Catalogue | Model | Basis |
|---|---|---|---|
| Overall length Lo | 525 | 525 | input |
| Width over rods B | 426 | 426 | input |
| Flange thickness c | 27 | 27 | input |
| Outer diameter d1 | 258 | 258 | input |
| Bellows centres l* | 364 | 364.0 | derived from tangents, convolutions, pitch |
| Flange | EN 1092-1 PN10 DN200 | OD 340, PCD 295, 8 x dia 22 | standard |
| Weight | 42.2 kg | 41.9 kg (-0.8%) | see below |

Assumed (not in the catalogue): 5 convolutions, pitch 10.2, height 12, 1 ply x 1.0 mm 316L; middle pipe DN200 Sch 40 (8.18 wall); collar 4 mm; M20 rods with 2 nuts per end; rod axis 22 mm in from the rod-ear edge; carbon steel flanges and pipe.

Weight is sensitive to the middle pipe wall and flange details, so 41.9 v 42.2 is a plausibility check, not proof.

Not modelled: movement and stiffness (bellows shape is not analysed), inner sleeve, outer cover, drain/test connections.

Regenerate: `python run_tied.py` (outputs `tied_joint_LA2BT_*` are git-ignored).
