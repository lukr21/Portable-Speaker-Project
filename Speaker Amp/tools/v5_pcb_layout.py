#!/usr/bin/env python3
"""Place and hand-route the V5 power section of the Speaker Amp (run with KiCad's python).
usage: pcb_layout.py synced.kicad_pcb out.kicad_pcb
Extends the board upward, places the two TPS61376 boost cells, port B input and the
CC-sense block, and routes the high-current / noise-critical copper. Low-current
signal nets are left for the autorouter."""
import sys, pcbnew

src, dst = sys.argv[1:3]
b = pcbnew.LoadBoard(src)
M = pcbnew.FromMM
P = lambda x, y: pcbnew.VECTOR2I(M(x), M(y))
mm = lambda v: v / 1e6
TOP = -6.45                      # new top edge (was 28.55)
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


# ------------------------------------------------------------------ outline and zones
for d in b.GetDrawings():
    if d.GetLayerName() == "Edge.Cuts":
        ps = d.GetPolyShape()
        o = ps.Outline(0)
        for i in range(o.PointCount()):
            v = o.CPoint(i)
            if abs(mm(v.y) - 28.55) < 0.3:
                o.SetPoint(i, pcbnew.VECTOR2I(v.x, M(TOP)))
for z in b.Zones():
    o = z.Outline().Outline(0)
    for i in range(o.PointCount()):
        v = o.CPoint(i)
        if abs(mm(v.y) - 32.135) < 0.01:
            o.SetPoint(i, pcbnew.VECTOR2I(v.x, M(TOP + 0.4)))
    z.SetNeedRefill(True) if hasattr(z, "SetNeedRefill") else None
# (the existing GND zone already covers both copper layers, so the extension gets a bottom plane too)

# ------------------------------------------------------------------ fixes around the old PD-trigger area
track("/+12V", [(82.55, 36.975), (84.695, 39.1), (84.695, 40.055)], 1.0)          # C2 -> U1 VIN (used to go via F1 pad)
track("/+12V", [(71.12, 36.83), (82.55, 36.975)], 0.3, B)                          # power LED anode -> +12V at C2
track("/VBUS_A", [(80.7, 40.3), (79.9, 39.5), (79.9, 33.2), (81.2, 31.9), (82.125, 30.85)], 1.5)   # F1 out -> boost A input

# ------------------------------------------------------------------ boost cell (local frame: IC at origin, inductor up, diode down)
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
# +12V bus down the right side of the cells to the bulk capacitor
BX = CX + 10.5
track("/+12V", [(BX, 3.25 + 1.6), (BX, 33.6), (99.9, 36.6), (99.695, 38.1)], 1.5)

# ------------------------------------------------------------------ port B input (left column)
j1 = fps["J1"]
place_at("J5", 69.85, 18.0, j1.GetOrientationDegrees())
place_pads("F2", {"VBUSB_RAW": (77.5, 14.64), "VBUS_B": (77.5, 10.36)})
place_pads("D4", {"VBUSB_RAW": (77.5, 20.75), "GND": (77.5, 25.05)})
place_pads("C21", {"VBUSB_RAW": (79.25, 16.4), "GND": (79.25, 18.22)})
place_pads("R33", {"CC1_B": (71.11, 25.2), "GND": (69.29, 25.2)})
place_pads("R34", {"CC2_B": (71.11, 27.3), "GND": (69.29, 27.3)})
jp = {p.GetNumber(): (mm(p.GetPosition().x), mm(p.GetPosition().y)) for p in fps["J5"].Pads() if p.GetNetname() == "/VBUSB_RAW"}
ys = sorted({round(v[1], 3) for v in jp.values()})
jx = list(jp.values())[0][0]
track("/VBUSB_RAW", [(jx, ys[0]), (75.6, ys[0]), (76.4, 14.9)], 0.6)
track("/VBUSB_RAW", [(jx, ys[-1]), (76.6, ys[-1])], 0.6)
track("/VBUSB_RAW", [(77.5, 14.9), (77.5, 20.3)], 1.2)
track("/VBUSB_RAW", [(77.5, 16.4), (79.25, 16.4)], 0.5)
track("/VBUS_B", [(77.9, 9.9), (79.6, 9.0), (82.0, 9.0)], 1.5)                    # fuse out -> boost B inductor

# ------------------------------------------------------------------ CC sense block (right column)
place_at("U5", 108.2, 4.0, 0)
row = lambda refs, y: [place_at(r, x, y, 0) for r, x in zip(refs, (105.3, 109.6))]
row(("R27", "R28"), -4.9)
row(("R31", "R32"), -2.8)
row(("C19", "C20"), 9.9)
row(("R25", "R29"), 11.9)
row(("R26", "R30"), 13.9)
row(("R22", "R23"), 15.9)
row(("R24", "C18"), 17.9)
place_at("U4", 105.6, 21.2, 0)
place_at("D3", 110.2, 21.2, 0)
place_at("R21", 105.3, 24.4, 0)

for t in b.GetTracks():
    t.SetLocked(True)                 # everything routed so far is fixed for the autorouter
b.Save(dst)
print("layout written")
