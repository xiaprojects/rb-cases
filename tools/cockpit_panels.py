"""Generate the RB-Cockpits 3D-printable panels with FreeCAD.

Run from the repo root:

    freecad.cmd tools/cockpit_panels.py

Environment options:

    RB_BED=250       largest tile side in mm (default 200, fits most printers)
    RB_ONLY=glider   build only the cockpits whose folder starts with this

The layouts and cut-out sizes are in tools/cockpit_layouts.py, shared with the
KiCad generator. Each panel is cut into tiles that fit the bed, joined by
glued dovetails. Output goes to RB-Cockpits/<cockpit>/: one STL per tile placed
face down, a DXF of each whole panel, a FreeCAD model, an SVG layout map, and
the generated parts block of README.md.
"""
import glob
import math
import os
import re
import sys

import FreeCAD as App
import MeshPart
import Part

sys.path.insert(0, os.path.join(os.getcwd(), "tools"))  # run from the repo root
from cockpit_layouts import COCKPITS, EAR, expand, parse_path, polygon  # noqa: E402

V = App.Vector

# ---------------------------------------------------------------- parameters
BED = float(os.environ.get("RB_BED", 200))
ONLY = os.environ.get("RB_ONLY", "")
THICK = 4.0             # panel thickness
ENGRAVE = 0.6           # label depth
MARGIN = 5.0            # material kept between a seam and a large cut-out
SMALL_MARGIN = 2.5      # ... and a screw hole or a label
SLIVER = 12.0           # a seam outside a display window keeps at least this much frame
MIN_TILE = 40.0         # shortest tile side
DOVETAILS = [(10.0, 14.0, 8.0), (6.0, 9.0, 6.0)]  # neck, head, depth; big one first
CLEAR = 0.15            # gap around each dovetail
DOVE_PITCH = 60.0       # one dovetail every DOVE_PITCH mm of seam
MAX_SEG = BED - DOVETAILS[0][2] - 1  # tiles grow by one dovetail depth

FONT = "/usr/share/fonts/truetype/liberation/LiberationSansNarrow-Bold.ttf"
LABEL = {"small": 4.6, "tiny": 3.8}  # font size in mm

def fail(msg):
    # FreeCAD's command mode drops the SystemExit message: print it first
    print(f"error: {msg}", flush=True)
    raise SystemExit(1)


LICENSE = "Free for personal use; commercial use requires an agreement, see [LICENSE.md](../../LICENSE.md)"


# ---------------------------------------------------------------- polygon helpers
def crossings(poly, axis, at):
    """Sorted coordinates where the line {axis = at} crosses the polygon."""
    a, b = (0, 1) if axis == "x" else (1, 0)
    out = []
    for p, q in zip(poly, poly[1:] + poly[:1]):
        if (p[a] <= at < q[a]) or (q[a] <= at < p[a]):
            out.append(p[b] + (at - p[a]) * (q[b] - p[b]) / (q[a] - p[a]))
    return sorted(out)


def inside(poly, x, y):
    c = crossings(poly, "x", x)
    return sum(1 for v in c if v < y) % 2 == 1


# ---------------------------------------------------------------- 1-D intervals
def intersect(a, b):
    out = []
    for x0, x1 in a:
        for y0, y1 in b:
            lo, hi = max(x0, y0), min(x1, y1)
            if hi > lo:
                out.append((lo, hi))
    return out


def subtract(ivs, lo, hi):
    out = []
    for a, b in ivs:
        if hi <= a or lo >= b:
            out.append((a, b))
        else:
            if lo > a:
                out.append((a, lo))
            if hi < b:
                out.append((hi, b))
    return out


