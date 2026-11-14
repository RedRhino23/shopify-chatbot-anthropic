#!/usr/bin/env python3
"""Turn the drawing master list (drawing-master-list-YYYY-MM-DD.csv from the register work) into the miner's manifest.

    python manifest_from_master_list.py drawing-master-list-2026-11-14.csv --out manifest.csv [--since 2003] [--ext dwg dxf] [--min-per-client 3]

Keeps rows with status "include" and a wanted extension. Writes path (primary_path, a Windows path on QD), client (client_code),
drawing_no (client_or_cad_number), rev (rev_from_name), year, master_id. Prints how many DWG per client and era, so you can see
which clients have enough drawings (--min-per-client) for the miner to find a template. Output holds client codes and paths:
keep it on the NAS, not in git.
"""
import argparse
import csv
import sys
from collections import Counter


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv"); ap.add_argument("--out", default="manifest.csv"); ap.add_argument("--since", type=int, default=2003)
    ap.add_argument("--ext", nargs="+", default=["dwg", "dxf"]); ap.add_argument("--min-per-client", type=int, default=3)
    a = ap.parse_args()
    exts = {e.lower().lstrip(".") for e in a.ext}
    rows = list(csv.DictReader(open(a.csv, encoding="utf-8-sig")))
    keep, era = [], Counter()
    for r in rows:
        if r["status"] != "include" or r["ext"].lower() not in exts:
            continue
        try:
            year = int(r["date"][-4:])
        except ValueError:
            year = 0
        era[(r["client_code"], "before " + str(a.since) if year < a.since else f"{a.since}+")] += 1
        if year >= a.since:
            keep.append((r["primary_path"], r["client_code"], r["client_or_cad_number"], r["rev_from_name"], year, r["master_id"]))
    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["path", "client", "drawing_no", "rev", "year", "master_id"]); w.writerows(keep)
    per = Counter(k[1] for k in keep)
    print(f"{len(keep)} drawing(s) from {a.since} on written to {a.out}", file=sys.stderr)
    for c, n in per.most_common():
        print(f"  {c:<14} {n:>5} {'(enough for a template)' if n >= a.min_per_client else '(too few)'}", file=sys.stderr)
    print(f"  {sum(v for (c, e), v in era.items() if e.startswith('before'))} more are from before {a.since} (not written)", file=sys.stderr)


if __name__ == "__main__":
    main()
