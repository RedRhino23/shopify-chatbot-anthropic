#!/usr/bin/env python3
"""Register of drawing templates (borders and title blocks), one or more per client.

The register and the template files live on the NAS, never in git (they carry client names).
Point --root at the NAS folder; it gets `register.json` and `files/`.

    python template_register.py --root R add border.dxf --client MIM --sheet A3 --projection first \\
           --rev-owner client --purpose both --name "MIM A3 landscape"
    python template_register.py --root R list [--client MIM]
    python template_register.py --root R show TPL-MIM-A3-001
    python template_register.py --root R find --client MIM --sheet A3        (what pipeline step 9b calls)
    python template_register.py --root R approve TPL-MIM-A3-001 --by "Ross"
    python template_register.py --root R check                                  files present, hashes match, fields found

Rules
- A template is never overwritten. `add` with the same client+sheet+name makes a new version (v2, v3 ...); old files stay.
- `find` returns only APPROVED templates, newest version. Draft templates are never used on a job.
- client = a short code (MIM, BHP). The full client name is optional and stays in the register on the NAS.
"""
import argparse
import datetime
import hashlib
import json
import shutil
import sys
from pathlib import Path

import ezdxf

SHEETS = ["A0", "A1", "A2", "A3", "A4"]
FIELDS = ["template_id", "client", "client_name", "name", "version", "sheet", "orientation", "projection", "rev_owner", "purpose_default",
          "file", "sha256", "title_block_tags", "layers", "extents", "text_heights", "status", "approved_by", "approved_on",
          "added_on", "source", "notes", "as1100_deviations"]


def now():
    return datetime.date.today().strftime("%d/%m/%Y")


def load(root):
    p = Path(root) / "register.json"
    return json.load(open(p, encoding="utf-8")) if p.exists() else {"templates": []}


def save(root, reg):
    p = Path(root) / "register.json"
    Path(root).mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    json.dump(reg, open(tmp, "w", encoding="utf-8"), indent=1)
    tmp.replace(p)


def sha(path):
    h = hashlib.sha256()
    h.update(Path(path).read_bytes())
    return h.hexdigest()


def read_template(path):
    """Observe a template DXF: attribute tags in block definitions (title block fields), layers, extents, text heights."""
    doc = ezdxf.readfile(path)
    tags = {}
    for blk in doc.blocks:
        for e in blk:
            if e.dxftype() == "ATTDEF":
                tags.setdefault(blk.name, []).append(e.dxf.tag)
    layers = [l.dxf.name for l in doc.layers]
    heights = set()
    for e in doc.modelspace():
        if e.dxftype() == "TEXT":
            heights.add(round(e.dxf.height, 2))
        elif e.dxftype() == "MTEXT":
            heights.add(round(e.dxf.char_height, 2))
    try:
        from ezdxf import bbox
        b = bbox.extents(doc.modelspace())
        ext = [round(b.extmin.x, 1), round(b.extmin.y, 1), round(b.extmax.x, 1), round(b.extmax.y, 1)]
    except Exception:
        ext = None
    return {"title_block_tags": tags, "layers": layers, "extents": ext, "text_heights": sorted(heights)}


def guess_sheet(ext):
    if not ext:
        return None, None
    w, h = abs(ext[2] - ext[0]), abs(ext[3] - ext[1])
    L, S = max(w, h), min(w, h)
    sizes = {"A4": (297, 210), "A3": (420, 297), "A2": (594, 420), "A1": (841, 594), "A0": (1189, 841)}
    for k, (a, b) in sizes.items():
        if a * 0.9 <= L <= a * 1.15 and b * 0.9 <= S <= b * 1.15:
            return k, "landscape" if w >= h else "portrait"
    return None, None


def cmd_add(a):
    reg = load(a.root)
    obs = read_template(a.file)
    g_sheet, g_or = guess_sheet(obs["extents"])
    sheet, orient = a.sheet or g_sheet, a.orientation or g_or
    if sheet not in SHEETS:
        sys.exit(f"sheet size not given and not guessable from the file extents ({obs['extents']}). Use --sheet A0..A4.")
    same = [t for t in reg["templates"] if t["client"] == a.client and t["sheet"] == sheet and t["name"] == a.name]
    version = max([t["version"] for t in same], default=0) + 1
    seq = len([t for t in reg["templates"] if t["client"] == a.client and t["sheet"] == sheet]) + 1
    tid = f"TPL-{a.client}-{sheet}-{seq:03d}" if not same else same[0]["template_id"]
    dest = Path(a.root) / "files" / f"{tid}_v{version}.dxf"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(a.file, dest)
    entry = {"template_id": tid, "client": a.client, "client_name": a.client_name or "", "name": a.name, "version": version, "sheet": sheet,
             "orientation": orient, "projection": a.projection, "rev_owner": a.rev_owner, "purpose_default": a.purpose,
             "file": str(dest.relative_to(a.root)).replace("\\", "/"), "sha256": sha(dest), "title_block_tags": obs["title_block_tags"],
             "layers": obs["layers"], "extents": obs["extents"], "text_heights": obs["text_heights"], "status": "DRAFT", "approved_by": "",
             "approved_on": "", "added_on": now(), "source": a.source or "", "notes": a.notes or "", "as1100_deviations": "not measured yet"}
    reg["templates"].append(entry)
    save(a.root, reg)
    print(f"added {tid} v{version} ({sheet} {orient}, projection {a.projection}, rev system: {a.rev_owner}), status DRAFT")
    if not obs["title_block_tags"]:
        print("note: no ATTDEF fields found, so title block values are plain text. Pipeline step 9b will have to find them by position.")