# ---------------------------------------------------------------- panel model
class Panel:
    def __init__(self, cockpit, name, spec):
        self.cockpit, self.name = cockpit, name
        self.w, self.h = spec["w"], spec["h"]
        self.path = spec["outline"]
        self.segs = parse_path(self.path)
        self.poly = polygon(self.segs)
        geo = expand(spec)
        self.holes = geo["holes"]    # (kind, cx, cy, size...) in panel coordinates, y down
        self.labels = geo["labels"]  # (cx, cy, text, size)
        self.ears = geo["ears"]      # (x0, y0, x1, y1, hx, hy) ear body and hole centre
        self.bom = geo["bom"]
        self.label_shapes = [self._text(*lab) for lab in self.labels]
        boxes = self.ear_boxes()
        xs = [p[0] for p in self.poly] + [b[0] for b in boxes] + [b[2] for b in boxes]
        ys = [p[1] for p in self.poly] + [b[1] for b in boxes] + [b[3] for b in boxes]
        self.x0, self.x1, self.y0, self.y1 = min(xs), max(xs), min(ys), max(ys)

    def ear_boxes(self):
        """Ear body and its rounded end, panel coordinates: (x0, y0, x1, y1, 'hard')."""
        r = EAR[0] / 2
        return [(min(x0, hx - r), min(y0, hy - r), max(x1, hx + r), max(y1, hy + r), "hard")
                for x0, y0, x1, y1, hx, hy in self.ears]

    # text outlines, centred on (cx, cy) in panel coordinates
    def _text(self, cx, cy, s, size):
        chars = Part.makeWireString(s, FONT, LABEL[size], 0)
        faces = [Part.Face(Part.Compound(ch), "Part::FaceMakerBullseye") for ch in chars if ch]
        comp = Part.Compound(faces)
        bb = comp.BoundBox
        comp.translate(V(cx - (bb.XMin + bb.XMax) / 2, (self.h - cy) - (bb.YMin + bb.YMax) / 2, 0))
        return comp

    # ------------------------------------------------------------ geometry helpers
    def P(self, x, y, z=0.0):
        """Panel coordinates (y down) to FreeCAD (y up)."""
        return V(x, self.h - y, z)

    def hole_boxes(self, grow=0.0):
        """Bounding boxes of every hole and label, panel coordinates: (x0, y0, x1, y1, kind)."""
        out = []
        for hl in self.holes:
            if hl[0] == "circle":
                r = hl[3] / 2 + grow
                out.append((hl[1] - r, hl[2] - r, hl[1] + r, hl[2] + r, "small" if hl[3] <= 6 else "hard"))
            else:
                w, h = hl[3] / 2 + grow, hl[4] / 2 + grow
                out.append((hl[1] - w, hl[2] - h, hl[1] + w, hl[2] + h, "window" if hl[0] == "window" else "hard"))
        for comp in self.label_shapes:
            bb = comp.BoundBox
            out.append((bb.XMin - grow, self.h - bb.YMax - grow, bb.XMax + grow, self.h - bb.YMin + grow, "small"))
        return out

    def check(self):
        """Holes and labels must not touch each other and must sit inside the panel."""
        problems = []
        circles = [hl for hl in self.holes if hl[0] == "circle"]
        for i, a in enumerate(circles):
            for b in circles[i + 1:]:
                gap = math.hypot(a[1] - b[1], a[2] - b[2]) - (a[3] + b[3]) / 2
                if gap < 1.5:
                    problems.append(f"holes at ({a[1]:g}, {a[2]:g}) and ({b[1]:g}, {b[2]:g}) are {gap:.1f} mm apart")
        n = len(self.holes)
        boxes = self.hole_boxes(grow=1)
        for i in range(n, len(boxes)):  # each label against every hole and the other labels
            lx0, ly0, lx1, ly1, _ = boxes[i]
            for j, (x0, y0, x1, y1, _) in enumerate(boxes):
                if j == i or not (x0 < lx1 and lx0 < x1 and y0 < ly1 and ly0 < y1):
                    continue
                if j < n and self.holes[j][0] == "circle":  # boxes overlap: is the circle itself in?
                    hl = self.holes[j]
                    nx, ny = min(max(hl[1], lx0), lx1), min(max(hl[2], ly0), ly1)
                    if math.hypot(nx - hl[1], ny - hl[2]) > hl[3] / 2 + 1:
                        continue
                problems.append(f"label '{self.labels[i - n][2]}' touches something near ({x0:.0f}, {y0:.0f})")
        ear_holes = {(e[4], e[5]) for e in self.ears}
        for hl in circles:
            if (hl[1], hl[2]) in ear_holes:
                continue
            r = hl[3] / 2 + 1.5
            if not all(inside(self.poly, hl[1] + r * math.cos(a), hl[2] + r * math.sin(a))
                       for a in [k * math.pi / 8 for k in range(16)]):
                problems.append(f"hole at ({hl[1]:g}, {hl[2]:g}) is too close to the panel edge")
        if problems:
            fail(f"{self.cockpit} {self.name}: " + "; ".join(problems))

    def solid(self):
        edges = []
        for s in self.segs:
            if s[0] == "L":
                edges.append(Part.LineSegment(self.P(*s[1]), self.P(*s[2])).toShape())
            else:
                c = Part.BezierCurve()
                c.setPoles([self.P(*s[1]), self.P(*s[2]), self.P(*s[3])])
                edges.append(c.toShape())
        body = Part.Face(Part.Wire(edges)).extrude(V(0, 0, THICK))
        for x0, y0, x1, y1, hx, hy in self.ears:
            body = body.fuse(Part.makeBox(x1 - x0, y1 - y0, THICK, self.P(x0, y1)))
            body = body.fuse(Part.makeCylinder(EAR[0] / 2, THICK, self.P(hx, hy)))
        cutters = []
        for hl in self.holes:
            if hl[0] == "circle":
                cutters.append(Part.makeCylinder(hl[3] / 2, THICK + 2, self.P(hl[1], hl[2], -1)))
            else:
                _, cx, cy, w, h, r = hl
                f = Part.makePlane(w - 2 * r, h - 2 * r, self.P(cx - w / 2 + r, cy + h / 2 - r, -1))
                cutters.append(Part.Face(f.OuterWire.makeOffset2D(r)).extrude(V(0, 0, THICK + 2)))
        for comp in self.label_shapes:
            t = comp.extrude(V(0, 0, ENGRAVE + 1))
            t.translate(V(0, 0, THICK - ENGRAVE))
            cutters.append(t)
        return body.removeSplitter().cut(Part.Compound(cutters)).removeSplitter()

    # ------------------------------------------------------------ tiling
    def seam_ok(self, s, keep):
        for a, b, kind in keep:
            m = SMALL_MARGIN if kind == "small" else MARGIN
            if kind != "window" and a - m < s < b + m:
                return False
            if kind == "window" and (a - SLIVER < s < a + 2 or b - 2 < s < b + SLIVER):
                return False
        return True

    def seams(self, lo, hi, keep):
        """Fewest seams splitting [lo, hi] in pieces of MIN_TILE..MAX_SEG, longest shortest piece
        wins; None when no layout fits."""
        if hi - lo <= MAX_SEG:
            return []
        cand = [lo] + [s for s in range(math.ceil(lo) + 1, math.floor(hi)) if self.seam_ok(s, keep)] + [hi]
        best = {lo: (0, -math.inf, None)}
        for p in cand[1:]:
            for q in cand:
                if q >= p:
                    break
                seg = p - q
                if q not in best or seg > MAX_SEG or seg < MIN_TILE:
                    continue
                c, m, _ = best[q]
                val = (c + 1, max(m, -seg) if m != -math.inf else -seg)
                if p not in best or val < best[p][:2]:
                    best[p] = val + (q,)
        if hi not in best:
            return None
        out, p = [], best[hi][2]
        while p != lo:
            out.append(p)
            p = best[p][2]
        return sorted(out)

    def allowed(self, lo, hi, keep):
        """Allowed seam positions as compact ranges, for error messages."""
        out, start, prev = [], None, None
        for s in range(math.ceil(lo) + 1, math.floor(hi)):
            if self.seam_ok(s, keep):
                if start is None:
                    start = s
                prev = s
            elif start is not None:
                out.append(f"{start}-{prev}")
                start = None
        if start is not None:
            out.append(f"{start}-{prev}")
        return ", ".join(out) or "nowhere"

    def plan(self):
        """Tiles as (id, x0, x1, y0, y1) plus seams; columns first or rows first, fewer tiles wins."""
        allb = self.hole_boxes() + self.ear_boxes()
        plans, why = [], []
        for first in ("x", "y"):
            a0, a1, b0, b1 = (self.x0, self.x1, self.y0, self.y1) if first == "x" else (self.y0, self.y1, self.x0, self.x1)
            ia, ib = (0, 1) if first == "x" else (1, 0)
            keep_a = [(bx[ia], bx[ia + 2], bx[4]) for bx in allb]
            cuts = self.seams(a0, a1, keep_a)
            if cuts is None:
                why.append(f"no {first} seams fit; allowed at {self.allowed(a0, a1, keep_a)}")
                continue
            cuts = [a0] + cuts + [a1]
            strips = []
            for s0, s1 in zip(cuts, cuts[1:]):
                keep_b = [(bx[ib], bx[ib + 2], bx[4]) for bx in allb if bx[ia] < s1 and bx[ia + 2] > s0]
                inner = self.seams(b0, b1, keep_b)
                if inner is None:
                    why.append(f"{first} strip {s0:.0f}..{s1:.0f} cannot be split; allowed at {self.allowed(b0, b1, keep_b)}")
                    break
                strips.append((s0, s1, [b0] + inner + [b1]))
            else:
                plans.append((sum(len(c) - 1 for _, _, c in strips), first, strips))
        if not plans:
            fail(f"{self.cockpit} {self.name}: no tiling fits a {BED:g} mm bed: " + "; ".join(why))
        n, first, strips = min(plans, key=lambda p: (p[0], p[1] != "x"))
        self.first, self.strips = first, strips
        tiles = []
        for i, (s0, s1, cuts) in enumerate(strips):
            for j, (c0, c1) in enumerate(zip(cuts, cuts[1:])):
                x0, x1, y0, y1 = (s0, s1, c0, c1) if first == "x" else (c0, c1, s0, s1)
                col, row = (i, j) if first == "x" else (j, i)
                tiles.append((f"{chr(65 + col)}{row + 1}", x0, x1, y0, y1))
        return tiles

    def material(self, axis, s, band, lo, hi, perp):
        """Intervals along a seam {axis = s} with solid panel on both sides for `band` mm."""
        ivs = None
        for at in (s - band, s - band / 2, s, s + band / 2, s + band):
            c = crossings(self.poly, axis, at)
            cur = [(c[k], c[k + 1]) for k in range(0, len(c) - 1, 2)]
            ivs = cur if ivs is None else intersect(ivs, cur)
        ivs = [(a + 2, b - 2) for a, b in ivs if b - a > 4]
        ia, ib = (0, 1) if axis == "x" else (1, 0)
        n = len(self.holes)
        for k, bx in enumerate(self.hole_boxes(grow=2)):
            hl = self.holes[k] if k < n else None
            if hl and hl[0] == "circle":  # exact chord of the circle inside the band
                r = hl[3] / 2 + 2
                across, along = hl[1 + ia], hl[1 + ib]
                d = max(0.0, abs(across - s) - band)
                if d < r:
                    half = math.sqrt(r * r - d * d)
                    ivs = subtract(ivs, along - half, along + half)
            elif bx[ia] < s + band and bx[ia + 2] > s - band:
                ivs = subtract(ivs, bx[ib], bx[ib + 2])
        clear = DOVETAILS[0][1] / 2 + DOVETAILS[0][2] + 2  # away from the tabs of a crossing seam
        for t in perp:
            ivs = subtract(ivs, t - clear, t + clear)
        return intersect(ivs, [(lo, hi)])

    def dovetails(self):
        """Dovetails as (axis, seam, centre, (neck, head, depth)); the left or upper tile owns each."""
        seams = []  # (axis, position, lo, hi, perpendicular seams)
        first = self.first
        strip_cuts = [c[1:-1] for _, _, c in self.strips]
        for i, (s0, s1, cuts) in enumerate(self.strips):
            if i > 0:  # seam between strip i-1 and i, along the whole strip
                perp = strip_cuts[i - 1] + strip_cuts[i]
                lo, hi = (self.y0, self.y1) if first == "x" else (self.x0, self.x1)
                seams.append((first, s0, lo, hi, perp))
            other = "y" if first == "x" else "x"
            for c in cuts[1:-1]:
                seams.append((other, c, s0, s1, [s0, s1]))
        out = []
        for axis, s, lo, hi, perp in seams:
            placed = []
            for neck, head, depth in DOVETAILS:
                ivs = self.material(axis, s, depth + 1, lo, hi, perp)
                for c0, _ in placed:  # keep clear of bigger dovetails already placed
                    ivs = subtract(ivs, c0 - head - 6, c0 + head + 6)
                for a, b in ivs:
                    length = b - a
                    if length < head + 2 * CLEAR + 1:
                        continue
                    n = max(1, round(length / DOVE_PITCH))
                    for k in range(n):
                        placed.append((a + length * (k + 0.5) / n, (neck, head, depth)))
            out += [(axis, s, c, size) for c, size in placed]
        return out

    def tab(self, axis, s, c, size, grow):
        neck, head, depth = size
        g = grow
        pts = [(s - 0.05, c - neck / 2 - g), (s + depth + g, c - head / 2 - g),
               (s + depth + g, c + head / 2 + g), (s - 0.05, c + neck / 2 + g)]
        if axis == "y":
            pts = [(q, p) for p, q in pts]
        wire = Part.makePolygon([self.P(x, y, -1) for x, y in pts] + [self.P(*pts[0], -1)])
        return Part.Face(wire).extrude(V(0, 0, THICK + 2))

    def tiles(self, body, plan, tabs):
        out = []
        big = 1000
        for tid, x0, x1, y0, y1 in plan:
            bx0 = x0 if x0 > self.x0 else x0 - big
            bx1 = x1 if x1 < self.x1 else x1 + big
            by0 = y0 if y0 > self.y0 else y0 - big
            by1 = y1 if y1 < self.y1 else y1 + big
            region = Part.makeBox(bx1 - bx0, by1 - by0, THICK + 2, self.P(bx0, by1, -1))
            own, foreign = [], []
            for axis, s, c, size in tabs:
                a0, a1, b0, b1 = (y0, y1, x0, x1) if axis == "x" else (x0, x1, y0, y1)
                if a0 < c < a1:
                    if s == b1:
                        own.append(self.tab(axis, s, c, size, 0))
                    elif s == b0:
                        foreign.append(self.tab(axis, s, c, size, CLEAR))
            if own:
                region = region.fuse(Part.Compound(own))
            if foreign:
                region = region.cut(Part.Compound(foreign))
            shape = body.common(region).removeSplitter()
            # a tile crossing a display window falls apart: name the pieces top to bottom
            pieces = sorted((so for so in shape.Solids if so.Volume >= 1),
                            key=lambda so: (-round(so.BoundBox.Center.y), so.BoundBox.Center.x))
            for k, sol in enumerate(pieces):
                out.append((tid if len(pieces) == 1 else f"{tid}{chr(97 + k)}", sol))
        return out


