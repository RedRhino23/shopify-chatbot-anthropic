"""Tied metal expansion joint (Belman LA2BT DN200 PN10 public catalogue entry): model, STEP, sheet, checks.
    python run_tied.py [tied_job.json]
"""
import itertools
import json
import sys

import cadquery as cq

from tied_model import build, masses
from tied_sheet import build_tied_sheet


def main():
    job = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "tied_job.example.json", encoding="utf-8"))
    p, parts = build()
    solids = [(k, s.val()) for k, l in parts.items() for s in l]
    cq.exporters.export(cq.Workplane(obj=cq.Compound.makeCompound([s for _, s in solids])), "tied_joint_LA2BT.step")
    m = build_tied_sheet(p, parts, job, "tied_joint_LA2BT_GA")
    bb = cq.Compound.makeCompound([s for _, s in solids]).BoundingBox()
    print(f"valid solids: {all(s.isValid() for _, s in solids)}")
    print(f"length incl. rod ends {bb.zmax - bb.zmin:.1f} (Lo {p.Lo} + 2 x {p.rod_ext} rod ends), width {bb.xmax - bb.xmin:.1f} (cat {p.B})")
    print(f"weight {m['total']:.2f} kg vs catalogue {p.catalogue_weight_kg} kg ({100 * (m['total'] / p.catalogue_weight_kg - 1):+.1f}%)")


if __name__ == "__main__":
    main()
