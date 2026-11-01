"""Dimensions of the printed display cases, shared by the FreeCAD generator
(tools/display_cases.py) and the KiCad generator.

Plain Python, no CAD imports. CASES maps each design folder to its Case. A case
is either a bezel case (bezel, honeycomb carrier, rear cover; RB-06 and the
rectangular RB-02) or a round instrument (shell and cap, RB-02).

Assembly coordinates in mm, the repo's case orientation: x right as seen from
the front, y depth from the bezel front face (the back is +y), z up, origin on
the centre of the bezel pocket. Display data are in the same x and z, with
depths from the front of the glass, measured from Waveshare's 3D models and
drawings (files.waveshare.com, October 2026) unless noted. Raspberry Pi 5 data
are from the Raspberry Pi 5 mechanical drawing; component heights above the
board are estimates with margin, not measured.
"""
import math

# ---------------------------------------------------------------- shared by every bezel case
SHARED = dict(
    KIND="bezel",
    GLASS_AT=(0.0, 0.0),     # centre of the glass in the pocket
    GLASS_T=2.2,             # glass and touch layer, for the reference model
    BOARD=None,              # driver board outline, x and z
    BOARD_OPEN=True,         # the carrier is open over the driver board; False: CARRIER_RECESS covers it
    DISPLAY_PARTS={},        # x0, x1, z0, z1, depth, side a plug comes from or None, "board" or "lcm" under it
    DISPLAY_BLOCKS={},       # more reference blocks: x0, x1, z0, z1, depth from, depth to
    DISPLAY_CG=4.0,          # centre of mass behind the glass front, for the load check
    PLUG_LEN={},             # room for a plug beyond its socket, by side, where the generator default does not fit
    TAPE=1.0,                # closed-cell foam tape on both sides of the display, nominal
    TAPE_SET=0.6,            # ... its thickness once clamped
    BACK_TAPE=True,          # False: the carrier is screwed to standoffs on the display board
    FRONT=3.0,               # bezel lip over the glass border
    FLANGE_T=4.5,            # bezel flange, front face to the panel
    CARRIER_T=8.0,
    PI_ROOM=21.0,            # Pi component face to the rear cover plate
    BACK=3.0,                # rear cover plate
    SKIRT=8.0,               # bezel wall around the pocket
    FLANGE=(13.0, 13.0),     # bezel flange beyond the body: sides, top and bottom
    BODY_MIN=(0.0, 0.0),     # make the body at least this big, for the Pi and its plugs
    WINDOW_CHAMFER=2.0,      # 45 degrees, on the front
    PANEL_HOLE=(4.4, 9.0),   # M4 or #8 flat head: hole, countersink at the front
    PANEL_PITCH=150.0,       # largest panel screw spacing
    CARRIER_PITCH=110.0,     # largest carrier screw spacing
    INSERT_M3=(4.0, 6.5),    # hole for M3 x 5.7 heat-set inserts (4.6 mm outside): diameter, depth
    INSERT_M25=(3.6, 5.0),   # hole for M2.5 x 4 heat-set inserts
    CLEAR_M3=3.4,
    CSK_M3=6.4,              # countersink for an M3 flat head (6.0 mm head)
    CLEAR_M2=2.4,
    CBORE_M2=(4.4, 3.0),     # counterbore for an M2 socket or pan head: diameter, depth
    # carrier
    RIB=1.6,                 # honeycomb walls: 4 lines of 0.4 mm
    CELL_CARRIER=10.0,       # honeycomb pitch, across flats
    RIM=6.0,                 # solid edge of the carrier
    AHRS=None,               # AHRS plane: x0, x1, z0, z1
    AHRS_RAISE=1.0,          # proud of the honeycomb
    AHRS_MARGIN=5.5,         # top and bottom bands with the engraved marks
    BOARD_CLEAR=1.5,         # carrier opening round the driver board
    CARRIER_OPEN={},         # more openings: name -> x0, x1, z0, z1
    CARRIER_RECESS={},       # pockets in the carrier front over low parts: name -> x0, x1, z0, z1, depth
    BOARD_SCREWS=[],         # M2 screws from the carrier into standoffs on the display board
    # rear cover
    WALL=2.5,
    CELL_COVER=16.0,
    RIB_H=5.0,               # honeycomb ribs inside the plate
    STANDOFF=6.0,            # Pi standoffs, flared to 10 mm in the last 2 mm
    COLUMN=(9.0, 6.2, 5.0),  # rear cover screw columns: outside, bore for the head, cap
    COVER_ROOM=20.0,         # carrier back to the plate, in a case without a Pi
    BACK_HOLES=[],           # label, x, z, ("circle", d) or ("slot", w, h); label engraved below
    TIE=(2.2, 3.4, 10.0),    # tie-wrap slot: along the pair, across, pair spacing
    CONVERTER=None,          # room for a 5 V converter on the ribs: x0, x1, z0, z1, height
    CONVERTER_TIES=[],       # x, z, pair spacing
    ROOMS={},                # more room on the rear cover ribs, like the converter: name -> x0, x1, z0, z1, height
    RELIEF={},               # boxes cut out of every part, plug bays in the skirt: name -> x0, x1, z0, z1, y0, y1
    LABEL_AT=None,           # where the name is engraved on the back, x and z; default top centre
    SPLIT={},                # parts too big for a 256 mm bed, cut into pieces at these x: part -> [x, ...]
    STEP_FRAME=None,         # for tools/step_check.py: the STEP model's axes along x, z, y; z shift; solids to leave out
    ALLOWANCE=100,           # g, for the load check
    ALLOWANCE_FOR="cables, AHRS and converter",
    PI_AT=None,              # no Pi: an ESP32 display board
    PI_ROT=0,
    PI_PLUG_ROOM=(28.0, 40.0),  # micro HDMI and USB-C plugs beyond the HDMI edge, USB plugs beyond the USB end
    PI_USB_V=(1.0, 55.0),    # USB plugs along the USB end: all four ports; (1, 36) leaves the Ethernet unused
    COMPUTER="",
)

