"""Self-test for weld_symbol_check.py: a library drawn to Appendix B must pass; known faults must be caught.   python test_weld_symbols.py"""
import subprocess
import sys
import tempfile
from pathlib import Path

import ezdxf

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from weld_symbols import add_library  # noqa: E402

tmp = Path(tempfile.mkdtemp())
blocks = ["WELD_FILLET", "WELD_V_BUTT", "WELD_BEVEL_BUTT", "WELD_SQUARE_BUTT", "WELD_J_BUTT", "WELD_U_BUTT", "WELD_PLUG_SLOT", "WELD_SPOT", "WELD_ALL_AROUND", "WELD_FIELD_FLAG"]


def run(path, names):
    a = []
    for n in names:
        a += ["--block", n]
    r = subprocess.run([sys.executable, str(HERE / "weld_symbol_check.py"), str(path)] + a, capture_output=True, text=True)
    return r.returncode, r.stdout


d = ezdxf.new(); add_library(d); ok = tmp / "ok.dxf"; d.saveas(ok)
cases = {"perfect library": (ok, blocks, 0, "")}
d = ezdxf.new(); add_library(d); b = d.blocks.get("WELD_FILLET"); [b.delete_entity(e) for e in list(b)]; b.add_line((0, 0), (0, 8)); b.add_line((0, 8), (8, 0)); p = tmp / "fillet8.dxf"; d.saveas(p)
cases["fillet too big (8 high)"] = (p, ["WELD_FILLET"], 1, "OFF")
d = ezdxf.new(); add_library(d); b = d.blocks.get("WELD_V_BUTT"); [b.delete_entity(e) for e in list(b)]; b.add_line((0, 0), (-5, 5)); b.add_line((0, 0), (5.2, 3.9)); p = tmp / "vangle.dxf"; d.saveas(p)
cases["V-butt arm at 37 degrees"] = (p, ["WELD_V_BUTT"], 1, "angle")
d = ezdxf.new(); add_library(d); b = d.blocks.get("WELD_SPOT"); [b.delete_entity(e) for e in list(b)]; b.add_circle((0, 4), 4.2); p = tmp / "spot.dxf"; d.saveas(p)
cases["spot circle dia 8.4"] = (p, ["WELD_SPOT"], 1, "OUT")
bad = 0
for name, (path, names, code, needle) in cases.items():
    rc, out = run(path, names)
    good = rc == code and needle in out
    bad += not good
    print(("ok   " if good else "FAIL ") + name)
    if not good:
        print(out[-500:])
print("all cases behave" if not bad else f"{bad} wrong")
sys.exit(1 if bad else 0)
