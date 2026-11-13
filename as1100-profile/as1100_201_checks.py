#!/usr/bin/env python3
"""AS 1100.201 (and AS 1101.3 process letters) checks that can be run on a DXF today. Every finding cites its clause.
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


def check(path, purpose="unknown"):
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
    # AS 1101.3 cl 2.3.4.4: process shown by Appendix A letter designation
    W = json.load(open(HERE_ITEMS.with_name("items_1101_3.json")))["params"]["nonstandard_names"]
    for name, use in W.items():
        if re.search(r"(?<![A-Z0-9])" + name + r"(?![A-Z0-9])", blob):
            F.append(("ADVISORY", "1101-2.3.4.4", f"'{name}' used for a welding process. AS 1101.3 cl 2.3.4.4 says use the Appendix A letters ({use})."))
    # general tolerance note (advisory)
    if not re.search(r"GENERAL.*TOLERANC|UNLESS (NOTED|STATED|OTHERWISE)|\bUNO\b|TOLERANCES? EXCEPT", blob):
        F.append(("ADVISORY", "201-2.1.2 / 201-A2", "no general tolerance note found. The standard prefers one (guidance only)."))
    # scales
    scales = {f"{a}:{b}" for a, b in SCALE.findall(blob)}
    nts = bool(re.search(r"N\.?T\.?S|NOT TO SCALE", blob))
    if len(scales) > 1:
        F.append(("ADVISORY", "201-2.4", f"more than one scale on the sheet ({', '.join(sorted(scales))}). Keep to a minimum and indicate each clearly."))
    # House rule R-009 (Ross, 13/11/2026): N.T.S. is accepted; scale does not matter for sales drawings.
    if nts and purpose == "manufacture":
        F.append(("ADVISORY", "201-2.4 / R-009", "N.T.S. on a drawing for manufacture. House rule R-009 allows it (dimensions govern); AS 1100.101 on scales is not on file to check against."))
    elif nts and purpose == "unknown":
        F.append(("ADVISORY", "201-2.4 / R-009", "N.T.S. sheet; purpose not given. Fine for sales (R-009). For manufacture see R-009. Pass --purpose sales|manufacture."))
    if not scales and not nts:
        F.append(("ADVISORY", "201-2.4", "no scale found on the sheet."))
    if len(scales) > 1 and purpose == "sales":
        F = [f for f in F if not (f[1] == "201-2.4" and "more than one scale" in f[2])]
    return F


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dxf"); ap.add_argument("--json")
    ap.add_argument("--purpose", choices=["sales", "manufacture", "unknown"], default="unknown", help="what the drawing is for (R-009)")
    a = ap.parse_args()
    F = check(a.dxf, a.purpose)
    for sev, item, msg in sorted(F, key=lambda f: f[0] != "ERROR"):
        print(f"{sev:8} {item:24} {msg}")
    err = sum(1 for f in F if f[0] == "ERROR")
    print(f"\n{err} error(s), {len(F) - err} advisory.  Manual items in items_201.json are not checked here.")
    if a.json:
        json.dump([{"severity": s, "item": i, "message": m} for s, i, m in F], open(a.json, "w"), indent=1)
    sys.exit(1 if err else 0)


if __name__ == "__main__":
    main()
