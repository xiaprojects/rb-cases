"""Generate the printed display cases with FreeCAD: the RB-06 cases and the
rectangular RB-02 case (bezel, honeycomb carrier, rear cover) and the round RB-02
instrument (shell and cap).

Run from the repo root:

    freecad.cmd tools/display_cases.py
    RB_ONLY=RB-06/printed-case-waveshare-8 freecad.cmd tools/display_cases.py   # cases whose folder starts with this

The dimensions are in tools/display_case_layouts.py, shared with the KiCad
generator. Output goes to each case folder: one STL per part, placed on the bed
in its print orientation; the FreeCAD model of the assembled case with
reference volumes for the display, the Pi and an AHRS board; a DXF of the panel
cut-out; PNG views; and the generated parts block of README.md.

The script stops if a part touches the display, the Pi, an AHRS board or the
room their plugs need.
"""
import math
import os
import re
import sys

import FreeCAD as App
import MeshPart
import Part

sys.path.insert(0, os.path.join(os.getcwd(), "tools"))  # run from the repo root
import display_case_layouts as D  # noqa: E402

V = App.Vector
ONLY = os.environ.get("RB_ONLY", "")
FONT = "/usr/share/fonts/truetype/liberation/LiberationSansNarrow-Bold.ttf"
LABEL_FONT = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
ENGRAVE = 0.6           # label depth on the rear cover
DENSITY = 1.20          # g/cm3, polycarbonate, for the masses in the README
G = 9.81
PLUG = {"+z": 20.0, "+x": 25.0, "-x": 25.0, "-z": 9.0}  # room for a plug beyond its socket


def fail(msg):
    # FreeCAD's command mode drops the SystemExit message: print it first
    print(f"error: {msg}", flush=True)
    raise SystemExit(1)


# ---------------------------------------------------------------- 2-D shapes, x right, second coordinate = z
def rrect(x0, x1, z0, z1, r=0.0):
    if r <= 0:
        return Part.makePlane(x1 - x0, z1 - z0, V(x0, z0, 0))
    f = Part.makePlane(x1 - x0 - 2 * r, z1 - z0 - 2 * r, V(x0 + r, z0 + r, 0))
    return Part.Face(f.OuterWire.makeOffset2D(r))


def centred(w, h, r=0.0, cx=0.0, cz=0.0):
    return rrect(cx - w / 2, cx + w / 2, cz - h / 2, cz + h / 2, r)


def circle(cx, cz, d):
    return Part.Face(Part.Wire(Part.makeCircle(d / 2, V(cx, cz, 0))))


def polygon(pts):
    return Part.Face(Part.makePolygon([V(x, z, 0) for x, z in pts] + [V(pts[0][0], pts[0][1], 0)]))


def hexagon(cx, cz, flats):
    """Hexagon with vertices up and down, `flats` across its vertical flats."""
    r = flats / math.sqrt(3)
    return polygon([(cx + r * math.cos(math.radians(90 + 60 * k)), cz + r * math.sin(math.radians(90 + 60 * k)))
                    for k in range(6)])


def hex_grid(pitch, w, h):
    """Centres of a honeycomb of the given pitch (across flats) covering a w x h rectangle."""
    dz = pitch * math.sqrt(3) / 2
    ni, nj = int(w / 2 / pitch) + 2, int(h / 2 / dz) + 2
    return [(i * pitch + (pitch / 2 if j % 2 else 0), j * dz) for j in range(-nj, nj + 1) for i in range(-ni, ni + 1)]


def union(faces):
    s = faces[0].fuse(faces[1:]).removeSplitter() if len(faces) > 1 else faces[0]
    return s.Faces[0] if len(s.Faces) == 1 else Part.makeCompound(s.Faces)


def text2d(s, size, font=FONT):
    chars = Part.makeWireString(s, font, size, 0)
    return Part.makeCompound([Part.Face(Part.Compound(ch), "Part::FaceMakerBullseye") for ch in chars if ch])


def arrow2d(length, width):
    """An arrow pointing up, centred on the origin."""
    head, stem = 0.9 * width, width / 3
    return polygon([(-stem / 2, -length / 2), (stem / 2, -length / 2), (stem / 2, length / 2 - head),
                    (width / 2, length / 2 - head), (0, length / 2), (-width / 2, length / 2 - head),
                    (-stem / 2, length / 2 - head)])


# ---------------------------------------------------------------- 3-D
def place(shape, y):
    """The 2-D drawing plane (x, z) to the assembly, at depth y."""
    s = shape.copy()
    s.rotate(V(0, 0, 0), V(1, 0, 0), 90)
    s.translate(V(0, y, 0))
    return s


def prism(face, y0, y1):
    solids = [f.extrude(V(0, 0, -(y1 - y0))) for f in face.Faces]
    return place(solids[0] if len(solids) == 1 else Part.makeCompound(solids), y0)


def cyl(x, z, d, y0, y1):
    return Part.makeCylinder(d / 2, y1 - y0, V(x, y0, z), V(0, 1, 0))


def cone(x, z, d0, d1, y0, y1):
    return Part.makeCone(d0 / 2, d1 / 2, y1 - y0, V(x, y0, z), V(0, 1, 0))


def box(x0, x1, y0, y1, z0, z1):
    return Part.makeBox(abs(x1 - x0), abs(y1 - y0), abs(z1 - z0), V(min(x0, x1), min(y0, y1), min(z0, z1)))


def moved(s, dx=0.0, dy=0.0, dz=0.0):
    s = s.copy()
    s.translate(V(dx, dy, dz))
    return s


def slot(w, h, cx, cz):
    """Slot with round ends, w along x."""
    r = h / 2 - 0.01
    return rrect(cx - w / 2, cx + w / 2, cz - h / 2, cz + h / 2, r)


def hole_size(spec):
    """Width and height of a back hole."""
    return (spec[1], spec[1]) if spec[0] == "circle" else (spec[1], spec[2])


# a face looking back (+y), read from behind: drawing x goes to -x, drawing y to +z
READ_FROM_BEHIND = App.Matrix(-1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 1)


def engrave(faces, x, z, y, depth):
    """Cutter engraving 2-D faces (drawn upright) into the face at depth y that looks back."""
    bb = faces.BoundBox
    f = faces.copy()
    f.translate(V(-(bb.XMin + bb.XMax) / 2, -(bb.YMin + bb.YMax) / 2, -depth))
    s = f.extrude(V(0, 0, depth + 1))
    s.transformShape(READ_FROM_BEHIND)
    s.translate(V(x, y, z))
    return s


def chamfered_prism(w, h, r, c, y0, y1, flare):
    """Rounded-rectangle prism whose y0 end is chamfered by c at 45 degrees:
    flare=-1 shrinks that end (outer edge), +1 widens it (a hole to cut)."""
    base = Part.makePlane(w - 2 * r, h - 2 * r, V(-w / 2 + r, -h / 2 + r, 0)).OuterWire
    end = place(base.makeOffset2D(r + flare * c), y0)
    loft = Part.makeLoft([end, place(base.makeOffset2D(r), y0 + c)], True)
    return loft.fuse(prism(centred(w, h, r), y0 + c - 0.01, y1)).removeSplitter()


def side_boxes(L):
    """Plug bays and openings for plugs on the display's edge, cut out of every part."""
    return [box(x0, x1, y0, y1, z0, z1) for x0, x1, z0, z1, y0, y1 in L.RELIEF.values()]


