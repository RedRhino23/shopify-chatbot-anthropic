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
    python template_register.py --root R retire TPL-MIM-A3-001 --version 1 --by "Ross" --why "client changed border"
    python template_register.py --root R add pump.step --kind 3d --scope client --client MIM --name "MIM pump skid" --rev-owner client --units mm
    python template_register.py --root R check                                  files present, hashes match, fields found
    python template_register.py --root R export-package OUT                    package for the drawing register's template import

Kinds: 2d (border / title block, DXF or DWG) and 3d (model template: STEP, Inventor, SolidWorks, Fusion or a parametric script).
Scopes: client (sits under that client's account: its own folder, clients/<CODE>/) or house (Drafting Central's own, house/).
Rules
- Approved templates are set in stone: the file is made read-only, its hash is recorded, and `check` flags any change. A change is a new version, never an edit. Old versions are never deleted; `retire` takes one out of use.
- A template is never overwritten. `add` with the same client+sheet+name makes a new version (v2, v3 ...); old files stay.
- `find` returns only APPROVED templates, newest version. Draft templates are never used on a job.
- client = a short code (MIM, BHP). The full client name is optional and stays in the register on the NAS.
"""
import argparse
import datetime
import hashlib
import json
import os
import shutil
import stat
import sys
from pathlib import Path

import ezdxf

SHEETS = ["A0", "A1", "A2", "A3", "A4"]
EXT2D = {".dxf", ".dwg"}
EXT3D = {".step", ".stp", ".iges", ".igs", ".ipt", ".iam", ".sldprt", ".sldasm", ".f3d", ".py"}
FIELDS = ["template_id", "kind", "scope", "client", "client_account_id", "client_name", "name", "version", "sheet", "orientation", "projection", "rev_owner", "purpose_default",
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
    ext = Path(a.file).suffix.lower()
    kind = a.kind or ("2d" if ext in EXT2D else "3d" if ext in EXT3D else None)
    if kind == "2d" and ext not in EXT2D or kind == "3d" and ext not in EXT3D or kind is None:
        sys.exit(f"file type {ext} does not fit kind {a.kind or '(unknown)'}. 2d: {sorted(EXT2D)}  3d: {sorted(EXT3D)}")
    if a.scope == "client" and not a.client:
        sys.exit("a client template needs --client (it is stored under that client's account folder)")
    client = a.client if a.scope == "client" else "HOUSE"
    obs = {"title_block_tags": {}, "layers": [], "extents": None, "text_heights": []}
    sheet = orient = None
    if kind == "2d":
        if ext == ".dxf":
            obs = read_template(a.file)
            g_sheet, g_or = guess_sheet(obs["extents"])
        else:
            g_sheet = g_or = None
        sheet, orient = a.sheet or g_sheet, a.orientation or g_or
        if sheet not in SHEETS:
            sys.exit(f"sheet size not given and not guessable ({obs['extents']}). Use --sheet A0..A4.")
        if not a.projection:
            sys.exit("a 2d template must say its projection: --projection first|third")
    same = [t for t in reg["templates"] if t["kind"] == kind and t["client"] == client and (t["sheet"] or "") == (sheet or "") and t["name"] == a.name]
    version = max([t["version"] for t in same], default=0) + 1
    seq = len([t for t in reg["templates"] if t["kind"] == kind and t["client"] == client and (t["sheet"] or "") == (sheet or "")]) + 1
    tag = (sheet or "3D")
    tid = f"TPL-{client}-{tag}-{seq:03d}" if not same else same[0]["template_id"]
    folder = Path("clients") / client if a.scope == "client" else Path("house")
    dest = Path(a.root) / folder / "files" / f"{tid}_v{version}{ext}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        sys.exit(f"{dest} already exists; nothing is overwritten")
    shutil.copyfile(a.file, dest)
    entry = {"template_id": tid, "kind": kind, "scope": a.scope, "client": client, "client_account_id": a.client_account_id or "",
             "client_name": a.client_name or "", "name": a.name, "version": version, "sheet": sheet, "orientation": orient,
             "projection": a.projection if kind == "2d" else None, "units": a.units if kind == "3d" else None,
             "family_code": a.family if kind == "3d" else None,
             "rev_owner": a.rev_owner, "purpose_default": a.purpose, "file": str(dest.relative_to(a.root)).replace("\\", "/"), "sha256": sha(dest),
             "title_block_tags": obs["title_block_tags"], "layers": obs["layers"], "extents": obs["extents"], "text_heights": obs["text_heights"],
             "status": "DRAFT", "approved_by": "", "approved_on": "", "locked_on": "", "added_on": now(), "source": a.source or "",
             "notes": a.notes or "", "as1100_deviations": "not measured yet"}
    reg["templates"].append(entry)
    save(a.root, reg)
    print(f"added {tid} v{version} ({kind}, {a.scope}{' ' + client if a.scope == 'client' else ''}" + (f", {sheet} {orient}, projection {a.projection}" if kind == "2d" else f", units {a.units}") + f", rev system: {a.rev_owner}), status DRAFT")
    if kind == "2d" and ext == ".dxf" and not obs["title_block_tags"]:
        print("note: no ATTDEF fields found, so title block values are plain text. Pipeline step 9b will have to find them by position.")


def rows(reg, a):
    r = reg["templates"]
    if getattr(a, "client", None):
        r = [t for t in r if t["client"] == a.client]
    if getattr(a, "sheet", None):
        r = [t for t in r if t["sheet"] == a.sheet]
    if getattr(a, "kind", None):
        r = [t for t in r if t["kind"] == a.kind]
    return r


def cmd_list(a):
    for t in rows(load(a.root), a):
        print(f"{t['template_id']} v{t['version']:<2} {t['kind']:<2} {t['client']:<6} {(t['sheet'] or '-'):<3} {(t['projection'] or t['units'] or ''):<6} rev:{t['rev_owner']:<7} {t['status']:<8} {t['name']}")


def cmd_show(a):
    for t in load(a.root)["templates"]:
        if t["template_id"] == a.id and (a.version is None or t["version"] == a.version):
            print(json.dumps(t, indent=1))


def cmd_find(a):
    r = [t for t in rows(load(a.root), a) if t["status"] == "APPROVED" and t["scope"] == "client"]
    if a.house:
        r += [t for t in rows(argparse.Namespace(client="HOUSE", sheet=a.sheet, kind=a.kind), a) if False]
        r += [t for t in load(a.root)["templates"] if t["scope"] == "house" and t["status"] == "APPROVED" and (not a.sheet or t["sheet"] == a.sheet) and (not a.kind or t["kind"] == a.kind)]
    if a.projection:
        r = [t for t in r if t["projection"] == a.projection]
    if not r:
        sys.exit("no APPROVED template under that client's account. Add one, approve a draft, or pass --house to allow a house template. Nothing is guessed.")
    best = {}
    for t in r:
        k = t["template_id"]
        if k not in best or t["version"] > best[k]["version"]:
            best[k] = t
    out = list(best.values())
    print(json.dumps(out[0] if len(out) == 1 else out, indent=1))
    if len(out) > 1:
        print(f"{len(out)} approved templates match; a person picks one.", file=sys.stderr)


def pick(reg, a):
    cand = [t for t in reg["templates"] if t["template_id"] == a.id]
    if not cand:
        sys.exit("no such template")
    return max(cand, key=lambda t: t["version"]) if a.version is None else next(t for t in cand if t["version"] == a.version)


def cmd_approve(a):
    reg = load(a.root)
    t = pick(reg, a)
    p = Path(a.root) / t["file"]
    if sha(p) != t["sha256"]:
        sys.exit("file differs from its recorded hash; refusing to approve. Add it again as a new version.")
    os.chmod(p, stat.S_IREAD)  # set in stone: read-only on disk; the hash catches anything else
    t["status"], t["approved_by"], t["approved_on"], t["locked_on"] = "APPROVED", a.by, now(), now()
    save(a.root, reg)
    print(f"{t['template_id']} v{t['version']} APPROVED and LOCKED (read-only) by {a.by} on {t['approved_on']}")


def cmd_retire(a):
    reg = load(a.root)
    t = pick(reg, a)
    t["status"] = "RETIRED"
    t["notes"] = (t["notes"] + f" | retired {now()} by {a.by}: {a.why}").strip(" |")
    save(a.root, reg)
    print(f"{t['template_id']} v{t['version']} RETIRED (file kept)")


def cmd_check(a):
    bad = 0
    for t in load(a.root)["templates"]:
        p = Path(a.root) / t["file"]
        if not p.exists():
            print(f"MISSING {t['template_id']} v{t['version']}: {t['file']}"); bad += 1
        elif sha(p) != t["sha256"]:
            print(f"CHANGED {t['template_id']} v{t['version']}: file differs from its recorded hash"); bad += 1
        if t["status"] == "APPROVED" and p.exists() and (p.stat().st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)) and os.name != "nt":
            print(f"UNLOCKED {t['template_id']} v{t['version']}: approved file is writable"); bad += 1
        if t["status"] == "APPROVED" and not t["approved_by"]:
            print(f"UNSIGNED {t['template_id']}: approved with no name"); bad += 1
    print("register ok" if not bad else f"{bad} problem(s)")
    sys.exit(1 if bad else 0)


TOOL_VERSION = "tpl-1"


def cmd_export_package(a):
    """Write OUT/templates.jsonl and OUT/manifest.json for the drawing register's template import (see IMPORT-SPEC.md).
    One JSON line per template version, sorted, stable keys: the same register gives a byte-identical package. File bytes are NOT in
    the package; each record carries the file's path under the register root and its sha256, so the import can attach it from the NAS
    and check every byte, as the legacy import does."""
    reg = load(a.root)
    problems = []
    recs = []
    for t in sorted(reg["templates"], key=lambda t: (t["client"], t["template_id"], t["version"])):
        p = Path(a.root) / t["file"]
        if not p.exists() or sha(p) != t["sha256"]:
            problems.append(f"{t['template_id']} v{t['version']}: file missing or changed")
            continue
        if a.approved_only and t["status"] not in ("APPROVED", "RETIRED"):
            continue
        recs.append({"kind": "template", "key": f"template:{t['template_id']}:v{t['version']}", "template_id": t["template_id"], "version": t["version"],
                     "template_kind": t["kind"], "scope": t["scope"], "client_code": t["client"], "client_account_id": t["client_account_id"] or None,
                     "name": t["name"], "sheet": t["sheet"], "orientation": t["orientation"], "projection": t["projection"], "units": t.get("units"),
                     "family_code": t.get("family_code"), "rev_owner": t["rev_owner"], "purpose_default": t["purpose_default"],
                     "title_block_tags": t["title_block_tags"], "layers": t["layers"], "text_heights": t["text_heights"], "file": t["file"],
                     "sha256": t["sha256"], "status": t["status"], "approved_by": t["approved_by"] or None, "approved_on": t["approved_on"] or None,
                     "locked_on": t.get("locked_on") or None, "added_on": t["added_on"], "source": t["source"], "notes": t["notes"],
                     "as1100_deviations": t["as1100_deviations"]})
    if problems:
        print("\n".join(problems), file=sys.stderr)
        sys.exit("package not written: fix the problems above first (run `check`)")
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    body = "".join(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in recs)
    (out / "templates.jsonl").write_text(body, encoding="utf-8", newline="\n")
    man = {"tool_version": TOOL_VERSION, "records": {"template": len(recs)}, "approved_only": bool(a.approved_only),
           "package_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
           "register_sha256": hashlib.sha256(json.dumps(reg, sort_keys=True).encode("utf-8")).hexdigest()}
    (out / "manifest.json").write_text(json.dumps(man, indent=1, sort_keys=True), encoding="utf-8", newline="\n")
    print(f"{len(recs)} template version(s) -> {out}  package sha256 {man['package_sha256'][:16]}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", required=True)
    sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("add"); s.add_argument("file"); s.add_argument("--client"); s.add_argument("--client-name")
    s.add_argument("--name", required=True); s.add_argument("--sheet", choices=SHEETS); s.add_argument("--orientation", choices=["landscape", "portrait"])
    s.add_argument("--kind", choices=["2d", "3d"]); s.add_argument("--scope", choices=["client", "house"], default="client")
    s.add_argument("--client-account-id", help="the client's account id in the portal, when known")
    s.add_argument("--projection", choices=["first", "third"]); s.add_argument("--units", default="mm"); s.add_argument("--family", help="register product family code (3d)")
    s.add_argument("--rev-owner", choices=["client", "afj"], required=True)
    s.add_argument("--purpose", choices=["both", "sales", "manufacture"], default="both"); s.add_argument("--source"); s.add_argument("--notes")
    s.set_defaults(f=cmd_add)
    s = sp.add_parser("list"); s.add_argument("--client"); s.add_argument("--sheet"); s.add_argument("--kind", choices=["2d", "3d"]); s.set_defaults(f=cmd_list)
    s = sp.add_parser("show"); s.add_argument("id"); s.add_argument("--version", type=int); s.set_defaults(f=cmd_show)
    s = sp.add_parser("find"); s.add_argument("--client", required=True); s.add_argument("--sheet"); s.add_argument("--kind", choices=["2d", "3d"])
    s.add_argument("--projection", choices=["first", "third"]); s.add_argument("--house", action="store_true", help="also allow approved house templates"); s.set_defaults(f=cmd_find)
    s = sp.add_parser("approve"); s.add_argument("id"); s.add_argument("--by", required=True); s.add_argument("--version", type=int); s.set_defaults(f=cmd_approve)
    s = sp.add_parser("retire"); s.add_argument("id"); s.add_argument("--by", required=True); s.add_argument("--why", required=True); s.add_argument("--version", type=int); s.set_defaults(f=cmd_retire)
    s = sp.add_parser("check"); s.set_defaults(f=cmd_check)
    s = sp.add_parser("export-package"); s.add_argument("out"); s.add_argument("--approved-only", action="store_true", help="leave DRAFT versions out"); s.set_defaults(f=cmd_export_package)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
