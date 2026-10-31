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