# ---------------------------------------------------------------- Raspberry Pi 5
PI = (85.0, 56.0)
PI_MASS = 70                         # g, with the Active Cooler
# the Pi hangs from the rear cover, component face back. Its own axes: u from the end
# opposite the USB ports, v from the edge with the micro HDMI sockets. With PI_ROT 0
# the USB end is right and the HDMI edge up: x = PI_AT[0] + u, z = PI_AT[1] - v;
# PI_ROT turns that counter-clockwise as seen from the front.
PI_HOLES = [(3.5, 3.5), (61.5, 3.5), (3.5, 52.5), (61.5, 52.5)]
# room above the component face: u0, u1, v0, v1, height. The corner holes keep
# 6 mm clear of parts, so the standoffs are 6 mm thick up to the plate.
PI_PARTS = {
    "cooler": (8.0, 58.0, 6.0, 50.0, 10.5),
    "USB and Ethernet": (66.0, 88.0, 1.0, 55.0, 16.3),
    "GPIO header with plugs": (7.0, 58.0, 49.5, 55.5, 19.0),
}
PI_BELOW = 3.0                       # pins and parts under the board
PI_FAN = (8.0, 58.0, 6.0, 50.0)      # where the cooler draws its air: u0, u1, v0, v1


class Case:
    """One printed case: its display, the computer behind it and the case dimensions."""

    def __init__(self, **kw):
        self.__dict__.update(kw)

    def pi_xz(self, u, v):
        a = math.radians(self.PI_ROT)
        c, s = round(math.cos(a), 9), round(math.sin(a), 9)
        return self.PI_AT[0] + u * c + v * s, self.PI_AT[1] + u * s - v * c

    def pi_rect(self, u0, u1, v0, v1):
        pts = [self.pi_xz(u, v) for u in (u0, u1) for v in (v0, v1)]
        return min(p[0] for p in pts), max(p[0] for p in pts), min(p[1] for p in pts), max(p[1] for p in pts)


def perimeter(ax, az, pitch):
    """Points round a rectangle of half sides ax, az, no more than pitch apart: top row
    left to right, right side down, bottom row right to left, left side up."""
    nx, nz = math.ceil(2 * ax / pitch), math.ceil(2 * az / pitch)
    top = [(-ax + 2 * ax * i / nx, az) for i in range(nx + 1)]
    right = [(ax, az - 2 * az * i / nz) for i in range(1, nz)]
    bottom = [(ax - 2 * ax * i / nx, -az) for i in range(nx + 1)]
    left = [(-ax, -az + 2 * az * i / nz) for i in range(1, nz)]
    return [(round(x, 3) + 0.0, round(z, 3) + 0.0) for x, z in top + right + bottom + left]


def bezel_case(**spec):
    c = Case(**{**SHARED, **spec})
    # ---------------------------------------------------------- stack, front to back
    c.Y_GLASS = c.FRONT + c.TAPE_SET                     # glass front
    c.Y_LCM = c.Y_GLASS + c.DISPLAY_T                    # the back face the carrier holds
    c.Y_CARRIER = c.Y_LCM + (c.TAPE_SET if c.BACK_TAPE else 0.0)
    c.Y_CARRIER_BACK = c.Y_CARRIER + c.CARRIER_T
    if c.PI_AT:
        c.Y_PI = c.Y_CARRIER_BACK + 3.5                  # Pi board, bottom face (3 mm of pins under it)
        c.Y_PI_TOP = c.Y_PI + 1.6                        # Pi board, component face, towards the rear cover
        c.Y_PLATE = c.Y_PI_TOP + c.PI_ROOM               # inner face of the rear cover plate
    else:
        c.Y_PLATE = c.Y_CARRIER_BACK + c.COVER_ROOM
    c.Y_BACK = c.Y_PLATE + c.BACK                        # back face of the case
    # ---------------------------------------------------------- outlines (w, h, corner radius)
    gw, gh, gr = c.GLASS
    if not hasattr(c, "POCKET"):
        c.POCKET = (gw + 0.8, gh + 0.8, gr + 0.4)        # 0.4 mm play around the glass
    pw, ph, _ = c.POCKET
    c.BODY = (max(pw + 2 * c.SKIRT, c.BODY_MIN[0]), max(ph + 2 * c.SKIRT, c.BODY_MIN[1]), 6.0)  # through the panel
    bw, bh, _ = c.BODY
    fx, fz = c.FLANGE
    c.BEZEL = (bw + 2 * fx, bh + 2 * fz, 8.0)
    c.CUTOUT = (bw + 1.0, bh + 1.0, 6.5)                 # panel cut-out
    c.VIEW_AT = getattr(c, "VIEW_AT", c.GLASS_AT)
    c.WINDOW = (c.VIEW[0] + 1.2, c.VIEW[1] + 1.2, 1.5)  # bezel window, at the glass
    # ---------------------------------------------------------- screws
    bx, bz = bw / 2, bh / 2
    if fx >= 10:   # corner screws in the corners of the flange
        c.PANEL_SCREWS = [p for p in perimeter(bx + fx / 2, bz + fz / 2, c.PANEL_PITCH)]
    else:          # narrow side flanges: screws in the top and bottom flanges only
        ax = bx - 4.0
        n = math.ceil(2 * ax / c.PANEL_PITCH)
        c.PANEL_SCREWS = [(round(-ax + 2 * ax * i / n, 3) + 0.0, sz * (bz + fz / 2))
                          for sz in (1, -1) for i in range(n + 1)]
    # carrier to bezel, M3 countersunk into heat-set inserts in the middle of the bezel skirt
    c.SKIRT_MID = ((pw / 2 + bx) / 2, (ph / 2 + bz) / 2)
    if not hasattr(c, "CARRIER_SCREWS"):
        c.CARRIER_SCREWS = perimeter(*c.SKIRT_MID, c.CARRIER_PITCH)
    # rear cover to carrier, M3 through the rear cover columns into inserts in the carrier
    if not hasattr(c, "COVER_SCREWS"):
        c.COVER_SCREWS = [(sx * (bx - 10), sz * (bz - 10)) for sz in (1, -1) for sx in (-1, 1)]
    # ---------------------------------------------------------- carrier
    if not hasattr(c, "TAPE_LANDS"):   # solid strips for the rear foam tape, inside the clamped edge
        x0, x1, z0, z1 = c.LCM
        c.TAPE_LANDS = [(x0 + 1.5, x1 - 1.5, z1 - 6.5, z1 - 1.5), (x0 + 1.5, x1 - 1.5, z0 + 1.5, z0 + 6.5),
                        (x0 + 1.5, x0 + 6.5, z0 + 1.5, z1 - 1.5), (x1 - 6.5, x1 - 1.5, z0 + 1.5, z1 - 1.5)]
    # ---------------------------------------------------------- Pi
    if c.PI_AT:
        hdmi, usb = c.PI_PLUG_ROOM
        c.PI_PLUGS = {
            "micro HDMI and USB-C plugs": (6.0, 46.0, -hdmi, 0.0, 9.0),
            "USB plugs": (88.0, 88.0 + usb, *c.PI_USB_V, 16.3),
        }
    # ---------------------------------------------------------- rear cover
    mid = (c.Y_CARRIER_BACK + c.Y_PLATE) / 2
    c.WALL_VENT = (6.0, 9.0, (round(mid - 3.5), round(mid + 3.5)), round(bx - 17.5)) \
        if c.Y_PLATE - c.Y_CARRIER_BACK >= 20 else None  # top and bottom walls: across flats, pitch, rows at y, half span
    return c