def rows(reg, a):
    r = reg["templates"]
    if getattr(a, "client", None):
        r = [t for t in r if t["client"] == a.client]
    if getattr(a, "sheet", None):
        r = [t for t in r if t["sheet"] == a.sheet]
    return r


def cmd_list(a):
    for t in rows(load(a.root), a):
        print(f"{t['template_id']} v{t['version']:<2} {t['client']:<6} {t['sheet']:<3} {t['orientation'] or '':<9} {t['projection']:<6} rev:{t['rev_owner']:<7} {t['status']:<8} {t['name']}")


def cmd_show(a):
    for t in load(a.root)["templates"]:
        if t["template_id"] == a.id and (a.version is None or t["version"] == a.version):
            print(json.dumps(t, indent=1))


def cmd_find(a):
    r = [t for t in rows(load(a.root), a) if t["status"] == "APPROVED"]
    if a.projection:
        r = [t for t in r if t["projection"] == a.projection]
    if not r:
        sys.exit("no APPROVED template for that client/sheet. Add one, or approve a draft. Nothing is guessed.")
    best = {}
    for t in r:
        k = t["template_id"]
        if k not in best or t["version"] > best[k]["version"]:
            best[k] = t
    out = list(best.values())
    print(json.dumps(out[0] if len(out) == 1 else out, indent=1))
    if len(out) > 1:
        print(f"{len(out)} approved templates match; a person picks one.", file=sys.stderr)


def cmd_approve(a):
    reg = load(a.root)
    cand = [t for t in reg["templates"] if t["template_id"] == a.id]
    if not cand:
        sys.exit("no such template")
    t = max(cand, key=lambda t: t["version"]) if a.version is None else next(t for t in cand if t["version"] == a.version)
    t["status"], t["approved_by"], t["approved_on"] = "APPROVED", a.by, now()
    save(a.root, reg)
    print(f"{t['template_id']} v{t['version']} APPROVED by {a.by} on {t['approved_on']}")


def cmd_check(a):
    bad = 0
    for t in load(a.root)["templates"]:
        p = Path(a.root) / t["file"]
        if not p.exists():
            print(f"MISSING {t['template_id']} v{t['version']}: {t['file']}"); bad += 1
        elif sha(p) != t["sha256"]:
            print(f"CHANGED {t['template_id']} v{t['version']}: file differs from its recorded hash"); bad += 1
        if t["status"] == "APPROVED" and not t["approved_by"]:
            print(f"UNSIGNED {t['template_id']}: approved with no name"); bad += 1
    print("register ok" if not bad else f"{bad} problem(s)")
    sys.exit(1 if bad else 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", required=True)
    sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("add"); s.add_argument("file"); s.add_argument("--client", required=True); s.add_argument("--client-name")
    s.add_argument("--name", required=True); s.add_argument("--sheet", choices=SHEETS); s.add_argument("--orientation", choices=["landscape", "portrait"])
    s.add_argument("--projection", choices=["first", "third"], required=True); s.add_argument("--rev-owner", choices=["client", "afj"], required=True)
    s.add_argument("--purpose", choices=["both", "sales", "manufacture"], default="both"); s.add_argument("--source"); s.add_argument("--notes")
    s.set_defaults(f=cmd_add)
    s = sp.add_parser("list"); s.add_argument("--client"); s.add_argument("--sheet"); s.set_defaults(f=cmd_list)
    s = sp.add_parser("show"); s.add_argument("id"); s.add_argument("--version", type=int); s.set_defaults(f=cmd_show)
    s = sp.add_parser("find"); s.add_argument("--client", required=True); s.add_argument("--sheet"); s.add_argument("--projection", choices=["first", "third"]); s.set_defaults(f=cmd_find)
    s = sp.add_parser("approve"); s.add_argument("id"); s.add_argument("--by", required=True); s.add_argument("--version", type=int); s.set_defaults(f=cmd_approve)
    s = sp.add_parser("check"); s.set_defaults(f=cmd_check)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
