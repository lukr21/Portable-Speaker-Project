#!/bin/zsh
# Rebuild the square amp board from the stripped, synced board: place, route, stitch, finish.
S=$1; cd $S/fresh
PY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
K=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
REPO="/Users/lucaskrippendorff/Documents/Personal Projects/Speaker Project"
fixpro(){ cp "$REPO/Speaker Amp/Speaker Amp.kicad_pro" "Speaker Amp.kicad_pro"; sed -i '' 's/"min_resolved_spokes": 2/"min_resolved_spokes": 1/' "Speaker Amp.kicad_pro"; }
drc(){ fixpro; $K pcb drc --refill-zones --save-board --schematic-parity --severity-error -o drc.rpt "Speaker Amp.kicad_pcb" 2>/dev/null | grep Found | tr '\n' ' '; echo; fixpro; }
step(){ r=$1; shift; cp "Speaker Amp.kicad_pcb" in.kicad_pcb; $PY $S/pcb_route.py in.kicad_pcb $r "Speaker Amp.kicad_pcb" "$@" 2>/dev/null | grep -E "routed|FAILED|STITCH F"; drc; }
$PY $S/fresh_layout.py stripped.kicad_pcb "Speaker Amp.kicad_pcb" 2>/dev/null | tail -1
drc
$PY - 2>/dev/null <<'PYEOF'
import pcbnew
b=pcbnew.LoadBoard("Speaker Amp.kicad_pcb")
out=[]
for ref in ("U2","U5"):
    for p in b.FindFootprintByReference(ref).Pads():
        if p.GetNetname()=="GND":
            c=p.GetPosition()
            out.append("[unconnected_items]: pre-stitch\n    x\n    @(%.4f mm, %.4f mm): Pad %s [GND] of %s on F.Cu\n    @(0.0000 mm, 0.0000 mm): Zone [GND]\n"%(c.x/1e6,c.y/1e6,p.GetNumber(),ref))
open("prestitch.rpt","w").write("".join(out))
PYEOF
step drc.rpt 0.25 "" "Net-(U3A-MUTE)"
step prestitch.rpt 0.25
step drc.rpt 1.0 "" "/+12V,/OUT_L+,/OUT_L-,/OUT_R+,/OUT_R-"
step drc.rpt 0.4 "" "/+3.3V,/VBUS_A,/VBUS_B,/VBUS_RAW,/VBUSB_RAW"
step drc.rpt 0.2
step drc.rpt 0.2
for i in 1 2 3; do
  $PY $S/islands.py "Speaker Amp.kicad_pcb" isl.rpt >/dev/null 2>&1
  cat drc.rpt isl.rpt > both.rpt
  step both.rpt 0.4
  grep -q "^\[" drc.rpt || break
done
cp "Speaker Amp.kicad_pcb" routed.kicad_pcb
$PY - 2>/dev/null <<'PYEOF'
import pcbnew
b=pcbnew.LoadBoard("routed.kicad_pcb")
for p in b.FindFootprintByReference("U3").Pads():
    if p.GetNumber() in ("8","9"): p.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
j1=b.FindFootprintByReference("J1"); j5=b.FindFootprintByReference("J5")
m5=j5.Models()
while len(m5)>0: m5.pop()
for m in j1.Models(): m5.append(m)
b.Save("Speaker Amp.kicad_pcb")
PYEOF
drc
grep "^\[" drc.rpt | sort | uniq -c
grep -A3 "^\[unconnected" drc.rpt | grep "@" | grep -v Zone | head
