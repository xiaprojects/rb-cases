"""Layouts of the RB-Cockpits panels, shared by the FreeCAD and the KiCad generators.

Plain Python, no CAD imports. The layouts are the five home cockpits shown on
www.rbavionics.com, copied from ../rb-panel-concept/scene/homecockpit.html:
millimetres, origin top left, y down. The round instrument cut-outs follow the
RB cases in this repo instead of the render (see ROUND).
"""
import math
import re

# Round RB instruments: panel hole, half side of the screw square, screw hole.
# 80 mm: RB-01 drilling template (RB01.05 Foratura) and front have the screws
# at +-31.25 mm, the RB-02 SixPack template at +-31.0; +-31.125 with 3.6 mm
# holes fits both with M3. 57 mm: the 48 mm square of the render, not checked
# against a case.
ROUND = {80: (80.5, 31.125, 3.6), 57: (57.5, 24.0, 3.4)}
# Instrument body behind the panel. 80 mm: the RB-01 front and the RB-02 SixPack
# front are 90 x 90 mm squares (corner radius 14 and 10), the front-install case
# a 78 mm cylinder. 57 mm: the one-piece boxes are 77 mm wide, 82.7 mm tall with
# the GPS hood on top: (half width, top above centre, bottom below centre).
BODY = {80: (45.0, 45.0, 45.0), 57: (38.5, 44.2, 38.5)}
DISPLAY_SCREW = 3.4     # M3, the four screws beside each RB-01 display
PANEL_SCREW = 4.5       # M4 panel mounting screws
ROCKER = (12.9, 19.2)   # KCD1 mini rocker cut-out, vertical
KEY = 19.0              # 19 mm key switch
PUSH_PULL = 10.2        # push-pull control bushing, 3/8" or M10
KNOB = 7.2              # potentiometer bushing, M7
EAR = (14.0, 5.5)       # profile mounting ear: width, M5 hole for a 40 mm profile T-nut


# ---------------------------------------------------------------- layout items
def rnd(cx, cy, name, size=80):
    return dict(t="round", cx=cx, cy=cy, name=name, size=size)


def display(x, y, w, aspect=1.6, bezel=7):
    return dict(t="display", x=x, y=y, w=w, aspect=aspect, bezel=bezel)


def rocker(x, y, name):
    return dict(t="rocker", x=x, y=y, name=name)


def key(x, y, name):
    return dict(t="key", x=x, y=y, name=name)


def push_pull(x, y, name, below=False):
    return dict(t="push_pull", x=x, y=y, name=name, below=below)


def knob(x, y, d, name):
    return dict(t="knob", x=x, y=y, d=d, name=name)


def screws(*pts):
    return [dict(t="screw", x=x, y=y) for x, y in pts]


def ears(side, *pos, w=0, h=0, reach=20):
    """Mounting ears reaching `reach` mm past one plate edge to a profile slot."""
    out = []
    for p in pos:
        x, y = {"l": (-reach, p), "r": (w + reach, p), "t": (p, -reach), "b": (p, h + reach)}[side]
        out.append(dict(t="ear", x=x, y=y, side=side, w=w, h=h))
    return out


def rrect_path(w, h, r):
    return (f"M{r} 0 H{w - r} Q{w} 0 {w} {r} V{h - r} Q{w} {h} {w - r} {h} "
            f"H{r} Q0 {h} 0 {h - r} V{r} Q0 0 {r} 0 Z")


def rig_plate(w, h, items, side_ears):
    e = []
    for side, pos in side_ears.items():
        e += ears(side, *pos, w=w, h=h)
    return dict(w=w, h=h, outline=rrect_path(w, h, 1.5), items=items + e)


