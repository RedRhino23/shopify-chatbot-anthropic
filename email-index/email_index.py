#!/usr/bin/env python3
"""Read-only index of the drafting emails in Outlook, then pair requests with replies.

Runs on Ross's PC (needs desktop Outlook open and pywin32: pip install pywin32).
Nothing is changed, moved, deleted or sent. Attachments are NOT saved.
The CSV keeps: dates, subject, sender/recipient DOMAINS only (no addresses),
drawing numbers found, and attachment names/types/sizes. No email bodies.
(The body is read in memory only, to look for drawing numbers, then dropped.)

Step 1  python email_index.py index --since 2024-01-01
        Reads Inbox\\AFJ and Sent Items. Writes out\\index.csv
Step 2  python email_index.py pair
        Groups by drawing number, finds request/reply, looks for files on the NAS.
        Writes out\\issues.csv and out\\nas_files.csv (cached list of NAS file names)

Options: --mailbox ross@mydraftingcentral  --inbox-sub AFJ (repeat for more folders)  --pattern REGEX  --out DIR
Dates in the CSV are YYYY-MM-DD HH:MM (sortable).
"""
import argparse
import csv
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

VERSION = "email_index 0.5 (one row per issued drawing file; writes issues.csv)"
DEFAULT_PATTERN = r"\bD\d{4,6}[A-Z]{0,2}-\d{1,3}\b"   # e.g. D17428M-1. Change with --pattern if other numbers exist.
NAS_ROOTS = [r"\\WHY4RSNAS\QuickDraw\AFJ", r"\\WHY4RSNAS\QuickDraw\AF"]
DRAWING_EXT = {".dwg", ".dxf"}
IGNORED_ATT = re.compile(r"^(image\d{3}\.(png|jpe?g|gif)|outlook-[\w.-]+\.(png|jpe?g|gif)|~WRD\d+\.jpg)$", re.I)   # signature images
IMAGE_EXT = {".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".heic"}
INDEX_COLS = ["direction", "folder", "entry_id_tail", "conversation_id_tail", "when", "subject", "domains",
              "drawing_numbers", "attachment_names", "attachment_kinds", "attachment_bytes"]


def domain_of(addr):
    addr = (addr or "").strip().lower()
    return addr.split("@", 1)[1] if "@" in addr else ""


def smtp(mail_item_or_recipient):
    """Best-effort SMTP address for Exchange or SMTP senders/recipients. Returns '' if unknown."""
    try:
        x = mail_item_or_recipient
        if hasattr(x, "SenderEmailType"):
            if x.SenderEmailType == "EX":
                return x.Sender.GetExchangeUser().PrimarySmtpAddress
            return x.SenderEmailAddress
        ae = x.AddressEntry
        if ae.Type == "EX":
            return ae.GetExchangeUser().PrimarySmtpAddress
        return x.Address
    except Exception:
        return ""


def walk_mail(folder, since):
    items = folder.Items
    items.Sort("[ReceivedTime]" if folder.Name != "Sent Items" else "[SentOn]", False)
    for it in items:
        try:
            if it.Class != 43:          # MailItem only
                continue
            when = it.SentOn if folder.Name == "Sent Items" else it.ReceivedTime
            if str(when)[:10] < since:
                continue
            yield it, when
        except Exception:
            continue


def find_stores(ns, needle):
    """Match a mailbox by name. Skips any store Outlook cannot open (one bad data file must not stop the run)."""
    found, names = [], []
    try:
        count = ns.Stores.Count
    except Exception:
        count = 0
    for i in range(1, count + 1):
        try:
            st = ns.Stores.Item(i)
            name = st.DisplayName
        except Exception:
            names.append(f"(store {i}: not available)")
            continue
        names.append(name)
        if needle in name.lower():
            found.append(st)
    if not found:                       # fall back to the top-level folder list
        try:
            for i in range(1, ns.Folders.Count + 1):
                try:
                    fo = ns.Folders.Item(i)
                    if needle in fo.Name.lower():
                        found.append(fo.Store)
                        names.append(fo.Name)
                except Exception:
                    continue
        except Exception:
            pass
    return found, names


def cmd_index(a):
    import win32com.client                # imported here so the file still loads on other systems
    ns = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
    stores, names = find_stores(ns, a.mailbox.lower())
    print("Mailboxes Outlook lists:", names)
    if len(stores) != 1:
        sys.exit(f"Expected exactly one mailbox matching '{a.mailbox}', found {len(stores)}. Use more of the name from the list above.")
    print("Reading mailbox:", stores[0].DisplayName)
    inbox, sent = stores[0].GetDefaultFolder(6), stores[0].GetDefaultFolder(5)
    targets = []
    for sub in a.inbox_sub:
        f = inbox
        for part in sub.split("\\"):
            f = f.Folders[part]
        targets.append(("received", f))
    targets.append(("sent", sent))

    rx = re.compile(a.pattern, re.I)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    rows = []
    for direction, folder in targets:
        n = 0
        for it, when in walk_mail(folder, a.since):
            try:
                atts = [(at.FileName, at.Size) for at in it.Attachments]
                kinds = sorted({os.path.splitext(n_)[1].lower() for n_, _ in atts})
                if direction == "received":
                    doms = {domain_of(smtp(it))}
                else:
                    doms = {domain_of(smtp(r)) for r in it.Recipients}
                text = " ".join([it.Subject or "", " ".join(n_ for n_, _ in atts), (it.Body or "")[:20000]])
                nums = sorted({m.upper() for m in rx.findall(text)})
                rows.append({
                    "direction": direction, "folder": folder.FolderPath.split("\\", 3)[-1],
                    "entry_id_tail": it.EntryID[-12:], "conversation_id_tail": (it.ConversationID or "")[-12:],
                    "when": str(when)[:16], "subject": (it.Subject or "").replace("\n", " ").strip(),
                    "domains": ";".join(sorted(d for d in doms if d)),
                    "drawing_numbers": ";".join(nums),
                    "attachment_names": ";".join(n_ for n_, _ in atts),
                    "attachment_kinds": ";".join(kinds),
                    "attachment_bytes": sum(s for _, s in atts),
                })
                n += 1
                if n % 200 == 0:
                    print(f"{direction}: {n} emails...", flush=True)
            except Exception as ex:
                print("skipped one email:", type(ex).__name__, file=sys.stderr)
        print(f"{direction} {folder.Name}: {n} emails")
    with open(out / "index.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=INDEX_COLS); w.writeheader(); w.writerows(rows)
    print("wrote", out / "index.csv", len(rows), "rows")


def scan_nas(out):
    cache = out / "nas_files.csv"
    if cache.exists():
        with open(cache, newline="", encoding="utf-8-sig") as fh:
            return [r["path"] for r in csv.DictReader(fh)]
    paths = []
    for root in NAS_ROOTS:
        if not os.path.isdir(root):
            print("NAS folder not reachable (skipped):", root, file=sys.stderr)
            continue
        for d, _, files in os.walk(root):
            for f in files:
                if os.path.splitext(f)[1].lower() in DRAWING_EXT | {".pdf"}:
                    paths.append(os.path.join(d, f))
    with open(cache, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh); w.writerow(["path"]); [w.writerow([p]) for p in paths]
    return paths


def cmd_pair(a):
    out = Path(a.out)
    with open(out / "index.csv", newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    nas = scan_nas(out)
    by_no = defaultdict(list)
    for p in nas:
        stem = os.path.basename(p).upper()
        for m in re.findall(a.pattern, stem, re.I):
            by_no[m.upper()].append(p)

    # One row per ISSUED DRAWING FILE (an attachment in a sent email), linked to the latest earlier request
    # scan in the same Outlook conversation. Requests and replies come in sets (one scan, many drawings),
    # so the drawing number is read from the reply's attachment NAME, not from anywhere in the conversation.
    from datetime import datetime
    conv_rows = defaultdict(list)
    for r in rows:
        conv_rows[r["conversation_id_tail"] or ("solo-" + r["entry_id_tail"])].append(r)

    def keep(r):
        return [x for x in r["attachment_names"].split(";") if x and not IGNORED_ATT.match(x)]

    def has(r, exts):
        return any(os.path.splitext(x)[1].lower() in exts for x in keep(r))

    def days(t0, t1):
        f = "%Y-%m-%d %H:%M"
        try:
            return round((datetime.strptime(t1, f) - datetime.strptime(t0, f)).total_seconds() / 86400, 1)
        except Exception:
            return ""

    events, seen = {}, {}
    for c, rs in conv_rows.items():
        rs = sorted(rs, key=lambda r: r["when"])
        for r in rs:
            if r["direction"] != "sent":
                continue
            for name in keep(r):
                if os.path.splitext(name)[1].lower() not in IMAGE_EXT | DRAWING_EXT | {".zip"}:
                    continue
                for no in sorted({m.upper() for m in re.findall(a.pattern, name, re.I)}):
                    key = (no, name.lower())
                    if key in events:
                        events[key]["times_sent"] += 1
                        continue
                    reqs = [x for x in rs if x["direction"] == "received" and has(x, IMAGE_EXT) and x["when"] <= r["when"]]
                    req = reqs[-1] if reqs else None
                    files = sorted(by_no.get(no, []))
                    m = re.search(r"rev\s*([A-Z0-9][A-Z0-9 \-]*?)(?:\.\w+)?$", name, re.I)
                    notes = []
                    if not req: notes.append("no request scan before this reply")
                    if not files: notes.append("no file found on NAS (typo in the name?)")
                    gap = days(req["when"], r["when"]) if req else ""
                    if gap != "" and gap > 120: notes.append("request is over 120 days earlier (check it is the right scan)")
                    events[key] = {
                        "drawing_no": no, "issued_file": name, "issued_rev": m.group(1).strip() if m else "",
                        "issued_when": r["when"], "issued_subject": r["subject"],
                        "drawings_in_that_email": len({n for x in keep(r) for n in re.findall(a.pattern, x, re.I)}),
                        "request_when": req["when"] if req else "", "request_subject": req["subject"] if req else "",
                        "request_attachments": ";".join(keep(req)) if req else "", "days_request_to_reply": gap,
                        "conversation": c, "times_sent": 1,
                        "nas_files": " | ".join(files[:10]),
                        "clean": "yes" if req and files else "no",
                        "notes": "; ".join(notes),
                    }
    ev = sorted(events.values(), key=lambda e: (e["drawing_no"], e["issued_when"]))
    with open(out / "issues.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(ev[0].keys()) if ev else ["drawing_no"])
        w.writeheader(); w.writerows(ev)
    clean = sum(1 for e in ev if e["clean"] == "yes")
    nums = {e["drawing_no"] for e in ev}
    print(f"{len(ev)} issued drawing files ({len(nums)} drawing numbers); {clean} clean (request scan found + files on NAS). Wrote {out / 'issues.csv'}")
    from collections import Counter
    why = Counter(n for e in ev for n in filter(None, (x.strip() for x in e["notes"].split(";"))))
    print("Reasons not clean:")
    for k, v in why.most_common():
        print(f"  {v:4d}  {k}")
    print(f"NAS: {len(nas)} drawing/PDF files listed; {len(by_no)} drawing numbers matched a file name")
    print(f"Emails: {sum(1 for r in rows if r['direction']=='received')} received, {sum(1 for r in rows if r['direction']=='sent')} sent; "
          f"conversations: {len(conv_rows)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (("index", cmd_index), ("pair", cmd_pair)):
        p = sub.add_parser(name)
        p.add_argument("--out", default="out")
        p.add_argument("--pattern", default=DEFAULT_PATTERN)
        if name == "index":
            p.add_argument("--since", default="2024-01-01")
            p.add_argument("--mailbox", default="ross@mydraftingcentral", help="part of the mailbox name in Outlook")
            p.add_argument("--inbox-sub", action="append", default=None, help="Inbox subfolder, repeatable (default AFJ)")
        p.set_defaults(fn=fn)
    a = ap.parse_args()
    print(VERSION)
    if getattr(a, "inbox_sub", "x") is None:
        a.inbox_sub = ["AFJ"]
    a.fn(a)


if __name__ == "__main__":
    main()
