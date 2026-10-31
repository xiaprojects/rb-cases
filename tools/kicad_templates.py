"""Generate the KiCad board templates of every design (KiCad 9).

Run from the repo root with the Python that has KiCad's pcbnew module:

    python3 tools/kicad_templates.py
    RB_ONLY=RB-02 python3 tools/kicad_templates.py   # designs whose path starts with this

A template is a KiCad project in <design>/kicad/<project>/: a board outline that
fits the case, mounting holes on the case's own bosses, the case cut at the board
plane on Dwgs.User, notes on Cmts.User, an empty schematic, and meta/info.html so
the folder also works as a KiCad project template. The script runs the KiCad DRC
on every board, draws <design>/images/kicad-<project>.svg from the saved board,
and regenerates the kicad block of the design README.md.

Case coordinates are seen from the front of the instrument: x right, y up, mm
from the instrument axis, taken from sections of the case STLs. The cockpit
backplanes use the panel layouts of tools/cockpit_layouts.py (y down).
"""
import datetime
import json
import math
import os
import re
import shutil
import subprocess
import sys
import textwrap
import uuid

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cockpit_layouts import BODY, COCKPITS, expand, parse_path  # noqa: E402
from stl_slice import area, load, section, simplify  # noqa: E402

ONLY = os.environ.get("RB_ONLY", "")
FP_LIB = "/usr/share/kicad/footprints/MountingHole.pretty"
HAT_TEMPLATE = "/usr/share/kicad/template/RaspberryPi-HAT"
HOLES = {"M2": ("MountingHole_2.2mm_M2", 2.2), "M2.5": ("MountingHole_2.7mm_M2.5", 2.7),
         "M3": ("MountingHole_3.2mm_M3", 3.2), "M4": ("MountingHole_4.3mm_M4", 4.3)}
PAPERS = [("A4", 297, 210), ("A3", 420, 297), ("A2", 594, 420), ("A1", 841, 594), ("A0", 1189, 841)]
LICENSE_RB = "Free for personal use; commercial use requires an agreement, see LICENSE.md"
CLEARANCE = 0.3      # board edge to case wall where the outline follows a measured wall
CUTOUT_GAP = 1.0     # backplane cut-out around an instrument body or display module
DATE = datetime.date.today().isoformat()


def mm(v):
    return pcbnew.FromMM(v)


def fail(msg):
    raise SystemExit(f"error: {msg}")


# ---------------------------------------------------------------- template model
class Template:
    """One board, recorded in design coordinates and written with pcbnew."""

    def __init__(self, design, name, title, summary, ydown=False, license=LICENSE_RB):
        self.design, self.name, self.title, self.summary = design, name, title, summary
        self.ydown, self.license = ydown, license
        self.shapes = []   # (layer, kind, data)
        self.texts = []    # (layer, x, y, text, size)
        self.holes = []    # (x, y, screw, value)
        self.notes = []
        self.base = None   # KiCad template board to start from
        self.warnings = []

    def shape(self, layer, kind, data):
        self.shapes.append((layer, kind, data))

    def rrect(self, layer, x0, y0, x1, y1, r):
        self.shape(layer, "rrect", (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1), r))

    def circle(self, layer, cx, cy, r):
        self.shape(layer, "circle", (cx, cy, r))

    def poly(self, layer, pts):
        self.shape(layer, "poly", list(pts))

    def text(self, layer, x, y, s, size=1.5):
        self.texts.append((layer, x, y, s, size))

    def hole(self, x, y, screw, value=""):
        self.holes.append((x, y, screw, value or screw))

    def section(self, stl, axis, at, to_design):
        """Draw the case cut by the plane {axis = at} on Dwgs.User."""
        for loop in section(load(stl), axis, at):
            if area(loop) > 0.5:
                self.poly("Dwgs.User", [to_design(*p) for p in simplify(loop)])

    def bbox(self):
        xs, ys = [], []
        for _, kind, d in self.shapes:
            if kind == "rrect":
                xs += [d[0], d[2]]; ys += [d[1], d[3]]
            elif kind == "circle":
                xs += [d[0] - d[2], d[0] + d[2]]; ys += [d[1] - d[2], d[1] + d[2]]
            elif kind == "poly":
                xs += [p[0] for p in d]; ys += [p[1] for p in d]
            elif kind == "path":
                for s in d:
                    xs += [p[0] for p in s[1:]]; ys += [p[1] for p in s[1:]]
        return min(xs), min(ys), max(xs), max(ys)


