# RB-Cockpits

Flight Simulator Cockpit examples

3D-printable panels for the five home cockpits shown on
[www.rbavionics.com](https://www.rbavionics.com/#rb-simulator), built around
real RB instruments driven by
[RB-Simulator](https://github.com/xiaprojects/rbsimulator).

## Designs

| Design | Instruments | Tiles | Author | License |
|---|---|---|---|---|
| [Desktop pod](desktop-pod/) | RB-09, RB-01 HSI, RB-01 10" display | 4 | RB-Avionics | Personal use; commercial by agreement |
| [Six-pack trainer](six-pack-trainer/) | RB-01 13.3", 7.1" and 8.9" displays, RB-09, RB-01 HSI, RB-04, RB-05, switches and engine controls | 13 | RB-Avionics | Personal use; commercial by agreement |
| [Glass-cockpit rig](glass-cockpit-rig/) | two RB-01 13.5" displays, RB-09, RB-05, on a 40 mm aluminium-profile frame | 14 | RB-Avionics | Personal use; commercial by agreement |
| [Glider panel](glider-panel/) | RB-01 7.5" display, RB-09, RB-01 HSI, RB-05 57 mm | 6 | RB-Avionics | Personal use; commercial by agreement |
| [Ultralight rehearsal](ultralight-rehearsal/) | RB-01 14.8" wide display, RB-09, RB-01 HSI, RB-04, RB-05, switches | 11 | RB-Avionics | Personal use; commercial by agreement |

Each design folder has the hardware list, a layout map of the tiles, one STL
per tile, a DXF of the whole panel for laser or CNC cutting, the FreeCAD model,
and a KiCad backplane template: a board with the panel outline, cut-outs for the
instrument bodies and displays, and the switch positions, to build the
electronics behind the panel.

## Printing

- Every tile is a flat 4 mm plate that fits a 200 × 200 mm bed. Print it as
  exported, front face down: the engraved labels come out on the first layer,
  and a textured sheet gives the panel its finish.
- PLA or PETG for a simulator, 0.2 mm layers, 4 perimeters, 25 % infill. A panel
  for an aircraft must withstand 100 °C in cruise on long flights: read
  [PRINTING.md](../PRINTING.md) for the materials and the test.
- Each dovetail has a 0.15 mm gap all round. If a joint is tight, sand the tab
  or trim the first-layer squish from the socket.

## Assembly

1. Lay the tiles face down on a flat table, as in the layout map of the design.
2. Glue every dovetail with CA glue or two-part epoxy, keeping the tiles pressed
   flat until it sets.
3. Fit the RB round instruments from behind with 4 × M3 screws, and the
   switches and controls with their own nuts.
4. Mount each RB-01 display behind its window with your own brackets on the four
   M3 holes beside it.
5. Fix the panel to its frame with M4 screws. The glass-cockpit rig plates have
   ears with M5 holes on the slot centre of 40 × 40 mm profiles, for T-nuts.

## Cut-outs

| Part | Cut-out | Source |
|---|---|---|
| RB 80 mm round instrument | Ø80.5 mm, 4 × M3 on a 62.25 mm square | RB-01 drilling template (±31.25 mm) and RB-02 SixPack template (±31.0 mm) in this repo |
| RB 57 mm round instrument | Ø57.5 mm, 4 × M3 on a 48 mm square | the concept render: check it against your case before printing |
| RB-01 display | the screen window of the concept render | resize it to your display |
| Mini rocker switch (KCD1) | 12.9 × 19.2 mm | KCD1 datasheet |
| Key switch | Ø19 mm | common 19 mm key switches |
| Push-pull control | Ø10.2 mm | 3/8" or M10 bushing |
| Potentiometer | Ø7.2 mm | M7 bushing |

Positions follow the concept renders, except where they did not work on a real
panel: the glider's upper panel screws sat inside the 80 mm holes and moved below
them, and the rig plates got mounting ears because the rendered plates only
fill the frame openings.

## Changing a panel

The panels are generated with FreeCAD by
[tools/cockpit_panels.py](../tools/cockpit_panels.py); the layouts and the
cut-out sizes are in [tools/cockpit_layouts.py](../tools/cockpit_layouts.py).
Rebuild from the repo root:

```
freecad.cmd tools/cockpit_panels.py               # all cockpits, 200 mm bed
RB_BED=250 freecad.cmd tools/cockpit_panels.py    # fewer, larger tiles
RB_ONLY=glider freecad.cmd tools/cockpit_panels.py
```

After a layout change, rebuild the KiCad backplanes too:
`python3 tools/kicad_templates.py` (needs KiCad 9).

`freecad.cmd` is the snap command; elsewhere it is `freecadcmd`. To open a model:
`QT_QPA_PLATFORM=xcb freecad RB-Cockpits/glider-panel/files/glider-panel.FCStd`.