# ---------------------------------------------------------------- the parts
def bezel(L):
    bw, bh, br = L.BEZEL
    body = chamfered_prism(bw, bh, br, 1.0, 0, L.FLANGE_T, -1)
    body = body.fuse(prism(centred(*L.BODY), 0, L.Y_CARRIER))  # the skirt round the glass
    ww, wh, wr = L.WINDOW
    cutters = [prism(centred(*L.POCKET), L.FRONT, L.Y_CARRIER + 1),
               moved(chamfered_prism(ww, wh, wr, L.WINDOW_CHAMFER, -0.01, L.FRONT + 1, 1), L.VIEW_AT[0], 0,
                     L.VIEW_AT[1])]
    hole, sink = L.PANEL_HOLE
    for x, z in L.PANEL_SCREWS:
        cutters += [cyl(x, z, hole, -1, L.FLANGE_T + 1), cone(x, z, sink + 0.02, hole, -0.01, (sink - hole) / 2)]
    d, depth = L.INSERT_M3
    cutters += [cyl(x, z, d, L.Y_CARRIER - depth, L.Y_CARRIER + 1) for x, z in L.CARRIER_SCREWS]
    return body.cut(Part.makeCompound(cutters + side_boxes(L))).removeSplitter()


def carrier_openings(L):
    faces = [rrect(*b, 1.0) for b in L.CARRIER_OPEN.values()]
    if L.BOARD and L.BOARD_OPEN:
        faces.append(polygon(L.BOARD).makeOffset2D(L.BOARD_CLEAR))
    return union(faces) if faces else None


def carrier_plan(L):
    """The carrier seen from the front: outline minus the openings and the honeycomb cells."""
    bw, bh, br = L.BODY
    openings = carrier_openings(L)
    inner = centred(bw - 2 * L.RIM, bh - 2 * L.RIM, max(0.5, br - L.RIM))
    solid = ([rrect(*land) for land in L.TAPE_LANDS] + [circle(x, z, 11.0) for x, z in L.CARRIER_SCREWS]
             + [circle(x, z, 10.0) for x, z in L.COVER_SCREWS] + [circle(x, z, 8.0) for x, z in L.BOARD_SCREWS])
    if L.AHRS:
        solid.append(rrect(*L.AHRS, 2.0))
    area = (inner.cut(openings.makeOffset2D(L.RIB)) if openings else inner).cut(union(solid))
    full = hexagon(0, 0, L.CELL_CARRIER - L.RIB).Area
    cells = []
    for cx, cz in hex_grid(L.CELL_CARRIER, bw, bh):
        for f in hexagon(cx, cz, L.CELL_CARRIER - L.RIB).common(area).Faces:
            if f.Area > 0.3 * full and f.Area / f.Length > 1.5:  # no slits along the edges
                cells.append(f)
    outline = centred(bw, bh, br)
    return (outline.cut(openings) if openings else outline).cut(Part.makeCompound(cells)), len(cells)


def carrier(L):
    plan, ncells = carrier_plan(L)
    body = prism(plan, L.Y_CARRIER, L.Y_CARRIER_BACK)
    top = L.Y_CARRIER_BACK + L.AHRS_RAISE
    if L.AHRS:
        body = body.fuse(prism(rrect(*L.AHRS, 2.0), L.Y_CARRIER_BACK - 0.01, top))
    cutters = []
    for x, z in L.CARRIER_SCREWS:
        cutters += [cyl(x, z, L.CLEAR_M3, L.Y_CARRIER - 1, L.Y_CARRIER_BACK + 1),
                    cone(x, z, L.CLEAR_M3, L.CSK_M3 + 0.02, L.Y_CARRIER_BACK - (L.CSK_M3 - L.CLEAR_M3) / 2,
                         L.Y_CARRIER_BACK + 0.01)]
    d, depth = L.INSERT_M3
    cutters += [cyl(x, z, d, L.Y_CARRIER_BACK - depth, L.Y_CARRIER_BACK + 1) for x, z in L.COVER_SCREWS]
    bore, sink = L.CBORE_M2
    for x, z in L.BOARD_SCREWS:  # into the standoffs of the display board, heads in the back
        cutters += [cyl(x, z, L.CLEAR_M2, L.Y_CARRIER - 1, L.Y_CARRIER_BACK + 1),
                    cyl(x, z, bore, L.Y_CARRIER_BACK - sink, L.Y_CARRIER_BACK + 1)]
    cutters += [prism(rrect(x0, x1, z0, z1, 1.0), L.Y_CARRIER - 1, L.Y_CARRIER + d)
                for x0, x1, z0, z1, d in L.CARRIER_RECESS.values()]
    if L.AHRS:  # AHRS plane: arrow up and the name, engraved in its margins; the board goes in between
        ax0, ax1, az0, az1 = L.AHRS
        cx, m = (ax0 + ax1) / 2, L.AHRS_MARGIN / 2
        cutters += [engrave(arrow2d(4.4, 3.6), cx - 5.5, az1 - m, top, 0.4),
                    engrave(text2d("UP", 3.2), cx + 2.0, az1 - m, top, 0.4),
                    engrave(text2d("AHRS", 3.2), cx, az0 + m, top, 0.4)]
    return body.cut(Part.makeCompound(cutters + side_boxes(L))).removeSplitter(), ncells


def rib_keepouts(L):
    """Where the rear cover ribs would hit the Pi, the display, a plug or a cable: x0, x1, z0, z1."""
    out = []
    reach = L.Y_PLATE - L.RIB_H - 1.0
    if L.PI_AT:
        for u0, u1, v0, v1, h in list(D.PI_PARTS.values()) + list(L.PI_PLUGS.values()):
            if L.Y_PI_TOP + h > reach:
                x0, x1, z0, z1 = L.pi_rect(u0, u1, v0, v1)
                out.append((x0 - 1, x1 + 1, z0 - 1, z1 + 1))
    for name, (x0, x1, z0, z1, depth, side, base) in L.DISPLAY_PARTS.items():
        if L.Y_GLASS + depth + 1.5 > reach:
            out.append((x0 - 1, x1 + 1, z0 - 1, z1 + 1))
    tw, th, sp = L.TIE
    for label, x, z, spec in L.BACK_HOLES:
        w, h = hole_size(spec)
        if not cable_hole(spec):  # SMA bulkhead: room for the nut and a spanner
            r = w / 2 + 6
            out.append((x - r, x + r, z - r, z + r))
        else:  # cable: from the hole up along the plate to its tie-wrap
            half = max(w / 2 + 3, sp / 2 + tw)
            out.append((x - half, x + half, z - h / 2 - 3, z + 12 + th / 2 + 3))
    for x, z, sp in L.CONVERTER_TIES:
        out += [(x + s * sp / 2 - tw, x + s * sp / 2 + tw, z - th, z + th) for s in (-1, 1)]
    return out


def cable_hole(spec):
    """Cable holes get a tie-wrap pair; the small round ones are for SMA bulkheads."""
    return spec[0] == "slot" or spec[1] > 8


def vent_cells(L):
    if not L.PI_AT:
        return []
    x0, x1, z0, z1 = L.pi_rect(*D.PI_FAN)
    posts = [L.pi_xz(u, v) for u, v in D.PI_HOLES]
    return [(cx, cz) for cx, cz in hex_grid(L.CELL_COVER, L.BODY[0], L.BODY[1])
            if x0 <= cx <= x1 and z0 <= cz <= z1 and all(math.hypot(cx - px, cz - pz) > 10 for px, pz in posts)]