# ---------------------------------------------------------------- Waveshare 8DP-CAPLCD
# From the STEP model and drawing (files.waveshare.com/wiki/8DP-CAPLCD, April 2024). The
# model has the display in portrait: x = its y, z = minus its x, depth = 4.80 minus its z.
_8DP_BOARD = [
    (-32.79, -46.96), (-32.79, -51.96), (-32.11, -53.47), (-30.79, -53.96), (37.21, -53.96),
    (38.72, -53.28), (39.21, -51.96), (39.21, 52.04), (38.53, 53.55), (37.21, 54.04),
    (30.21, 54.04), (29.21, 53.04), (29.21, 42.29), (28.21, 41.29), (14.21, 41.29),
    (13.21, 42.29), (13.21, 53.04), (12.21, 54.04), (-30.79, 54.04), (-32.30, 53.36),
    (-32.79, 52.04), (-32.79, 23.04), (-31.79, 22.04), (-25.79, 22.04), (-24.79, 21.04),
    (-24.79, -44.96), (-25.79, -45.96), (-31.79, -45.96), (-32.79, -46.96)]

CASE_8DP = bezel_case(
    ROOT="RB-06/printed-case-waveshare-8", NAME="rb06-8dp", LABEL="RB-06",
    STEP_FRAME=("+y", "-x", "-z", 0.0),  # its STEP model: right, up and back axes, z shift
    DISPLAY_NAME="Waveshare 8DP-CAPLCD", COMPUTER="Raspberry Pi 5",
    GLASS=(194.0, 119.0, 2.0),       # touch glass outline, +-0.1, corner radius
    VIEW=(172.82, 108.24),           # visible area of the glass, centred
    LCM=(-94.58, 89.48, -57.33, 57.33),  # LCD module behind the glass: x0, x1, z0, z1
    DISPLAY_T=5.74,                  # glass front to the LCD module back
    BOARD_BACK=7.39,                 # glass front to the component side of the driver board
    DISPLAY_DEPTH=13.67,             # glass front to the back of the HDMI socket, the deepest part
    DISPLAY_MASS=406,                # g, Waveshare data
    BOARD=[(y, -x) for x, y in _8DP_BOARD[:-1]],
    # parts on the back of the display: x0, x1, z0, z1, depth behind the glass front,
    # the side a plug comes from ("+z", "+x", "-z") or None, and what they stand on
    DISPLAY_PARTS={
        "HDMI": (-20.21, -5.21, 15.24, 26.79, 13.67, "+z", "board"),
        "USB-C, top": (-37.98, -29.04, 18.46, 25.06, 10.8, "+z", "board"),
        "USB-C, right": (34.39, 41.69, -26.18, -17.24, 10.8, "+x", "board"),
        "audio jack": (5.55, 12.90, 21.40, 25.78, 12.01, "+z", "board"),
        "speaker": (-10.96, -1.21, -39.01, -34.91, 10.3, "-z", "board"),
        "button board": (0.79, 10.54, -39.01, -34.91, 10.3, "-z", "board"),
        "LCD flex": (-88.74, -49.51, -32.47, 6.06, 8.35, None, "lcm"),
    },
    # the Pi: component face back, USB end right, HDMI edge up
    PI_AT=(-31.0, 24.0),
    AHRS=(-94.0, -56.0, 12.0, 50.0),
    # open areas, x0, x1, z0, z1, added to the driver board outline
    CARRIER_OPEN={
        "plugs above the board": (-44.0, 18.0, 24.0, 49.5),
        "USB-C plug on the right": (41.0, 76.0, -29.5, -14.0),
        "plugs below the board": (-14.0, 14.0, -50.0, -38.0),
        "LCD flex": (-90.2, -48.0, -34.0, 7.6),
    },
    TAPE_LANDS=[(-93.0, 88.0, 50.8, 55.8), (-93.0, 88.0, -55.8, -50.8),
                (-93.6, -90.9, -55.8, 55.8), (83.0, 88.0, -55.8, 55.8)],
    BACK_HOLES=[
        ("PWR", -42.0, -48.0, ("circle", 12.2)),   # GX12 aviation socket or M12 cable gland
        ("AUX", -18.0, -48.0, ("circle", 12.2)),
        ("GPS", 4.0, -48.0, ("circle", 6.5)),      # SMA bulkhead
        ("ANT", 20.0, -48.0, ("circle", 6.5)),
        ("USB", 46.0, -48.0, ("slot", 18.0, 10.0)),  # a USB-A plug passes
        ("USB", 72.0, -48.0, ("slot", 18.0, 10.0)),
    ],
    CONVERTER=(-90.0, -48.0, -60.0, -5.0, 18.0),
    CONVERTER_TIES=[(-69.0, -12.0, 30.0), (-69.0, -52.0, 30.0)],
)


def squares(centres, half):
    """Square openings round small posts."""
    return [(x - half, x + half, z - half, z + half) for x, z in centres]