# The five cockpits; panel coordinates as in homecockpit.html. Deviations from
# the render are commented where they are made.
COCKPITS = {
    "desktop-pod": dict(
        title="Desktop pod", concept="desk",
        caption="An RB-09, an RB-01 synthetic vision and an RB-01 HSI in a pod under the monitor: "
                "the smallest RB home cockpit, next to your joystick.",
        missing="the pod body (top and sides, the face is tilted back 14°) and the joystick",
        panels={"": dict(
            w=520, h=170, outline="M14 0 H506 Q520 0 520 14 V170 H0 V14 Q0 0 14 0 Z",
            items=[rnd(62, 80, "RB-09"), rnd(458, 80, "RB-01 · HSI"), display(145, 9, 230)]
            + screws((14, 14), (506, 14), (14, 158), (506, 158)))}),
    "six-pack-trainer": dict(
        title="Six-pack trainer", concept="trainer",
        caption="The RB-01 six-pack in front of the pilot, an RB-09 standby, the RB-01 HSI and radio page, "
                "RB-04 engine and RB-05 traffic, on a classic trainer panel with a yoke.",
        missing="the glare shield and the yoke",
        panels={"": dict(
            w=960, h=330,
            outline="M16 0 H944 Q960 0 960 16 V314 Q960 330 944 330 H16 Q0 330 0 314 V16 Q0 0 16 0 Z",
            items=[display(28, 30, 300)]
            + [rocker(x, 266, n) for x, n in zip(range(48, 259, 30),
               ["MASTER", "AVIONICS", "FUEL PUMP", "BEACON", "LAND", "TAXI", "NAV", "STROBE"])]
            + [key(306, 268, "MAGNETOS"),
               rnd(400, 76, "RB-09"), rnd(400, 186, "RB-01 · HSI"),
               display(458, 30, 166),
               push_pull(500, 250, "THROTTLE"), push_pull(548, 250, "MIXTURE"), push_pull(590, 250, "CARB HEAT"),
               knob(540, 300, 13, "PANEL LT"),
               rnd(724, 76, "RB-04"), rnd(860, 76, "RB-05"),
               display(690, 150, 206)]
            # the render's screws along its two aluminium seams, now frame screws
            + screws(*[(x, y) for y in range(24, 311, 70) for x in (345, 645)])
            + screws((12, 12), (948, 12), (12, 318), (948, 318), (480, 9), (200, 9), (780, 9), (200, 321), (780, 321)))}),
    "glass-cockpit-rig": dict(
        title="Glass-cockpit rig", concept="rig",
        caption="Two RB-01 screens, synthetic vision with the guidance tunnel and the attitude and HSI page, "
                "with an RB-09 and an RB-05 between them, on an aluminium-profile frame.",
        missing="the 40 × 40 mm aluminium-profile frame and the monitor riser",
        # The render's plates fill the frame openings exactly; here each plate has
        # ears reaching the slot of the profile around it. Ears on a shared
        # mullion are staggered so the neighbouring plates use the same slot.
        panels={
            "left": rig_plate(340, 220, [display(18, 13, 304)],
                              {"l": (55, 165), "r": (55, 165), "t": (85, 255), "b": (85, 255)}),
            "centre": rig_plate(100, 220, [rnd(50, 60, "RB-09"), rnd(50, 160, "RB-05")],
                                # side ears near the corners: the seam runs between the instruments
                                {"l": (12, 208), "r": (12, 208), "t": (50,), "b": (50,)}),
            "right": rig_plate(340, 220, [display(18, 13, 304)],
                               {"l": (55, 165), "r": (55, 165), "t": (85, 255), "b": (85, 255)}),
        }),
    "glider-panel": dict(
        title="Glider panel", concept="glider",
        caption="Glider panels are cut for 80 mm and 57 mm instruments, the RB formats: an RB-09 and an "
                "RB-01 HSI at 80 mm and an RB-05 at 57 mm, around an RB-01 synthetic vision.",
        missing="the instrument hood",
        panels={"": dict(
            w=400, h=240,
            outline="M0 70 Q0 22 48 14 Q200 -14 352 14 Q400 22 400 70 V226 Q400 240 386 240 H14 Q0 240 0 226 Z",
            items=[display(112, 38, 176),
                   rnd(58, 90, "RB-09"), rnd(342, 90, "RB-01 · HSI"), rnd(200, 190, "RB-05", size=57),
                   rocker(96, 200, "MASTER"), push_pull(304, 204, "TOW RELEASE")]
            # the render's upper screws (18, 84) sit inside the 80 mm holes: moved below them
            + screws((14, 150), (386, 150), (16, 226), (384, 226)))}),
    "ultralight-rehearsal": dict(
        title="Ultralight rehearsal", concept="ultralight",
        caption="Your own panel on the ground: the RB-01 wide display with the aircraft, engine and radio pages, "
                "an RB-09, RB-01 HSI, RB-04 and RB-05, in carbon like the one you fly.",
        missing="the glare shield and the registration placard",
        panels={"": dict(
            w=800, h=270,
            outline="M30 0 H770 Q800 0 800 30 V210 Q800 240 760 240 H560 Q520 240 500 270 H300 "
                    "Q280 240 240 240 H40 Q0 240 0 210 V30 Q0 0 30 0 Z",
            items=[display(225, 24, 350, aspect=2),
                   rnd(62, 78, "RB-09"), rnd(156, 78, "RB-01 · HSI"), rnd(644, 78, "RB-04"), rnd(738, 78, "RB-05"),
                   key(48, 186, "IGNITION"),
                   rocker(92, 186, "MASTER"), rocker(122, 186, "AVIONICS"), rocker(152, 186, "FUEL PUMP"),
                   rocker(182, 186, "LAND"), rocker(618, 186, "NAV"), rocker(648, 186, "STROBE"),
                   rocker(678, 186, "FLAPS"),
                   push_pull(360, 232, "CHOKE"), push_pull(440, 232, "PARK BRAKE"),
                   knob(752, 186, 13, "PANEL LT")]
            + screws((14, 14), (786, 14), (14, 226), (786, 226), (400, 10), (210, 10), (590, 10)))}),
}