def rear_cover(L):
    bw, bh, br = L.BODY
    w = L.WALL
    y0 = L.Y_CARRIER_BACK
    inner = centred(bw - 2 * w, bh - 2 * w, br - w)
    shell = prism(centred(bw, bh, br), y0, L.Y_BACK).cut(prism(inner, y0 - 1, L.Y_PLATE))
    cells = [hexagon(cx, cz, L.CELL_COVER - L.RIB) for cx, cz in hex_grid(L.CELL_COVER, bw, bh)]
    net = inner.cut(Part.makeCompound(cells)).cut(union([rrect(*k) for k in rib_keepouts(L)]))
    adds = [prism(net, L.Y_PLATE - L.RIB_H, L.Y_PLATE + 0.01)]
    if L.PI_AT:
        for u, v in D.PI_HOLES:  # Pi standoffs, flared into the plate
            x, z = L.pi_xz(u, v)
            adds += [cyl(x, z, L.STANDOFF, L.Y_PI_TOP, L.Y_PLATE + 0.01),
                     cone(x, z, L.STANDOFF, L.STANDOFF + 4.0, L.Y_PLATE - 2.0, L.Y_PLATE + 0.01)]
    col, bore, cap = L.COLUMN
    for x, z in L.COVER_SCREWS:  # screw columns, tied to both walls
        sx, sz = math.copysign(1, x), math.copysign(1, z)
        wx, wz = sx * (bw / 2 - w + 0.5), sz * (bh / 2 - w + 0.5)
        adds += [cyl(x, z, col, y0, L.Y_PLATE + 0.01), box(x - 1.2, x + 1.2, y0, L.Y_PLATE + 0.01, z, wz)]
        if abs(x) > bw / 2 - 20:  # a corner column: tied to the side wall too
            adds.append(box(x, wx, y0, L.Y_PLATE + 0.01, z - 1.2, z + 1.2))
    body = shell.fuse(adds).removeSplitter()

    cutters = []
    if L.PI_AT:
        d, depth = L.INSERT_M25
        for u, v in D.PI_HOLES:
            x, z = L.pi_xz(u, v)
            cutters.append(cyl(x, z, d, L.Y_PI_TOP - 1, L.Y_PI_TOP + depth))
    for x, z in L.COVER_SCREWS:
        cutters += [cyl(x, z, bore, y0 + cap, L.Y_BACK + 1), cyl(x, z, L.CLEAR_M3, y0 - 1, y0 + cap + 1)]
    plate = (L.Y_PLATE - 0.5, L.Y_BACK + 1)
    tw, th, sp = L.TIE
    for label, x, z, spec in L.BACK_HOLES:
        if spec[0] == "circle":
            cutters.append(cyl(x, z, spec[1], *plate))
        else:
            cutters.append(prism(slot(spec[1], spec[2], x, z), *plate))
        if cable_hole(spec):
            cutters += [prism(centred(tw, th, 0, x + s * sp / 2, z + 12), *plate) for s in (-1, 1)]
        cutters.append(engrave(text2d(label, 4.6), x, z - 11, L.Y_BACK, ENGRAVE))
    for x, z, s in L.CONVERTER_TIES:
        cutters += [prism(centred(tw, th, 0, x + k * s / 2, z), *plate) for k in (-1, 1)]
    lx, lz = L.LABEL_AT or (0, bh / 2 - 12)
    cutters.append(engrave(text2d(L.LABEL, 6.0), lx, lz, L.Y_BACK, ENGRAVE))
    vents = vent_cells(L)
    cutters += [prism(hexagon(cx, cz, L.CELL_COVER - L.RIB), *plate) for cx, cz in vents]
    # top and bottom walls: hexagons pointing front and back print without support
    nwall = 0
    if L.WALL_VENT:
        flats, pitch, rows, span = L.WALL_VENT
        r = flats / math.sqrt(3)
        for k, yv in enumerate(rows):
            n = int(span / pitch)
            for i in range(-n, n + 1):
                xv = i * pitch + (pitch / 2 if k % 2 else 0)
                if abs(xv) > span:
                    continue
                pts = [V(xv + r * math.cos(math.radians(90 + 60 * j)), yv + r * math.sin(math.radians(90 + 60 * j)), 0)
                       for j in range(6)]
                hexf = Part.Face(Part.makePolygon(pts + pts[:1]))
                for sz in (1, -1):
                    h = hexf.extrude(V(0, 0, w + 2))
                    h.translate(V(0, 0, bh / 2 - w - 1 if sz > 0 else -bh / 2 - 1))
                    cutters.append(h)
                    nwall += 1
    return body.cut(Part.makeCompound(cutters + side_boxes(L))).removeSplitter(), len(vents), nwall


# ---------------------------------------------------------------- reference volumes (not printed)
def display_model(L):
    """The display as simple blocks: glass, the back the carrier holds, driver board and the parts on it."""
    gw, gh, gr = L.GLASS
    gx, gz = L.GLASS_AT
    yb = L.Y_GLASS + L.BOARD_BACK
    pieces = {"glass": prism(centred(gw, gh, gr, gx, gz), L.Y_GLASS, L.Y_GLASS + L.GLASS_T),
              "lcd": prism(rrect(*L.LCM), L.Y_GLASS + L.GLASS_T, L.Y_LCM)}
    if L.BOARD:
        pieces["board"] = prism(polygon(L.BOARD), yb - 1.6, yb)
    for name, (x0, x1, z0, z1, depth, _, base) in L.DISPLAY_PARTS.items():
        y0 = L.Y_LCM if base == "lcm" else yb
        pieces[name] = prism(rrect(x0, x1, z0, z1), y0, L.Y_GLASS + depth)
    for name, (x0, x1, z0, z1, d0, d1) in L.DISPLAY_BLOCKS.items():
        pieces[name] = prism(rrect(x0, x1, z0, z1), L.Y_GLASS + d0, L.Y_GLASS + d1)
    return pieces


def display_plugs(L):
    """Room for the plugs of the display sockets."""
    out = {}
    yb = L.Y_GLASS + L.BOARD_BACK
    for name, (x0, x1, z0, z1, depth, side, base) in L.DISPLAY_PARTS.items():
        if side is None:
            continue
        n = L.PLUG_LEN.get(side, PLUG[side])
        r = {"+z": (x0 - 2, x1 + 2, z1, z1 + n), "+x": (x1, x1 + n, z0 - 2, z1 + 2),
             "-x": (x0 - n, x0, z0 - 2, z1 + 2), "-z": (x0 - 1, x1 + 1, z0 - n, z0)}[side]
        out[f"{name} plug"] = prism(rrect(*r), yb - 0.5, L.Y_GLASS + depth + 1.5)
    return out


def pi_model(L):
    if not L.PI_AT:
        return {}
    outline = L.pi_rect(0, D.PI[0], 0, D.PI[1])
    pieces = {"Pi board": prism(rrect(*outline, 3.0), L.Y_PI, L.Y_PI_TOP),
              "Pi underside": prism(rrect(*outline, 3.0), L.Y_PI - D.PI_BELOW, L.Y_PI)}
    for name, (u0, u1, v0, v1, h) in D.PI_PARTS.items():
        pieces[name] = prism(rrect(*L.pi_rect(u0, u1, v0, v1)), L.Y_PI_TOP, L.Y_PI_TOP + h)
    holes = [cyl(*L.pi_xz(u, v), 2.7, L.Y_PI - 1, L.Y_PI_TOP + 1) for u, v in D.PI_HOLES]
    pieces["Pi board"] = pieces["Pi board"].cut(Part.makeCompound(holes))
    return pieces


