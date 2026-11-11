# Parametric proof of concept: umbrella box stacking rack (RI-RACK-001)

The rack is modelled in 3D from the dimensions on the two issued sheets, and both drawing sheets are generated from the model.
Change a number in `rack_model.py` (class `Params`) and run `python run.py`: the model, the views, the dimensions, the cut list,
the stock order, the weights and the general-arrangement text all follow.

Needs: `pip install cadquery ezdxf matplotlib`

| File | What it does |
|---|---|
| `rack_model.py` | the 3D model and all the parameters |
| `drawing_lib.py` | hidden-line projection into 2D, DXF placing, dimensions, balloons |
| `ga_sheet.py` | sheet 1, general arrangement (front, plan, end, isometric, notes) |
| `parts_sheet.py` | sheet 2, cut list, stock order, fabrication notes, part details, Details A and B |
| `run.py` | builds everything and writes `COMPARE.md` (model against the issued sheets, clash and stacking checks) |

Outputs: `umbrella_rack.step`, `umbrella_rack_sheet1_GA` and `umbrella_rack_sheet2_PARTS` (`.dxf`, `.pdf`, `.png`), `COMPARE.md`.

Limits: proof of concept. Foot shape, gusset position and the fork/box figures are assumptions or use inputs (see `COMPARE.md`).
Dimensions are real DXF dimension entities (not associative) with DIMLFAC set for the 1:20 scale.