# ---------------------------------------------------------------- writing boards
class Writer:
    def __init__(self, t):
        self.t = t
        if t.base:
            self.b = pcbnew.LoadBoard(t.base)
            self.ox, self.oy = 0.0, 0.0
            bb = self.b.GetBoardEdgesBoundingBox()
            self.paper = "A4"
            self.notes_at = (pcbnew.ToMM(bb.GetX()), pcbnew.ToMM(bb.GetBottom()) + 8)
            return
        self.b = pcbnew.BOARD()
        x0, y0, x1, y1 = t.bbox()
        if not t.ydown:
            y0, y1 = -y1, -y0
        w, h = x1 - x0, y1 - y0
        notes_h = 4 + 3 * sum(len(textwrap.wrap(n, 100)) for n in t.notes)
        for name, pw, ph in PAPERS:
            if w + 40 <= pw and h + notes_h + 50 <= ph:
                break
        self.paper = name  # pcbnew's Python API has no PAGE_INFO: set in the saved file
        # board centred across the sheet, near the top; notes below it
        self.ox = (pw - w) / 2 - x0
        self.oy = 25 - y0
        self.notes_at = (self.ox + x0, self.oy + y1 + 8)

    def p(self, x, y):
        return pcbnew.VECTOR2I(mm(self.ox + x), mm(self.oy + (y if self.t.ydown else -y)))

    def layer(self, name):
        # GetLayerID() wants the display names (User.Drawings): use the constants
        return {"Edge.Cuts": pcbnew.Edge_Cuts, "Dwgs.User": pcbnew.Dwgs_User, "Cmts.User": pcbnew.Cmts_User}[name]

    def add_shape(self, layer, kind, d):
        lid, w = self.layer(layer), mm(0.1 if layer == "Edge.Cuts" else 0.15)

        def seg(a, b):
            s = pcbnew.PCB_SHAPE(self.b)
            s.SetShape(pcbnew.SHAPE_T_SEGMENT)
            s.SetStart(self.p(*a)); s.SetEnd(self.p(*b))
            s.SetLayer(lid); s.SetWidth(w)
            self.b.Add(s)

        def arc(a, m, b):
            s = pcbnew.PCB_SHAPE(self.b)
            s.SetShape(pcbnew.SHAPE_T_ARC)
            s.SetArcGeometry(self.p(*a), self.p(*m), self.p(*b))
            s.SetLayer(lid); s.SetWidth(w)
            self.b.Add(s)

        if kind == "circle":
            s = pcbnew.PCB_SHAPE(self.b)
            s.SetShape(pcbnew.SHAPE_T_CIRCLE)
            s.SetCenter(self.p(d[0], d[1])); s.SetEnd(self.p(d[0] + d[2], d[1]))
            s.SetLayer(lid); s.SetWidth(w); s.SetFilled(False)
            self.b.Add(s)
        elif kind == "rrect":
            x0, y0, x1, y1, r = d
            if r <= 0:
                pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
                for a, b in zip(pts, pts[1:] + pts[:1]):
                    seg(a, b)
                return
            k = r * (1 - math.sqrt(0.5))
            seg((x0 + r, y0), (x1 - r, y0)); seg((x1, y0 + r), (x1, y1 - r))
            seg((x1 - r, y1), (x0 + r, y1)); seg((x0, y1 - r), (x0, y0 + r))
            arc((x1 - r, y0), (x1 - k, y0 + k), (x1, y0 + r))
            arc((x1, y1 - r), (x1 - k, y1 - k), (x1 - r, y1))
            arc((x0 + r, y1), (x0 + k, y1 - k), (x0, y1 - r))
            arc((x0, y0 + r), (x0 + k, y0 + k), (x0 + r, y0))
        elif kind == "poly":
            for a, b in zip(d, d[1:] + d[:1]):
                seg(a, b)
        elif kind == "path":  # cockpit outline: lines and quadratic Beziers
            for s in d:
                if s[0] == "L":
                    seg(s[1], s[2])
                else:
                    _, a, c, b = s
                    z = pcbnew.PCB_SHAPE(self.b)
                    z.SetShape(pcbnew.SHAPE_T_BEZIER)
                    z.SetStart(self.p(*a)); z.SetEnd(self.p(*b))
                    z.SetBezierC1(self.p(a[0] + 2 / 3 * (c[0] - a[0]), a[1] + 2 / 3 * (c[1] - a[1])))
                    z.SetBezierC2(self.p(b[0] + 2 / 3 * (c[0] - b[0]), b[1] + 2 / 3 * (c[1] - b[1])))
                    z.SetLayer(lid); z.SetWidth(w)
                    z.RebuildBezierToSegmentsPointsList(mm(0.05))
                    self.b.Add(z)

    def add_text(self, layer, x, y, s, size, at=None):
        t = pcbnew.PCB_TEXT(self.b)
        t.SetText(s)
        t.SetLayer(self.layer(layer))
        t.SetPosition(at if at is not None else self.p(x, y))
        t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
        t.SetTextThickness(mm(size * 0.12))
        if at is not None:
            t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
            t.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_TOP)
        self.b.Add(t)

    def write(self, folder):
        t = self.t
        for layer, kind, d in t.shapes:
            self.add_shape(layer, kind, d)
        for layer, x, y, s, size in t.texts:
            self.add_text(layer, x, y, s, size)
        for i, (x, y, screw, value) in enumerate(t.holes, 1):
            fp = pcbnew.FootprintLoad(FP_LIB, HOLES[screw][0])
            fp.SetFPID(pcbnew.LIB_ID("MountingHole", HOLES[screw][0]))
            fp.SetPosition(self.p(x, y))
            fp.SetReference(f"H{i}")
            fp.SetValue(value)
            self.b.Add(fp)
        nx, ny = self.notes_at
        self.add_text("Cmts.User", 0, 0, "\n".join(textwrap.fill(n, 100) for n in t.notes), 1.6,
                      at=pcbnew.VECTOR2I(mm(nx), mm(ny)))
        tb = self.b.GetTitleBlock()
        tb.SetTitle(t.title)
        tb.SetCompany("RB-Avionics")
        tb.SetDate(DATE)
        tb.SetRevision("1")
        tb.SetComment(0, f"Board template for {t.design}")
        tb.SetComment(1, t.license)
        tb.SetComment(2, "Generated by tools/kicad_templates.py")
        os.makedirs(folder, exist_ok=True)
        pcb = os.path.join(folder, t.name + ".kicad_pcb")
        pcbnew.SaveBoard(pcb, self.b)
        text = open(pcb).read()
        open(pcb, "w").write(re.sub(r'\(paper "[^"]*"\)', f'(paper "{self.paper}")', text, count=1))
        prl = os.path.join(folder, t.name + ".kicad_prl")
        if os.path.exists(prl):
            os.remove(prl)
        pro = os.path.join(folder, t.name + ".kicad_pro")
        if not os.path.exists(pro):  # SaveBoard writes no project for a board loaded from a template
            src = t.base[:-len(".kicad_pcb")] + ".kicad_pro" if t.base else "/usr/share/kicad/template/kicad.kicad_pro"
            data = json.load(open(src))
            data.setdefault("meta", {})["filename"] = t.name + ".kicad_pro"
            json.dump(data, open(pro, "w"), indent=2)
        return pcb


