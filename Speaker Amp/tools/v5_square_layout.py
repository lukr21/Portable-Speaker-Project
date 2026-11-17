#!/usr/bin/env python3
"""From-scratch layout of the Speaker Amp V5 (run with KiCad's python).
usage: fresh_layout.py stripped.kicad_pcb out.kicad_pcb   (input: synced board with all tracks removed)
Extends the board upward, places the two TPS61376 boost cells, port B input and the
CC-sense block, and routes the high-current / noise-critical copper. Low-current
signal nets are left for the autorouter."""
import sys, pcbnew

src, dst = sys.argv[1:3]
b = pcbnew.LoadBoard(src)
M = pcbnew.FromMM
P = lambda x, y: pcbnew.VECTOR2I(M(x), M(y))
mm = lambda v: v / 1e6
TOP, BOT, LEFT, RIGHT = -6.45, 57.0, 52.0, 114.0
fps = {f.GetReference(): f for f in b.GetFootprints()}
F, B = pcbnew.F_Cu, pcbnew.B_Cu


def net(name):
    n = b.FindNet(name)
    assert n is not None, name
    return n


def track(netname, pts, w, layer=F):
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(P(x1, y1)); t.SetEnd(P(x2, y2)); t.SetWidth(M(w)); t.SetLayer(layer); t.SetNet(net(netname))
        b.Add(t)


def via(netname, x, y, dia=0.6, drill=0.3):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(P(x, y)); v.SetWidth(F, M(dia)) if v.SetWidth.__code__.co_argcount > 2 else v.SetWidth(M(dia))
    v.SetDrill(M(drill)); v.SetNet(net(netname)); v.SetLayerPair(F, B)
    b.Add(v)


def place_at(ref, x, y, rot):
    f = fps[ref]
    f.SetOrientationDegrees(rot)
    f.SetPosition(P(x, y))


def place_pads(ref, targets, tol=0.06):
    """targets: {netname or pad number: (x, y)}; find orientation+position so pads land on targets."""
    f = fps[ref]
    def key(p):
        return p.GetNumber() if p.GetNumber() in targets else p.GetNetname().lstrip("/")
    for rot in (0, 90, 180, 270):
        f.SetOrientationDegrees(rot)
        f.SetPosition(P(0, 0))
        pads = [p for p in f.Pads() if key(p) in targets]
        cxp = sum(mm(p.GetPosition().x) for p in pads) / len(pads); cyp = sum(mm(p.GetPosition().y) for p in pads) / len(pads)
        ctx = sum(targets[key(p)][0] for p in pads) / len(pads); cty = sum(targets[key(p)][1] for p in pads) / len(pads)
        f.SetPosition(P(ctx - cxp, cty - cyp))
        if all(abs(mm(p.GetPosition().x) - targets[key(p)][0]) < 0.2 and abs(mm(p.GetPosition().y) - targets[key(p)][1]) < 0.2 for p in pads):
            return
    raise SystemExit(f"cannot place {ref} on {targets}")



# ------------------------------------------------------------------ start clean: no copper from the old layout
drawings = list(b.GetDrawings()); zones = list(b.Zones()); allfps = list(b.GetFootprints())

# ------------------------------------------------------------------ outline, ground zone (both layers), mounting holes
for d in drawings:
    if d.GetLayerName() == "Edge.Cuts":
        ps = d.GetPolyShape(); ps.RemoveAllContours(); ps.NewOutline()
        for x, y in [(LEFT, TOP), (RIGHT, TOP), (RIGHT, BOT), (LEFT, BOT)]:
            ps.Append(M(x), M(y))
for z in zones:
    o = z.Outline(); o.RemoveAllContours(); o.NewOutline()
    for x, y in [(LEFT + 0.4, TOP + 0.4), (RIGHT - 0.4, TOP + 0.4), (RIGHT - 0.4, BOT - 0.4), (LEFT + 0.4, BOT - 0.4)]:
        o.Append(M(x), M(y))
holes = [f for f in allfps if f.GetReference().startswith("REF")]
for f, (x, y) in zip(holes, [(55.3, -3.2), (110.6, -3.2), (55.3, 53.6), (110.6, 53.6)]):
    f.SetPosition(P(x, y))

