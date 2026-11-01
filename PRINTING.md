# Printing for aircraft

> **Disclaimer.** RB-Avionics cases and panels are not certified aircraft parts.
> Choosing the material, printing, testing and installing them is the builder's
> responsibility, under the rules that apply to the aircraft. A part printed in
> the wrong material can soften, warp or drop an instrument in flight.

## Requirement: 100 °C for the whole flight

Every printed part installed in an aircraft must keep its shape and hold its
screws at **100 °C, continuously, for as long as your longest flight**. That is
the temperature behind the panel in cruise on long flights, in the sun and next
to the electronics.

Choose a filament whose **heat deflection temperature (HDT)** is well above
100 °C: at least 110 °C, measured to ISO 75 at 0.45 MPa, as printed in the
filament datasheet. The glass transition temperature (Tg) alone is not enough.

| Material | Typical HDT at 0.45 MPa | For aircraft parts |
|---|---|---|
| PLA, PLA+ | 55–60 °C | **No.** Softens in a parked aircraft in the sun |
| PETG | 65–75 °C | **No** |
| ABS, ASA | 85–100 °C | **No.** At or below the requirement, no margin |
| PC, PC blends | 110–120 °C | Yes, if your brand's datasheet shows at least 110 °C |
| PA-CF, PAHT-CF (carbon-fibre nylon) | 150–190 °C | Yes, the most margin |

Values vary between brands: always check the datasheet of the exact filament
you print. Some filaments reach their datasheet HDT only after annealing, and
annealing shrinks the part, so check the fit afterwards. Prefer a
flame-retardant grade where your filament maker offers one.

## Printing requirements

- An enclosed printer at the chamber temperature the datasheet asks for: PC and
  nylon warp and crack in open air.
- Dry the filament before printing, nylon especially: it absorbs moisture within
  hours and prints weak.
- A hardened steel nozzle for carbon-fibre filaments.
- At least 4 perimeters and 40 % infill for cases and mounts, at the
  temperatures of the filament datasheet.

## Print tips

- **Orientation.** The printed display cases (the RB-06
  [printed cases](RB-06/printed-case-waveshare-8/), and the RB-02
  [2.41"](RB-02/printed-case-amoled-2-41/) and
  [round 1.75"](RB-02/round-case-amoled-1-75/) cases) and the RB-Cockpits
  tiles come placed on the bed the way they print best: print them as
  exported, without supports. For the other cases, put the largest flat face
  on the bed.
- **Large flat parts warp.** PC and nylon shrink as they cool, and the RB-06
  8" bezel is 237 × 162 mm; the 13.3" case comes in pieces up to 222 × 226 mm.
  - Print on textured PEI or on a layer of glue stick: PC can stick to smooth
    PEI hard enough to tear it.
  - Add a 5–8 mm brim.
  - Keep the part cooling fan low, 10–30 %.
  - Let the part cool down inside the closed printer before you take it off.
- **Honeycomb walls.** The walls of the printed cases' honeycomb are 1.6 mm: with a
  0.4 mm nozzle and 0.4 mm lines they are exactly 4 perimeters, with no thin
  gap fill. Print 0.2 mm layers. Keep the 40 % infill for the solid areas.
- **Flat AHRS plane.** Turn on ironing for top surfaces, or at least for the
  AHRS plane, so the sensor board sits flat on it.
- **Check the size before the inserts.** Fit the display in the bezel pocket
  and the screws in their holes on the first print. Annealing shrinks the part:
  anneal and measure a test piece first, scale the print by its shrinkage, and
  press the inserts in after annealing.
- **Heat-set inserts, not printed threads.** Every screw of a part that flies
  goes into a brass insert. The hole sizes are in each design README. Use an
  iron with an insert tip at about the filament's printing temperature. Press
  straight and slowly, stop flush with the surface, and hold the iron flat for
  a few seconds. Let the insert cool before you load it.
- **No liquid threadlocker on polycarbonate.** Anaerobic threadlockers make PC
  crack under stress. Lock the screws with nylon-insert nuts or a nylon patch
  instead.
- **Tape and glue fly too.** Foam tape, glue and cable ties inside the case
  see the same 100 °C. Use silicone foam tape, heat-stabilised cable ties
  rated 105 °C, and epoxy rated above 100 °C for glued sensors.

## Test before flying

Put one printed part, for example a front ring or a bezel, in an oven at
100 °C for as long as your longest flight, with an oven thermometer: kitchen
ovens drift. Let it cool, then check that it has not warped, that the
instrument still fits and that the screws still hold. Print the real parts only
when the test part passes.

## Simulator panels

The [RB-Cockpits](RB-Cockpits/) panels are made for flight simulators, indoors:
PLA or PETG is fine there. A panel printed for an aircraft falls under the
same 100 °C requirement as every other part, and so does the glue of its
dovetails: use an epoxy rated above 100 °C, because common CA glue and
five-minute epoxy soften well below that.