def write_schematic(t, folder, base_sch=None):
    path = os.path.join(folder, t.name + ".kicad_sch")
    if base_sch:
        text = open(base_sch).read()
        text = re.sub(r'\(uuid "[0-9a-f-]+"\)', lambda _: f'(uuid "{uuid.uuid4()}")', text, count=1)
        text = re.sub(r"\(title_block.*?\n\t\)", lambda _: title_block(t), text, count=1, flags=re.S)
        open(path, "w").write(text)
        return
    note = "\\n".join([t.summary, "", "Add your circuit here, then Tools > Update PCB from Schematic:",
                       "the board outline and the mounting holes are already in the PCB."]).replace('"', "'")
    open(path, "w").write(f"""(kicad_sch
\t(version 20250114)
\t(generator "eeschema")
\t(generator_version "9.0")
\t(uuid "{uuid.uuid4()}")
\t(paper "A4")
{title_block(t)}
\t(lib_symbols)
\t(text "{note}"
\t\t(exclude_from_sim no)
\t\t(at 25.4 38.1 0)
\t\t(effects
\t\t\t(font
\t\t\t\t(size 2.54 2.54)
\t\t\t)
\t\t\t(justify left top)
\t\t)
\t\t(uuid "{uuid.uuid4()}")
\t)
\t(sheet_instances
\t\t(path "/"
\t\t\t(page "1")
\t\t)
\t)
\t(embedded_fonts no)
)
""")


def title_block(t):
    q = lambda s: s.replace('"', "'")
    return (f'\t(title_block\n\t\t(title "{q(t.title)}")\n\t\t(date "{DATE}")\n\t\t(rev "1")\n'
            f'\t\t(company "RB-Avionics")\n\t\t(comment 1 "Board template for {q(t.design)}")\n'
            f'\t\t(comment 2 "{q(t.license)}")\n\t)')


def write_meta(t, folder):
    os.makedirs(os.path.join(folder, "meta"), exist_ok=True)
    esc = lambda s: s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    items = "".join(f"<li>{esc(n)}</li>" for n in t.notes if n)
    open(os.path.join(folder, "meta", "info.html"), "w").write(
        f"<!DOCTYPE html>\n<html><head><meta charset=\"utf-8\"><title>{esc(t.title)}</title></head>\n"
        f"<body><h1>{esc(t.title)}</h1><p>{esc(t.summary)}</p><ul>{items}</ul>\n"
        f"<p>RB-Avionics, {esc(t.license)}.</p></body></html>\n")


def drc(pcb):
    out = pcb[:-len(".kicad_pcb")] + "-drc.json"
    subprocess.run(["kicad-cli", "pcb", "drc", "--format", "json", "-o", out, pcb],
                   check=True, capture_output=True)
    report = json.load(open(out))
    os.remove(out)
    found = [v for v in report.get("violations", []) if isinstance(v, dict)
             and "does not include the footprint library" not in v.get("description", "")]
    errors = [v for v in found if v.get("severity") == "error"]
    return errors, [v for v in found if v.get("severity") != "error"]


# ---------------------------------------------------------------- preview
def polyline(s):
    """A board shape as points in mm (circles and polygons closed)."""
    P = lambda v: (pcbnew.ToMM(v.x), pcbnew.ToMM(v.y))
    k = s.GetShape()
    if k == pcbnew.SHAPE_T_SEGMENT:
        return [P(s.GetStart()), P(s.GetEnd())]
    if k == pcbnew.SHAPE_T_CIRCLE:
        (cx, cy), r = P(s.GetCenter()), pcbnew.ToMM(s.GetRadius())
        return [(cx + r * math.cos(a * math.pi / 36), cy + r * math.sin(a * math.pi / 36)) for a in range(73)]
    if k == pcbnew.SHAPE_T_ARC:
        (cx, cy), (sx, sy) = P(s.GetCenter()), P(s.GetStart())
        r, a0 = math.hypot(sx - cx, sy - cy), math.atan2(sy - cy, sx - cx)
        sweep = math.radians(s.GetArcAngle().AsDegrees())
        n = max(2, int(abs(sweep) / 0.1))
        return [(cx + r * math.cos(a0 + sweep * i / n), cy + r * math.sin(a0 + sweep * i / n)) for i in range(n + 1)]
    if k == pcbnew.SHAPE_T_BEZIER:
        return [P(q) for q in s.GetBezierPoints()]
    if k == pcbnew.SHAPE_T_POLY:
        o = s.GetPolyShape().Outline(0)
        pts = [P(o.CPoint(j)) for j in range(o.PointCount())]
        return pts + pts[:1]
    return []