# ---------------------------------------------------------------- Waveshare 6.25inch 720x1560 LCD
# From the STEP model (6_25inch-720x1560-LCD.stp) and the size drawing on the product
# page. Mounted in landscape with the driver board's HDMI and USB-C facing right: x = the
# model's y, z = minus its x, depth = 3.48 minus its z. Mass estimated from the model.
CASE_625 = bezel_case(
    ROOT="RB-06/printed-case-waveshare-6-25", NAME="rb06-625", LABEL="RB-06",
    STEP_FRAME=("+y", "-x", "-z", 0.0),  # its STEP model: right, up and back axes, z shift
    DISPLAY_NAME="Waveshare 6.25inch 720x1560 LCD", COMPUTER="Raspberry Pi 5",
    GLASS=(159.18, 74.70, 5.85), GLASS_T=1.1,
    VIEW=(144.18, 66.60),
    LCM=(-78.19, 73.21, -34.45, 34.35),
    DISPLAY_T=3.48,
    BOARD=[(-27.59, -27.45), (33.81, -27.45), (33.81, 27.55), (-27.59, 27.55)],
    BOARD_BACK=6.0, DISPLAY_DEPTH=12.30, DISPLAY_MASS=100, DISPLAY_CG=3.0,
    DISPLAY_PARTS={
        "HDMI": (21.81, 33.81, -22.45, -7.45, 12.30, "+x", "board"),
        "USB-C": (26.41, 33.81, 1.95, 10.95, 9.25, "+x", "board"),
        "power button": (28.21, 31.61, 17.15, 23.95, 9.40, None, "board"),
        "speaker headers": (-4.99, 21.21, 21.15, 25.95, 9.20, "+z", "board"),
        "LCD connector": (-26.19, -20.79, -18.05, 5.95, 8.53, None, "board"),
        "inductor": (-14.59, -7.79, 12.55, 19.35, 8.20, None, "board"),
        "LCD flex": (-78.0, -48.59, -12.25, 30.75, 6.18, None, "lcm"),
    },
    PLUG_LEN={"+z": 8.0},            # JST 1.25 speaker plugs
    CARRIER_OPEN={
        "plugs on the right": (33.0, 60.5, -26.5, 14.5),
        "speaker plugs": (-8.5, 24.5, 25.0, 35.5),
    },
    CARRIER_RECESS={"LCD flex": (-79.5, -47.0, -13.8, 32.3, 2.9)},  # the AHRS plane is behind it
    PI_AT=(-52.0, 15.0), PI_USB_V=(1.0, 36.0),
    AHRS=(-84.0, -55.0, -19.0, 19.0),
    BACK_HOLES=[
        ("PWR", -77.0, 27.0, ("circle", 12.2)),
        ("GPS", -63.0, 27.0, ("circle", 6.5)),
        ("USB", 60.0, 27.0, ("slot", 18.0, 10.0)),
    ],
    CONVERTER=(-84.0, -56.0, -30.0, 14.0, 15.0),
    CONVERTER_TIES=[(-70.0, 8.0, 22.0), (-70.0, -24.0, 22.0)],
)

# ---------------------------------------------------------------- Waveshare 5.5inch HDMI AMOLED
# From the STEP model (5_5inch-hdmi-amoled.stp), the drawing (5_5inch-hdmi-amoled.pdf) and
# the labelled photo of the Rev2.1 board: x = the model's x, z = minus its z, depth = 0.70
# minus its y. The driver board covers the back; the carrier holds its edges. The model
# has no micro USB sockets: those two come from the photo, +-1 mm. Mass estimated.
_55_POSTS = [(48.3, 31.38), (-39.7, 23.38), (18.3, 23.38), (-61.7, 16.58), (-39.7, -25.62),
             (18.3, -25.62), (-61.7, -31.12), (60.2, -31.12)]
CASE_55 = bezel_case(
    ROOT="RB-06/printed-case-waveshare-5-5-amoled", NAME="rb06-55amoled", LABEL="RB-06",
    STEP_FRAME=("+x", "-z", "-y", 0.0),  # its STEP model: right, up and back axes, z shift
    DISPLAY_NAME="Waveshare 5.5inch HDMI AMOLED", COMPUTER="Raspberry Pi 5",
    GLASS=(140.40, 74.76, 4.0), GLASS_T=1.1,
    VIEW=(121.76, 68.70),
    LCM=(-65.77, 64.23, -35.12, 35.38),   # the driver board, its back face
    DISPLAY_T=4.70,
    BOARD=[(-65.77, -35.12), (64.23, -35.12), (64.23, 35.38), (-65.77, 35.38)], BOARD_OPEN=False,
    BOARD_BACK=4.70, DISPLAY_DEPTH=11.02, DISPLAY_MASS=90, DISPLAY_CG=3.0,
    DISPLAY_PARTS={
        "HDMI": (-19.2, -4.2, 17.4, 29.0, 11.02, "+z", "board"),
        "audio jack": (7.0, 13.4, 15.0, 29.0, 9.5, "+z", "board"),
        "power micro USB": (-36.5, -28.5, 23.0, 29.0, 8.5, "+z", "board"),
        "touch micro USB": (40.0, 47.0, -23.5, -15.0, 8.5, "+x", "board"),
        **{f"standoff {i + 1}": (x - 2.7, x + 2.7, z - 2.7, z + 2.7, 8.7, None, "board")
           for i, (x, z) in enumerate(_55_POSTS)},
    },
    PLUG_LEN={"+z": 18.0, "+x": 20.0},
    BODY_MIN=(0.0, 104.0),               # room above the board for the plugs on its top edge
    RELIEF={"plug bay above the display": (-40.0, 16.0, 36.0, 48.5, 7.6, 9.0)},
    CARRIER_OPEN={
        "connectors and plugs at the top": (-38.5, 15.5, 13.5, 48.0),
        "touch plug": (38.5, 69.0, -27.0, -11.5),
        **{f"standoff {i + 1}": r for i, r in enumerate(squares(_55_POSTS, 4.5))},
    },
    CARRIER_RECESS={"board": (-63.5, 57.73, -30.5, 28.88, 2.4),
                    "LCD flex at the top left": (-65.0, -48.5, 14.0, 36.0, 2.4),
                    "touch flex at the top right": (52.0, 69.0, 13.0, 34.0, 2.4)},
    PI_AT=(-40.0, 21.5), PI_PLUG_ROOM=(28.0, 25.0), PI_USB_V=(1.0, 36.0),
    AHRS=(-74.0, -44.0, -19.0, 19.0),
    BACK_HOLES=[
        ("PWR", -66.0, 30.0, ("circle", 12.2)),
        ("GPS", -51.0, 30.0, ("circle", 6.5)),
        ("USB", 55.0, 32.0, ("slot", 18.0, 10.0)),
    ],
    CONVERTER=(-75.0, -45.0, -36.0, 8.0, 15.0),
    CONVERTER_TIES=[(-60.0, 2.0, 22.0), (-60.0, -30.0, 22.0)],
)

