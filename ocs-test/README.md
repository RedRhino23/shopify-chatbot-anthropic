# Open CAD Studio test (on Ross's PC)

Tests the headless modes of Open CAD Studio (OCS) with a small synthetic drawing. Nothing touches real drawings.

1. Download `OpenCADStudio-*-windows-x86_64-portable.exe` from https://github.com/HakanSeven12/OpenCADStudio/releases/latest (no install needed).
2. In a new empty folder, with the worker's Python (`C:\DC\worker` venv is fine): `pip install ezdxf`
3. Copy `run_ocs_tests.py` into the folder, then run:

       python run_ocs_tests.py "C:\path\OpenCADStudio-...-portable.exe"
       python run_ocs_tests.py "C:\path\OpenCADStudio-...-portable.exe" --ctb "C:\path\monochrome.ctb"

4. Send back `ocs-out\report.txt` and the PDFs in `ocs-out`.

## Then, by eye (5 minutes)
- Open `ocs-out\plot_mono.pdf` next to a RevA PDF plotted the usual way. Compare: hairlines, no lineweights, centring, paper size.
- Open `ocs-out\test.dwg` in OCS. Is the hatch, the dimension (1200) and the text the same as `test.dxf`?
- In OCS, grip-edit the dimension's end point. Does the number update? (Ross's rule 5: AutoCAD silently reverts associative edits.)

## What the script records
Exit codes for DXF to DWG, DWG to DXF and DWG 2000. Entity counts and dimension values before and after the round trip. The session `audit` and `save_verified` replies. Whether headless `plot` produces a PDF.
It does not decide pass or fail. I read the report.
