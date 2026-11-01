# Printed case, Waveshare 6.25"

![Assembled case, front view](images/assembly.png)

A 3D-printed case for the RB-06 with the Waveshare 6.25inch 720x1560 LCD, a
720 × 1560 HDMI touch display shaped as a long strip, mounted in landscape. It
holds the display together with a Raspberry Pi 5 and an AHRS sensor. The case
slides into the instrument panel from the front and is held by six screws
through the bezel. It is the [8" printed case](../printed-case-waveshare-8/)
cut to this display, three parts printed without supports:

- **Bezel:** holds the glass and screws to the panel.
- **Carrier:** a honeycomb plate that clamps the display from behind and
  carries the AHRS plane.
- **Rear cover:** carries the Pi, the cable holes and the vents.

| | |
|---|---|
| Author | RB-Avionics |
| License | Free for personal use; commercial use requires an agreement, see [LICENSE.md](../../LICENSE.md) |
| Display | [Waveshare 6.25inch 720x1560 LCD](https://www.waveshare.com/wiki/6.25inch_720x1560_LCD): 159.2 × 74.7 mm glass, HDMI, USB-C power and touch |
| Computer | Raspberry Pi 5 with the Active Cooler |
| Depth | 44.8 mm from the bezel front, 40.3 mm behind the front face of the panel |
| Material | PC or PA-CF for an aircraft, see [PRINTING.md](../../PRINTING.md) |
| Units | millimetres |

> **Printing for an aircraft:** the case must withstand 100 °C in cruise on
> long flights. Print it in PC or PA-CF, never PLA, PETG, ABS or ASA, and run
> the oven test first: read [PRINTING.md](../../PRINTING.md).

## Design

The honeycomb, the screws into brass and the shock design are those of the
[8" printed case](../printed-case-waveshare-8/#design). What changes here:

- **Measured from Waveshare's 3D model** of the display (the ZIP on its wiki)
  and the size drawing on the product page. The display mass, 100 g, is
  estimated from the model.
- **Landscape.** The driver board sits right of centre on the back of the
  display, with its HDMI, USB-C and power button facing right and its two
  speaker headers facing up.
- **Carrier.** Open over the driver board and over the plugs on its right.
  The LCD flex lies 2.7 mm proud of the display on the left; the carrier is
  recessed over it, and the AHRS plane is on its back.
- **Room for every plug.** The display's HDMI plug has 25 mm to its right:
  use a slim plug or a 90° adapter. The rear cover keeps 40 mm free beyond
  the Pi's two USB stacks, but not beyond its Ethernet port, which the case
  leaves unused. A script checks the parts against blocks for the display,
  the Pi, an AHRS board and the room their plugs need, and the parts were
  checked against Waveshare's model of the display.
- **A small case.** Three back holes instead of six, a 29 mm wide AHRS plane,
  and room for a smaller 5 V converter.

## What goes where

Directions are as seen from the front.

| Item | Where |
|---|---|
| Display | glass down in the bezel pocket, the driver board right of centre, its HDMI and USB-C facing right |
| Raspberry Pi 5 | on the rear cover standoffs, component side back so the Active Cooler draws air through the open cells; USB to the right, micro HDMI up |
| AHRS plane | back of the carrier, at the left: a flat pad 1 mm proud of the honeycomb, parallel to the panel, with an UP arrow |
| 5 V converter | left on the rear cover ribs, above the AHRS plane: room for 28 × 44 × 15 mm, two tie-wrap pairs to strap it |
| Back holes | PWR, 12.2 mm, for a GX12 socket or an M12 cable gland; GPS, 6.5 mm, for an SMA bulkhead; an 18 × 10 mm USB slot that passes a USB-A plug. The cable holes have a tie-wrap pair above them, and the labels are engraved on the back |

## Cables

- **HDMI:** micro HDMI on the Pi (HDMI0, next to the USB-C) to HDMI on the
  display. An FPC ribbon HDMI cable with angled adapters fits best.
- **Touch and display power:** USB-A on the Pi to the display's USB-C, with
  an angled USB-C plug. Waveshare: the USB-C is both the power and the touch
  port.
- **AHRS:** four wires to the GPIO header, I2C bus 1: 3.3 V pin 1, SDA pin 3,
  SCL pin 5, GND pin 6.
- **Power:** 12 or 24 V in through PWR to a 5 V, 5 A converter, then to the
  Pi's USB-C.

Leave the cables between the Pi and the display long enough to open the case
like a book: the Pi comes away with the rear cover.

## Assembly

1. Print the three parts. Before going on, check that the display drops
   into the bezel pocket.
2. Press in the heat-set inserts listed under Hardware: M3 in the back face
   of the bezel skirt, M3 in the back of the carrier corners, M2.5 in the
   rear cover standoffs.
3. Stick 3 mm foam tape on the bezel lip round the window, 2 mm outside its
   edge. Stick 5 mm tape on the flat strips of the carrier's front face, not
   in the recess.
4. Lay the bezel face down on a soft cloth and put the display in, glass
   down.
5. Lay the carrier on the display, front face down, with its large opening
   over the driver board and its recess over the LCD flex. Drive the M3 flat
   head screws into the bezel crosswise, until the carrier sits on the skirt.
6. Glue the AHRS board between the marks of the AHRS plane, edges square to
   the arrow, with an epoxy rated above 100 °C.
7. Lay the rear cover inside up, its top edge away from you. Put the Pi on
   the standoffs, component side down, USB ports to the right and the micro
   HDMI edge away from you. Fix it with 4 × M2.5 × 6 screws from the back of
   the board.
8. Fit the SMA bulkhead and the GX12 socket or gland. Strap the 5 V
   converter to its tie-wrap pairs. Pass the outside cables through the back
   holes and tie each one at its tie-wrap pair. Then connect HDMI, USB and
   the AHRS wires.
9. Close the rear cover on the carrier. Its 4 × M3 × 10 socket head screws
   go down the columns, driven with a 2.5 mm hex key.
10. Cut the panel from the DXF below, slide the case in from the front, and
    fix the bezel with the M4 flat head screws and nylon-insert lock nuts.

## AHRS

The AHRS plane is tied to the panel through the carrier and the bezel, and it
stays put when the rear cover comes off. The plane is parallel to the panel,
so the sensor's Z axis points fore and aft. Run the AHRS orientation and
calibration of the RB software with the panel installed. The 5 V converter
sits on the ribs right behind the plane: calibrate the magnetometer in place
with the converter loaded, or do not rely on magnetic heading.

## Changing the case

The case is generated with FreeCAD by [tools/display_cases.py](../../tools/display_cases.py)
from the dimensions in [tools/display_case_layouts.py](../../tools/display_case_layouts.py).
Rebuild from the repo root with
`RB_ONLY=RB-06/printed-case-waveshare-6-25 freecad.cmd tools/display_cases.py`,
then the AHRS board template with
`RB_ONLY=RB-06/printed-case-waveshare-6-25 python3 tools/kicad_templates.py`.
The FreeCAD model in `files/` is the assembled case for viewing and measuring;
edit the scripts, not the model.

<!-- BEGIN parts: generated by tools/display_cases.py, do not edit by hand -->
## Parts

| Part | On the bed | Size on the bed (mm) | Mass in PC | File |
|---|---|---|---:|---|
| Bezel | front face down | 202 × 118 × 8 | 83 g | [rb06-625-bezel.stl](files/rb06-625-bezel.stl) (352 KB) |
| Carrier | front face down | 176 × 92 × 9 | 76 g | [rb06-625-carrier.stl](files/rb06-625-carrier.stl) (513 KB) |
| Rear cover | back face down | 176 × 92 × 29 | 105 g | [rb06-625-rear-cover.stl](files/rb06-625-rear-cover.stl) (1023 KB) |

The parts print without supports, placed as exported. The bezel needs a bed of at least 205 × 120 mm. Masses are for solid polycarbonate; the honeycomb is already thin solid walls (1.6 mm, four 0.4 mm lines): 56 cells in the carrier, 9 open vent cells in the rear cover over the Pi fan and 60 vents in its top and bottom walls.

<img src="images/exploded-front.png" alt="Exploded view from the front: bezel, display, honeycomb carrier, Raspberry Pi 5, rear cover">

<img src="images/exploded-rear.png" alt="Exploded view from the back: rear cover with the back holes, Raspberry Pi 5, carrier with the AHRS plane, display, bezel">

## Hardware

| Item | Qty | Where |
|---|---:|---|
| M3 heat-set insert, 5.7 mm long, for a 4 mm hole | 10 | bezel skirt (6), carrier corners (4) |
| M2.5 heat-set insert, 4 mm long, for a 3.6 mm hole | 4 | rear cover standoffs |
| M3 × 12 flat head, ISO 10642 | 6 | carrier to bezel |
| M3 × 10 socket head, ISO 4762 | 4 | rear cover to carrier, inside the columns (2.5 mm hex key) |
| M2.5 × 6 pan or socket head | 4 | Raspberry Pi to the standoffs |
| M4 × 12 flat head, ISO 10642 (or #8), with nylon-insert lock nuts | 6 | bezel to the panel, up to 3 mm of panel |
| Closed-cell foam tape, 1 mm, silicone or EPDM rated above 100 °C | 0.4 m × 3 mm, 0.4 m × 5 mm | on the bezel lip round the window; on the carrier's flat strips behind the display |
| Epoxy rated above 100 °C | a few grams | AHRS board on the AHRS plane |
| Tie-wraps, 2.5 mm, heat-stabilised, rated 105 °C | 6 to 10 | cables at the back holes, 5 V converter |

## Panel cut-out

176.98 × 92.5 mm with 6.5 mm corners, and 6 holes of 4.4 mm at x = ±94.5 and 0, z = ±52.2 mm from the centre of the cut-out. The case slides in from the front and the bezel (201.98 × 117.5 mm) covers the edge. Drawing 1:1, layers CUT and BEZEL: [rb06-625-panel-cutout.dxf](files/rb06-625-panel-cutout.dxf)

## Load check, -3 to +6 G

Static loads for the whole unit, 534 g: display 100 g, Pi 5 with cooler 70 g, printed parts 264 g in PC, 100 g for cables, AHRS and converter. Every load is taken as if it acted in the worst direction for that part.

| | +6 G | -3 G |
|---|---:|---:|
| Unit weight × G | 31 N | 16 N |
| Shear on each M4 panel screw | 5.2 N | 2.6 N |
| Pull on each screw of the top or bottom row, from the overhang behind the panel | 1.5 N | 0.8 N |
| Display on the bezel pocket wall | 6 N | 3 N |
| Pull on each carrier insert, display pushed back | 1.7 N | 0.9 N |
| Bending at the root of each Pi standoff | 1.0 MPa | 0.5 MPa |

Each load is a few newtons, against the hundreds of newtons an M3 heat-set insert holds and the tens of MPa printed PC or PA-CF takes across its layers at 100 °C. Shock and vibration are what remain: the display is clamped on foam and backed by the honeycomb, every screw goes into brass, and the cables are tied at the back holes so their plugs carry no load.

FreeCAD model, assembled, with reference blocks for the display, the Pi and an AHRS board: [rb06-625-case.FCStd](files/rb06-625-case.FCStd)
<!-- END parts -->

<!-- BEGIN kicad: generated by tools/kicad_templates.py, do not edit by hand -->
## KiCad board template

A KiCad project as the starting point for your own electronics.

<img src="images/kicad-rb06-625-ahrs-board.svg" alt="Waveshare 6.25inch 720x1560 LCD printed case: AHRS board">

[kicad/rb06-625-ahrs-board/rb06-625-ahrs-board.kicad_pro](kicad/rb06-625-ahrs-board/rb06-625-ahrs-board.kicad_pro): A 27 x 27 mm IMU board for the AHRS plane of the carrier, glued flat.

- Seen from behind, the component side; up is up on the instrument, as the arrow on the plane.
- Outline = the AHRS plane between its engraved marks, 1 mm inside its sides: a 25.4 mm breakout fits too.
- No mounting holes: glue the board flat with an epoxy rated above 100 °C, edges square to the arrow.
- Parts up to 4 mm tall clear the rear cover and the 5 V converter above the plane.
- Wire it to the Pi GPIO, I2C bus 1: 3.3 V pin 1, SDA pin 3, SCL pin 5, GND pin 6. The RB software finds ICM-20948 and MPU-9250 family IMUs at 0x68 and BMP280/388/390 baros at 0x76 or 0x77.
- The plane is parallel to the panel; set the sensor orientation in the AHRS calibration of the RB software.
- Dwgs.User shows the carrier cut 0.5 mm in front of its back face, round the AHRS plane.

<!-- END kicad -->