# ---------------------------------------------------------------- output
def human(n):
    return f"{n / 1048576:.1f} MB" if n >= 1048576 else f"{(n + 1023) // 1024} KB"


def write_stl(sol, path):
    s = sol.copy()
    s.rotate(V(0, 0, 0), V(1, 0, 0), 180)  # face down on the bed
    bb = s.BoundBox
    s.translate(V(-bb.XMin, -bb.YMin, -bb.ZMin))
    mesh = MeshPart.meshFromShape(Shape=s, LinearDeflection=0.1, AngularDeflection=math.radians(15))
    mesh.write(path)
    bb = s.BoundBox
    return bb.XLength, bb.YLength


def write_dxf(body, panel, path):
    """2-D drawing of the whole panel in mm, for laser or CNC cutting: CUT and ENGRAVE layers."""
    out = ["0", "SECTION", "2", "ENTITIES"]

    def poly(layer, pts):
        out.extend(["0", "POLYLINE", "8", layer, "66", "1", "70", "1"])
        for q in pts:
            out.extend(["0", "VERTEX", "8", layer, "10", f"{q.x:.4f}", "20", f"{q.y:.4f}", "30", "0"])
        out.extend(["0", "SEQEND", "8", layer])

    back = max((f for f in body.Faces if abs(f.normalAt(0, 0).z + 1) < 1e-6 and abs(f.BoundBox.ZMin) < 1e-6),
               key=lambda f: f.Area)
    for wire in back.Wires:
        e = wire.Edges
        if len(e) == 1 and isinstance(e[0].Curve, Part.Circle) and e[0].isClosed():
            c = e[0].Curve
            out.extend(["0", "CIRCLE", "8", "CUT", "10", f"{c.Center.x:.4f}", "20", f"{c.Center.y:.4f}",
                        "30", "0", "40", f"{c.Radius:.4f}"])
        else:
            poly("CUT", wire.discretize(Deflection=0.02))
    for comp in panel.label_shapes:
        for f in comp.Faces:
            for wire in f.Wires:
                poly("ENGRAVE", wire.discretize(Deflection=0.02))
    out.extend(["0", "ENDSEC", "0", "EOF"])
    with open(path, "w") as fh:
        fh.write("\n".join(out) + "\n")


