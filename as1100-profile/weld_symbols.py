"""Weld symbols drawn to AS 1101.3-1987 Appendix B (Figs B1 to B22), as DXF blocks. Dimensions come from items_1101_3.json (1101-AppB).

    from weld_symbols import add_library
    add_library(doc)        # adds blocks WELD_FILLET, WELD_V_BUTT, ... drawn on the reference line, origin at the symbol's reference point

Symbols sit ON the reference line (the standard's rule, cl 2.1.3) on the side towards the reader (arrow side), perpendicular leg to the
left (cl 2.3.11). They are drawn at paper size in millimetres; scale the INSERT by the sheet's plot factor.
Appendix B was read by eye from page images: check values against the printed page before relying on them.
"""
import json
import math
from pathlib import Path

P = next(i for i in json.load(open(Path(__file__).with_name("items_1101_3.json")))["items"] if i["id"] == "1101-AppB")["params"]


def _arc(b, c, r, a0, a1):
    b.add_arc(c, r, a0, a1)


def add_library(doc, layer="0"):
    made = []

    def blk(name):
        made.append(name)
        return doc.blocks.new(name)

    h = P["B6_fillet"]["height"]
    b = blk("WELD_FILLET")                                    # vertical leg on the left, 45 degree hypotenuse
    b.add_line((0, 0), (0, h)); b.add_line((0, h), (h, 0))
    h = P["B5_V_butt"]["height"]
    b = blk("WELD_V_BUTT")
    b.add_line((0, 0), (-h, h)); b.add_line((0, 0), (h, h))
    h = P["B3_bevel_butt"]["height"]
    b = blk("WELD_BEVEL_BUTT")                                # perpendicular leg on the left
    b.add_line((0, 0), (0, h)); b.add_line((0, 0), (h, h))
    s = P["B2_square_butt"]
    b = blk("WELD_SQUARE_BUTT")
    b.add_line((-s["gap"] / 2, 0), (-s["gap"] / 2, s["height"])); b.add_line((s["gap"] / 2, 0), (s["gap"] / 2, s["height"]))
    j = P["B4_J_butt"]
    b = blk("WELD_J_BUTT")                                    # shape by eye from Fig B4; sizes are the figure's height, offset and R3
    b.add_line((0, 0), (0, j["height"]))
    _arc(b, (j["radius"], j["offset"]), j["radius"], 180, 270)
    u = P["B7_U_butt"]
    b = blk("WELD_U_BUTT")                                    # shape by eye from Fig B7
    b.add_line((-u["offset"] / 2, 0), (-u["offset"] / 2, u["height"])); b.add_line((u["offset"] / 2, 0), (u["offset"] / 2, u["height"]))
    _arc(b, (-u["offset"] / 2 - u["radius"], u["offset"]), u["radius"], 270, 360); _arc(b, (u["offset"] / 2 + u["radius"], u["offset"]), u["radius"], 180, 270)
    pl = P["B10_plug_or_slot"]
    b = blk("WELD_PLUG_SLOT")
    b.add_line((0, 0), (0, pl["height"])); b.add_line((0, pl["height"]), (pl["width"], pl["height"])); b.add_line((pl["width"], pl["height"]), (pl["width"], 0))
    b = blk("WELD_SPOT")
    b.add_circle((0, P["B14_spot_or_projection"]["diameter"] / 2), P["B14_spot_or_projection"]["diameter"] / 2)
    b = blk("WELD_ALL_AROUND")
    b.add_circle((0, 0), P["B17_weld_all_around"]["circle_diameter"] / 2)
    f = P["B18_field_weld"]
    b = blk("WELD_FIELD_FLAG")
    b.add_line((0, 0), (0, f["pole_height"])); b.add_lwpolyline([(0, f["pole_height"]), (-f["flag_width"], f["pole_height"] - f["offset"]), (0, f["pole_height"] - 2 * f["offset"])], close=True)
    return made
