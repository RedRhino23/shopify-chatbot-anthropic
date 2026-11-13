"""Self-test for overlay_check.py. Builds synthetic PDFs from a DXF with known faults and checks each is caught.
    python tests/run_tests.py path/to/any.dxf
Exit 0 only if every case behaves as expected."""
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASES = {  # name: (expected exit code, text that must appear)
    "ok": (0, "PASS"),
    "offset_scaled": (0, "PASS"),
    "missing_line": (1, "EXTRA in result"),
    "extra_line": (1, "MISSING in result"),
    "wrong_number": (1, "numbers on source, not on result"),
    "moved_number": (1, "moved:"),
}


def main(dxf):
    tmp = Path(tempfile.mkdtemp())
    subprocess.run([sys.executable, str(HERE / "make_synthetic.py"), dxf, str(tmp)], check=True, capture_output=True)
    bad = 0
    for name, (code, needle) in CASES.items():
        r = subprocess.run([sys.executable, str(HERE.parent / "overlay_check.py"), str(tmp / f"{name}.pdf"), dxf, "--out", str(tmp / name)], capture_output=True, text=True)
        ok = r.returncode == code and needle in r.stdout
        bad += not ok
        print(("ok   " if ok else "FAIL ") + name)
        if not ok:
            print(r.stdout[-600:], r.stderr[-300:])
    print("all cases behave" if not bad else f"{bad} case(s) wrong")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main(sys.argv[1])