def label_point(sol):
    """The point of the tile's back face farthest from its edges, to write the tile name on."""
    face = max((f for f in sol.Faces if abs(f.normalAt(0, 0).z + 1) < 1e-6 and abs(f.BoundBox.ZMin) < 1e-6),
               key=lambda f: f.Area)
    edges = Part.Compound(face.Wires)
    bb, best, far = face.BoundBox, face.BoundBox.Center, -1.0
    for i in range(1, 24):
        for j in range(1, 24):
            q = V(bb.XMin + bb.XLength * i / 24, bb.YMin + bb.YLength * j / 24, 0)
            if face.isInside(q, 0.01, True):
                d = Part.Vertex(q).distToShape(edges)[0]
                if d > far:
                    best, far = q, d
    return best


def svg(panel, tiles, tabs, path):
    m = 30
    x0, y0 = panel.x0 - m, panel.y0 - m
    w, h = panel.x1 - panel.x0 + 2 * m, panel.y1 - panel.y0 + 2 * m
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0:.1f} {y0:.1f} {w:.1f} {h:.1f}" '
         f'width="{w * 1.6:.0f}" height="{h * 1.6:.0f}" font-family="Liberation Sans Narrow, Arial Narrow, sans-serif">',
         f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{w:.1f}" height="{h:.1f}" fill="#ffffff"/>']
    body = '<g fill="#dfe3e6" stroke="#2b2f33" stroke-width="0.6">'
    for ex0, ey0, ex1, ey1, hx, hy in panel.ears:
        body += f'<rect x="{ex0:.1f}" y="{ey0:.1f}" width="{ex1 - ex0:.1f}" height="{ey1 - ey0:.1f}"/>'
        body += f'<circle cx="{hx:.1f}" cy="{hy:.1f}" r="{EAR[0] / 2:.1f}"/>'
    body += f'<path d="{panel.path}"/></g>'
    o.append(body)
    g = '<g fill="#ffffff" stroke="#2b2f33" stroke-width="0.5">'
    for hl in panel.holes:
        if hl[0] == "circle":
            g += f'<circle cx="{hl[1]:.2f}" cy="{hl[2]:.2f}" r="{hl[3] / 2:.2f}"/>'
        else:
            _, cx, cy, ww, hh, r = hl
            g += f'<rect x="{cx - ww / 2:.2f}" y="{cy - hh / 2:.2f}" width="{ww:.2f}" height="{hh:.2f}" rx="{r}"/>'
    o.append(g + "</g>")
    # the engraved labels, drawn from their real outlines
    d = ""
    for comp in panel.label_shapes:
        for f in comp.Faces:
            for wire in f.Wires:
                pts = wire.discretize(Deflection=0.05)
                d += "M" + " L".join(f"{q.x:.2f} {panel.h - q.y:.2f}" for q in pts) + "Z"
    o.append(f'<path d="{d}" fill="#5b6268" fill-rule="evenodd"/>')
    # seams with their dovetails, drawn as one outline per tile
    g = '<g fill="none" stroke="#c62828" stroke-width="0.9" stroke-linejoin="round">'
    for tid, sol in tiles:
        for f in sol.Faces:
            if abs(f.normalAt(0, 0).z + 1) < 1e-6 and abs(f.BoundBox.ZMin) < 1e-6:
                for e in f.OuterWire.Edges:
                    pts = e.discretize(Deflection=0.3)
                    g += '<polyline points="' + " ".join(f"{p.x:.2f},{panel.h - p.y:.2f}" for p in pts) + '"/>'
    o.append(g + "</g>")
    o.append('<g fill="#c62828" font-weight="bold" font-size="14" text-anchor="middle" dominant-baseline="central" '
             'stroke="#ffffff" stroke-width="3" paint-order="stroke">')
    for tid, sol in tiles:
        c = label_point(sol)
        o.append(f'<text x="{c.x:.1f}" y="{panel.h - c.y:.1f}">{tid}</text>')
    o.append("</g></svg>")
    with open(path, "w") as f:
        f.write("\n".join(o) + "\n")


