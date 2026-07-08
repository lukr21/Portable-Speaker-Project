Speaker Amp V4 - JLCPCB fabrication + assembly package
Generated 2026-07-08 (KiCad 10.0.4). DRC: 0 errors (1 accepted starved
thermal on R6), 0 unconnected, 0 parity.

CONTENTS
  gerbers.zip  - Gerber X2 + Excellon drill. Upload as the PCB file.
  BOM_JLC.csv  - JLC-format BOM (Comment / Designator / Footprint / LCSC Part #)
  CPL_JLC.csv  - JLC-format placement file (mm)

V4 CHANGES vs V3
  - D2 TVS: P6KE16A THT -> SMBJ15A SMB, LCSC C19077569 (JLC Preferred, no
    feeder fee). Polarity is in the netlist; cathode pad faces VBUS_RAW.
  - F1 polyfuse: Bourns MF-RG300 radial -> SMD1812P300TF/16 (3A hold, 16V,
    1812), LCSC C702820. Extended part (~$3 feeder fee). Do NOT substitute
    the suffix-less SMD1812P300TF (C21004): that one is only rated 8V.
  - D1 indicator LED: APA1606 side LED -> 5mm THT (hand-solder).
  - J2/J3/J4 terminals: 5.08mm Phoenix -> 2P 3.5mm KF350-style (hand-solder,
    Detkin stock).

ORDERING NOTES
  - 2-layer 1.6mm FR-4. All SMD on TOP side.
  - JLC assembles the SMD: passives, D2 (C19077569), F1 (C702820),
    J1 USB-C (C165948), SW1-3 (C2856783), U1/U2/U4, Y1.
  - Mark as DO NOT PLACE (hand-solder yourself): D1 5mm LED, J2/J3/J4
    terminals, U3 TDA7297 (C96009, THT; order part + heatsink separately),
    C2/C3/C15 10uF radials, C16 470uF radial.
  - Blank LCSC cells: JLC's BOM tool auto-suggests Basic parts from value +
    package. Accept those. U2 PCM2704CDBR must be matched manually if JLC
    stock allows, else hand-solder from Digikey.
  - Check JLC's DFM/placement preview: SOT-23/SMB rotations sometimes need
    their one-click rotate fix.