# ---------------------------------------------------------------- Waveshare 7inch HDMI LCD (C)
# From the STEP model (7inch_cad.zip, 1118.stp, one solid), the exterior size drawing and
# the LCM drawing (7inch-hdmi-lcd-c-panel-dimension.pdf): x = minus the model's x, z = minus
# its z, depth = its y plus 3.40. Origin on the centre of the PCB, which has a mounting
# ear at each corner (124.27 mm over the ears); the glass sits 1.48 mm above it and the
# visible area is centred on the LCM bezel opening. Mass estimated.
CASE_7C = bezel_case(
    ROOT="RB-06/printed-case-waveshare-7c", NAME="rb06-7c", LABEL="RB-06",
    STEP_FRAME=("-x", "-z", "+y", 0.0),  # its STEP model: right, up and back axes, z shift
    DISPLAY_NAME="Waveshare 7inch HDMI LCD (C)", COMPUTER="Raspberry Pi 5",
    GLASS=(165.0, 100.0, 0.5), GLASS_AT=(0.0, 1.48), GLASS_T=2.0,
    VIEW=(154.08, 85.92), VIEW_AT=(-1.9, 5.08),
    POCKET=(165.8, 125.1, 1.0),          # the PCB with its ears, 0.4 mm play
    LCM=(-82.45, 82.45, -62.13, 62.13),  # the PCB, its back face
    DISPLAY_T=8.0,
    BOARD_BACK=8.0, DISPLAY_DEPTH=14.1, DISPLAY_MASS=260, DISPLAY_CG=5.0,
    DISPLAY_PARTS={
        "HDMI": (71.5, 83.5, 28.88, 43.88, 14.1, "+x", "board"),
        "touch micro USB": (77.7, 83.3, 13.28, 21.08, 10.68, "+x", "board"),
        "backlight switch": (75.9, 79.5, -0.92, 8.08, 13.8, None, "board"),
        "LCD connector": (-17.3, 13.5, -10.52, -5.72, 10.0, None, "board"),
        "header": (57.9, 78.5, -14.32, -9.32, 10.0, None, "board"),
        "capacitor": (-43.9, -39.3, -33.12, -21.72, 11.4, None, "board"),
        "part near the LCD connector": (-22.1, -17.3, 4.48, 9.28, 10.6, None, "board"),
        "part at the left": (-77.9, -72.5, -30.12, -25.92, 10.4, None, "board"),
    },
    PLUG_LEN={"+x": 18.0},               # a 90 degree HDMI adapter
    BODY_MIN=(211.0, 0.0),               # room right of the PCB for the plugs
    RELIEF={"plug bay right of the display": (82.4, 102.0, -3.0, 46.5, 10.5, 12.3)},
    TAPE_LANDS=[(-80.0, 80.0, 48.5, 53.0), (-80.0, 80.0, -53.0, -48.5), (-82.0, -77.5, -48.5, 48.5),
                (77.5, 82.0, -48.5, -4.0)] + [(x0, x0 + 7.0, z0, z0 + 7.0)
                                             for x0 in (-81.5, 74.5) for z0 in (-61.0, 54.0)],
    CARRIER_OPEN={"plugs on the right": (70.0, 102.0, -3.0, 47.0)},
    CARRIER_RECESS={"PCB": (-77.0, 76.0, -47.5, 47.5, 3.6), "header": (56.4, 80.0, -15.8, -7.8, 3.6),
                    "part at the left": (-79.5, -71.0, -31.6, -24.4, 3.6)},
    PI_AT=(-35.0, 28.0),
    AHRS=(-100.0, -62.0, 14.0, 52.0),
    BACK_HOLES=[
        ("PWR", -42.0, -50.0, ("circle", 12.2)),
        ("AUX", -18.0, -50.0, ("circle", 12.2)),
        ("GPS", 4.0, -50.0, ("circle", 6.5)),
        ("ANT", 20.0, -50.0, ("circle", 6.5)),
        ("USB", 46.0, -50.0, ("slot", 18.0, 10.0)),
        ("USB", 72.0, -50.0, ("slot", 18.0, 10.0)),
    ],
    CONVERTER=(-100.0, -58.0, -54.0, 0.0, 18.0),
    CONVERTER_TIES=[(-79.0, -6.0, 30.0), (-79.0, -48.0, 30.0)],
)

# ---------------------------------------------------------------- Waveshare 7.9inch HDMI LCD
# From the STEP model (7.9inch_HDMI_LCD_3D_Drawing.zip, 0820-1.stp, one solid) and the
# size drawing: x = minus the model's x, z = its y, depth = its z plus 3.67. The driver
# board and a taped flex sit 2.2 mm proud of the LCD back; the carrier is recessed over
# them and holds the LCD back beside them. Mass estimated.
_79_POSTS = [(-45.1, 29.2), (68.9, 29.2), (-29.1, 22.7), (29.1, 22.7), (-29.1, -26.5), (28.9, -26.5),
             (-45.1, -29.9), (68.9, -29.9)]