def cell(pfx, cx, cy, U, L, D, Rtop, Rbot, Rilim, Rhigh, Rc, Rfbt, Rfbb, Cin, Cvin, Cen, Cc, Cvcc, Cboot, Cout1, Cout2):
    G = lambda lx, ly: (cx + ly, cy - lx)          # rotate local frame: local up -> board left
    N = lambda n: {"VBUS": f"/VBUS_{pfx}", "+12V": "/+12V", "GND": "GND"}.get(n, f"/{n}_{pfx}")
    def pp(ref, tg):
        place_pads(ref, {N(k).lstrip("/"): G(*v) for k, v in tg.items()})
    def T(n, pts, w):
        track(N(n), [G(*p) for p in pts], w)
    def V(n, lx, ly):
        via(N(n), *G(lx, ly))
    f = fps[U]
    for rot in (0, 90, 180, 270):
        f.SetOrientationDegrees(rot); f.SetPosition(P(cx, cy))
        p13 = [p for p in f.Pads() if p.GetNumber() == "13"][0]
        gx, gy = G(-0.5, -0.9375)
        if abs(mm(p13.GetPosition().x) - gx) < 0.05 and abs(mm(p13.GetPosition().y) - gy) < 0.05:
            break
    else:
        raise SystemExit("IC orientation")
    pp(Cboot, {"BOOT": (-1.86, -3.0), "SW": (-0.04, -3.0)})
    pp(L, {"VBUS": (-5.75, -7.7), "SW": (0.3, -7.7)})
    pp(Cvin, {"VBUS": (-5.51, -2.2), "GND": (-3.69, -2.2)})
    pp(Cin, {"VBUS": (-8.6, -8.975), "GND": (-8.6, -6.025)})
    pp(Rtop, {"VBUS": (-7.3, -2.075), "EN": (-7.3, -0.25)})
    pp(Rbot, {"EN": (-7.3, 1.39), "GND": (-7.3, 3.21)})
    pp(Cen, {"EN": (-9.4, 1.39), "GND": (-9.4, 3.21)})
    pp(Cvcc, {"VCC": (1.6, -2.6), "GND": (3.425, -2.6)})
    pp(Rhigh, {"ILIM": (5.9, -2.4), "HIGH": (7.73, -2.4)})
    pp(Rilim, {"ILIM": (5.9, -0.4), "GND": (7.73, -0.4)})
    pp(Rc, {"COMP": (5.9, 1.6), "CZ": (7.73, 1.6)})
    pp(Cc, {"GND": (5.9, 3.6), "CZ": (7.73, 3.6)})
    pp(Rfbb, {"GND": (4.1, 2.6), "FB": (4.1, 4.42)})
    pp(Rfbt, {"FB": (4.1, 6.2), "+12V": (4.1, 8.02)})
    pp(D, {"VP": (-1.6, 3.3), "+12V": (-1.6, 7.3)})
    pp(Cout1, {"GND": (1.6, 3.6), "+12V": (1.6, 6.55)})
    pp(Cout2, {"GND": (-4.9, 4.35), "+12V": (-4.9, 7.3)})
    # switch node, bootstrap
    T("SW", [(0, -1.1), (0, -2.4)], 0.25)
    T("SW", [(0, -2.7), (0, -6.2)], 0.8)
    T("BOOT", [(-0.5, -1.1), (-0.5, -1.65), (-1.5, -2.5), (-1.86, -3.0)], 0.2)
    T("VCC", [(1.03, -1.1), (1.03, -1.6), (1.5, -2.2)], 0.2)
    T("GND", [(0.5, -0.8), (0.5, 0.0)], 0.2)                                   # AGND to PGND under the IC
    # input side
    T("VBUS", [(-1.3, -0.75), (-5.51, -0.75), (-5.51, -1.7)], 0.25)
    T("VBUS", [(-7.3, -2.075), (-5.51, -2.2)], 0.3)
    T("VBUS", [(-5.6, -2.6), (-5.6, -6.2)], 0.5)
    T("VBUS", [(-8.6, -8.975), (-6.0, -8.975)], 1.2)
    T("EN", [(-1.3, -0.25), (-7.3, -0.25)], 0.2)
    T("EN", [(-7.3, -0.25), (-7.3, 1.39), (-9.4, 1.39)], 0.25)
    T("ISEL", [(-1.3, 0.25), (-4.2, 0.25), (-4.6, 0.6)], 0.2)
    V("ISEL", -4.6, 0.6)
    # output side
    T("+12V", [(-1.3, 0.75), (-2.6, 0.75), (-3.3, 1.45), (-3.3, 7.3), (-1.6, 7.3)], 0.3)
    T("+12V", [(-4.9, 7.3), (-1.6, 7.3)], 1.0)
    T("+12V", [(-1.6, 6.9), (1.6, 6.9)], 1.0)
    T("+12V", [(1.6, 6.9), (2.7, 8.02), (4.1, 8.02)], 0.4)
    T("+12V", [(-1.6, 7.6), (-1.6, 10.5)], 1.5)                               # out to the +12V bus
    T("VP", [(-0.5, 1.1), (-0.5, 1.9)], 0.25)
    T("VP", [(-0.5, 1.9), (-1.0, 2.4), (-1.3, 2.9)], 0.6)
    T("GND", [(0.5, 1.1), (0.5, 1.9)], 0.25)
    T("GND", [(0.5, 1.9), (1.2, 2.6), (1.6, 3.3)], 0.6)
    T("GND", [(1.6, 3.6), (1.6, 5.05)], 0.6)
    V("GND", 1.6, 5.05)
    # feedback, compensation, current-limit set
    T("FB", [(1.3, 0.75), (1.9, 0.75), (2.95, 1.8), (2.95, 5.31), (4.1, 5.31)], 0.2)
    T("FB", [(4.1, 4.42), (4.1, 6.2)], 0.25)
    T("COMP", [(1.3, 0.25), (4.4, 0.25), (5.2, 1.05), (5.2, 1.4), (5.9, 1.6)], 0.2)
    T("ILIM", [(1.3, -0.25), (5.0, -0.25), (5.9, -0.4)], 0.2)
    T("ILIM", [(5.9, -0.4), (5.9, -2.4)], 0.25)
    T("CZ", [(7.73, 1.6), (7.73, 3.6)], 0.25)
    # ground stitching to the bottom plane
    T("GND", [(-3.69, -2.2), (-3.3, -3.5)], 0.4); V("GND", -3.3, -3.6)
    T("GND", [(-8.6, -6.025), (-8.6, -4.6)], 0.5); V("GND", -8.6, -4.5)
    T("GND", [(3.425, -2.6), (3.425, -3.7)], 0.4); V("GND", 3.425, -3.8)
    T("GND", [(-4.9, 4.35), (-4.9, 3.1)], 0.5); V("GND", -4.9, 3.0)
    T("GND", [(7.73, -0.4), (8.6, -0.4)], 0.3); V("GND", 8.7, -0.4)