# ---------------------------------------------------------------- outline paths
def parse_path(d):
    """SVG path with M, H, V, L, Q, Z into ('L', p0, p1) and ('Q', p0, c, p1) segments."""
    tok = re.findall(r"[MHVLQZ]|-?\d+(?:\.\d+)?", d)
    segs, i, cur, start = [], 0, None, None
    while i < len(tok):
        c = tok[i]
        i += 1
        if c == "M":
            cur = start = (float(tok[i]), float(tok[i + 1]))
            i += 2
        elif c in "HVL":
            if c == "H":
                p = (float(tok[i]), cur[1]); i += 1
            elif c == "V":
                p = (cur[0], float(tok[i])); i += 1
            else:
                p = (float(tok[i]), float(tok[i + 1])); i += 2
            segs.append(("L", cur, p))
            cur = p
        elif c == "Q":
            ctrl = (float(tok[i]), float(tok[i + 1]))
            p = (float(tok[i + 2]), float(tok[i + 3]))
            i += 4
            segs.append(("Q", cur, ctrl, p))
            cur = p
        elif c == "Z":
            if cur != start:
                segs.append(("L", cur, start))
            cur = start
    return segs


def polygon(segs, n=24):
    pts = []
    for s in segs:
        if s[0] == "L":
            pts.append(s[1])
        else:
            _, a, c, b = s
            for k in range(n):
                t = k / n
                pts.append(((1 - t) ** 2 * a[0] + 2 * (1 - t) * t * c[0] + t * t * b[0],
                            (1 - t) ** 2 * a[1] + 2 * (1 - t) * t * c[1] + t * t * b[1]))
    return pts