def loops_path(pieces, tol=0.01):
    """Join polylines end to end into closed loops, as one SVG path."""
    open_ = [p for p in pieces if len(p) > 1]
    out = []
    while open_:
        loop = open_.pop()
        while math.dist(loop[0], loop[-1]) > tol:
            for i, q in enumerate(open_):
                if math.dist(loop[-1], q[0]) <= tol:
                    loop += q[1:]
                elif math.dist(loop[-1], q[-1]) <= tol:
                    loop += q[::-1][1:]
                else:
                    continue
                open_.pop(i)
                break
            else:
                break  # not closed: leave it out of the fill
        if math.dist(loop[0], loop[-1]) <= tol:
            out.append("M" + " L".join(f"{x:.2f} {y:.2f}" for x, y in loop) + "Z")
    return " ".join(out)


def preview(pcb, svg_path):
    """SVG of Edge.Cuts, Dwgs.User and the holes, drawn from the saved board."""
    b = pcbnew.LoadBoard(pcb)
    edge, dwg = pcbnew.Edge_Cuts, pcbnew.Dwgs_User
    paths = {edge: [], dwg: []}
    pts_all = []
    pieces = []  # Edge.Cuts as polylines in mm, chained into loops below

    def P(v):
        x, y = pcbnew.ToMM(v.x), pcbnew.ToMM(v.y)
        pts_all.append((x, y))
        return f"{x:.2f} {y:.2f}"

    for s in b.GetDrawings():
        if isinstance(s, pcbnew.PCB_SHAPE) and s.GetLayer() == edge:
            pieces.append(polyline(s))
        if not isinstance(s, pcbnew.PCB_SHAPE) or s.GetLayer() not in paths:
            continue
        k, out = s.GetShape(), paths[s.GetLayer()]
        if k == pcbnew.SHAPE_T_SEGMENT:
            out.append(f"M{P(s.GetStart())} L{P(s.GetEnd())}")
        elif k == pcbnew.SHAPE_T_CIRCLE:
            c, r = s.GetCenter(), pcbnew.ToMM(s.GetRadius())
            P(c - pcbnew.VECTOR2I(mm(r), mm(r))); P(c + pcbnew.VECTOR2I(mm(r), mm(r)))
            cx, cy = pcbnew.ToMM(c.x), pcbnew.ToMM(c.y)
            out.append(f"M{cx - r:.2f} {cy:.2f} a{r:.2f} {r:.2f} 0 1 0 {2 * r:.2f} 0 a{r:.2f} {r:.2f} 0 1 0 {-2 * r:.2f} 0")
        elif k == pcbnew.SHAPE_T_ARC:
            r = pcbnew.ToMM(s.GetRadius())
            sweep = 1 if s.GetArcAngle().AsDegrees() > 0 else 0
            large = 1 if abs(s.GetArcAngle().AsDegrees()) > 180 else 0
            out.append(f"M{P(s.GetStart())} A{r:.2f} {r:.2f} 0 {large} {sweep} {P(s.GetEnd())}")
        elif k == pcbnew.SHAPE_T_BEZIER:
            pts = list(s.GetBezierPoints())
            if pts:
                out.append("M" + " L".join(P(q) for q in pts))
        elif k == pcbnew.SHAPE_T_POLY:
            ps = s.GetPolyShape()
            for i in range(ps.OutlineCount()):
                o = ps.Outline(i)
                out.append("M" + " L".join(P(o.CPoint(j)) for j in range(o.PointCount())) + "Z")
        elif k == pcbnew.SHAPE_T_RECT:
            a, c = s.GetStart(), s.GetEnd()
            out.append(f"M{P(a)} H{pcbnew.ToMM(c.x):.2f} V{pcbnew.ToMM(c.y):.2f} H{pcbnew.ToMM(a.x):.2f}Z")
            P(c)
    holes = []
    for fp in b.GetFootprints():
        for pad in fp.Pads():
            d = pcbnew.ToMM(pad.GetDrillSize().x)
            if d > 0:
                c = pad.GetPosition()
                holes.append((pcbnew.ToMM(c.x), pcbnew.ToMM(c.y), d / 2))
    texts = []
    for t in b.GetDrawings():
        if isinstance(t, pcbnew.PCB_TEXT) and t.GetLayer() == dwg:
            c = t.GetPosition()
            x, y, sz = pcbnew.ToMM(c.x), pcbnew.ToMM(c.y), pcbnew.ToMM(t.GetTextHeight())
            texts.append((x, y, t.GetText(), sz))
            half = 0.32 * sz * len(t.GetText())
            pts_all.extend([(x - half, y - sz), (x + half, y + sz)])
    xs, ys = [p[0] for p in pts_all], [p[1] for p in pts_all]
    m = 6
    x0, y0, w, h = min(xs) - m, min(ys) - m, max(xs) - min(xs) + 2 * m, max(ys) - min(ys) + 2 * m
    scale = min(6.0, 900 / w)
    esc = lambda s: s.replace("&", "&amp;").replace("<", "&lt;")
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0:.1f} {y0:.1f} {w:.1f} {h:.1f}" '
         f'width="{w * scale:.0f}" height="{h * scale:.0f}" font-family="sans-serif">',
         f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{w:.1f}" height="{h:.1f}" fill="#ffffff"/>',
         f'<path d="{" ".join(paths[dwg])}" fill="none" stroke="#8a9299" stroke-width="{0.35 / scale * 3:.2f}"/>',
         f'<path d="{loops_path(pieces)}" fill="#2e7d4f" fill-opacity="0.18" fill-rule="evenodd" stroke="none"/>',
         f'<path d="{" ".join(paths[edge])}" fill="none" stroke="#1b5e3a" stroke-width="{0.5 / scale * 3:.2f}"/>']
    o += [f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r:.2f}" fill="#ffffff" stroke="#c62828" '
          f'stroke-width="{0.4 / scale * 3:.2f}"/>' for x, y, r in holes]
    o += [f'<text x="{x:.1f}" y="{y:.1f}" font-size="{sz:.1f}" fill="#5b6268" text-anchor="middle" '
          f'dominant-baseline="central">{esc(s)}</text>' for x, y, s, sz in texts]
    o.append("</svg>")
    open(svg_path, "w").write("\n".join(o) + "\n")


