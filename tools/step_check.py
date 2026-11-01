"""Check a generated display case against Waveshare's 3D model of its display.

Run from the repo root, after tools/display_cases.py:

    RB_ONLY=RB-06/printed-case-waveshare-6-25 STEP=~/models/6_25inch-720x1560-LCD.stp \
        freecad.cmd tools/step_check.py

The generator checks the parts against simple blocks for the display; this places
the real model in the case frame (STEP_FRAME of the case in
tools/display_case_layouts.py, glass front at Y_GLASS) and reports every solid of
the model that a printed part cuts into. The models are Waveshare's: download them
from the display's wiki, keep them out of the repo, and keep them under $HOME, which
the FreeCAD snap can read.
"""
import os
import sys

import FreeCAD as App
import Import

sys.path.insert(0, os.path.join(os.getcwd(), "tools"))  # run from the repo root
import display_case_layouts as D  # noqa: E402

AXES = {"x": 0, "y": 1, "z": 2}


def fail(msg):
    # FreeCAD's command mode drops the SystemExit message: print it first
    print(f"error: {msg}", flush=True)
    raise SystemExit(1)


def main():
    only, step = os.environ.get("RB_ONLY", ""), os.path.expanduser(os.environ.get("STEP", ""))
    cases = [L for root, L in D.CASES.items() if root.startswith(only)] if only else []
    if len(cases) != 1 or not os.path.isfile(step):
        fail("set RB_ONLY to one case folder and STEP to its display's model")
    L = cases[0]
    if not L.STEP_FRAME:
        fail(f"{L.ROOT}: no STEP_FRAME in tools/display_case_layouts.py")
    doc = App.openDocument(os.path.abspath(os.path.join(L.ROOT, "files", f"{L.NAME}-case.FCStd")))
    parts = {o.Label: o.Shape for o in doc.Objects if o.TypeId == "Part::Feature" and o.InList == []
             and o.Shape.Solids}
    # case x, depth y, z from the model axes
    rows = [[0.0] * 3 for _ in range(3)]
    for row, spec in zip((0, 2, 1), L.STEP_FRAME[:3]):
        rows[row][AXES[spec[-1]]] = -1.0 if spec[0] == "-" else 1.0
    m = App.Matrix(*rows[0], 0, *rows[1], 0, *rows[2], 0, 0, 0, 0, 1)
    model = App.newDocument("model")
    Import.insert(step, model.Name)
    solids = []
    skip = L.STEP_FRAME[4] if len(L.STEP_FRAME) > 4 else []
    for o in model.Objects:
        if o.TypeId == "Part::Feature" and not o.Shape.isNull() and o.Shape.Solids \
                and not any(k in o.Label for k in skip):
            s = o.Shape.copy()
            s.Placement = o.getGlobalPlacement()
            solids.append((o.Label, s.transformGeometry(m)))
    front = min(s.BoundBox.YMin for _, s in solids)
    shift = App.Vector(0, L.Y_GLASS - front, L.STEP_FRAME[3])
    bad = 0
    for label, s in solids:
        s.translate(shift)
        for name, p in parts.items():
            if s.BoundBox.intersect(p.BoundBox):
                v = s.common(p).Volume
                if v > 0.05:
                    bad += 1
                    print(f"{name} cuts into {label} ({v:.1f} mm3)", flush=True)
    print(f"{L.ROOT}: {len(solids)} solids of the model, {bad} overlaps", flush=True)
    if bad:
        fail("the case cuts into the display")


main()
