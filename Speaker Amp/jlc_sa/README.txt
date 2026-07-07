Speaker Amp V3 - JLCPCB fabrication + assembly package
Generated 2026-07-07 from the V3 design (KiCad 10.0.4).
DRC: fully routed, 0 unconnected, 0 parity; 1 accepted starved-thermal spoke.

CONTENTS
  gerbers.zip  - Gerber X2 + Excellon drill. Upload as the PCB file.
  BOM_JLC.csv  - JLC-format BOM
  CPL_JLC.csv  - JLC-format placement file (mm)

ORDERING NOTES
  - 2-layer 1.6mm FR-4, rectangular outline. All components on TOP side.
  - Mixed SMD + THT on one side: choose Standard PCBA with through-hole
    assembly, or assemble SMD only and hand-solder the THT parts
    (electrolytics C2/C3/C15/C16, diode D2, fuse F1, buttons SW1-SW3,
    amp U3, terminal blocks J2-J4, and USB-C shell anchors).
  - Pre-filled LCSC numbers: U3 TDA7297 = C96009, J1 USB-C = C165948.
  - Fill/confirm in the JLC BOM matcher:
    * U2 PCM2704CDBR (search by MPN; verify stock - it is the heart of the board)
    * U1 LD1117S33TR, U4 CH221K, D2 P6KE16A (search by MPN)
    * D1 LED: Kingbright APA1606CGCK green side-view; if not stocked,
      any 1.6x0.6mm side-view green LED footprint-compatible part
    * SW1-3: C&K PTS645VL58-2 LFS right-angle tactile (verify stock;
      footprint fits the PTS645V series with 5.8mm actuator)
    * Y1: 12MHz crystal, 5032 2-pad, CL = 18pF
    * F1: Bourns MF-RG300 polyfuse; J2-J4: 5.08mm screw terminals
      (Phoenix MKDS 1,5/2 or compatible)
    * Generic 0805 R/C and radial electrolytics: accept JLC's basic-part
      auto-matches (electrolytics: 10uF and 470uF radial, 16V+)
  - U3 mounts vertically; NO heatsink at assembly (customer fits own).
  - Check the DFM/placement preview for rotations before confirming,
    especially U1/U2/U4 and the diode.
