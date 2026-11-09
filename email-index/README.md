# Email index (read-only)

Builds a CSV of the drafting emails so requests can be paired with the replies and the drawings.
Runs on Ross's PC. Nothing is changed, moved, deleted or sent. Attachments are not saved. No email bodies or addresses are written (domains only).

## Setup (once)
Needs desktop Outlook (classic) open and signed in. The "new Outlook" does not allow this kind of access: if Outlook looks like a web page in an app, switch back (toggle in the top right) or tell the reviewer.

    mkdir C:\email-index
    cd C:\email-index
    C:\ocs-test\venv\Scripts\python.exe -m pip install pywin32

Copy `email_index.py` into `C:\email-index` (Raw, Copy raw file, then `notepad C:\email-index\email_index.py`).

## Run
    C:\ocs-test\venv\Scripts\python.exe .\email_index.py index --since 2024-01-01 --mailbox ross@mydraftingcentral
    C:\ocs-test\venv\Scripts\python.exe .\email_index.py pair

- `out\index.csv`: one row per email
- `out\issues.csv`: one row per drawing number, with request, reply, NAS files and a `clean` flag
- `out\nas_files.csv`: cached list of NAS file names (delete it to rescan)

Send the two CSVs to the reviewer (Ross agreed). They contain subjects and file names, so do not post them anywhere public.

## If something goes wrong
- Several mailboxes in Outlook: the script reads only the one whose name contains `--mailbox` (default `ross@mydraftingcentral`). If it lists the mailboxes and stops, use more of the name.
- `Inbox\AFJ` not found: check the folder name; use `--inbox-sub "AFJ"` or another folder (repeat the option for more).
- Few drawing numbers found: the pattern assumes numbers like `D17428M-1`. Send the reviewer five other examples and change `--pattern`.
- NAS folders skipped: connect to `\\WHY4RSNAS` first (no mapped drives in the script, UNC paths only).

## Step 3: build test cases from the issued drawings (local, no upload)
    C:\ocs-test\venv\Scripts\python.exe -m pip install pypdf
    C:\ocs-test\venv\Scripts\python.exe .\build_cases.py

Reads the earlier and the issued revision PDFs from the NAS (read-only) and writes what changed to `cases\dev\` (about 70%) and `cases\heldout\` (about 30%, chosen by a fixed rule on the drawing number). Keep `heldout` unseen until the agent is working. The case files hold drawing text, so keep them on the NAS and out of any repo. It sends nothing anywhere.
