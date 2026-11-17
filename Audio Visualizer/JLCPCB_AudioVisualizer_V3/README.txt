Audio Visualizer V3 - JLCPCB fabrication + assembly package
Generated 2026-11-17 (KiCad 10.0.4). DRC: 0 errors, 0 unconnected, 0 parity.
NOT YET TESTED ON HARDWARE.

CONTENTS
  gerbers.zip  - Gerber X2 + Excellon drill. Upload as the PCB file.
  BOM_JLC.csv  - JLC-format BOM (Comment / Designator / Footprint / LCSC Part #)
  CPL_JLC.csv  - JLC-format placement file (mm)

V3 CHANGES vs V2
  - R67, R68 (47k) added from each peak-detector diode anode to GND. Without
    this DC return the 1 uF coupling capacitors charge up and the meter
    fades to zero. R68 is 0603 (C25819) to fit beside C3; R67 is 0805.
  - C5 100 nF at the LM358 supply pin and C6 10 uF 25 V ceramic at J3: the
    board had no decoupling on +12 V.
  - Board outline, LED and terminal positions are unchanged from V2.

V2 BOARDS YOU ALREADY HAVE can be fixed by hand: tack a 47k resistor from the
anode pad of D1 and of D12 to a GND pad, and put a capacitor across J3.

ORDERING NOTES
  - 2-layer 1.6 mm FR-4. SMD is on the TOP side only; C2, C4 and J3-J7 are
    hand-soldered on the underside as in V2.
  - Mark as DO NOT PLACE (hand-solder): all LEDs D2-D11/D13-D22, C2/C4, J3-J7.
  - Blank LCSC cells (resistors, 1u caps): accept JLC's Basic suggestion.
  - Check JLC's DFM/placement preview: SOT-23 and diode rotations sometimes
    need their one-click rotate fix.
  - Needs a 12 V supply of at least 11 V: the top LEDs switch at about 9.6 V
    of envelope.
