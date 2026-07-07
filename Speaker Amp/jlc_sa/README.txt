Speaker Amp V3.1 - JLCPCB fabrication + assembly package
Generated 2026-07-07 (KiCad 10.0.4). DRC: fully routed, 0 unconnected,
0 parity; accepted starved-thermal warnings only.

Changes vs previous package: Y1 crystal is now 3225 4-pad (2-pin-mapped
footprint), SW1-SW3 are now SMD side-press XUNPU TS-1005B (machine
assembled!), cap values normalized (22n/220n).

CONTENTS
  gerbers.zip  - Gerber X2 + Excellon drill. RE-UPLOAD this as the PCB file.
  BOM_JLC.csv  - JLC-format BOM
  CPL_JLC.csv  - JLC-format placement file (mm)

ORDERING NOTES
  - SW1-SW3: XUNPU TS-1005B-AR04526 = C2856783 (pre-filled).
  - Y1: pick a BASIC 12MHz crystal, 3.2x2.5mm (3225) 4-pad, CL 18-20pF
    (e.g. YXC X322512MSB4SI). 20pF is fine with the 22pF load caps.
  - U2 PCM2704CDBR: search by MPN, VERIFY STOCK FIRST (no substitutes).
  - U1 LD1117S33TR, U4 CH221K, D2 P6KE16A: search by MPN.
  - D1: Kingbright APA1606CGCK green side-view (1.6x0.6mm); DNP+hand-solder
    if not stocked.
  - Generic 0805 R/C: accept JLC basic auto-matches.
  - Electrolytics: 10uF >=16V radial 5mm/2mm pitch; 470uF >=16V 10mm/5mm.
  - J2-J4 terminal blocks: DNP, hand-solder (5.08mm pitch, e.g. Phoenix MKDS
    or KF301/DG500 clones with <=1.3mm pins).
  - U3 TDA7297 mounts vertically; NO heatsink at assembly (customer fits own).
  - Check the DFM/placement preview: rotations of U1/U2/U4, D2, and the
    side-press switches (button must face OFF the board edge).
