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
TOP, BOT, LEFT, RIGHT = -6.45, 83.0, 67.31, 113.69
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
for f, (x, y) in zip(holes, [(70.8, -3.0), (110.4, -3.0), (77.0, 80.0), (110.4, 80.0)]):
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



CX = 91.1
cell("A", CX, 22.25, "U6", "L1", "D5", "R35", "R36", "R37", "R38", "R39", "R40", "R41", "C22", "C23", "C24", "C25", "C26", "C27", "C28", "C29")
cell("B", CX, 3.25, "U7", "L2", "D6", "R42", "R43", "R44", "R45", "R46", "R47", "R48", "C30", "C31", "C32", "C33", "C34", "C35", "C36", "C37")
BX = CX + 10.5
place_at("C16", 99.695, 38.1, 0)
track("/+12V", [(BX, 3.25 + 1.6), (BX, 33.6), (99.9, 36.6), (99.695, 38.1)], 1.5)

# ------------------------------------------------------------------ USB-C inputs on the left edge
JROT = fps["J1"].GetOrientationDegrees()


def usb_in(J, jy, F_, D_, C_, vraw, vout, fy, dy, cxy):
    place_at(J, 69.85, jy, JROT)
    place_pads(F_, {vraw: (77.5, fy + 2.14), vout: (77.5, fy - 2.14)})
    place_pads(D_, {vraw: (77.5, dy - 2.15), "GND": (77.5, dy + 2.15)})
    place_pads(C_, {vraw: (cxy[0], cxy[1] - 0.91), "GND": (cxy[0], cxy[1] + 0.91)})
    ys = sorted({round(mm(p.GetPosition().y), 3) for p in fps[J].Pads() if p.GetNetname() == "/" + vraw})
    jx = [mm(p.GetPosition().x) for p in fps[J].Pads() if p.GetNetname() == "/" + vraw][0]
    track("/" + vraw, [(jx, ys[0]), (75.6, ys[0]), (76.4, fy + 2.4)], 0.6)
    track("/" + vraw, [(jx, ys[-1]), (76.6, ys[-1])], 0.6)
    track("/" + vraw, [(77.5, fy + 2.4), (77.5, dy - 2.6)], 1.2)
    track("/" + vraw, [(77.5, cxy[1] - 0.91), (cxy[0], cxy[1] - 0.91)], 0.5)


usb_in("J5", 18.0, "F2", "D4", "C21", "VBUSB_RAW", "VBUS_B", 12.5, 22.9, (79.25, 17.31))
track("/VBUS_B", [(77.9, 9.9), (79.6, 9.0), (82.0, 9.0)], 1.5)
place_pads("R33", {"CC1_B": (71.11, 25.2), "GND": (69.29, 25.2)})
place_pads("R34", {"CC2_B": (71.11, 27.3), "GND": (69.29, 27.3)})
usb_in("J1", 41.0, "F1", "D2", "C1", "VBUS_RAW", "VBUS_A", 37.2, 44.6, (80.9, 41.35))
track("/VBUS_A", [(78.6, 34.8), (79.9, 33.5), (81.2, 31.9), (82.125, 30.85)], 1.5)
place_pads("R3", {"CC1_A": (71.11, 47.5), "GND": (69.29, 47.5)})
place_pads("R4", {"CC2_A": (71.11, 49.6), "GND": (69.29, 49.6)})

# ------------------------------------------------------------------ CC sense block (right column)
SY = 6.2
place_at("U5", 108.2, 4.0 + SY, 0)
row = lambda refs, y: [place_at(r, x, y + SY, 0) for r, x in zip(refs, (105.3, 109.6))]
row(("R27", "R28"), -4.9); row(("R31", "R32"), -2.8)
row(("C19", "C20"), 9.9); row(("R25", "R29"), 11.9); row(("R26", "R30"), 13.9)
row(("R22", "R23"), 15.9); row(("R24", "C18"), 17.9)
place_at("U4", 105.6, 21.2 + SY, 0); place_at("D3", 110.2, 21.2 + SY, 0); place_at("R21", 105.3, 24.4 + SY, 0)

# ------------------------------------------------------------------ 3.3 V regulator
place_at("U1", 88.0, 43.6, -90)
place_at("C2", 83.9, 37.2, 90)
place_at("C3", 89.9, 37.2, 90)

# ------------------------------------------------------------------ amplifier, bulk cap, terminals (right side)
place_at("U3", 102.3, 62.9, 90)
for r, y in (("J3", 50.0), ("J2", 58.9), ("J4", 67.8)):
    place_at(r, 107.72, y, 90)
place_at("C17", 94.3, 65.5, 0); place_at("R18", 97.9, 65.5, 0); place_at("R19", 101.5, 65.5, 0)
place_at("C15", 99.4, 71.2, 90)

# ------------------------------------------------------------------ USB DAC
place_at("U2", 84.0, 60.0, 0)
place_at("Y1", 84.0, 52.3, 0); place_at("C10", 80.0, 52.3, 0); place_at("C9", 88.0, 52.3, 0); place_at("R7", 84.0, 49.4, 0)
for r, y in (("C4", 57.4), ("R1", 59.5), ("R2", 61.6), ("R8", 63.7), ("C5", 65.8)):
    place_at(r, 77.2, y, 0)
for r, y in (("C8", 59.4), ("C7", 61.5), ("C6", 63.6)):
    place_at(r, 90.55, y, 0)
for r, x in (("R13", 80.9), ("C11", 84.5), ("R12", 88.1), ("C12", 91.7)):
    place_at(r, x, 67.6, 0)
for r, x in (("R15", 80.9), ("R16", 84.5), ("R14", 88.1), ("R17", 91.7)):
    place_at(r, x, 69.7, 0)
place_at("C14", 82.7, 71.8, 0); place_at("C13", 89.9, 71.8, 0)

# ------------------------------------------------------------------ buttons, pull-downs, power LED
for sw, y in (("SW1", 56.5), ("SW2", 66.2), ("SW3", 75.9)):
    place_at(sw, 70.5, y, 90)
place_at("R9", 77.3, 73.6, 0); place_at("R10", 77.3, 75.7, 0); place_at("R11", 81.0, 74.6, 0)
place_at("D1", 86.5, 77.5, 0)
place_at("R20", 82.5, 77.5, 0)

b.Save(dst)
print("fresh layout written")