def pi_plugs(L):
    out = {}
    if L.PI_AT:
        out = {name: prism(rrect(*L.pi_rect(u0, u1, v0, v1)), L.Y_PI_TOP, L.Y_PI_TOP + h)
               for name, (u0, u1, v0, v1, h) in L.PI_PLUGS.items()}
    if L.CONVERTER:
        x0, x1, z0, z1, h = L.CONVERTER
        out["5 V converter room"] = prism(rrect(x0, x1, z0, z1), L.Y_PLATE - L.RIB_H - h, L.Y_PLATE - L.RIB_H)
    for name, (x0, x1, z0, z1, h) in L.ROOMS.items():
        out[name] = prism(rrect(x0, x1, z0, z1), L.Y_PLATE - L.RIB_H - h, L.Y_PLATE - L.RIB_H)
    return out


def ahrs_model(L):
    """A 25.4 mm square IMU breakout glued on the AHRS plane."""
    if not L.AHRS:
        return {}
    x0, x1, z0, z1 = L.AHRS
    cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
    top = L.Y_CARRIER_BACK + L.AHRS_RAISE
    return {"AHRS board": prism(centred(25.4, 25.4, 1.0, cx, cz), top, top + 1.6),
            "IMU chip": prism(centred(4.0, 4.0, 0, cx, cz), top + 1.6, top + 2.6)}


def check(parts, refs):
    problems = []
    for pn, ps in parts.items():
        for rn, rs in refs.items():
            v = ps.common(rs).Volume
            if v > 0.05:
                problems.append(f"{pn} and the {rn} overlap ({v:.1f} mm3)")
    if problems:
        fail("; ".join(problems))


# ---------------------------------------------------------------- output
def human(n):
    return f"{n / 1048576:.1f} MB" if n >= 1048576 else f"{(n + 1023) // 1024} KB"


def print_pose(shape, face_down):
    """The part as it goes on the bed: front face down (bezel, carrier) or back face down (rear cover)."""
    s = shape.copy()
    s.rotate(V(0, 0, 0), V(1, 0, 0), 90 if face_down == "front" else -90)
    bb = s.BoundBox
    s.translate(V(-bb.XMin, -bb.YMin, -bb.ZMin))
    return s


def write_stl(shape, path):
    mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.05, AngularDeflection=math.radians(10))
    mesh.write(path)
    bb = shape.BoundBox
    return bb.XLength, bb.YLength, bb.ZLength


def write_dxf(path, cut, screws, hole, outline, outline_layer="BEZEL"):
    """Panel cut-out and screw holes 1:1 in mm, seen from the front: layers CUT and BEZEL or BODY (outline only)."""
    out = ["0", "SECTION", "2", "ENTITIES"]

    def poly(layer, face):
        out.extend(["0", "POLYLINE", "8", layer, "66", "1", "70", "1"])
        for q in face.OuterWire.discretize(Deflection=0.02):
            out.extend(["0", "VERTEX", "8", layer, "10", f"{q.x:.4f}", "20", f"{q.y:.4f}", "30", "0"])
        out.extend(["0", "SEQEND", "8", layer])

    poly("CUT", cut)
    for x, z in screws:
        out.extend(["0", "CIRCLE", "8", "CUT", "10", f"{x:.4f}", "20", f"{z:.4f}", "30", "0", "40", f"{hole / 2:.4f}"])
    poly(outline_layer, outline)
    out.extend(["0", "ENDSEC", "0", "EOF"])
    with open(path, "w") as f:
        f.write("\n".join(out) + "\n")


