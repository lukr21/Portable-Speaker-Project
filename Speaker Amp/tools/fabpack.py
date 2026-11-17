#!/usr/bin/env python3
"""Build a JLCPCB package (gerbers.zip, BOM_JLC.csv, CPL_JLC.csv) from a KiCad board.
usage: fabpack.py <project dir> <board file name> <schematic file name> <out dir> <gerber prefix>"""
import sys, os, subprocess, csv, zipfile, glob, re, shutil, tempfile
import xml.etree.ElementTree as ET
proj, pcb, sch, out, prefix = sys.argv[1:6]
K = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
os.makedirs(out, exist_ok=True)
tmp = tempfile.mkdtemp()
run = lambda *a: subprocess.run([K, *a], cwd=proj, capture_output=True, text=True)
LAYERS = "F.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts"
r = run("pcb", "export", "gerbers", "-o", tmp + "/", "--layers", LAYERS, "--subtract-soldermask", pcb); assert r.returncode == 0, r.stderr
r = run("pcb", "export", "drill", "-o", tmp + "/", "--format", "excellon", "--drill-origin", "absolute", "--excellon-units", "mm", pcb); assert r.returncode == 0, r.stderr
base = os.path.splitext(pcb)[0]
with zipfile.ZipFile(os.path.join(out, "gerbers.zip"), "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(glob.glob(tmp + "/*")):
        z.write(f, os.path.basename(f).replace(base, prefix))
# ---- BOM from the schematic netlist
r = run("sch", "export", "netlist", "--format", "kicadxml", "-o", tmp + "/n.xml", sch); assert r.returncode == 0, r.stderr
LCSC = {  # value/footprint -> JLC part, where the schematic carries none
    ("SMBJ15A", "D_SMB"): "C19077569", ("Polyfuse", "Fuse_1812_4532Metric"): "C702820",
    ("USB_C_Receptacle_USB2.0_16P", "USB_C_Receptacle_HRO_TYPE-C-31-M-12"): "C165948", ("SW_Push", "SW_TS-1005B_2PinMapped"): "C2856783",
    ("AMS1117-3.3", "SOT-223-3_TabPin2"): "C6186", ("TDA7297", None): "C96009", ("12M", "Crystal_SMD_3225_2PinMapped"): "C9002",
    ("PCM2704CDBR", None): "C2859784", ("22u 25V", "C_1206_3216Metric"): "C12891", ("4.7u", "C_0805_2012Metric"): "C1746",
    ("470n", "C_0805_2012Metric"): "C123623", ("22n", "C_0805_2012Metric"): "C1729", ("93.1k", None): "C2933511", ("88.7k", None): "C5121549",
    ("80.6k", None): "C2960781", ("30.9k", None): "C2933411", ("30k", "R_0805_2012Metric"): "C17621", ("1M", "R_0805_2012Metric"): "C17514",
    ("220k", "R_0805_2012Metric"): "C17556", ("56k", "R_0805_2012Metric"): "C17756", ("10M", "R_0805_2012Metric"): "C2933281",
    ("18k", "R_0805_2012Metric"): "C2907231", ("3k", "R_0805_2012Metric"): "C17661", ("680", "R_0805_2012Metric"): "C17798",
    ("47k", "R_0805_2012Metric"): "C17713", ("47k", "R_0603_1608Metric"): "C25819", ("100k", "R_0805_2012Metric"): "C149504",
    ("3.3k", "R_0805_2012Metric"): "C26010", ("LM339", None): "C7948", ("TL431", None): "C181103", ("BAT54C", None): "C22466350",
    ("SS34", None): "C7420365", ("4.7u", "L_Changjiang_FXL0630"): "C167220", ("TPS61376", None): "C7073367",
    ("10u 25V", "C_0805_2012Metric"): "C15850", ("100n", "C_0805_2012Metric"): "C49678",
    ("D_Schottky", "D_SOD-123"): "C8598", ("MMBT3904", "SOT-23"): "C20526", ("LM358", None): "C7950",
}
groups = {}
key = lambda r: (re.match(r"[A-Za-z#]+", r).group(0), int(re.search(r"\d+", r).group(0)))
for c in ET.parse(tmp + "/n.xml").getroot().iter("comp"):
    ref = c.get("ref"); val = c.findtext("value"); fp = (c.findtext("footprint") or "").split(":")[-1]
    l = ""
    for f in c.iter("field"):
        if f.get("name") in ("LCSC Part", "LCSC", "LCSC Part #") and (f.text or "").strip():
            l = f.text.strip()
    l = LCSC.get((val, fp)) or LCSC.get((val, None)) or l
    groups.setdefault((val, fp, l), []).append(ref)
rows = sorted(((sorted(refs, key=key), val, fp, l) for (val, fp, l), refs in groups.items()), key=lambda r: key(r[0][0]))
with open(os.path.join(out, "BOM_JLC.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
    for refs, val, fp, l in rows:
        w.writerow([val, ",".join(refs), fp, l])
# ---- placement
r = run("pcb", "export", "pos", "-o", tmp + "/pos.csv", "--format", "csv", "--units", "mm", "--side", "both", pcb); assert r.returncode == 0, r.stderr
pos = list(csv.DictReader(open(tmp + "/pos.csv")))
with open(os.path.join(out, "CPL_JLC.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
    for p in sorted([p for p in pos if not p["Ref"].startswith("REF")], key=lambda p: key(p["Ref"])):
        w.writerow([p["Ref"], "%.4fmm" % float(p["PosX"]), "%.4fmm" % float(p["PosY"]), "Top" if p["Side"].lower().startswith("top") else "Bottom", "%.1f" % (float(p["Rot"]) % 360)])
print("gerbers:", len(glob.glob(tmp + "/*")) - 2, "files; BOM lines:", len(rows), "; placements:", len(pos))
shutil.rmtree(tmp)
