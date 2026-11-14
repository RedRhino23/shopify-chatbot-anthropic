#!/usr/bin/env python3
"""Check a folder of converted DXFs before the miner uses them.

    python verify_dxf.py DXF_FOLDER [--out verify.csv]

For each DXF: does it read, how many entities in model space, is there a sheet-sized border (the miner's test), the DXF version, and
the extents. Writes verify.csv and prints a summary. Exit 1 if more than 10% fail to read (the ADR-0010 quality gate).
"""
import argparse
import csv
import sys
from pathlib import Path

import ezdxf

sys.path.insert(0, str(Path(__file__).parent))
from template_miner import find_border  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder"); ap.add_argument("--out", default="verify.csv")
    a = ap.parse_args()
    rows, bad = [], 0
    files = sorted(Path(a.folder).glob("*.dxf"))
    for f in files:
        try:
            doc = ezdxf.readfile(f)
            msp = doc.modelspace()
            b = find_border(msp)
            rows.append([f.name, "ok", len(msp), doc.dxfversion, b[4] if b else "no border", ""])
        except Exception as e:
            bad += 1
            rows.append([f.name, "unreadable", 0, "", "", str(e)[:120]])
    with open(a.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(["file", "status", "entities", "dxf_version", "border", "error"]); w.writerows(rows)
    withb = sum(1 for r in rows if r[1] == "ok" and r[4] != "no border")
    print(f"{len(files)} DXF: {len(files) - bad} read, {bad} unreadable, {withb} with a sheet-sized border -> {a.out}")
    if files and bad / len(files) > 0.10:
        print("More than 10% unreadable: fails the ADR-0010 quality gate. Use the other tool or check the failures.")
        sys.exit(1)


if __name__ == "__main__":
    main()