CX = 80.25
cell("A", CX, 22.25, "U6", "L1", "D5", "R35", "R36", "R37", "R38", "R39", "R40", "R41", "C22", "C23", "C24", "C25", "C26", "C27", "C28", "C29")
cell("B", CX, 3.25, "U7", "L2", "D6", "R42", "R43", "R44", "R45", "R46", "R47", "R48", "C30", "C31", "C32", "C33", "C34", "C35", "C36", "C37")
BX = CX + 10.5
place_at("C16", 92.5, 39.5, 0)
track("/+12V", [(BX, 3.25 + 1.6), (BX, 37.6), (92.5, 39.5)], 1.5)

# ------------------------------------------------------------------ left edge: buttons on top, then the two USB-C ports
JROT = fps["J1"].GetOrientationDegrees()
JX, SWX = LEFT + 2.54, LEFT + 3.19
for sw, y in (("SW1", 4.6), ("SW2", 14.25), ("SW3", 23.9)):
    place_at(sw, SWX, y, 90)


def usb_in(J, jy, F_, D_, vraw, vout, col, fy, dy):
    """connector on the edge; fuse above TVS in one column. Fuse top pad = switched output."""
    place_at(J, JX, jy, JROT)
    place_pads(F_, {vout: (col, fy - 2.14), vraw: (col, fy + 2.14)})
    place_pads(D_, {vraw: (col, dy - 2.15), "GND": (col, dy + 2.15)})
    ys = sorted({round(mm(p.GetPosition().y), 3) for p in fps[J].Pads() if p.GetNetname() == "/" + vraw})
    jx = [mm(p.GetPosition().x) for p in fps[J].Pads() if p.GetNetname() == "/" + vraw][0]
    track("/" + vraw, [(jx, ys[0]), (col - 2.4, ys[0]), (col - 1.2, fy + 2.3)], 0.6)
    track("/" + vraw, [(jx, ys[-1]), (col - 2.4, ys[-1]), (col - 1.0, dy - 2.2)], 0.6)
    track("/" + vraw, [(col, fy + 2.5), (col, dy - 2.6)], 1.2)