def build(slug, spec):
    root = os.path.join("RB-Cockpits", slug)
    files, images = os.path.join(root, "files"), os.path.join(root, "images")
    os.makedirs(files, exist_ok=True)
    os.makedirs(images, exist_ok=True)
    for old in glob.glob(os.path.join(files, "*")) + glob.glob(os.path.join(images, "layout*.svg")):
        os.remove(old)
    doc = App.newDocument(slug.replace("-", "_"))
    bom, sections = {}, []
    for pname, pspec in spec["panels"].items():
        panel = Panel(slug, pname, pspec)
        panel.check()
        body = panel.solid()
        plan = panel.plan()
        tabs = panel.dovetails()
        tiles = panel.tiles(body, plan, tabs)
        base = slug + (f"-{pname}" if pname else "")
        obj = doc.addObject("Part::Feature", (pname or "panel").capitalize())
        obj.Shape = body
        rows = []
        for tid, sol in tiles:
            t = doc.addObject("Part::Feature", f"{(pname or 'panel').capitalize()}_{tid}")
            t.Shape = sol
            fn = f"{base}-{tid}.stl"
            sx, sy = write_stl(sol, os.path.join(files, fn))
            rows.append((tid, sx, sy, fn))
        write_dxf(body, panel, os.path.join(files, base + ".dxf"))
        lay = f"layout{'-' + pname if pname else ''}.svg"
        svg(panel, tiles, tabs, os.path.join(images, lay))
        for k, v in panel.bom.items():
            bom[k] = bom.get(k, 0) + v
        sections.append((pname, base, lay, rows, panel))
        print(f"{base}: {len(rows)} tiles, {len(tabs)} dovetails", flush=True)
    doc.recompute()
    doc.saveAs(os.path.abspath(os.path.join(files, slug + ".FCStd")))
    App.closeDocument(doc.Name)
    write_readme(slug, spec, root, files, bom, sections)