# ---------------------------------------------------------------- items -> geometry
def expand(spec):
    """Holes, labels, ears, bill of materials and typed parts of one panel, y down.

    holes:  ("circle", cx, cy, d) | ("window" | "rect", cx, cy, w, h, corner radius)
    labels: (cx, cy, text, "small" | "tiny")
    ears:   (x0, y0, x1, y1, hx, hy) ear body and hole centre
    bom:    {(item, cut-out): quantity}
    parts:  one dict per item, with its kind and the geometry the KiCad backplane needs
    """
    g = dict(holes=[], labels=[], ears=[], bom={}, parts=[])

    def count(item, cut):
        g["bom"][(item, cut)] = g["bom"].get((item, cut), 0) + 1

    for it in spec["items"]:
        t = it["t"]
        if t == "round":
            hole, k, sd = ROUND[it["size"]]
            cx, cy = it["cx"], it["cy"]
            g["holes"].append(("circle", cx, cy, hole))
            screw_pts = [(cx + sx * k, cy + sy * k) for sx in (-1, 1) for sy in (-1, 1)]
            g["holes"] += [("circle", x, y, sd) for x, y in screw_pts]
            r = 41 if it["size"] == 80 else 30  # label distance as in the render
            g["labels"].append((cx, cy + r + 7.5, it["name"], "small" if it["size"] == 80 else "tiny"))
            count(f"RB {it['size']} mm round instrument", f"Ø{hole} mm, 4 × M3 on a {2 * k:g} mm square")
            g["parts"].append(dict(kind="round", cx=cx, cy=cy, size=it["size"], name=it["name"],
                                   hole=hole, screws=screw_pts, screw_d=sd))
        elif t == "display":
            x, y, w, b = it["x"], it["y"], it["w"], it["bezel"]
            sw = w - 2 * b
            sh = sw / it["aspect"]
            h = sh + 2 * b + 4
            g["holes"].append(("window", x + b + sw / 2, y + b + sh / 2, sw, sh, 1.5))
            screw_pts = [(x - 5, y + 6), (x - 5, y + h - 6), (x + w + 5, y + 6), (x + w + 5, y + h - 6)]
            g["holes"] += [("circle", sx, sy, DISPLAY_SCREW) for sx, sy in screw_pts]
            diag = math.hypot(sw, sh) / 25.4
            count(f"RB-01 display, screen {sw:g} × {sh:g} mm ({diag:.1f}\")",
                  f"window {sw:g} × {sh:g} mm, 4 × M3 beside the bezel")
            g["parts"].append(dict(kind="display", x=x, y=y, w=w, h=h, screen=(sw, sh), diag=diag,
                                   screws=screw_pts))
        elif t == "rocker":
            g["holes"].append(("rect", it["x"], it["y"], ROCKER[0], ROCKER[1], 0.5))
            g["labels"].append((it["x"], it["y"] - 18, it["name"], "tiny"))
            count("Mini rocker switch (KCD1)", f"{ROCKER[0]:g} × {ROCKER[1]:g} mm")
            g["parts"].append(dict(kind="rocker", cx=it["x"], cy=it["y"], name=it["name"]))
        elif t == "key":
            g["holes"].append(("circle", it["x"], it["y"], KEY))
            g["labels"].append((it["x"], it["y"] - 15, it["name"], "tiny"))
            count("Key switch", f"Ø{KEY:g} mm")
            g["parts"].append(dict(kind="key", cx=it["x"], cy=it["y"], name=it["name"]))
        elif t == "push_pull":
            g["holes"].append(("circle", it["x"], it["y"], PUSH_PULL))
            g["labels"].append((it["x"], it["y"] + 15 if it["below"] else it["y"] - 14, it["name"], "tiny"))
            count("Push-pull control", f"Ø{PUSH_PULL:g} mm")
            g["parts"].append(dict(kind="push_pull", cx=it["x"], cy=it["y"], name=it["name"]))
        elif t == "knob":
            g["holes"].append(("circle", it["x"], it["y"], KNOB))
            g["labels"].append((it["x"], it["y"] - it["d"] / 2 - 6, it["name"], "tiny"))
            count("Potentiometer with knob", f"Ø{KNOB:g} mm")
            g["parts"].append(dict(kind="knob", cx=it["x"], cy=it["y"], name=it["name"]))
        elif t == "screw":
            g["holes"].append(("circle", it["x"], it["y"], PANEL_SCREW))
            count("Panel mounting screw M4", f"Ø{PANEL_SCREW:g} mm")
            g["parts"].append(dict(kind="screw", cx=it["x"], cy=it["y"]))
        elif t == "ear":
            x, y, side, w, h = it["x"], it["y"], it["side"], it["w"], it["h"]
            half = EAR[0] / 2
            body = {"l": (x, y - half, 1, y + half), "r": (w - 1, y - half, x, y + half),
                    "t": (x - half, y, x + half, 1), "b": (x - half, h - 1, x + half, y)}[side]
            g["ears"].append(body + (x, y))
            g["holes"].append(("circle", x, y, EAR[1]))
            count("M5 screw and T-nut for the 40 mm profile slot", f"Ø{EAR[1]:g} mm in the ears")
            g["parts"].append(dict(kind="ear", cx=x, cy=y))
    return g
