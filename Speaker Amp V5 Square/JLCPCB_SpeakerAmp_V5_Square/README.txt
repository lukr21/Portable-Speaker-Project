Speaker Amp V5 Square - JLCPCB fabrication + assembly package
Generated 2026-11-17 (KiCad 10.0.4). DRC: 0 errors, 0 unconnected, 0 parity.
Board: 62.0 x 63.45 mm, 2 layers, 1.6 mm FR-4. NOT YET TESTED ON HARDWARE.

CONTENTS
  gerbers.zip  - Gerber X2 + Excellon drill. Upload as the PCB file.
  BOM_JLC.csv  - JLC-format BOM (Comment / Designator / Footprint / LCSC Part #)
  CPL_JLC.csv  - JLC-format placement file (mm)

V5 CHANGES vs V4
  - Power: the CH221K PD trigger is gone (its CFG resistor went to GND, so V4
    only ever got 5 V). Both USB-C ports are plain 5 V sinks. J1 = data + power,
    J5 = power only.
  - Each port has its own TPS61376 boost to 12 V (U6 for J1, U7 for J5) with an
    input current limit of 0.35 / 1.4 / 2.84 A, chosen from what the source
    advertises on CC (LM339 U5 + TL431 U4). U7 is set to 12.3 V and U6 to
    11.7 V so the power-only port carries the load first.
  - C16 bulk capacitor is now 2200 uF 16 V (was 470 uF), same 10 mm footprint.
  - New from-scratch layout: square outline, M2.5 holes in the four corners,
    SW1-SW3 + J5 + J1 in a row on the left edge, J4 (12 V out) / J2 (left) /
    J3 (right) and the TDA7297 on the right edge.

ORDERING NOTES
  - All SMD is on the TOP side.
  - JLC assembles the SMD parts in the BOM. Extended parts (one-time feeder
    fee each): U6/U7 TPS61376RYHR (C7073367), U5 LM339 (C7948), U4 TL431
    (C181103), D3 BAT54C, D5/D6 SS34, L1/L2 FXL0630-4R7-M (C167220),
    U2 PCM2704C (C2859784), F1/F2, J1/J5, SW1-3, and the E96 resistors
    (93.1k, 88.7k, 80.6k, 30.9k, 18k, 10M, 56k).
  - Mark as DO NOT PLACE (hand-solder): D1 5 mm LED, J2/J3/J4 terminals,
    U3 TDA7297 (C96009), C2/C3/C15 10 uF radials, C16 2200 uF radial.
  - Blank LCSC cells: accept JLC's Basic suggestion from value + 0805.
  - U6/U7 footprint (TPS61376_RYH0013A) was drawn from TI's land pattern
    4226722/A. Check it in JLC's DFM/placement preview before paying, and
    check SOT-23 / SMA / SMB / SOIC rotations (one-click rotate fix).
  - L1/L2 must saturate above 5.4 A (the converter's worst-case peak limit).
  - Six through-hole ground pads have a single thermal spoke; the TDA7297's
    two ground pins connect solidly to the plane (use a hot iron).
  - 20 reference labels in dense areas are hidden on the silkscreen; use the
    placement file or KiCad to identify those parts.
  - First power-up: no speakers, a 5 V/3 A USB-C charger on J5, check +12 V at
    J4 (expect about 12.3 V) before fitting U3 and the speakers.