def write_readme(slug, spec, root, files, bom, sections):
    b = ["<!-- BEGIN parts: generated by tools/cockpit_panels.py, do not edit by hand -->", "## Hardware", "",
         "| Item | Qty | Panel cut-out |", "|---|---:|---|"]
    for (item, cut), n in sorted(bom.items(), key=lambda kv: (not kv[0][0].startswith("RB"), kv[0][0])):
        b.append(f"| {item} | {n} | {cut} |")
    b.append("")
    for pname, base, lay, rows, panel in sections:
        title = f"{pname.capitalize()} plate" if pname else "Panel"
        b += [f"## {title}", "", f'<img src="images/{lay}" alt="{title} layout with the print tiles">', "",
              f"{panel.w:g} × {panel.h:g} mm, {THICK:g} mm thick, {len(rows)} tiles for a {BED:g} mm bed.", "",
              "| Tile | Size on the bed (mm) | File |", "|---|---|---|"]
        for tid, sx, sy, fn in rows:
            size = human(os.path.getsize(os.path.join(files, fn)))
            b.append(f"| {tid} | {sx:.0f} × {sy:.0f} | [{fn}](files/{fn}) ({size}) |")
        b += ["", f"Whole {title.lower()} for laser or CNC cutting, layers CUT and ENGRAVE, mm: "
                  f"[{base}.dxf](files/{base}.dxf)", ""]
    b += [f"FreeCAD model with the whole panels and the tiles: [{slug}.FCStd](files/{slug}.FCStd)",
          "<!-- END parts -->"]
    block = "\n".join(b) + "\n"
    readme = os.path.join(root, "README.md")
    if os.path.exists(readme):
        text = open(readme).read()
        text = re.sub(r"<!-- BEGIN parts.*?<!-- END parts -->\n", lambda _: block, text, flags=re.S)
    else:
        text = "\n".join([
            f"# {spec['title']}", "",
            f"![{spec['title']} concept render](images/concept.webp)", "",
            spec["caption"], "",
            "| | |", "|---|---|",
            "| Author | RB-Avionics |",
            f"| License | {LICENSE} |",
            "| Concept | [www.rbavionics.com, RB-Simulator](https://www.rbavionics.com/#rb-simulator) |", "",
            "> **Printing for an aircraft:** these panels are made for simulators, where PLA or PETG is fine. "
            "Printed for an aircraft, they must withstand 100 °C in cruise on long flights: "
            "read [PRINTING.md](../../PRINTING.md).", "",
            f"A 3D-printable version of the panel in the concept render. Not included: {spec['missing']}.",
            "Print and assembly notes are in the [RB-Cockpits README](../README.md).", "", block])
    with open(readme, "w") as f:
        f.write(text)


if not os.path.isdir("RB-Cockpits"):
    fail("run from the repo root: freecad.cmd tools/cockpit_panels.py")
for slug, spec in COCKPITS.items():
    if slug.startswith(ONLY):
        build(slug, spec)