# ---------------------------------------------------------------- the designs
def case_xz(cx, cz):
    """STL section coordinates (x, z) to design coordinates around the instrument axis."""
    return lambda x, z: (x - cx, z - cz)


def inner_loop(stl, axis, at, cx, cz):
    """Smallest section loop around the axis: the case wall at that plane."""
    loops = [lp for lp in section(load(stl), axis, at) if area(lp) > 500]
    around = [lp for lp in loops if winding(lp, cx, cz)]
    return [(x - cx, z - cz) for x, z in simplify(min(around, key=area))]


def winding(loop, x, y):
    c = 0
    for (x0, y0), (x1, y1) in zip(loop, loop[1:] + loop[:1]):
        if (y0 <= y < y1) or (y1 <= y < y0):
            if x0 + (y - y0) * (x1 - x0) / (y1 - y0) > x:
                c += 1
    return c % 2 == 1


def shrink(loop, d):
    """Pull a roughly round loop towards its centre (0, 0) by d."""
    return [(x * (1 - d / math.hypot(x, y)), y * (1 - d / math.hypot(x, y))) for x, y in loop]


def notch(outline, holes, r):
    """Cut an open slot from each hole centre out through the board edge, radially."""
    board = to_polyset(outline)
    for x, y in holes:
        c = [(x + r * math.cos(a * math.pi / 12), y + r * math.sin(a * math.pi / 12)) for a in range(24)]
        board.BooleanSubtract(to_polyset(c))
        ux, uy = x / math.hypot(x, y), y / math.hypot(x, y)
        nx, ny = -uy * r, ux * r
        slot = [(x + nx, y + ny), (x + 6 * ux + nx, y + 6 * uy + ny), (x + 6 * ux - nx, y + 6 * uy - ny), (x - nx, y - ny)]
        board.BooleanSubtract(to_polyset(slot))
    o = board.Outline(0)
    return [(pcbnew.ToMM(o.CPoint(j).x), pcbnew.ToMM(o.CPoint(j).y)) for j in range(o.PointCount())]


def edge_distance(loop, x, y):
    best = math.inf
    for (x0, y0), (x1, y1) in zip(loop, loop[1:] + loop[:1]):
        dx, dy = x1 - x0, y1 - y0
        L = dx * dx + dy * dy
        u = 0 if L == 0 else max(0, min(1, ((x - x0) * dx + (y - y0) * dy) / L))
        best = min(best, math.hypot(x - x0 - u * dx, y - y0 - u * dy))
    return best


def rb01():
    t = Template("RB-01/3d-synthview-7162277", "rb01-pi-hat", "RB-01 3D SynthView: Raspberry Pi HAT",
                 "A Raspberry Pi HAT for the RB-01: the Pi 5 sits on the 58 x 49 mm bosses of the "
                 "RB01.05 Base A sled inside the 84 mm tube of the Ogiva.")
    t.base = os.path.join(HAT_TEMPLATE, "RaspberryPi-HAT.kicad_pcb")
    t.notes = [
        "Based on KiCad's RaspberryPi-HAT template: HAT outline, M2.5 holes, the 40-pin socket and the ID EEPROM schematic.",
        "In the RB-01 the Pi 5 stands on the 58 x 49 mm bosses of the Base A sled (2.5 mm pilots).",
        "The Ogiva is an 84 mm tube: a board up to about 74 mm wide clears it at HAT height; the standard HAT is 56.5 mm.",
        "Other sled bosses carry the power converter and the radios: keep the HAT within the Pi footprint.",
    ]
    return [t]


def rb02_sixpack():
    d = "RB-02/sixpack-box-80mm-7088576"
    t = Template(d, "rb02-sixpack-module", "RB-02 SixPack Box 80mm: module board",
                 "The module board of the SixPack Box rear: 45 x 32.3 mm on the bar and the top bosses, M2 screws.")
    rear = f"{d}/files/RB02B_Rear_Meshed.stl"
    t.section(rear, 1, 22.5, case_xz(0, -200))     # just below the bar top: bar and bosses in section
    t.circle("Dwgs.User", 0, 0, 40.25)             # the 80 mm panel hole, for orientation
    t.text("Dwgs.User", 0, -28, "80 mm panel hole (front)", 2)
    t.text("Dwgs.User", 0, 4, "bar under the board", 2)
    t.rrect("Edge.Cuts", -22.5, 8.5, 22.5, 40.8, 1.0)
    for x in (-16, 16):
        for y in (11.5, 39):
            t.hole(x, y, "M2", "M2 into the 2 mm pilot")
    t.notes = [
        "Seen from the front (display side); the F side faces the display.",
        "The board rests on the bar and the two top bosses of RB02B_Rear, 7 mm below its rim and 8 mm above the back wall; in RB02B_Rear_GPS the same holes are 19 mm below the rim.",
        "4 x M2 screws thread into the printed 2 mm pilots.",
        "The top edge touches the case wall: keep copper 0.5 mm from it.",
        "Dwgs.User shows the case cut at the board plane.",
    ]
    return [t]