usb_in("J5", 34.1, "F2", "D4", "VBUSB_RAW", "VBUS_B", 62.2, 30.0, 36.9)
usb_in("J1", 44.9, "F1", "D2", "VBUS_RAW", "VBUS_A", 66.8, 40.8, 47.7)
track("/VBUS_B", [(63.2, 27.86), (67.5, 27.86), (68.4, 26.96), (68.4, 13.3), (69.7, 12.0), (71.275, 11.85)], 1.5)
track("/VBUS_A", [(67.9, 38.4), (68.9, 37.4), (68.9, 32.9), (70.1, 31.7), (71.275, 30.85)], 1.5)
place_pads("C21", {"VBUSB_RAW": (65.6, 32.45), "GND": (65.6, 34.35)})
track("/VBUSB_RAW", [(63.6, 32.14), (65.6, 32.45)], 0.5)
place_pads("C1", {"VBUS_RAW": (62.5, 42.45), "GND": (62.5, 44.35)})
place_at("R33", 61.35, 25.95, 0); place_at("R34", 64.85, 25.95, 0)
place_at("R3", 62.2, 49.6, 0); place_at("R4", 62.2, 51.7, 0)

# ------------------------------------------------------------------ 3.3 V regulator and power LED (between the buttons and the converters)
place_at("U1", 63.3, 20.4, -90)
place_at("C2", 63.3, 13.9, 90)
place_at("C3", 63.3, 8.2, 90)
place_at("D1", 62.0, 0.3, 0)
place_at("R20", 63.0, -4.6, 0)

# ------------------------------------------------------------------ CC sense block (right of the +12 V bus)
place_at("U5", 97.35, 4.0, 0)
row = lambda refs, y: [place_at(r, x, y, 0) for r, x in zip(refs, (94.45, 98.75))]
row(("R27", "R28"), -4.9); row(("R31", "R32"), -2.8)
row(("C19", "C20"), 9.9); row(("R25", "R29"), 11.9); row(("R26", "R30"), 13.9)
row(("R22", "R23"), 15.9); row(("R24", "C18"), 17.9)
place_at("U4", 94.75, 21.2, 0); place_at("D3", 99.35, 21.2, 0); place_at("R21", 94.45, 24.4, 0)

# ------------------------------------------------------------------ right edge: terminals on top, amplifier below
JTX = RIGHT - 5.97
for r, y in (("J4", 8.0), ("J2", 16.9), ("J3", 25.8)):
    place_at(r, JTX, y, 90)
place_at("U3", 112.3, 49.0, 90)
place_at("C17", 92.5, 46.6, 0); place_at("R18", 96.1, 46.6, 0); place_at("R19", 99.7, 46.6, 0)
place_at("C15", 97.0, 53.3, 90)

# ------------------------------------------------------------------ USB DAC along the bottom
DX = 77.6
place_at("U2", DX, 47.0, 0)
place_at("Y1", DX, 39.3, 0); place_at("C10", DX - 4.0, 39.3, 0); place_at("C9", DX + 4.0, 39.3, 0); place_at("R7", DX, 36.4, 0)
for r, y in (("C4", 44.4), ("R1", 46.5), ("R2", 48.6), ("R8", 50.7), ("C5", 52.8)):
    place_at(r, DX - 6.6, y, 0)
for r, y in (("C8", 46.4), ("C7", 48.5), ("C6", 50.6)):
    place_at(r, DX + 6.55, y, 0)
for r, x in (("R13", 74.6), ("C11", 78.2), ("R15", 81.8), ("R16", 85.4), ("C14", 89.0)):
    place_at(r, x, 54.5, 0)
for r, y in (("R12", 45.9), ("C12", 47.9), ("R14", 49.9), ("R17", 51.9)):
    place_at(r, DX + 10.3, y, 0)
place_at("C13", 91.5, 49.9, 0)
# button pull-downs sit between the crystal and the bulk capacitor
place_at("R9", 84.9, 36.0, 90); place_at("R10", 87.0, 36.0, 90); place_at("R11", 84.9, 40.2, 90)

b.Save(dst)
print("fresh layout written")
