#!/usr/bin/env python3
"""Turn the drawing register's legacy package into the miner's manifest. Run it on QD, where the package lives.

    python manifest_from_package.py PACKAGE_FOLDER --config tools/legacy/config.toml --out manifest.csv [--ext dwg dxf] [--since 2003]

Reads <package>/package.jsonl (built by `python -m tools.legacy.package` in the drawing-register repo, ADR-0014 section 1).
For every file record of role "drawing" with a wanted extension it writes: path (the real path on this machine, from the roots in
config.toml), client (the drawing's company, which the register already matched to a customer), drawing_no, rev, year, source_key.
template_miner.py --manifest takes this CSV. Reads the package only; writes only --out. Output holds client names: keep it on the NAS.
"""
import argparse
import csv
import json
import re
import sys
import tomllib
from pathlib import Path

REV = re.compile(r"\bRev\s*([A-Z0-9][-A-Z0-9]*)", re.I)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("package"); ap.add_argument("--config", required=True); ap.add_argument("--out", default="manifest.csv")
    ap.add_argument("--ext", nargs="+", default=["dwg", "dxf"]); ap.add_argument("--since", type=int, default=0)
    a = ap.parse_args()
    roots = tomllib.loads(Path(a.config).read_text(encoding="utf-8"))["roots"]
    drawings, companies, files = {}, {}, []
    for line in open(Path(a.package) / "package.jsonl", encoding="utf-8"):
        r = json.loads(line)
        k = r.get("kind")
        if k == "drawing":
            drawings[r["key"]] = r
        elif k == "company":
            companies[r["key"]] = r
        elif k == "file" and r.get("role") == "drawing":
            files.append(r)
    exts = {"." + e.lower().lstrip(".") for e in a.ext}
    n = skipped = 0
    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["path", "client", "drawing_no", "rev", "year", "source_key"])
        for r in files:
            if Path(r["name"]).suffix.lower() not in exts:
                continue
            year = int((r.get("mtime") or "0000")[:4] or 0)
            if year < a.since:
                skipped += 1; continue
            d = drawings.get(r.get("drawing")) or {}
            comp = companies.get(d.get("company") or "", {})
            client = (comp.get("names") or [str(d.get("company") or "").replace("company:", "")])[0]
            dno = next((x["value"] for x in d.get("refs", []) if x.get("kind") in ("client_no", "register_no", "cad_file")), d.get("title", ""))
            rev = r.get("rev_hint") or (REV.search(r["name"]).group(1) if REV.search(r["name"]) else "")
            for p in r.get("paths", []):
                root, _, rel = p.partition(":")
                base = roots.get(root.replace("Q_Drive", "Q_Drive"))
                if not base:
                    continue
                w.writerow([str(Path(base) / rel.replace("\\", "/")) if "/" in base else base.rstrip("\\") + "\\" + rel, client, dno, rev, year, r.get("drawing", "")])
                n += 1
    print(f"{n} drawing file path(s) written to {a.out}; {skipped} before {a.since}", file=sys.stderr)


if __name__ == "__main__":
    main()
