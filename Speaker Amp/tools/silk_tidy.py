#!/usr/bin/env python3
"""Tidy silkscreen reference designators (run with KiCad's python).
usage: silk_tidy.py in.kicad_pcb out.kicad_pcb
Each reference is shrunk and moved to the first spot beside its part that does not
touch another part's courtyard, a pad, a hole, another label or the board edge."""
import sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1])
mm = lambda v: v / 1e6
M = pcbnew.FromMM
H, TH = 0.8, 0.12
fps = list(b.GetFootprints())
bb = b.GetBoardEdgesBoundingBox()
EDGE = (mm(bb.GetLeft()) + 0.6, mm(bb.GetTop()) + 0.6, mm(bb.GetRight()) - 0.6, mm(bb.GetBottom()) - 0.6)


def box(r):
    return (mm(r.GetLeft()), mm(r.GetTop()), mm(r.GetRight()), mm(r.GetBottom()))


def hit(a, c, m=0.0):
    return a[0] < c[2] + m and a[2] > c[0] - m and a[1] < c[3] + m and a[3] > c[1] - m


obst = {}          # per side: list of (ref, box)
for f in fps:
    side = "B" if f.IsFlipped() else "F"
    cy = f.GetCourtyard(pcbnew.B_CrtYd if side == "B" else pcbnew.F_CrtYd)
    if cy.OutlineCount():
        obst.setdefault(side, []).append((f.GetReference() + str(id(f)), box(cy.BBox())))
    for p in f.Pads():
        for s, l in (("F", pcbnew.F_Mask), ("B", pcbnew.B_Mask)):
            if p.IsOnLayer(l) or p.HasHole():
                obst.setdefault(s, []).append(("pad", box(p.GetBoundingBox())))
placed = {"F": [], "B": []}
hidden = []
for f in sorted(fps, key=lambda f: -f.GetCourtyard(pcbnew.F_CrtYd).BBox().GetWidth() * f.GetCourtyard(pcbnew.F_CrtYd).BBox().GetHeight()):
    ref = f.Reference()
    val = f.Value()
    if val.GetLayerName().endswith("SilkS") or val.GetLayerName().endswith("Silkscreen"):
        val.SetVisible(False)
    name = f.GetReference()
    if name.startswith("REF"):
        ref.SetVisible(False)
        continue
    side = "B" if f.IsFlipped() else "F"
    cyl = f.GetCourtyard(pcbnew.B_CrtYd if side == "B" else pcbnew.F_CrtYd)
    c = box(cyl.BBox()) if cyl.OutlineCount() else box(f.GetBoundingBox(False))
    me = name + str(id(f))
    w = len(name) * H * 0.9 + 0.2
    cx, cyy = (c[0] + c[2]) / 2, (c[1] + c[3]) / 2
    cands = []
    for rot, tw, th in ((0, w, H + 0.2), (90, H + 0.2, w)):
        g = 0.15
        cands += [(cx, c[1] - th / 2 - g, rot, tw, th), (cx, c[3] + th / 2 + g, rot, tw, th),
                  (c[2] + tw / 2 + g, cyy, rot, tw, th), (c[0] - tw / 2 - g, cyy, rot, tw, th),
                  (c[0] + tw / 2, c[1] - th / 2 - g, rot, tw, th), (c[2] - tw / 2, c[1] - th / 2 - g, rot, tw, th),
                  (c[0] + tw / 2, c[3] + th / 2 + g, rot, tw, th), (c[2] - tw / 2, c[3] + th / 2 + g, rot, tw, th)]
    done = False
    for x, y, rot, tw, th in cands:
        t = (x - tw / 2, y - th / 2, x + tw / 2, y + th / 2)
        if t[0] < EDGE[0] or t[1] < EDGE[1] or t[2] > EDGE[2] or t[3] > EDGE[3]:
            continue
        if any(hit(t, o) for r_, o in obst.get(side, []) if r_ != me) or any(hit(t, o, 0.1) for o in placed[side]):
            continue
        ref.SetTextSize(pcbnew.VECTOR2I(M(H), M(H))); ref.SetTextThickness(M(TH))
        ref.SetPosition(pcbnew.VECTOR2I(M(x), M(y))); ref.SetTextAngleDegrees(rot)
        ref.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER); ref.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
        ref.SetVisible(True); ref.SetKeepUpright(True)
        placed[side].append(t); done = True
        break
    if not done:
        big = (c[2] - c[0]) * (c[3] - c[1]) > 30
        if big:        # large part: label sits on the body outline area (readable before assembly)
            ref.SetTextSize(pcbnew.VECTOR2I(M(H), M(H))); ref.SetTextThickness(M(TH))
            ref.SetPosition(pcbnew.VECTOR2I(M(cx), M(cyy))); ref.SetTextAngleDegrees(0); ref.SetVisible(True)
        else:
            ref.SetVisible(False); hidden.append(name)
b.Save(sys.argv[2])
print("hidden refs:", ",".join(sorted(hidden)) or "none")
