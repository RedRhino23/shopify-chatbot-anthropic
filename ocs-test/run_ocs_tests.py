#!/usr/bin/env python3
"""Observational test of Open CAD Studio's headless modes. Needs: pip install ezdxf

  python run_ocs_tests.py "C:\\path\\OpenCADStudio-...-portable.exe" [--ctb C:\\path\\monochrome.ctb]

Writes everything to .\\ocs-out\\ : test drawings, PDFs, report.json, report.txt.
Nothing is deleted or overwritten outside that folder. Send report.txt back.
It records what happened. It does not decide pass or fail, except where noted.
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import ezdxf

OUT = Path("ocs-out")
REPORT = []


def log(step, **kw):
    REPORT.append({"step": step, **kw})
    print(f"[{step}] " + json.dumps(kw, default=str)[:300])


def make_drawing(path):
    doc = ezdxf.new("R2010", setup=True)
    msp = doc.modelspace()
    for a, b in [((0, 0), (1200, 0)), ((1200, 0), (1200, 500)), ((1200, 500), (0, 500)), ((0, 500), (0, 0))]:
        msp.add_line(a, b)
    msp.add_line((300, 100), (300, 400))           # interior line: stays
    msp.add_line((1500, 100), (1500, 300))         # orphan: deliberate
    msp.add_linear_dim(base=(0, -100), p1=(0, 0), p2=(1200, 0)).render()
    h = msp.add_hatch(color=2)
    h.set_pattern_fill("ANSI31", scale=10)
    h.paths.add_polyline_path([(600, 100), (1100, 100), (1100, 400), (600, 400)], is_closed=True)
    msp.add_text("TITLE BLOCK TEST", height=25).set_placement((0, 560))
    doc.saveas(path)


def run_exe(exe, *args, timeout=120):
    t = time.time()
    p = subprocess.run([str(exe), *map(str, args)], capture_output=True, text=True, timeout=timeout)
    return p.returncode, round(time.time() - t, 1), (p.stdout + p.stderr)[-400:]


class Serve:
    def __init__(self, exe):
        self.p = subprocess.Popen([str(exe), "--serve"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, text=True, bufsize=1)
        self.banner = self.p.stdout.readline().strip()

    def send(self, req):
        self.p.stdin.write(json.dumps(req) + "\n")
        self.p.stdin.flush()
        line = self.p.stdout.readline()
        try:
            return json.loads(line)
        except Exception:
            return {"raw": line}

    def close(self):
        try:
            self.p.stdin.close()
            self.p.wait(timeout=30)
        except Exception:
            self.p.kill()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("exe")
    ap.add_argument("--ctb", help="path to monochrome.ctb (optional)")
    a = ap.parse_args()
    exe = Path(a.exe).resolve()
    OUT.mkdir(exist_ok=True)
    src = (OUT / "test.dxf").resolve()
    make_drawing(src)
    log("make_drawing", path=src)

    # 1. one-shot conversions
    dwg, back, dwg2000 = (OUT / "test.dwg").resolve(), (OUT / "back.dxf").resolve(), (OUT / "test2000.dwg").resolve()
    log("export dxf->dwg", result=run_exe(exe, "--export", src, dwg))
    log("export dwg->dxf", result=run_exe(exe, "--export", dwg, back))
    log("export dwg 2000", result=run_exe(exe, "--export", src, dwg2000, "--target-version", "2000"))

    # 2. does the round trip keep dimensions, hatch, text?
    try:
        for name, p in (("original", src), ("roundtrip", back)):
            d = ezdxf.readfile(p)
            counts = {}
            for e in d.modelspace():
                counts[e.dxftype()] = counts.get(e.dxftype(), 0) + 1
            dims = [round(x.get_measurement(), 2) for x in d.modelspace().query("DIMENSION")]
            log("entities " + name, counts=counts, dimension_values=dims)
    except Exception as ex:
        log("entities roundtrip", error=str(ex))

    # 3. headless session: open, audit, query, plot
    s = Serve(exe)
    log("serve banner", banner=s.banner)
    try:
        r = s.send({"op": "open", "path": str(dwg)})
        log("serve open", reply=r)
        doc_id = r.get("document_id", 1)
        log("serve entities", reply=s.send({"op": "entities"}))
        log("serve audit dwg2000", reply=s.send({"op": "audit", "parameters": {"target_format": "dwg", "target_version": "2000"}}))
        log("serve query Dimension", reply=s.send({"op": "query", "type": "Dimension", "detail": "geometry"}))

        # PDF plot, RevA-style: A4 landscape, fit, centred, window not used here
        pdf = (OUT / "plot_default.pdf").resolve()
        base = {"protocol": 1, "document_id": doc_id, "path": str(pdf), "layout": "Model", "paper": "A4",
                "orientation": "landscape", "fit": True, "center": True}
        log("serve plot default", reply=s.send({**base, "op": "plot", "request_id": "p1"}))
        if a.ctb:
            pdf2 = (OUT / "plot_mono.pdf").resolve()
            log("serve plot ctb", reply=s.send({**base, "op": "plot", "request_id": "p2", "path": str(pdf2),
                                                "plot_style": a.ctb, "lineweights": False}))

        # Try to move the dimension's second point (rule 5 probe): record whatever happens.
        dims = s.send({"op": "query", "type": "Dimension", "detail": "summary"})
        log("serve dim summary", reply=dims)
        edited = (OUT / "edited.dxf").resolve()
        log("serve save_verified", reply=s.send({"protocol": 1, "op": "save_verified", "request_id": "sv1",
                                                  "document_id": doc_id, "path": str(edited),
                                                  "target_format": "dxf", "target_version": "2000"}))
    finally:
        s.close()

    (OUT / "report.json").write_text(json.dumps(REPORT, indent=2, default=str))
    (OUT / "report.txt").write_text("\n".join(f"[{r['step']}] " + json.dumps({k: v for k, v in r.items() if k != 'step'}, default=str)
                                               for r in REPORT))
    print(f"\nDone. Send {OUT / 'report.txt'} and the PDFs in {OUT}.")


if __name__ == "__main__":
    sys.exit(main())
