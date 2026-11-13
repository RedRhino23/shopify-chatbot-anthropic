#!/usr/bin/env python3
"""AS 1100.201 checks that can be run on a DXF today. Every finding cites its clause.
    python as1100_201_checks.py drawing.dxf [--json out.json]
Only reads text. It does not judge geometry. Items in items_201.json marked "manual" are not checked here.
Severity: ERROR = contradicts an amendment or a table; ADVISORY = the standard says should/prefer, or needs Ross's ruling.
Exit 1 if any ERROR."""
import argparse
import json
import re
import sys

import ezdxf
from ezdxf import disassemble

HERE_ITEMS = __import__("pathlib").Path(__file__).with_name("items_201.json")
RA_SERIES = next(i["params"]["ra_um"] for i in json.load(open(HERE_ITEMS))["items"] if i["id"] == "201-3.3.1")
RA = re.compile(r"\bRA\s*[=:]?\s*(\d+(?:\.\d+)?)", re.I)
SCALE = re.compile(r"(?:\bSCALE\b[^0-9A-Z]*)?\b(\d+)\s*:\s*(\d+)\b", re.I)


def texts(path):
    doc = ezdxf.readfile(path)
    out = []
    for e in disassemble.recursive_decompose(doc.modelspace()):
        t = e.dxftype()
        if t == "TEXT":
            out.append(e.dxf.text)
        elif t == "MTEXT":
            out.append(e.plain_text())
    return [t.replace("\\P", "\n") for t in out if t and t.strip()]


def check(path):
    F = []
    tx = texts(path)
    blob = "\n".join(tx).upper()
    # Amendments: names
    for word, use, item in (("SQUARENESS", "PERPENDICULARITY", "AMD201-A4 / AMD101-8.3"), ("ROUNDNESS", "CIRCULARITY", "AMD101-8.3")):
        if word in blob:
            F.append(("ERROR", item, f"text contains '{word}'; the amended tables use '{use}'."))
    # Table 3.1 Ra series
    for m in RA.finditer(blob):
        v = float(m.group(1))
        if not any(abs(v - s) < 1e-9 for s in RA_SERIES):
            F.append(("ERROR", "201-3.3.1", f"Ra {m.group(1)} is not in the preferred series (Table 3.1: {', '.join(str(s) for s in RA_SERIES)})."))
    # general tolerance note (advisory)
    if not re.search(r"GENERAL.*TOLERANC|UNLESS (NOTED|STATED|OTHERWISE)|\bUNO\b|TOLERANCES? EXCEPT", blob):
        F.append(("ADVISORY", "201-2.1.2 / 201-A2", "no general tolerance note found. The standard prefers one (guidance only)."))
    # scales
    scales = {f"{a}:{b}" for a, b in SCALE.findall(blob)}
    nts = bool(re.search(r"N\.?T\.?S|NOT TO SCALE", blob))
    if len(scales) > 1:
        F.append(("ADVISORY", "201-2.4", f"more than one scale on the sheet ({', '.join(sorted(scales))}). Keep to a minimum and indicate each clearly."))
    if nts:
        F.append(("ADVISORY", "201-2.4", "sheet is marked N.T.S. Clause 2.4 sends scales to AS 1100.101 (body not on file). Needs Ross's ruling."))
    if not scales and not nts:
        F.append(("ADVISORY", "201-2.4", "no scale found on the sheet."))
    return F


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dxf"); ap.add_argument("--json")
    a = ap.parse_args()
    F = check(a.dxf)
    for sev, item, msg in sorted(F, key=lambda f: f[0] != "ERROR"):
        print(f"{sev:8} {item:24} {msg}")
    err = sum(1 for f in F if f[0] == "ERROR")
    print(f"\n{err} error(s), {len(F) - err} advisory.  Manual items in items_201.json are not checked here.")
    if a.json:
        json.dump([{"severity": s, "item": i, "message": m} for s, i, m in F], open(a.json, "w"), indent=1)
    sys.exit(1 if err else 0)


if __name__ == "__main__":
    main()