CASE_79 = bezel_case(
    ROOT="RB-06/printed-case-waveshare-7-9", NAME="rb06-79", LABEL="RB-06",
    STEP_FRAME=("-x", "+y", "+z", 0.0),  # its STEP model: right, up and back axes, z shift
    DISPLAY_NAME="Waveshare 7.9inch HDMI LCD", COMPUTER="Raspberry Pi 5",
    GLASS=(207.78, 69.80, 1.0), GLASS_T=1.8,
    VIEW=(191.08, 60.40),
    LCM=(-103.0, 102.6, -34.1, 33.9),
    DISPLAY_T=7.8,
    BOARD=[(-49.0, -33.5), (72.8, -33.5), (72.8, 33.5), (-49.0, 33.5)], BOARD_OPEN=False,
    BOARD_BACK=10.0, DISPLAY_DEPTH=16.0, DISPLAY_MASS=230, DISPLAY_CG=5.0,
    DISPLAY_BLOCKS={"flex under tape": (-103.0, -49.0, -21.5, 7.0, 7.8, 10.0),
                    "flex at the top left": (-103.0, -86.4, 14.1, 27.1, 7.8, 10.0)},
    DISPLAY_PARTS={
        "HDMI": (-8.6, 6.4, 15.7, 27.7, 16.0, "+z", "board"),
        "power micro USB": (-25.6, -17.6, 20.9, 26.5, 12.71, "+z", "board"),
        "audio jack": (17.8, 24.2, 14.5, 28.5, 14.75, "+z", "board"),
        "buttons": (36.2, 55.8, 27.7, 32.7, 11.5, None, "board"),
        "touch micro USB": (51.2, 57.0, -24.5, -16.3, 12.78, "-z", "board"),
        "LCD connectors": (-49.0, -41.4, -21.1, 23.5, 12.3, None, "board"),
        **{f"standoff {i + 1}": (x - 2.7, x + 2.7, z - 2.7, z + 2.7, 14.0, None, "board")
           for i, (x, z) in enumerate(_79_POSTS)},
    },
    PLUG_LEN={"+z": 15.0, "-z": 18.0},   # a 90 degree HDMI adapter at the top
    FLANGE=(6.0, 13.0),                  # narrow sides: the bezel fits a 250 mm bed
    BODY_MIN=(0.0, 94.0),                # room for the Pi and its micro HDMI plugs
    TAPE_LANDS=[(75.8, 101.0, -32.5, 32.5), (-101.0, -52.0, 28.6, 32.4), (-101.0, -52.0, -32.4, -23.0)],
    CARRIER_OPEN={
        "connectors and plugs at the top": (-29.5, 58.0, 13.0, 44.0),
        "touch plug": (49.5, 59.0, -44.0, -14.5),
        "LCD connectors": (-50.5, -40.0, -22.6, 25.0),
        **{f"standoff {i + 1}": r for i, r in enumerate(squares(_79_POSTS, 4.5))},
    },
    CARRIER_RECESS={"driver board": (-50.5, 74.3, -35.0, 35.0, 2.8),
                    "flex under tape": (-104.5, -48.0, -23.0, 8.6, 2.8),
                    "flex at the top left": (-104.5, -85.0, 12.6, 28.6, 2.8)},
    PI_AT=(-40.0, 16.5), PI_USB_V=(1.0, 36.0),
    AHRS=(-101.0, -63.0, -19.0, 19.0),
    BACK_HOLES=[
        ("PWR", -95.0, 28.0, ("circle", 12.2)),
        ("GPS", -80.0, 28.0, ("circle", 6.5)),
        ("ANT", -66.0, 28.0, ("circle", 6.5)),
        ("USB", 68.0, 30.0, ("slot", 18.0, 10.0)),
        ("USB", 68.0, -32.0, ("slot", 18.0, 10.0)),
    ],
    CONVERTER=(-97.0, -62.0, -31.0, 14.0, 15.0),
    CONVERTER_TIES=[(-80.0, 8.0, 30.0), (-80.0, -24.0, 30.0)],
)

# ---------------------------------------------------------------- Waveshare 70H-1024600, touch (CT) version
# From the STEP model of Waveshare's own printed shell (70H-1024600-IPS-CT-3D Pringting
# Shell.stp, without the shell) and the size drawings: x = the model's x, z = its y plus
# 2.35 (the model's origin is the centre of the visible area), depth = 1.27 minus its z.
# The HDMI adapter board comes apart from the display on a 40-pin FPC: it rides on the
# rear cover ribs. Mass estimated.
CASE_70H = bezel_case(
    ROOT="RB-06/printed-case-waveshare-70h", NAME="rb06-70h", LABEL="RB-06",
    STEP_FRAME=("+x", "+y", "-z", 2.35, ["CT_CASE"]),  # its STEP model: right, up, back, z shift, solids to leave out
    DISPLAY_NAME="Waveshare 70H-1024600", COMPUTER="Raspberry Pi 5",
    GLASS=(173.0, 103.0, 1.0), GLASS_T=1.3,
    VIEW=(154.58, 86.42), VIEW_AT=(0.0, 2.35),
    LCM=(-80.3, 83.7, -49.1, 48.5),
    DISPLAY_T=4.0,
    BOARD=[(-15.4, -11.9), (30.6, -11.9), (30.6, 39.6), (-15.4, 39.6)],
    BOARD_BACK=5.21, DISPLAY_DEPTH=8.21, DISPLAY_MASS=140, DISPLAY_CG=3.0,
    DISPLAY_BLOCKS={"LCD and touch flex": (-15.5, 71.3, -48.9, -9.0, 4.0, 5.3)},
    DISPLAY_PARTS={
        "40-pin connector": (-6.5, 21.7, 33.5, 38.9, 7.52, None, "board"),
        "LCD connector": (-14.5, 16.5, -10.3, -3.3, 7.52, None, "board"),
        "touch connector": (19.3, 29.7, -10.3, -3.9, 8.21, None, "board"),
    },
    CARRIER_OPEN={"40-pin FPC": (-8.0, 23.2, 38.0, 48.0)},
    CARRIER_RECESS={"flex": (-17.0, 73.0, -50.5, -7.5, 1.6)},
    PI_AT=(-36.0, 29.4),
    AHRS=(-90.0, -52.0, -24.0, 14.0),
    ROOMS={"HDMI adapter board": (-90.0, -46.0, 18.0, 44.0, 14.0)},
    BACK_HOLES=[
        ("PWR", -34.0, -45.0, ("circle", 12.2)),
        ("GPS", -14.0, -45.0, ("circle", 6.5)),
        ("ANT", 2.0, -45.0, ("circle", 6.5)),
        ("USB", 28.0, -45.0, ("slot", 18.0, 10.0)),
        ("USB", 54.0, -45.0, ("slot", 18.0, 10.0)),
    ],
    CONVERTER=(-90.0, -50.0, -44.0, -10.0, 15.0),
    CONVERTER_TIES=[(-70.0, -16.0, 30.0), (-70.0, -38.0, 30.0), (-68.0, 24.0, 30.0), (-68.0, 39.0, 30.0)],
    ALLOWANCE_FOR="cables, AHRS, converter and HDMI adapter",
)