def render(items, path, az, el, width=1400, labels=()):
    """Shaded orthographic view with outlines, drawn with a z-buffer: items are (shape, rgb),
    labels (text, 3-D point). az 0 looks from the front, 90 from the right; el from above."""
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont

    a, e = math.radians(az), math.radians(el)
    d = np.array([math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)])  # towards the camera
    rgt = np.cross(-d, [0.0, 0.0, 1.0])
    rgt /= np.linalg.norm(rgt)
    up = np.cross(rgt, -d)
    light = 0.6 * d + 0.7 * up - 0.3 * rgt
    light /= np.linalg.norm(light)
    tris, cols = [], []
    for shape, rgb in items:
        mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.15, AngularDeflection=math.radians(20))
        pts, fac = mesh.Topology
        p = np.array([[q.x, q.y, q.z] for q in pts])
        tris.append(p[np.array(fac, dtype=int)])
        cols.append(np.tile(np.array(rgb, float), (len(fac), 1)))
    t, c = np.concatenate(tris), np.concatenate(cols)
    n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
    ln = np.linalg.norm(n, axis=1)
    ok = ln > 1e-12
    t, c, n = t[ok], c[ok], n[ok] / ln[ok, None]
    front = n @ d > 0
    t, c, n = t[front], c[front], n[front]
    c = c * (0.42 + 0.58 * np.clip(n @ light, 0, 1))[:, None]
    sx, sy, sz = t @ rgt, t @ up, t @ d
    ss = 2  # supersampling
    x0, x1, y0, y1 = sx.min(), sx.max(), sy.min(), sy.max()
    m = 0.03 * (x1 - x0)
    k = width * ss / (x1 - x0 + 2 * m)
    W, H = int(width * ss), int((y1 - y0 + 2 * m) * k)
    px, py = (sx - x0 + m) * k, (y1 + m - sy) * k
    zbuf = np.full((H, W), -np.inf)
    img = np.full((H, W, 3), 255.0)
    nbuf = np.zeros((H, W, 3))
    for i in range(len(px)):
        xa, xb, xc = px[i]
        ya, yb, yc = py[i]
        ix0, ix1 = max(int(min(xa, xb, xc)), 0), min(int(max(xa, xb, xc)) + 1, W - 1)
        iy0, iy1 = max(int(min(ya, yb, yc)), 0), min(int(max(ya, yb, yc)) + 1, H - 1)
        if ix1 < ix0 or iy1 < iy0:
            continue
        area = (xb - xa) * (yc - ya) - (xc - xa) * (yb - ya)
        if abs(area) < 1e-9:
            continue
        gx, gy = np.meshgrid(np.arange(ix0, ix1 + 1) + 0.5, np.arange(iy0, iy1 + 1) + 0.5)
        w0 = ((xb - gx) * (yc - gy) - (xc - gx) * (yb - gy)) / area
        w1 = ((xc - gx) * (ya - gy) - (xa - gx) * (yc - gy)) / area
        w2 = 1 - w0 - w1
        inside = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
        if not inside.any():
            continue
        z = w0 * sz[i, 0] + w1 * sz[i, 1] + w2 * sz[i, 2]
        zs = zbuf[iy0:iy1 + 1, ix0:ix1 + 1]
        hit = inside & (z > zs)
        zs[hit] = z[hit]
        img[iy0:iy1 + 1, ix0:ix1 + 1][hit] = c[i]
        nbuf[iy0:iy1 + 1, ix0:ix1 + 1][hit] = n[i]
    # outlines: silhouettes, creases, and depth steps found by the second difference
    # of depth, which stays near zero across a sloping face
    bg = ~np.isfinite(zbuf)
    zf = np.where(bg, -1e6, zbuf)
    edge = np.zeros((H, W), bool)
    for dy, dx in ((0, 1), (1, 0)):
        a_, b_ = (slice(0, H - dy), slice(0, W - dx)), (slice(dy, H), slice(dx, W))
        crease = ((nbuf[a_] * nbuf[b_]).sum(axis=2) < 0.82) | (bg[a_] != bg[b_])
        edge[a_] |= crease & ~bg[a_]
        edge[b_] |= crease & ~bg[b_]
        c_ = (slice(2 * dy, H), slice(2 * dx, W))
        a2 = (slice(0, H - 2 * dy), slice(0, W - 2 * dx))
        m2 = (slice(dy, H - dy), slice(dx, W - dx))
        edge[m2] |= (np.abs(zf[a2] - 2 * zf[m2] + zf[c_]) > 0.3) & ~bg[m2]
    img[edge] *= 0.3
    im = Image.fromarray(img.clip(0, 255).astype("uint8")).resize((W // ss, H // ss), Image.LANCZOS)
    if labels:
        draw = ImageDraw.Draw(im)
        font = ImageFont.truetype(LABEL_FONT, 22)
        for text, p in labels:
            q = np.array([p.x, p.y, p.z])
            lx, ly = ((q @ rgt) - x0 + m) * k / ss, (y1 + m - (q @ up)) * k / ss
            draw.text((lx, ly), text, font=font, fill=(20, 24, 28), anchor="mm", stroke_width=4, stroke_fill=(255, 255, 255))
    im.save(path, optimize=True)


def replace_block(root, block):
    readme = os.path.join(root, "README.md")
    text = open(readme).read()
    if "<!-- BEGIN parts" not in text:
        fail(f"{readme}: no <!-- BEGIN parts --> block to replace")
    text = re.sub(r"<!-- BEGIN parts.*?<!-- END parts -->\n", lambda _: block, text, flags=re.S)
    with open(readme, "w") as f:
        f.write(text)


def join_and(items):
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def plus_minus(values):
    """'±31 and 0' from a list of coordinates."""
    vs = sorted({round(abs(v), 1) for v in values}, reverse=True)
    return " and ".join(f"±{v:g}" if v else "0" for v in vs)


# ---------------------------------------------------------------- README of a bezel case
def loads(L, masses, cg_y):
    """Static loads at the -3 and +6 G of the requirement, for the README."""
    total = sum(masses.values())
    zmax = max(abs(z) for _, z in L.PANEL_SCREWS)
    rows = []
    for n in (6, -3):
        f = total / 1000 * abs(n) * G
        arm = cg_y - L.FLANGE_T  # behind the panel's front face
        row = dict(
            n=n, f=f,
            panel_shear=f / len(L.PANEL_SCREWS),
            panel_pull=f * arm / (2 * zmax) / sum(1 for _, z in L.PANEL_SCREWS if abs(z) == zmax) * 2,
            display=L.DISPLAY_MASS / 1000 * abs(n) * G,
            carrier=(L.DISPLAY_MASS + masses["Carrier"]) / 1000 * abs(n) * G / len(L.CARRIER_SCREWS))
        if L.PI_AT:
            row["standoff"] = 32 * (D.PI_MASS / 1000 * abs(n) * G / 4 * L.PI_ROOM) / (math.pi * L.STANDOFF ** 3)
        rows.append(row)
    return total, rows


def write_readme(L, rows, masses, piece_mass, total, load_rows, ncells, nvents, nwall):
    bw, bh, _ = L.BEZEL
    cw, ch, cr = L.CUTOUT
    tape_front = 2 * (L.WINDOW[0] + L.WINDOW[1] + 8)  # 2 mm outside the window
    tape_back = sum(max(x1 - x0, z1 - z0) for x0, x1, z0, z1 in L.TAPE_LANDS) if L.BACK_TAPE else 0
    printed = sum(masses[k] for k in ("Bezel", "Carrier", "Rear cover"))
    vents = [f"{ncells} cells in the carrier"]
    if nvents:
        vents.append(f"{nvents} open vent cells in the rear cover over the Pi fan")
    if nwall:
        vents.append(f"{nwall} vents in its top and bottom walls")
    b = ["<!-- BEGIN parts: generated by tools/display_cases.py, do not edit by hand -->", "## Parts", "",
         "| Part | On the bed | Size on the bed (mm) | Mass in PC | File |", "|---|---|---|---:|---|"]
    for part, pose, (sx, sy, sz), fn in rows:
        size = human(os.path.getsize(os.path.join(L.ROOT, "files", fn)))
        b.append(f"| {part} | {pose} | {sx:.0f} × {sy:.0f} × {sz:.0f} | {piece_mass[part]:.0f} g "
                 f"| [{fn}](files/{fn}) ({size}) |")
    if L.SPLIT:
        big = max(rows, key=lambda r: r[2][0] * r[2][1])[2]
        bed = (f"Each part is cut in two to fit the bed; the largest piece needs a bed of at least "
               f"{big[0] + 3:.0f} × {big[1] + 3:.0f} mm.")
    else:
        bed = f"The bezel needs a bed of at least {bw + 3:.0f} × {bh + 3:.0f} mm."
    b += ["", f"The parts print without supports, placed as exported. {bed} Masses are for solid polycarbonate; "
              f"the honeycomb is already "
              f"thin solid walls ({L.RIB:g} mm, four 0.4 mm lines): {join_and(vents)}.", "",
          f'<img src="images/exploded-front.png" alt="Exploded view from the front: bezel, display, honeycomb '
          f'carrier, {"Raspberry Pi 5, " if L.PI_AT else ""}rear cover">', "",
          f'<img src="images/exploded-rear.png" alt="Exploded view from the back: rear cover with the back holes, '
          f'{"Raspberry Pi 5, " if L.PI_AT else ""}carrier{" with the AHRS plane" if L.AHRS else ""}, display, '
          f'bezel">', "",
          "## Hardware", "",
          "| Item | Qty | Where |", "|---|---:|---|",
          f"| M3 heat-set insert, 5.7 mm long, for a {L.INSERT_M3[0]:g} mm hole | "
          f"{len(L.CARRIER_SCREWS) + len(L.COVER_SCREWS)} | bezel skirt ({len(L.CARRIER_SCREWS)}), "
          f"carrier corners ({len(L.COVER_SCREWS)}) |"]
    if L.PI_AT:
        b.append(f"| M2.5 heat-set insert, 4 mm long, for a {L.INSERT_M25[0]:g} mm hole | {len(D.PI_HOLES)} | "
                 "rear cover standoffs |")
    flat = min(n for n in (8, 10, 12, 16, 20) if n >= L.CARRIER_T + 4)
    b += [f"| M3 × {flat} flat head, ISO 10642 | {len(L.CARRIER_SCREWS)} | carrier to bezel |",
          f"| M3 × 10 socket head, ISO 4762 | {len(L.COVER_SCREWS)} | rear cover to carrier, inside the columns "
          "(2.5 mm hex key) |"]
    if L.BOARD_SCREWS:
        b.append(f"| M2 × {L.CARRIER_T - L.CBORE_M2[1] + 3:g} socket or pan head | {len(L.BOARD_SCREWS)} | "
                 "carrier to the standoffs of the display board |")
    if L.PI_AT:
        b.append(f"| M2.5 × 6 pan or socket head | {len(D.PI_HOLES)} | Raspberry Pi to the standoffs |")
    b.append(f"| M4 × 12 flat head, ISO 10642 (or #8), with nylon-insert lock nuts | {len(L.PANEL_SCREWS)} | "
             "bezel to the panel, up to 3 mm of panel |")
    tape = f"{tape_front / 1000:.1f} m × 3 mm" + (f", {tape_back / 1000:.1f} m × 5 mm" if tape_back else "")
    where = "on the bezel lip round the window" + ("; on the carrier's flat strips behind the display"
                                                  if tape_back else "")
    b.append(f"| Closed-cell foam tape, 1 mm, silicone or EPDM rated above 100 °C | {tape} | {where} |")
    if L.AHRS:
        b.append("| Epoxy rated above 100 °C | a few grams | AHRS board on the AHRS plane |")
    b += ["| Tie-wraps, 2.5 mm, heat-stabilised, rated 105 °C | 6 to 10 | cables at the back holes"
          + (", 5 V converter" if L.CONVERTER_TIES else "") + " |", "",
          "## Panel cut-out", "",
          f"{cw:g} × {ch:g} mm with {cr:g} mm corners, and {len(L.PANEL_SCREWS)} holes of "
          f"{L.PANEL_HOLE[0]:g} mm at x = {plus_minus([x for x, _ in L.PANEL_SCREWS])}, "
          f"z = {plus_minus([z for _, z in L.PANEL_SCREWS])} mm from the centre of the cut-out. The case slides in "
          f"from the front and the bezel ({bw:g} × {bh:g} mm) covers the edge. Drawing 1:1, layers CUT and BEZEL: "
          f"[{L.NAME}-panel-cutout.dxf](files/{L.NAME}-panel-cutout.dxf)", "",
          "## Load check, -3 to +6 G", ""]
    extra = [f"display {L.DISPLAY_MASS} g"] + ([f"Pi 5 with cooler {D.PI_MASS} g"] if L.PI_AT else []) + \
        [f"printed parts {printed:.0f} g in PC", f"{L.ALLOWANCE} g for {L.ALLOWANCE_FOR}"]
    b += [f"Static loads for the whole unit, {total:.0f} g: " + ", ".join(extra) + ". Every load is taken as if it "
          "acted in the worst direction for that part.", "",
          "| | +6 G | -3 G |", "|---|---:|---:|"]
    p, q = load_rows
    b += [f"| Unit weight × G | {p['f']:.0f} N | {q['f']:.0f} N |",
          f"| Shear on each M4 panel screw | {p['panel_shear']:.1f} N | {q['panel_shear']:.1f} N |",
          f"| Pull on each screw of the top or bottom row, from the overhang behind the panel "
          f"| {p['panel_pull']:.1f} N | {q['panel_pull']:.1f} N |",
          f"| Display on the bezel pocket wall | {p['display']:.0f} N | {q['display']:.0f} N |",
          f"| Pull on each carrier insert, display pushed back | {p['carrier']:.1f} N | {q['carrier']:.1f} N |"]
    if L.PI_AT:
        b.append(f"| Bending at the root of each Pi standoff | {p['standoff']:.1f} MPa | {q['standoff']:.1f} MPa |")
    held = "clamped on foam and backed by the honeycomb" if L.BACK_TAPE else \
        "clamped on foam by the bezel and screwed to the carrier by its own standoffs"
    b += ["", "Each load is a few newtons, against the hundreds of newtons an M3 heat-set insert holds and the "
          "tens of MPa printed PC or PA-CF takes across its layers at 100 °C. Shock and vibration are what "
          f"remain: the display is {held}, every screw goes into brass"
          + (" or into the board's own standoffs" if L.BOARD_SCREWS else "") + ", "
          "and the cables are tied at the back holes so their plugs carry no load.", "",
          f"FreeCAD model, assembled, with reference blocks for the display"
          + (", the Pi and an AHRS board" if L.PI_AT and L.AHRS else "") + ": "
          f"[{L.NAME}-case.FCStd](files/{L.NAME}-case.FCStd)",
          "<!-- END parts -->"]
    replace_block(L.ROOT, "\n".join(b) + "\n")


# ---------------------------------------------------------------- build a bezel case
COLOURS = {"Bezel": (62, 68, 76), "Carrier": (226, 168, 58), "Rear cover": (94, 116, 134),
           "Shell": (62, 68, 76), "Cap": (94, 116, 134), "GPS antenna": (220, 200, 150),
           "glass": (28, 34, 44), "lcd": (150, 154, 160), "board": (46, 110, 64), "Pi board": (40, 128, 60),
           "Pi underside": (40, 128, 60), "cooler": (170, 176, 182), "USB and Ethernet": (196, 200, 204),
           "GPIO header with plugs": (30, 30, 30), "LCD flex": (201, 138, 43), "AHRS board": (110, 64, 160),
           "IMU chip": (30, 30, 30)}


def colour(k):
    return COLOURS.get(k, (190, 194, 198))


def save_model(L, parts, groups):
    doc = App.newDocument(L.NAME.replace("-", "_") + "_case")
    for name, s in parts.items():
        doc.addObject("Part::Feature", name.replace(" ", "")).Shape = s
    group = doc.addObject("App::DocumentObjectGroup", "Reference")
    for title, pieces in groups:
        if pieces:
            obj = doc.addObject("Part::Feature", title)
            obj.Shape = Part.makeCompound(list(pieces.values()))
            group.addObject(obj)
    doc.recompute()
    doc.saveAs(os.path.abspath(os.path.join(L.ROOT, "files", f"{L.NAME}-case.FCStd")))
    App.closeDocument(doc.Name)


def solid(name, s):
    if not s.isValid() or len(s.Solids) != 1:
        fail(f"{name}: {len(s.Solids)} solids, valid {s.isValid()}")
    return s.Solids[0]


def build_bezel_case(L):
    files, images = os.path.join(L.ROOT, "files"), os.path.join(L.ROOT, "images")
    print(f"{L.ROOT}: bezel", flush=True)
    parts = {"Bezel": bezel(L)}
    print(f"{L.ROOT}: carrier", flush=True)
    parts["Carrier"], ncells = carrier(L)
    print(f"{L.ROOT}: rear cover", flush=True)
    parts["Rear cover"], nvents, nwall = rear_cover(L)
    parts = {k: solid(k, s) for k, s in parts.items()}

    disp, pi, ahrs = display_model(L), pi_model(L), ahrs_model(L)
    refs = {**disp, **display_plugs(L), **pi, **pi_plugs(L), **ahrs}
    print(f"{L.ROOT}: clearance check", flush=True)
    check(parts, refs)

    masses = {k: s.Volume / 1000 * DENSITY for k, s in parts.items()}
    masses.update({"display": L.DISPLAY_MASS, "allowance": L.ALLOWANCE})
    yc = {k: parts[k].CenterOfMass.y for k in ("Bezel", "Carrier", "Rear cover")}
    yc.update({"display": L.Y_GLASS + L.DISPLAY_CG, "allowance": (L.Y_CARRIER_BACK + L.Y_BACK) / 2})
    if L.PI_AT:
        masses["Pi"], yc["Pi"] = D.PI_MASS, L.Y_PI + 6.0
    cg_y = sum(masses[k] * yc[k] for k in masses) / sum(masses.values())
    total, load_rows = loads(L, masses, cg_y)

    for old in os.listdir(files):
        os.remove(os.path.join(files, old))
    rows, piece_mass, shown = [], {}, {}
    for part, pose in (("Bezel", "front"), ("Carrier", "front"), ("Rear cover", "back")):
        for name, piece, dx in split(L, part, parts[part]):
            fn = f"{L.NAME}-{name.lower().replace(', ', '-').replace(' ', '-')}.stl"
            size = write_stl(print_pose(piece, pose), os.path.join(files, fn))
            rows.append((name, f"{pose} face down", size, fn))
            piece_mass[name] = piece.Volume / 1000 * DENSITY
            shown.setdefault(part, []).append(moved(piece, dx))
    write_dxf(os.path.join(files, f"{L.NAME}-panel-cutout.dxf"), centred(*L.CUTOUT), L.PANEL_SCREWS,
              L.PANEL_HOLE[0], centred(*L.BEZEL))
    save_model(L, parts, (("Display", disp), ("RaspberryPi5", pi), ("AHRS", ahrs)))

    print(f"{L.ROOT}: renders", flush=True)
    whole = [(parts[k], colour(k)) for k in parts] + [(disp["glass"], colour("glass"))]
    render(whole, os.path.join(images, "assembly.png"), -32, 22, width=1200)
    gap = {"display": 45, "Carrier": 90, "Pi": 150, "Rear cover": 230 if L.PI_AT else 170}  # exploded along y
    scale = max(L.BODY[0], L.BODY[1]) / 211  # the 8" case is the reference
    gap = {k: v * max(scale, 0.45) for k, v in gap.items()}
    items = [(moved(s, 0, gap.get(k, 0)), colour(k)) for k in ("Bezel", "Carrier", "Rear cover") for s in shown[k]]
    items += [(moved(s, 0, gap["display"]), colour(k)) for k, s in disp.items()]
    items += [(moved(s, 0, gap["Pi"]), colour(k)) for k, s in pi.items()]
    items += [(moved(s, 0, gap["Carrier"]), colour(k)) for k, s in ahrs.items()]
    lab = [("bezel", V(0, 0, L.BEZEL[1] / 2 + 14)),
           ("display", V(0, gap["display"] + L.Y_GLASS, L.GLASS[1] / 2 + L.GLASS_AT[1] + 12)),
           ("carrier", V(0, gap["Carrier"] + L.Y_CARRIER, L.BODY[1] / 2 + 12)),
           ("rear cover", V(0, gap["Rear cover"] + L.Y_BACK, L.BODY[1] / 2 + 12))]
    if L.PI_AT:
        x0, x1, z0, z1 = L.pi_rect(0, D.PI[0], 0, D.PI[1])
        lab.append(("Raspberry Pi 5", V((x0 + x1) / 2, gap["Pi"] + L.Y_PI, z0 - 14)))
    render(items, os.path.join(images, "exploded-front.png"), -58, 24, labels=lab)
    render(items, os.path.join(images, "exploded-rear.png"), 128, 26, labels=lab)

    write_readme(L, rows, masses, piece_mass, total, load_rows, ncells, nvents, nwall)
    for part, pose, (sx, sy, sz), fn in rows:
        print(f"{fn}: {sx:.1f} x {sy:.1f} x {sz:.1f} mm, {piece_mass[part]:.0f} g", flush=True)
    print(f"{L.ROOT}: unit {total:.0f} g, centre of mass {cg_y:.1f} mm behind the bezel front", flush=True)


def split(L, part, shape):
    """The pieces of a part as printed: (name, solid, shift along x for the exploded views)."""
    cuts = L.SPLIT.get(part, [])
    if not cuts:
        return [(part, shape, 0.0)]
    edges = [-1000.0] + sorted(cuts) + [1000.0]
    names = ["left", "right"] if len(cuts) == 1 else ["left"] + [f"middle {i + 1}" for i in range(len(cuts) - 1)] + ["right"]
    out = []
    for i, (a, b) in enumerate(zip(edges, edges[1:])):
        name = f"{part}, {names[i]}"
        piece = solid(name, shape.common(box(a, b, -100, 200, -1000, 1000)).removeSplitter())
        out.append((name, piece, 4.0 * (i - (len(edges) - 2) / 2)))
    return out


# ---------------------------------------------------------------- round instrument: shell and cap
def hood_box(L):
    """The GPS hood above the shell, and the antenna pocket in it."""
    H = L.HOOD
    top = L.SHELL[1] / 2
    pw, ph = H["pocket"]
    outer = box(-H["half"], H["half"], 0, H["depth"], top, top + 2 * H["wall"] + ph)
    pocket = box(-pw / 2, pw / 2, H["from_y"], H["depth"] + 1, top + H["wall"], top + H["wall"] + ph)
    return outer, pocket


def shell(L):
    w, h, r = L.SHELL
    body = prism(centred(w, h, r), 0, L.SHELL_T)
    cutters = []
    if L.HOOD:
        outer, pocket = hood_box(L)
        body = body.fuse(outer)
        cutters.append(pocket)
    c = L.WINDOW_CHAMFER
    cutters += [cone(0, 0, L.WINDOW_D + 2 * c, L.WINDOW_D, -0.01, c), cyl(0, 0, L.WINDOW_D, c - 0.01, L.FRONT + 1),
                cyl(0, 0, L.POCKET_D, L.FRONT, L.SHELL_T + 1)]
    d, depth = L.INSERT_M3
    for x, z in L.PANEL_SCREWS:
        cutters.append(cyl(x, z, d, -1, depth))
    for x, z in L.CAP_SCREWS:
        cutters.append(cyl(x, z, d, L.SHELL_T - depth, L.SHELL_T + 1))
    return body.cut(Part.makeCompound(cutters + side_boxes(L))).removeSplitter()


def cap(L):
    w, h, r = L.SHELL
    body = prism(centred(w, h, r), L.Y_CAP, L.Y_BACK)
    pad_from = L.Y_GLASS + L.STANDOFF_END
    body = body.fuse([cyl(x, z, 6.5, pad_from, L.Y_CAP + 0.01) for x, z in L.POSTS])
    cutters = [prism(rrect(*o, 1.0), L.Y_CAP - 3, L.Y_BACK + 1) for o in L.CAP_OPEN.values()]
    bore, sink = L.CBORE_M2
    for x, z in L.POSTS:   # into the standoffs of the display board, heads in the back
        cutters += [cyl(x, z, L.CLEAR_M2, pad_from - 1, L.Y_BACK + 1), cyl(x, z, bore, L.Y_BACK - sink, L.Y_BACK + 1)]
    for x, z in L.CAP_SCREWS:
        cutters += [cyl(x, z, L.CLEAR_M3, L.Y_CAP - 1, L.Y_BACK + 1),
                    cone(x, z, L.CLEAR_M3, L.CSK_M3 + 0.02, L.Y_BACK - (L.CSK_M3 - L.CLEAR_M3) / 2, L.Y_BACK + 0.01)]
    cutters.append(engrave(text2d(L.LABEL, 5.0), 0, -h / 2 + 7, L.Y_BACK, ENGRAVE))
    return body.cut(Part.makeCompound(cutters)).removeSplitter()


def round_display_model(L):
    y = L.Y_GLASS
    yb = y + L.BOARD_BACK
    pieces = {"glass": cyl(0, 0, L.GLASS_D, y, y + L.GLASS_T),
              "lcd": cyl(0, 0, L.SPACER[0], y + L.GLASS_T, y + L.SPACER[1]),
              "board": cyl(0, 0, L.BOARD_D, y + L.SPACER[1], yb)}
    for i, (x, z) in enumerate(L.POSTS):
        pieces[f"standoff {i + 1}"] = cyl(x, z, 3.6, yb - 0.01, y + L.STANDOFF_END)
    for name, (x0, x1, z0, z1, depth, _, base) in L.DISPLAY_PARTS.items():
        pieces[name] = prism(rrect(x0, x1, z0, z1), yb, y + depth)
    if L.HOOD:
        H = L.HOOD
        aw, ad, ah = H["antenna"]
        floor = L.SHELL[1] / 2 + H["wall"]
        pieces["GPS antenna"] = box(-aw / 2, aw / 2, H["from_y"] + 0.5, H["from_y"] + 0.5 + ad, floor, floor + ah)
    return pieces


def write_round_readme(L, rows, masses, total, cg_y):
    hole, half, screw = L.PANEL
    printed = masses["Shell"] + masses["Cap"]
    f6, f3 = [total / 1000 * n * G for n in (6, 3)]
    pull = [f * cg_y / (2 * half) / 2 for f in (f6, f3)]
    ring = math.pi * (L.POCKET_D + L.WINDOW_D) / 2
    b = ["<!-- BEGIN parts: generated by tools/display_cases.py, do not edit by hand -->", "## Parts", "",
         "| Part | On the bed | Size on the bed (mm) | Mass in PC | File |", "|---|---|---|---:|---|"]
    for part, pose, (sx, sy, sz), fn in rows:
        size = human(os.path.getsize(os.path.join(L.ROOT, "files", fn)))
        b.append(f"| {part} | {pose} | {sx:.0f} × {sy:.0f} × {sz:.0f} | {masses[part]:.0f} g "
                 f"| [{fn}](files/{fn}) ({size}) |")
    b += ["", "The parts print without supports, placed as exported. Masses are for solid polycarbonate.", "",
          '<img src="images/exploded-front.png" alt="Exploded view from the front: shell with the GPS hood, '
          'display board, cap">', "",
          '<img src="images/exploded-rear.png" alt="Exploded view from the back: cap with the cable openings, '
          'display board, shell">', "",
          "## Hardware", "",
          "| Item | Qty | Where |", "|---|---:|---|",
          f"| M3 heat-set insert, 5.7 mm long, for a {L.INSERT_M3[0]:g} mm hole | "
          f"{len(L.PANEL_SCREWS) + len(L.CAP_SCREWS)} | front face of the shell ({len(L.PANEL_SCREWS)}), "
          f"back face of the shell ({len(L.CAP_SCREWS)}) |",
          f"| M3 × 8 pan or flat head, black | {len(L.PANEL_SCREWS)} | through the panel into the shell, "
          "up to 3 mm of panel |",
          f"| M3 × 8 flat head, ISO 10642 | {len(L.CAP_SCREWS)} | cap to shell |",
          f"| M2 × {min(n for n in (4, 5, 6, 8, 10) if n >= L.CAP_T - L.CBORE_M2[1] + L.PAD + 2)} socket or pan "
          f"head | {len(L.POSTS)} | "
          "cap to the standoffs of the display board |",
          f"| Closed-cell foam tape, 1 mm, silicone or EPDM rated above 100 °C | {ring / 1000:.2f} m × 2 mm "
          "| on the lip round the window |",
          "| Silicone foam tape, rated above 100 °C | a 28 mm square | GPS antenna to the floor of the hood |", "",
          "## Panel cut-out", "",
          f"A {hole:g} mm hole and {len(L.PANEL_SCREWS)} holes of {screw:g} mm on a {2 * half:g} mm square. "
          f"The shell goes on the back of the panel and the screws go in from the front. Drawing 1:1, layers CUT and BODY (the shell outline behind the panel): "
          f"[{L.NAME}-panel-cutout.dxf](files/{L.NAME}-panel-cutout.dxf)", "",
          "## Load check, -3 to +6 G", "",
          f"Static loads for the whole unit, {total:.0f} g: display board {L.DISPLAY_MASS} g, printed parts "
          f"{printed:.0f} g in PC, {L.ALLOWANCE} g for {L.ALLOWANCE_FOR}.", "",
          "| | +6 G | -3 G |", "|---|---:|---:|",
          f"| Unit weight × G | {f6:.1f} N | {f3:.1f} N |",
          f"| Shear on each M3 panel screw | {f6 / 4:.2f} N | {f3 / 4:.2f} N |",
          f"| Pull on each panel insert, from the overhang behind the panel | {pull[0]:.2f} N | {pull[1]:.2f} N |",
          "", "Every load is a newton or two per screw, against the hundreds of newtons an M3 heat-set insert "
          "holds. The display is clamped on foam between the lip and the cap, which holds the board by its own "
          "standoffs.", "",
          f"FreeCAD model, assembled, with reference blocks for the display board, its plugs and the GPS antenna: "
          f"[{L.NAME}-case.FCStd](files/{L.NAME}-case.FCStd)",
          "<!-- END parts -->"]
    replace_block(L.ROOT, "\n".join(b) + "\n")


def build_round_case(L):
    files, images = os.path.join(L.ROOT, "files"), os.path.join(L.ROOT, "images")
    print(f"{L.ROOT}: shell", flush=True)
    parts = {"Shell": solid("Shell", shell(L)), "Cap": solid("Cap", cap(L))}
    disp = round_display_model(L)
    refs = {**disp, **display_plugs(L)}
    print(f"{L.ROOT}: clearance check", flush=True)
    check(parts, refs)
    masses = {k: s.Volume / 1000 * DENSITY for k, s in parts.items()}
    yc = {k: parts[k].CenterOfMass.y for k in parts}
    masses.update({"display": L.DISPLAY_MASS, "allowance": L.ALLOWANCE})
    yc.update({"display": L.Y_GLASS + 6.0, "allowance": L.Y_BACK})
    cg_y = sum(masses[k] * yc[k] for k in masses) / sum(masses.values())
    total = sum(masses.values())

    for old in os.listdir(files):
        os.remove(os.path.join(files, old))
    rows = []
    for part, pose in (("Shell", "front"), ("Cap", "back")):
        fn = f"{L.NAME}-{part.lower()}.stl"
        size = write_stl(print_pose(parts[part], pose), os.path.join(files, fn))
        rows.append((part, f"{pose} face down", size, fn))
    w, h, r = L.SHELL
    outline = centred(w, h, r)
    if L.HOOD:
        outline = union([outline, rrect(-L.HOOD["half"], L.HOOD["half"], h / 2 - r, hood_box(L)[0].BoundBox.ZMax)])
    write_dxf(os.path.join(files, f"{L.NAME}-panel-cutout.dxf"), circle(0, 0, L.PANEL[0]), L.PANEL_SCREWS,
              L.PANEL[2], outline, "BODY")
    save_model(L, parts, (("Display", disp),))

    print(f"{L.ROOT}: renders", flush=True)
    render([(parts["Shell"], colour("Shell")), (parts["Cap"], colour("Cap")), (disp["glass"], colour("glass"))],
           os.path.join(images, "assembly.png"), -32, 22, width=900)
    gap = {"display": 30.0, "Cap": 60.0}
    items = [(parts["Shell"], colour("Shell")), (moved(parts["Cap"], 0, gap["Cap"]), colour("Cap"))]
    items += [(moved(s, 0, 0 if k == "GPS antenna" else gap["display"]), colour(k)) for k, s in disp.items()]
    lab = [("shell", V(0, 0, h / 2 + 22)), ("display board", V(0, gap["display"] + L.Y_GLASS, -h / 2 - 8)),
           ("cap", V(0, gap["Cap"] + L.Y_BACK, -h / 2 - 8))]
    render(items, os.path.join(images, "exploded-front.png"), -58, 24, width=1100, labels=lab)
    render(items, os.path.join(images, "exploded-rear.png"), 128, 26, width=1100, labels=lab)
    write_round_readme(L, rows, masses, total, cg_y)
    for part, pose, (sx, sy, sz), fn in rows:
        print(f"{fn}: {sx:.1f} x {sy:.1f} x {sz:.1f} mm, {masses[part]:.0f} g", flush=True)
    print(f"{L.ROOT}: unit {total:.0f} g, centre of mass {cg_y:.1f} mm behind the panel", flush=True)


# ---------------------------------------------------------------- main
def build():
    cases = [L for root, L in D.CASES.items() if root.startswith(ONLY)]
    if not cases:
        fail(f"no case folder starts with {ONLY!r}")
    for L in cases:
        if not os.path.isfile(os.path.join(L.ROOT, "README.md")):
            fail(f"run from the repo root, with {L.ROOT}/README.md in place")
        os.makedirs(os.path.join(L.ROOT, "files"), exist_ok=True)
        os.makedirs(os.path.join(L.ROOT, "images"), exist_ok=True)
        for old in ("assembly.png", "exploded-front.png", "exploded-rear.png"):
            if os.path.exists(os.path.join(L.ROOT, "images", old)):
                os.remove(os.path.join(L.ROOT, "images", old))
        if L.KIND == "bezel":
            build_bezel_case(L)
        else:
            build_round_case(L)


build()
