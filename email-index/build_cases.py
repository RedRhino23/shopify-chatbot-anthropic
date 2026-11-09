#!/usr/bin/env python3
"""Turn issues.csv into local test cases: what changed between the earlier and the issued revision PDF.

Runs on Ross's PC. Reads PDFs from the NAS (read-only). Writes only to --out (default cases\\).
Nothing is uploaded and nothing is sent to any AI service. Needs: pip install pypdf  (BSD licence; not pymupdf, which is AGPL).

  python build_cases.py                       uses out\\issues.csv, writes cases\\
  python build_cases.py --issues out\\issues.csv --out cases

What it does per issued drawing (clean rows only, letter revisions A, B, C...):
  1. finds the issued PDF and the previous revision PDF among the NAS files
  2. reads the text on each (dimensions, notes, title block)
  3. lists what was added, removed, or changed in place
  4. writes cases\\dev\\<drawing>_<rev>.json or cases\\heldout\\...  (about 30% held out, chosen by a fixed rule on the drawing number)
Keep the heldout folder unseen until the agent is working. The files contain drawing text: keep them on the NAS, not in a repo.
Drawings whose PDF has no text layer (lines only) are counted and skipped: the text diff cannot see them.
"""
import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

from pypdf import PdfReader


def rev_letter(path):
    m = re.search(r"rev\s*([A-Z])(?![A-Za-z0-9])", Path(path).stem, re.I)
    return m.group(1).upper() if m else None


def split_of(drawing_no):
    return "heldout" if int(hashlib.sha1(drawing_no.encode()).hexdigest(), 16) % 10 >= 7 else "dev"


def read_items(path):
    """Return a list of (text, page, x, y) for every text run in the PDF."""
    items = []
    reader = PdfReader(str(path))
    for pno, page in enumerate(reader.pages, 1):
        def visit(text, cm, tm, font_dict, font_size, _p=pno):
            t = (text or "").strip()
            if t:
                items.append((t, _p, round(tm[4] / 5) * 5, round(tm[5] / 5) * 5))
        page.extract_text(visitor_text=visit)
    return items


def diff(prev, new):
    prev_c, new_c = Counter(t for t, *_ in prev), Counter(t for t, *_ in new)
    removed = sorted((prev_c - new_c).elements())
    added = sorted((new_c - prev_c).elements())
    # changed in place: a removed and an added item at the same page and spot
    pos_prev = {(p, x, y): t for t, p, x, y in prev}
    changed = []
    for t, p, x, y in new:
        old = pos_prev.get((p, x, y))
        if old is not None and old != t:
            changed.append({"page": p, "was": old, "now": t})
    return {"added": added, "removed": removed, "changed_in_place": changed}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--issues", default="out/issues.csv")
    ap.add_argument("--out", default="cases")
    a = ap.parse_args()
    out = Path(a.out)
    for d in ("dev", "heldout"):
        (out / d).mkdir(parents=True, exist_ok=True)

    with open(a.issues, newline="", encoding="utf-8-sig") as fh:
        rows = [r for r in csv.DictReader(fh) if r["clean"] == "yes"]
    stats = Counter()
    for r in rows:
        files = [f.strip() for f in r["nas_files"].split("|") if f.strip()]
        pdfs = {rev_letter(f): f for f in files if f.lower().endswith(".pdf") and rev_letter(f)}
        rev = rev_letter(r["issued_file"])
        if not rev:
            stats["skipped: revision is not a single letter (numeric style)"] += 1
            continue
        if rev == "A":
            stats["skipped: RevA has no earlier revision"] += 1
            continue
        prev_rev = chr(ord(rev) - 1)
        if rev not in pdfs or prev_rev not in pdfs:
            stats["skipped: earlier or issued PDF not on the NAS"] += 1
            continue
        try:
            before, after = read_items(pdfs[prev_rev]), read_items(pdfs[rev])
        except Exception as ex:
            stats[f"skipped: PDF unreadable ({type(ex).__name__})"] += 1
            continue
        if not before or not after:
            stats["skipped: PDF has no text layer"] += 1
            continue
        d = diff(before, after)
        split = split_of(r["drawing_no"])
        case = {
            "drawing_no": r["drawing_no"], "previous_rev": prev_rev, "issued_rev": rev,
            "previous_file": pdfs[prev_rev], "issued_file_on_nas": pdfs[rev],
            "request_when": r["request_when"], "issued_when": r["issued_when"],
            "request_attachments": r["request_attachments"], "drawings_in_that_reply": r["drawings_in_that_email"],
            "text_items_before": len(before), "text_items_after": len(after), **d,
            "unchanged_text_only": not (d["added"] or d["removed"] or d["changed_in_place"]),
        }
        (out / split / f"{r['drawing_no']}_Rev{rev}.json").write_text(json.dumps(case, indent=1), encoding="utf-8")
        stats[f"case written ({split})"] += 1
        if case["unchanged_text_only"]:
            stats["note: no text change found (geometry-only change?)"] += 1
    for k, v in sorted(stats.items()):
        print(f"{v:4d}  {k}")


if __name__ == "__main__":
    sys.exit(main())