# ---------------------------------------------------------------- Waveshare ESP32-S3-Touch-AMOLED-2.41
# From the drawing (Dimension_Appearance_Diagram.zip, ESP32-S3-Touch-AMOLED-2.41.pdf); no
# 3D model. Mounted in landscape with the edge connectors up: x = minus the drawing's
# front-view z, z = its front-view x. The board's four M2 standoffs (3.5 mm) carry the
# carrier, so the board and the display hang from it; the bezel clamps the lens on foam.
CASE_241 = bezel_case(
    ROOT="RB-02/printed-case-amoled-2-41", NAME="rb02-amoled241", LABEL="RB-02",
    DISPLAY_NAME="Waveshare ESP32-S3-Touch-AMOLED-2.41", COMPUTER="",
    GLASS=(61.56, 44.72, 1.0), GLASS_T=0.7,
    VIEW=(49.65, 37.22),
    LCM=(-28.35, 28.35, -21.3, 21.3),    # the board, to the ends of its standoffs
    DISPLAY_T=9.5, BACK_TAPE=False,
    BOARD=[(-28.35, -21.3), (28.35, -21.3), (28.35, 21.3), (-28.35, 21.3)], BOARD_OPEN=False,
    BOARD_BACK=6.0, DISPLAY_DEPTH=11.5, DISPLAY_MASS=30, DISPLAY_CG=4.0,
    BOARD_SCREWS=[(sx * 25.5, sz * 18.25) for sz in (1, -1) for sx in (-1, 1)],
    DISPLAY_PARTS={
        "USB-C": (-4.35, 4.65, 14.95, 22.5, 9.5, "+z", "board"),
        "connector, left": (-15.2, -8.6, 16.0, 21.5, 9.5, "+z", "board"),
        "connector, right": (8.9, 15.5, 16.0, 21.5, 9.5, "+z", "board"),
        "RTC battery header": (-22.07, -17.57, 14.95, 20.85, 9.5, None, "board"),
        "battery header": (15.5, 23.3, 12.4, 16.6, 10.0, None, "board"),
        "GPIO header with plug": (-21.6, 21.6, -19.6, -11.9, 21.0, None, "board"),
        "buttons": (25.7, 29.3, -10.0, 10.0, 9.0, None, "board"),
    },
    PLUG_LEN={"+z": 12.0},               # angled USB-C plug, 4-pin plugs
    BODY_MIN=(0.0, 76.0),                # the plug bay above the display
    RELIEF={"plug bay above the display": (-19.0, 19.5, 22.0, 35.0, 8.8, 13.2)},
    TAPE_LANDS=[],
    CARRIER_OPEN={"plugs at the top": (-19.0, 19.5, 21.0, 35.0), "GPIO header": (-23.1, 23.1, -21.1, -10.4)},
    CARRIER_RECESS={"battery header": (14.5, 24.3, 11.4, 17.6, 1.2)},
    COVER_ROOM=14.0,                 # room for a board on the GPIO header, see the KiCad template
    GPIO_PINS=[(-20.32 + 2.54 * i, z) for z in (-17.02, -14.48) for i in range(17)],  # the 2 x 17 header
    BACK_HOLES=[
        ("USB", -12.0, 6.0, ("slot", 14.0, 8.0)),
        ("AUX", 14.0, 6.0, ("circle", 8.2)),
    ],
    ALLOWANCE=20, ALLOWANCE_FOR="cables",
)

CASES = {c.ROOT: c for c in [CASE_8DP, CASE_625, CASE_55, CASE_7C, CASE_79, CASE_70H, CASE_241]}


# ---------------------------------------------------------------- round instruments, RB-02
# Mounted behind the panel like the RB-02 Compact Edition: the shell's front face sits on
# the back of the panel, four screws through the panel into heat-set inserts in the
# shell, the glass seen through the round panel hole. The cap closes the back and holds
# the display board on its own standoffs. Coordinates as the bezel cases, y from the front
# face of the shell.
def round_case(**spec):
    c = Case(**{**dict(
        KIND="round",
        FRONT=2.0,                   # lip over the glass border
        TAPE=1.0, TAPE_SET=0.6,      # foam tape on the lip
        SHELL=(64.0, 64.0, 8.0),     # outline behind the panel: w, h, corner radius
        SHELL_T=15.0,                # front face to the back face of the shell
        CAP_T=4.0,
        PAD=2.0,                     # cap pads reaching forward to the board standoffs
        WINDOW_CHAMFER=1.0,
        INSERT_M3=(4.0, 6.5),
        CLEAR_M3=3.4, CSK_M3=6.4, CLEAR_M2=2.4, CBORE_M2=(4.4, 2.5),
        DISPLAY_PARTS={}, CAP_OPEN={}, RELIEF={}, HOOD=None, STEP_FRAME=None,
        ALLOWANCE=20, ALLOWANCE_FOR="cables and the GPS antenna",
    ), **spec})
    c.Y_GLASS = c.FRONT + c.TAPE_SET
    c.Y_CAP = c.SHELL_T                          # cap front face
    c.Y_BACK = c.SHELL_T + c.CAP_T
    c.POCKET_D = c.GLASS_D + 0.8                 # 0.4 mm play round the glass
    c.WINDOW_D = c.VIEW_D + 1.2
    hole, half, screw = c.PANEL                  # panel hole, half side of the screw square, screw hole
    c.PANEL_SCREWS = [(sx * half, sz * half) for sz in (1, -1) for sx in (-1, 1)]
    c.CAP_SCREWS = c.PANEL_SCREWS                # from the back, into inserts behind the panel inserts
    if c.Y_GLASS + c.STANDOFF_END > c.Y_CAP:
        raise ValueError(f"{c.ROOT}: the board standoffs end behind the cap")
    return c