def rb02_front_install():
    d = "RB-02/front-install-sixpack-box-80mm-7103368"
    t = Template(d, "rb02-front-install-board", "RB-02 Front Install SixPack Box: round board",
                 "A round 70 mm board inside the front-install case, on its three M2 bosses.")
    # boss faces measured between y = 16.8 (absent) and 17.2 (present) in the section
    case = f"{d}/files/RB02D_-_case_Meshed.stl"
    t.section(case, 1, 17.4, case_xz(-100, 0))
    # 70 mm round board, notched around the block at the top left that stands 0.7 mm proud of the bosses
    board = to_polyset([(35 * math.cos(a * math.pi / 90), 35 * math.sin(a * math.pi / 90)) for a in range(180)])
    board.BooleanSubtract(to_polyset([(-23.5, 26.5), (-13.3, 26.5), (-13.3, 40), (-23.5, 40)]))
    o = board.Outline(0)
    t.poly("Edge.Cuts", [(pcbnew.ToMM(o.CPoint(j).x), pcbnew.ToMM(o.CPoint(j).y)) for j in range(o.PointCount())])
    t.hole(-12.6, -30.4, "M2", "M2 boss")
    t.hole(10.4, -30.4, "M2", "M2 boss")
    t.hole(15.8, 29.1, "M2", "M2 boss, 2 mm deeper")
    t.notes = [
        "Seen from the front (display side); the F side faces the display.",
        "The board sits on the boss faces 17 mm behind the front of RB02D_-_case, inside its 72 mm tube; the notch at the top left clears a block that stands 0.7 mm proud of them.",
        "The top right boss is 2 mm deeper: put a 2 mm spacer under the board there.",
        "3 x M2 screws thread into the printed 1.8 mm pilots.",
        "Dwgs.User shows the case cut at the board plane.",
    ]
    return [t]


def rb02_gps_mount():
    d = "RB-02/gps-mount-v2-7169108"
    t = Template(d, "rb02-gps-shelf-board", "RB-02 GPS mount V2: GPS board on the shelf",
                 "A 45 x 30 mm board in place of the NEO-7M module on SeeCoryRun's GPS shelf, two M3 bolts.",
                 license="CC BY-SA, derived from the GPS mount V2 by SeeCoryRun (see LICENSE.txt)")
    shelf = f"{d}/files/GPSmountN7v1.stl"
    t.section(shelf, 1, 32.4, lambda x, z: (x - 110.4, -z))   # the shelf plate, seen from above
    t.text("Dwgs.User", 0, 3, "display module side", 2)
    t.rrect("Edge.Cuts", -22.5, -30, 22.5, 0, 1.0)
    t.hole(-1.0, -14.4, "M3", "M3x16 + 7 mm standoff")
    t.hole(16.3, -24.3, "M3", "M3x16 + 7 mm standoff")
    t.notes = [
        "Seen from above the shelf; the display module is along the top edge.",
        "The board stands 7 mm above the shelf on the printed standoffs, held by two M3x16 bolts.",
        "Outline = the shelf plate; the board may overhang it where the case allows.",
        "Derived from the GPS mount V2 by SeeCoryRun: CC BY-SA, keep the credit.",
    ]
    return [t]


def rb02_shell(d, name, title, stl, cx, bosses, size):
    t = Template(d, name, title,
                 f"A board in place of the display module PCB inside the {size} mm shell"
                 + (", on the four M3 bosses." if bosses else "; the shell has no screw bosses."))
    wall = inner_loop(stl, 1, 2.0, cx, 0)              # the wall near the open rim
    outline = shrink(wall, CLEARANCE)
    t.section(stl, 1, 11.0, case_xz(cx, 0))            # 0.5 mm behind the boss tops (y = 10.5)
    notches = []
    for x, y in bosses:
        if edge_distance(outline, x, y) < HOLES["M3"][1] / 2 + 0.5:
            notches.append((x, y))  # too close to the wall for a drilled hole: open it to the edge
            t.circle("Dwgs.User", x, y, 2.75)
            t.text("Dwgs.User", x, y - 4.5, "M3 notch", 1.5)
        else:
            t.hole(x, y, "M3", "M3 boss")
    t.poly("Edge.Cuts", notch(outline, notches, HOLES["M3"][1] / 2) if notches else outline)
    t.notes = [
        "Seen from the front; the F side faces the display glass.",
        f"Outline = the shell wall measured near its rim, {CLEARANCE} mm inside it.",
        "The display module PCB sits here: a custom board of this outline replaces it or stacks behind it.",
        ("The four bosses take M3 screws (2.8-3 mm printed pilots)." if bosses
         else "No screw bosses: hold the board like the display module, or glue in standoffs."),
        *(["Two bosses sit 2 mm from the wall: the board has open M3 notches there, the screw heads clamp it."]
          if notches else []),
        "Dwgs.User shows the shell cut 0.5 mm behind the plane where the display PCB sits; the GPS hood is above the top edge.",
    ]
    return t


