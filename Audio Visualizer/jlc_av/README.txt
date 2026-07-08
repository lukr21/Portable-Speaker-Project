Audio Visualizer V1 - JLCPCB fabrication + assembly package
Generated 2026-07-07 (KiCad 10.0.4). DRC: 0 errors, 0 unconnected, 0 parity.

CONTENTS
  gerbers.zip  - Gerber X2 + Excellon drill. Upload as the PCB file.
  BOM_JLC.csv  - JLC-format BOM (Comment / Designator / Footprint / LCSC Part #)
  CPL_JLC.csv  - JLC-format placement file (both sides, mm)

ORDERING NOTES
  - 2-layer 1.6mm FR-4. Board is a long bar (~85x25mm), all LEDs on TOP side.
  - Assembly is DOUBLE-SIDED: top = LED ladder SMD; bottom = 2x SMD
    electrolytics (C2, C4) + 3x THT screw terminals. Choose Standard PCBA
    (economic only covers single-side SMD). Cheaper alternative: assemble
    TOP side only and hand-solder the bottom (2 easy SMD caps + 3 THT blocks).
  - LED colors are encoded in the BOM (left = connector end, per row):
    * LED-GREEN  (D2-D6, D13-D17)  = C2297
    * LED-ORANGE (D7-D10, D18-D21) = search "0805 LED orange" in the matcher;
      if nothing orange is stocked/reasonable, use yellow C2296 instead
    * LED-RED    (D11, D22)        = C2286
  - Blank LCSC cells (resistors, 1u caps, 10u electrolytics): JLC's BOM tool
    auto-suggests basic parts from value + 0805/4x5.4 package. Accept those.
  - J3 (2P terminal) = LCSC C5188434 (MaiXu MX126-5.0-02P).
  - J1/J2 (4P terminals): the MX126 4P is NOT stocked at LCSC. Options:
    (a) fit TWO C5188434 2P blocks side-by-side per footprint (they gang
        flush at 5.0mm pitch - this is what the 3D render shows), or
    (b) hand-solder any 5.0mm-pitch 4P screw terminal.
    Either way, mark J1/J2 "do not place" in the assembly and hand-fit.
  - Check JLC's DFM/placement preview before confirming: SOT-23 and
    diode rotations sometimes need their one-click rotate fix.
  - Wire polarity: pin order was mirrored when terminals moved to the back.
    Wire per the schematic/silkscreen, not from memory.