# ---------------------------------------------------------------- Waveshare ESP32-S3-Touch-AMOLED-1.75
# From the STEP model (ESP32-S3-Touch-AMOLED-1.75-3D.zip) and the drawing in the same ZIP:
# x = the model's z, z = its x, depth = 2.77 minus its y. The header is on the right and
# the USB-C at the bottom. The GPS version (-G) adds a 25 mm ceramic patch on a 28 mm
# board, on an IPEX cable: it rides in the hood, face up.
CASE_175 = round_case(
    ROOT="RB-02/round-case-amoled-1-75", NAME="rb02-amoled175", LABEL="RB-02",
    STEP_FRAME=("+z", "+x", "-y", 0.0),  # its STEP model: right, up and back axes, z shift
    DISPLAY_NAME="Waveshare ESP32-S3-Touch-AMOLED-1.75", COMPUTER="",
    GLASS_D=48.96, VIEW_D=44.16, GLASS_T=2.05,  # cover glass and AMOLED panel
    SPACER=(46.0, 5.7),              # acrylic spacer and the parts on the front of the board: diameter, depth
    BOARD_D=46.02, BOARD_BACK=6.9,   # board, 1.2 mm thick, its back face
    STANDOFF_END=10.4,               # the three M2 standoffs on the back of the board, 3.5 mm
    POSTS=[(-20.5, 0.0), (14.7, 13.75), (14.7, -13.75)],
    DISPLAY_MASS=25,
    DISPLAY_PARTS={
        "USB-C": (-4.77, 4.81, -23.79, -16.26, 10.15, "-z", "board"),
        "header": (17.48, 19.88, -10.43, 10.42, 12.7, None, "board"),
        "speaker plug": (-20.12, -15.92, 2.67, 10.32, 11.7, None, "board"),
        "battery plug": (-20.12, -15.92, -10.63, -2.98, 11.7, None, "board"),
        "buttons": (-13.8, 13.8, 14.73, 19.56, 8.73, None, "board"),
    },
    PLUG_LEN={"-z": 20.0},
    PANEL=(57.5, 24.0, 3.4),         # the 57 mm hole and screw square of tools/cockpit_layouts.py
    RELIEF={"USB-C plug": (-7.0, 7.0, -34.0, -23.5, 7.0, 16.0),
            "antenna cable": (-4.0, 4.0, 23.0, 34.0, 9.0, 16.0)},
    CAP_OPEN={"header": (15.9, 21.5, -11.0, 11.0),
              "speaker plug": (-21.6, -14.4, 1.7, 11.3), "battery plug": (-21.6, -14.4, -11.6, -2.0)},
    # GPS hood on top: outside half width, depth; antenna pocket w, h, floor and roof, pocket
    # front wall; the antenna w, depth, height
    HOOD=dict(half=17.0, depth=34.0, pocket=(30.0, 7.5), wall=1.6, from_y=2.0, antenna=(28.0, 28.0, 6.5)),
)

CASES[CASE_175.ROOT] = CASE_175


# ---------------------------------------------------------------- Waveshare 13.3inch FHD AMOLED
# A portable monitor in its own metal case, 307 x 183 x 10 mm, from the size drawing on the
# wiki (13.3inch-FHD-AMOLED-details-size.jpg). Waveshare publishes no 3D model: the ports
# (two USB-C and mini HDMI on one side, buttons and audio jack on the other) are placed
# from the product photos only, low on each side, so the skirt is open along most of both
# sides. The glass sits 6.3 mm behind the bezel face so that the side ports are behind a
# panel up to 3 mm thick; the window is bevelled at 45 degrees all the way. Mass estimated.
# Every part is cut in two for a 256 mm bed, at seams that do not line up: the carrier
# bridges the bezel seam, the bezel and the rear cover bridge the carrier seam, and the
# carrier bridges the rear cover seam, each with screws on both sides.
_133_ROWS = [-157.9, -100.0, -45.0, -12.0, 12.0, 45.0, 75.0, 120.0, 157.9]
CASE_133 = bezel_case(
    ROOT="RB-06/printed-case-waveshare-13-3-amoled", NAME="rb06-133amoled", LABEL="RB-06",
    DISPLAY_NAME="Waveshare 13.3inch FHD AMOLED", COMPUTER="Raspberry Pi 5",
    GLASS=(307.0, 183.0, 3.0), GLASS_T=1.5,
    VIEW=(293.65, 165.70),
    LCM=(-152.5, 152.5, -90.5, 90.5),   # the back of the monitor, inside its corner radius
    DISPLAY_T=10.0,
    BOARD_BACK=10.0, DISPLAY_DEPTH=10.0, DISPLAY_MASS=650, DISPLAY_CG=5.0,
    FRONT=5.7, WINDOW_CHAMFER=5.7,
    RELIEF={f"ports and buttons, {side}": (sx * 153.0, sx * 175.0, -80.0, 30.0, 8.0, 17.0)
            for side, sx in (("left", -1), ("right", 1))},
    CARRIER_SCREWS=[(x, sz * 95.9) for sz in (1, -1) for x in _133_ROWS] + [(sx * 157.9, 50.0) for sx in (-1, 1)],
    COVER_SCREWS=[(x, sz * 89.9) for sz in (1, -1) for x in (-151.9, -75.0, -45.0, 45.0, 75.0, 151.9)],
    SPLIT={"Bezel": [0.0], "Carrier": [60.0], "Rear cover": [-60.0]},
    PI_AT=(-31.0, 24.0),
    AHRS=(-150.0, -112.0, 20.0, 58.0),
    BACK_HOLES=[
        ("PWR", -42.0, -62.0, ("circle", 12.2)),
        ("AUX", -18.0, -62.0, ("circle", 12.2)),
        ("GPS", 4.0, -62.0, ("circle", 6.5)),
        ("ANT", 20.0, -62.0, ("circle", 6.5)),
        ("USB", 46.0, -62.0, ("slot", 18.0, 10.0)),
        ("USB", 72.0, -62.0, ("slot", 18.0, 10.0)),
    ],
    CONVERTER=(-150.0, -108.0, -75.0, -20.0, 18.0),
    CONVERTER_TIES=[(-129.0, -27.0, 30.0), (-129.0, -67.0, 30.0)],
)

CASES[CASE_133.ROOT] = CASE_133