def rb02_parrot():
    d = "RB-02/parrot-gps-sixpack-box-80mm-7208654"
    return [rb02_shell(d, "rb02-parrot-80mm", "RB-02 Parrot GPS 80 mm: display board",
                       f"{d}/files/RB02B_-_1.02_-_80mm.stl", 0.0, [], 80),
            rb02_shell(d, "rb02-parrot-57mm", "RB-02 Parrot GPS 57 mm: display board",
                       f"{d}/files/RB02B_-_2.1_-_57mm.stl", 100.0,
                       [(-29.5, 13.5), (29.5, 13.5), (-18, -28), (18, -28)], 57)]


def rb02_compact():
    d = "RB-02/sixpack-box-57mm-80mm-compact-edition-7228713"
    return [rb02_shell(d, "rb02-compact-80mm", "RB-02 Compact Edition 80 mm: display board",
                       f"{d}/files/RB02Bep50_2.2.stl", -200.0, [], 80),
            rb02_shell(d, "rb02-compact-57mm", "RB-02 Compact Edition 57 mm: display board",
                       f"{d}/files/RB02BEP80_1.1.stl", -150.0,
                       [(-29.5, 12.0), (29.5, 12.0), (-18, -28.5), (18, -28.5)], 57)]


def rb03():
    t = Template("RB-03/aluminium-amazon-box", "rb03-box-board", "RB-03 aluminium box: carrier board",
                 "A 116 x 60 mm carrier board for the 122 x 66 x 39.5 mm aluminium box.")
    t.rrect("Dwgs.User", -61, -33, 61, 33, 3)
    t.text("Dwgs.User", 0, 36, "box outside 122 x 66 mm (nominal)", 2)
    t.rrect("Edge.Cuts", -58, -30, 58, 30, 2)
    t.notes = [
        "Seen from above.",
        "Sized from the nominal outside of the box, not measured: check the wall thickness, the end caps and any PCB slots of your box before ordering.",
        "No mounting holes: add them where your box has slots or standoffs.",
        "Contents in the RB-03 build: Pi Zero 2W, USB-RS232, 12 V to 5 V, USB GPS, RTL-SDR, 1090 MHz connector.",
    ]
    return [t]


def rb06():
    t = Template("RB-06/aluminium-waveshare-8", "rb06-box-board", "RB-06 aluminium box: board behind the display",
                 "A 186 x 110 mm board inside the RB-06 box for the 8\" Waveshare display, parallel to its back.")
    # the centre face of the flat pattern in the DXF (191.6 x 116.3 mm between the bend lines)
    cx, cy = 91.48, 161.83
    t.rrect("Dwgs.User", -95.8, -58.13, 95.8, 58.13, 0)
    for x, y in [(32.32, 108.76), (32.32, 214.89), (72.32, 108.76), (72.32, 214.89)]:
        t.circle("Dwgs.User", x - cx, y - cy, 1.7)
    t.circle("Dwgs.User", 102.76 - cx, 161.83 - cy, 2.15)
    t.text("Dwgs.User", 0, 61, "centre face of the flat pattern (DXF)", 2.5)
    t.rrect("Edge.Cuts", -93, -55, 93, 55, 2)
    t.notes = [
        "Drawn as the centre face of RB_Box_WS8inch_v3.dxf, 191.6 x 116.3 mm between the bend lines.",
        "The board keeps 2.8 mm from each side for the sheet thickness, which the DXF does not state.",
        "No mounting holes: the box has no bosses. Mount the board on the display's standoffs or add rivet nuts.",
        "The connector cut-outs are not drawn: in the v3 DXF the vent grid and a fitting fall outside the sheet outline, so their positions need checking with the designer first.",
    ]
    return [t]


def round_rect_poly(x0, y0, x1, y1, r, n=6):
    pts = []
    for cx, cy, a0 in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def to_polyset(pts):
    ps = pcbnew.SHAPE_POLY_SET()
    ps.NewOutline()
    for x, y in pts:
        ps.Append(mm(x), mm(y))
    return ps


