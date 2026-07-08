Audio Visualizer V2 - JLCPCB fabrication + assembly package
Generated 2026-07-08 (KiCad 10.0.4). DRC: 0 errors, 0 unconnected, 0 parity.

CONTENTS
  gerbers.zip  - Gerber X2 + Excellon drill. Upload as the PCB file.
  BOM_JLC.csv  - JLC-format BOM (Comment / Designator / Footprint / LCSC Part #)
  CPL_JLC.csv  - JLC-format placement file (mm)

V2 CHANGES vs V1
  - All 20 ladder LEDs are 5mm THT (hand-solder, Detkin stock). Colors per
    position (left = connector end, per row): green D2-D6/D13-D17,
    orange D7-D10/D18-D21, red D11/D22.
  - C2/C4 10uF are THT radials (user's 100V "BPSM2316" caps, hand-solder).
  - Terminals are five 2P 3.5mm KF350-style blocks J3-J7 (hand-solder,
    Detkin stock). The old MX126 4P blocks are gone.
  - Board re-laid out: ALL SMD is on the TOP side only.
  - Resistor ladder recalculated so every resistor value is in JLC's
    BASIC catalog (per-stage Rtop/Rk pairs; see Docs/vu_ladder_math.pdf).
    Worst threshold error improved from 3.8% to 1.4%.

ORDERING NOTES
  - 2-layer 1.6mm FR-4.
  - Assembly is SINGLE-SIDED TOP, SMD only -> Economic PCBA works now.
    JLC assembles: R1-R66, C1/C3, D1/D12 Schottky (C8598), Q2-Q21 (C20526),
    U1 (C7950).
  - Mark as DO NOT PLACE (hand-solder yourself): all LEDs D2-D11/D13-D22,
    C2/C4, J3-J7.
  - Blank LCSC cells (resistors, 1u caps): JLC's BOM tool auto-suggests
    Basic parts from value + 0805 package. Accept those.
  - Check JLC's DFM/placement preview: SOT-23 and diode rotations sometimes
    need their one-click rotate fix.
  - Wire per the schematic/silkscreen, not from memory.
