#!/usr/bin/env python3
"""Sync Speaker Amp PCB to the V5 schematic netlist (run with KiCad's python).
usage: pcb_sync.py in.kicad_pcb netlist.xml out.kicad_pcb
New footprints are parked in a grid above the board; placement/routing is a later step."""
import sys, pcbnew
import xml.etree.ElementTree as ET

src, netxml, dst = sys.argv[1:4]
KFP = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/"
PRJFP = "/Users/lucaskrippendorff/Documents/Personal Projects/Speaker Project/Speaker Amp/footprints.pretty"
b = pcbnew.LoadBoard(src)
M = pcbnew.FromMM
P = lambda x, y: pcbnew.VECTOR2I(M(x), M(y))
root = ET.parse(netxml).getroot()

comps = {}
for c in root.iter("comp"):
    ref = c.get("ref")
    fp = c.findtext("footprint") or ""
    ts = c.find("tstamps")
    sp = c.find("sheetpath")
    comps[ref] = dict(value=c.findtext("value"), fp=fp, uuid=(ts.text.strip().split()[0] if ts is not None else ""),
                      fields={f.get("name"): (f.text or "") for f in c.iter("field")})
padnet = {}
for n in root.iter("net"):
    for node in n.iter("node"):
        padnet[(node.get("ref"), node.get("pin"))] = n.get("name")


def net(name):
    ni = b.FindNet(name)
    if ni is None:
        ni = pcbnew.NETINFO_ITEM(b, name)
        b.Add(ni)
    return ni


all_fps = list(b.GetFootprints())
all_tracks = list(b.GetTracks())
gone = set()
dead_nets = {"Net-(U4-PG)", "Net-(U4-VDD)", "Net-(U4-CFG)"}
mmxy = lambda v: (round(v.x / 1e6, 3), round(v.y / 1e6, 3))
# +12V copper that hung off F1 pad 2 (F1 now feeds VBUS_A, not +12V)
dead_12v = {((71.12, 36.83), (77.677, 36.83)), ((77.677, 36.83), (81.315, 40.468)), ((81.915, 37.61), (82.55, 36.975)),
            ((81.915, 40.055), (81.915, 37.61)), ((81.915, 40.055), (84.695, 40.055))}
for t in all_tracks:
    if t.GetNetname() in dead_nets:
        b.Remove(t); gone.add(id(t))
    elif t.GetNetname() == "/+12V" and t.GetClass() == "PCB_TRACK":
        k = (mmxy(t.GetStart()), mmxy(t.GetEnd()))
        if k in dead_12v or (k[1], k[0]) in dead_12v:
            b.Remove(t); gone.add(id(t))

# 2. renamed nets: move existing copper
for old, new in {"Net-(J1-CC1)": "/CC1_A", "Net-(J1-CC2)": "/CC2_A"}.items():
    nn = net(new)
    for t in all_tracks:
        if id(t) not in gone and t.GetNetname() == old:
            t.SetNet(nn)

# remove footprints no longer in the schematic (last, pcbnew invalidates containers on Remove)
for f in all_fps:
    r = f.GetReference()
    if r in ("U4", "R5", "R6") and f.GetValue() != "TL431":
        b.Remove(f)
        gone.add(id(f))
# 3. add new footprints, update values and pad nets everywhere
existing = {f.GetReference(): f for f in all_fps if id(f) not in gone and not f.GetReference().startswith("REF")}
park_i = 0
for ref, c in sorted(comps.items()):
    if ref.startswith("#"):
        continue
    f = existing.get(ref)
    if f is None:
        lib, name = c["fp"].split(":")
        f = pcbnew.FootprintLoad(PRJFP if lib == "SpeakerAmp" else KFP + lib + ".pretty", name)
        assert f is not None, c["fp"]
        f.SetFPID(pcbnew.LIB_ID(lib, name))
        f.SetReference(ref)
        b.Add(f)
        f.SetPosition(P(60 + (park_i % 12) * 9, -40 + (park_i // 12) * 9))
        park_i += 1
        f.SetPath(pcbnew.KIID_PATH("/" + c["uuid"]))
        f.SetSheetname("Root")
        f.SetSheetfile("Speaker Amp.kicad_sch")
    f.SetValue(c["value"])
    for p in f.Pads():
        nm = padnet.get((ref, p.GetNumber()))
        if nm:
            p.SetNet(net(nm))
        elif p.GetNumber():
            p.SetNetCode(0)
for ref in existing:
    assert ref in comps, f"{ref} on board but not in schematic"

b.Save(dst)
print("synced; parked", park_i, "new footprints")