def cockpit(slug, spec):
    out = []
    for pname, pspec in spec["panels"].items():
        name = f"{slug}{'-' + pname if pname else ''}-backplane"
        label = f"{spec['title']}{' ' + pname + ' plate' if pname else ''}"
        t = Template(f"RB-Cockpits/{slug}", name, f"{label}: backplane",
                     f"A backplane behind the {label.lower()}: same outline, cut-outs for the instruments and "
                     "displays, holes on the panel screws.", ydown=True)
        geo = expand(pspec)
        t.shape("Edge.Cuts", "path", parse_path(pspec["outline"]))
        boxes = []
        for p in geo["parts"]:
            if p["kind"] == "round":
                hw, top, bot = BODY[p["size"]]
                g = CUTOUT_GAP
                boxes.append((f"{p['name']} body", (p["cx"] - hw - g, p["cy"] - top - g, p["cx"] + hw + g, p["cy"] + bot + g, 5)))
            elif p["kind"] == "display":
                g = CUTOUT_GAP
                boxes.append((f"display {p['diag']:.1f}\"", (p["x"] - g, p["y"] - g, p["x"] + p["w"] + g, p["y"] + p["h"] + g, 2)))
        for i, (na, a) in enumerate(boxes):
            for nb, b in boxes[i + 1:]:
                if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]:
                    t.warnings.append(f"{na} and {nb} overlap behind the panel: their cut-outs are merged, "
                                      "check that the two parts clear each other before building")
        cut = pcbnew.SHAPE_POLY_SET()
        for _, (x0, y0, x1, y1, r) in boxes:
            cut.BooleanAdd(to_polyset(round_rect_poly(x0, y0, x1, y1, r)))
        for i in range(cut.OutlineCount()):
            o = cut.Outline(i)
            t.poly("Edge.Cuts", [(pcbnew.ToMM(o.CPoint(j).x), pcbnew.ToMM(o.CPoint(j).y)) for j in range(o.PointCount())])
        for p in geo["parts"]:
            if p["kind"] == "screw":
                t.hole(p["cx"], p["cy"], "M4", "M4 panel screw")
            elif p["kind"] == "display":
                for x, y in p["screws"]:
                    t.hole(x, y, "M3", "M3 display screw")
        # the panel cut-outs, for placing PCB-mount parts or adding their own cut-outs
        for h in geo["holes"]:
            if h[0] == "circle" and h[3] > 6:
                t.circle("Dwgs.User", h[1], h[2], h[3] / 2)
            elif h[0] in ("rect", "window"):
                t.rrect("Dwgs.User", h[1] - h[3] / 2, h[2] - h[4] / 2, h[1] + h[3] / 2, h[2] + h[4] / 2, 0)
        for p in geo["parts"]:
            if p["kind"] in ("rocker", "key", "push_pull", "knob"):
                t.text("Dwgs.User", p["cx"], p["cy"] - 13, p["name"], 2.2)
        t.notes = [
            "Seen from the front; the F side faces the back of the panel. Outline = the panel outline.",
            f"Cut-outs clear the instrument bodies and display modules by {CUTOUT_GAP:g} mm: 92 mm squares for the 80 mm RB cases, 79 x 85 mm for the 57 mm shells with the GPS hood, display bezel + 2 mm.",
            "Holes on the panel screws (M4) and the display screws (M3): stand the board off the panel on them.",
            "Switches, keys, push-pulls and knobs are drawn on Dwgs.User at their panel cut-outs: place PCB-mount parts there, or add cut-outs for panel-mount parts.",
            "PCB fabs limit the board size (often 500 mm or less): split the board along the print tile seams.",
        ] + [f"Warning: {w}." for w in t.warnings]
        out.append(t)
    return out


DESIGNS = [rb01, rb02_sixpack, rb02_front_install, rb02_gps_mount, rb02_parrot, rb02_compact, rb03, rb06] + [
    (lambda s=slug, sp=spec: cockpit(s, sp)) for slug, spec in COCKPITS.items()]


# ---------------------------------------------------------------- README block
def readme_block(design, templates):
    many = len(templates) > 1
    b = ["<!-- BEGIN kicad: generated by tools/kicad_templates.py, do not edit by hand -->",
         "## KiCad board template" + ("s" if many else ""), ""]
    if many:
        b += ["One KiCad project per board, each a starting point for your own electronics.", ""]
    else:
        b += ["A KiCad project as the starting point for your own electronics.", ""]
    for t in templates:
        if many:
            b += [f"### {t.title}", ""]
        b += [f'<img src="images/kicad-{t.name}.svg" alt="{t.title}">', "",
              f"[kicad/{t.name}/{t.name}.kicad_pro](kicad/{t.name}/{t.name}.kicad_pro): {t.summary}", ""]
        b += [f"- {n}" for n in t.notes] + [""]
    b.append("<!-- END kicad -->")
    readme = os.path.join(design, "README.md")
    text = open(readme).read()
    block = "\n".join(b) + "\n"
    if "<!-- BEGIN kicad" in text:
        text = re.sub(r"<!-- BEGIN kicad.*?<!-- END kicad -->\n", lambda _: block, text, flags=re.S)
    else:
        text = text.rstrip("\n") + "\n\n" + block
    open(readme, "w").write(text)


def main():
    if not os.path.isdir("RB-Cockpits"):
        fail("run from the repo root: python3 tools/kicad_templates.py")
    by_design = {}
    for make in DESIGNS:
        for t in make():
            if t.design.startswith(ONLY):
                by_design.setdefault(t.design, []).append(t)
    for design, templates in by_design.items():
        kicad_dir = os.path.join(design, "kicad")
        if os.path.isdir(kicad_dir):
            shutil.rmtree(kicad_dir)
        os.makedirs(os.path.join(design, "images"), exist_ok=True)
        for old in os.listdir(os.path.join(design, "images")):
            if old.startswith("kicad-") and old.endswith(".svg"):
                os.remove(os.path.join(design, "images", old))
        for t in templates:
            folder = os.path.join(kicad_dir, t.name)
            pcb = Writer(t).write(folder)
            write_schematic(t, folder, os.path.join(HAT_TEMPLATE, "RaspberryPi-HAT.kicad_sch") if t.base else None)
            write_meta(t, folder)
            errors, warnings = drc(pcb)
            preview(pcb, os.path.join(design, "images", f"kicad-{t.name}.svg"))
            status = f"{len(errors)} DRC errors, {len(warnings)} warnings"
            print(f"{t.name}: {status}" + "".join(f"\n  warning: {w}" for w in t.warnings))
            for w in warnings:
                print(f"  DRC warning: {w.get('description')}")
            for e in errors:
                print(f"  DRC error: {e.get('description')}: {[i.get('description') for i in e.get('items', [])]}")
            if errors:
                fail(f"{t.name}: DRC errors")
        readme_block(design, templates)


if __name__ == "__main__":
    main()
