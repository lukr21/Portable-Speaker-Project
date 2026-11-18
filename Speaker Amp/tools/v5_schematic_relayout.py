#!/usr/bin/env python3
"""Redraw the Speaker Amp V5 schematic as one sheet of labelled functional blocks.
usage: sch_relayout.py in.kicad_sch netlist.xml out.kicad_sch
Every symbol keeps its UUID, reference, value, footprint and extra fields, so the PCB
link is preserved. Connections come from the netlist of the input schematic; each pin
gets a net label (or a GND symbol / no-connect flag). Unnamed nets get readable names."""
import re, sys, uuid
import xml.etree.ElementTree as ET

SRC, NETXML, DST = sys.argv[1:4]
s = open(SRC).read()
ROOT = re.search(r'\(uuid "([^"]+)"\)', s).group(1)
U = lambda: str(uuid.uuid4())
RENAME = {"Net-(C13-Pad1)": "DIV_R", "Net-(C14-Pad1)": "DIV_L", "Net-(D1-K)": "LED_K", "Net-(J1-D+-PadA6)": "USB_DP",
          "Net-(J1-D--PadA7)": "USB_DM", "Net-(U2-D+)": "DAC_DP", "Net-(U2-D-)": "DAC_DM", "Net-(U2-HID0/MS)": "HID0",
          "Net-(U2-HID1/MC)": "HID1", "Net-(U2-HID2/MD)": "HID2", "Net-(U2-VCOM)": "VCOM", "Net-(U2-VOUTL)": "DAC_OUT_L",
          "Net-(U2-VOUTR)": "DAC_OUT_R", "Net-(U2-XTI)": "XTI", "Net-(U2-XTO)": "XTO", "Net-(U3A-+)": "AMP_IN_L",
          "Net-(U3A-MUTE)": "MUTE", "Net-(U3B-+)": "AMP_IN_R"}


def block_at(t, start):
    d = 0
    for i in range(start, len(t)):
        if t[i] == '(':
            d += 1
        elif t[i] == ')':
            d -= 1
            if d == 0:
                return t[start:i + 1]


def fmt(v):
    return ('%.4f' % v).rstrip('0').rstrip('.')


# ---- nets per pin
netof = {}
for n in ET.parse(NETXML).getroot().iter("net"):
    nm = n.get("name")
    for node in n.iter("node"):
        if nm.startswith("unconnected-"):
            disp = None
        elif nm == "GND":
            disp = "GND"
        else:
            disp = RENAME.get(nm, nm.lstrip("/"))
        netof[(node.get("ref"), node.get("pin"))] = disp

# ---- split the sheet: header + lib_symbols | items
li = s.find("(lib_symbols")
lib_block = block_at(s, li)
head = s[:li] + lib_block
rest = s[li + len(lib_block):]
insts = {}
for m in re.finditer(r'\n\t\(symbol\s*\(lib_id "([^"]+)"\)', rest):
    blk = block_at(rest, m.start() + 2)
    ref = re.search(r'\(reference "([^"]+)"\)', blk).group(1)
    if ref.startswith("#"):
        continue
    unit = int(re.search(r'\(unit (\d+)\)', blk).group(1))
    props = re.findall(r'\(property "([^"]+)" "((?:[^"\\]|\\.)*)"', blk)
    insts.setdefault(ref, {})[unit] = dict(lib=m.group(1), uuid=re.search(r'\(uuid "([^"]+)"\)', blk).group(1), props=props)


def lib_pins(lib_id):
    i = lib_block.find(f'(symbol "{lib_id}"')
    b = block_at(lib_block, i)
    out = {}
    for m in re.finditer(r'\(symbol "[^"]*_(\d+)_(\d+)"', b):
        sub = block_at(b, m.start())
        for p in re.finditer(r'\(pin\s+\w+\s+\w+\s*\(at\s+([\d\.\-]+)\s+([\d\.\-]+)\s+(\d+)\)', sub):
            pb = block_at(sub, p.start())
            num = re.search(r'\(number\s+"([^"]*)"', pb).group(1)
            out.setdefault(num, []).append((int(m.group(1)), float(p.group(1)), float(p.group(2)), int(p.group(3))))
    return out


out, placed, done = [], set(), set()
pwr_n = [0]; flg_n = [0]


def label(net, x, y, rot=0):
    key = (net, round(x, 2), round(y, 2))
    if key in placed:
        return
    placed.add(key)
    just = "left bottom" if rot in (0, 90) else "right bottom"
    out.append(f'(label "{net}"\n\t\t(at {fmt(x)} {fmt(y)} {rot})\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify {just})\n\t\t)\n\t\t(uuid "{U()}")\n\t)')


def noconn(x, y):
    key = ("NC", round(x, 2), round(y, 2))
    if key in placed:
        return
    placed.add(key)
    out.append(f'(no_connect\n\t\t(at {fmt(x)} {fmt(y)})\n\t\t(uuid "{U()}")\n\t)')


def prop(name, val, x, y, hide=False, just=None):
    h = "\n\t\t\t(hide yes)" if hide else ""
    j = f"\n\t\t\t\t(justify {just})" if just else ""
    return (f'\t\t(property "{name}" "{val}"\n\t\t\t(at {fmt(x)} {fmt(y)} 0){h}\n\t\t\t(show_name no)\n\t\t\t(do_not_autoplace no)\n'
            f'\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t){j}\n\t\t\t)\n\t\t)\n')


def emit(lib_id, ref, unit, uid, props, x, y, refpos, valpos, just, pins, hide_ref=False, hide_val=False):
    t = (f'(symbol\n\t\t(lib_id "{lib_id}")\n\t\t(at {fmt(x)} {fmt(y)} 0)\n\t\t(unit {unit})\n\t\t(body_style 1)\n\t\t(exclude_from_sim no)\n'
         f'\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(in_pos_files yes)\n\t\t(dnp no)\n\t\t(uuid "{uid}")\n')
    for name, val in props:
        if name == "Reference":
            t += prop(name, val, refpos[0], refpos[1], hide=hide_ref, just=just)
        elif name == "Value":
            t += prop(name, val, valpos[0], valpos[1], hide=hide_val, just=just)
        else:
            t += prop(name, val, x, y, hide=True)
    for n in pins:
        t += f'\t\t(pin "{n}"\n\t\t\t(uuid "{U()}")\n\t\t)\n'
    t += (f'\t\t(instances\n\t\t\t(project "Speaker Amp"\n\t\t\t\t(path "/{ROOT}"\n\t\t\t\t\t(reference "{ref}")\n\t\t\t\t\t(unit {unit})\n'
          f'\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)')
    out.append(t)


def power(lib, val, x, y, rot=0):
    n = pwr_n if lib == "power:GND" else flg_n
    n[0] += 1
    ref = ("#PWR0%d" if lib == "power:GND" else "#FLG0%d") % n[0]
    dv = {0: (0, 5.08), 180: (0, -5.08), 90: (5.08, 0), 270: (-5.08, 0)}[rot] if lib == "power:GND" else (0, -5.08)
    t = (f'(symbol\n\t\t(lib_id "{lib}")\n\t\t(at {fmt(x)} {fmt(y)} {rot})\n\t\t(unit 1)\n\t\t(body_style 1)\n\t\t(exclude_from_sim no)\n'
         f'\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(in_pos_files yes)\n\t\t(dnp no)\n\t\t(uuid "{U()}")\n')
    t += prop("Reference", ref, x, y + 6.35, hide=True) + prop("Value", val, x + dv[0], y + dv[1], hide=(lib != "power:GND" and False))
    t += prop("Footprint", "", x, y, hide=True) + prop("Datasheet", "", x, y, hide=True) + prop("Description", "Power symbol", x, y, hide=True)
    t += f'\t\t(pin "1"\n\t\t\t(uuid "{U()}")\n\t\t)\n'
    t += (f'\t\t(instances\n\t\t\t(project "Speaker Amp"\n\t\t\t\t(path "/{ROOT}"\n\t\t\t\t\t(reference "{ref}")\n\t\t\t\t\t(unit 1)\n'
          f'\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)')
    out.append(t)


LROT = {0: 180, 180: 0, 270: 90, 90: 270}
GROT = {90: 0, 270: 180, 0: 270, 180: 90}


def place(ref, x, y, unit=1, refpos=None, valpos=None, just="left", lrot=None, hide_val=False):
    """put one unit of a part at (x, y), unrotated, and hang its nets on the pins"""
    inst = insts[ref][unit]
    pl = lib_pins(inst["lib"])
    mine = {n: [p for p in ps if p[0] in (0, unit)] for n, ps in pl.items()}
    mine = {n: ps[0] for n, ps in mine.items() if ps}
    rp = refpos or (x + 2.54, y - 1.27)
    vp = valpos or (x + 2.54, y + 1.27)
    emit(inst["lib"], ref, unit, inst["uuid"], inst["props"], x, y, rp, vp, just, list(mine), hide_val=hide_val)
    done.add((ref, unit))
    for n, (u, px, py, ang) in mine.items():
        gx, gy = x + px, y - py
        net = netof.get((ref, n))
        if net is None:
            noconn(gx, gy)
        elif net == "GND":
            key = ("GND", round(gx, 2), round(gy, 2))
            if key not in placed:
                placed.add(key)
                power("power:GND", "GND", gx, gy, GROT[ang])
        else:
            label(net, gx, gy, (lrot or {}).get(n, LROT[ang]))


def flag(net, x, y):
    power("power:PWR_FLAG", "PWR_FLAG", x, y)
    label(net, x, y, 0)


def text(t, x, y, size=1.5):
    out.append(f'(text "{t}"\n\t\t(exclude_from_sim no)\n\t\t(at {fmt(x)} {fmt(y)} 0)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size {size} {size})\n\t\t\t)\n\t\t\t(justify left bottom)\n\t\t)\n\t\t(uuid "{U()}")\n\t)')


def frame(title, x1, y1, x2, y2, note=""):
    out.append(f'(rectangle\n\t\t(start {fmt(x1)} {fmt(y1)})\n\t\t(end {fmt(x2)} {fmt(y2)})\n\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type dash)\n\t\t)\n\t\t(fill\n\t\t\t(type none)\n\t\t)\n\t\t(uuid "{U()}")\n\t)')
    text(title, x1 + 1.27, y1 + 3.6, 2.0)
    if note:
        text(note, x1 + 1.27, y1 + 6.4, 1.2)


def row(refs, x0, y, pitch=10.16):
    for i, r in enumerate(refs):
        place(r, x0 + i * pitch, y)


def ic(ref, x, y, unit=1, w=10.16, top=11.43):
    place(ref, x, y, unit, refpos=(x - w, y - top), valpos=(x + 1.27, y - top))


# ================================================================== row 1: USB inputs | 3.3 V + LED | amplifier
frame("USB-C inputs", 20.32, 21.59, 170.18, 86.36, "J1 = data + power, J5 = power only. Rd 5.1k on each CC. Fuse then TVS on each VBUS.")
for j, f, d, c, r1, r2, x, vr, va in (("J1", "F1", "D2", "C1", "R3", "R4", 38.1, "VBUS_RAW", "VBUS_A"), ("J5", "F2", "D4", "C21", "R33", "R34", 114.3, "VBUSB_RAW", "VBUS_B")):
    place(j, x, 55.88, refpos=(x - 7.62, 33.02), valpos=(x - 7.62, 30.48), hide_val=True)
    row((f, c), x + 38.1, 44.45)
    place(d, x + 43.18, 59.69, refpos=(x + 43.18, 54.61), valpos=(x + 43.18, 57.15), just=None)
    row((r1, r2), x + 38.1, 73.66)
    flag(vr, x + 21.59, 76.2); flag(va, x + 21.59, 84.455)

frame("3.3 V regulator and power LED", 173.99, 21.59, 251.46, 86.36)
place("U1", 212.09, 44.45, refpos=(212.09, 36.83), valpos=(212.09, 39.37), just=None)
place("C2", 187.96, 49.53); place("C3", 236.22, 49.53)
place("D1", 224.79, 71.12, refpos=(224.79, 66.04), valpos=(224.79, 68.58), just=None)
place("R20", 196.85, 73.66)
# ground reference flag for ERC
power("power:PWR_FLAG", "PWR_FLAG", 241.3, 73.66); power("power:GND", "GND", 241.3, 73.66)

frame("Amplifier and outputs", 255.27, 21.59, 400.05, 86.36, "TDA7297, 12 V. MUTE/STBY held at half supply by R18/R19, C15 gives a soft start.")
place("U3", 276.86, 45.72, 1, refpos=(266.7, 55.88), valpos=(274.32, 55.88))
place("U3", 276.86, 73.66, 2, refpos=(266.7, 81.28), valpos=(274.32, 81.28))
place("U3", 304.8, 58.42, 3, refpos=(309.88, 57.15), valpos=(309.88, 59.69))
row(("C16", "C17", "R18", "R19", "C15"), 325.12, 44.45, 13.97)
for r, x, y in (("J2", 340.36, 73.66), ("J3", 365.76, 73.66), ("J4", 391.16, 73.66)):
    place(r, x, y, refpos=(x - 2.54, y - 7.62), valpos=(x - 2.54, y + 5.08), hide_val=True)
flag("+12V", 388.62, 58.42)

# ================================================================== row 2: CC current sensing
frame("USB-C current sensing", 20.32, 90.17, 400.05, 143.51,
      "CCS = (CC1 + CC2) / 2. Above TH_MED (0.34 V) the source offers 1.5 A: ISEL goes high. Above TH_HIGH (0.65 V) it offers 3 A: HIGH pulls the second ILIM resistor to GND.")
Y = 105.41
place("D3", 38.1, Y + 5.08, refpos=(38.1, Y - 1.27), valpos=(38.1, Y + 1.27), just=None)
flag("VAUX", 58.42, Y)
row(("C18", "R21"), 73.66, Y + 5.08, 12.7)
place("U4", 104.14, Y + 15.24, refpos=(104.14, Y + 20.32), valpos=(104.14, Y + 22.86), just=None)
for r, yy in (("R22", Y + 2.54), ("R23", Y + 10.16), ("R24", Y + 17.78)):
    place(r, 124.46, yy, refpos=(121.92, yy - 1.27), valpos=(121.92, yy + 1.27), just="right", lrot={"1": 0, "2": 0} if r == "R23" else ({"2": 0} if r == "R22" else {"1": 0}))
pl5 = lib_pins("Comparator:LM339")
order = {"2": (165.1, Y + 2.54), "1": (165.1, Y + 22.86), "13": (226.06, Y + 2.54), "14": (226.06, Y + 22.86)}
for u in sorted(insts["U5"]):
    pins_u = [n for n, ps in pl5.items() for p in ps if p[0] == u]
    key = [n for n in pins_u if n in order]
    if key:
        x, y = order[key[0]]
        place("U5", x, y, u, refpos=(x - 5.08, y + 7.62), valpos=(x + 2.54, y + 7.62))
    else:
        place("U5", 195.58, Y + 12.7, u, refpos=(199.39, Y + 11.43), valpos=(199.39, Y + 13.97))
row(("R25", "R26", "C19", "R27", "R28"), 261.62, Y + 12.7)
row(("R29", "R30", "C20", "R31", "R32"), 327.66, Y + 12.7)
text("Port A (J1)", 261.62, Y + 31.75, 1.3); text("Port B (J5)", 327.66, Y + 31.75, 1.3)


# ================================================================== row 3: boost converters
def boost(pfx, x0, title, note, U_, L_, D_, parts):
    frame(title, x0 - 7.62, 147.32, x0 + 180.34, 212.09, note)
    row(parts, x0, 167.64, 10.16)
    ux, uy = x0 + 20.32, 194.31
    ic(U_, ux, uy)
    place(L_, ux + 33.02, uy)
    place(D_, ux + 50.8, uy, refpos=(ux + 50.8, uy - 5.08), valpos=(ux + 50.8, uy - 2.54), just=None)


boost("A", 27.94, "Boost A: J1 (data port), 5 V to 11.7 V", "Input current limit 0.35 / 1.4 / 2.84 A from ISEL_A and HIGH_A.", "U6", "L1", "D5",
      ("C22", "C23", "R35", "R36", "C24", "R37", "R38", "R39", "C25", "R40", "R41", "C26", "C27", "C28", "C29"))
boost("B", 219.71, "Boost B: J5 (power port), 5 V to 12.3 V", "Set slightly higher than boost A, so the power-only port carries the load first.", "U7", "L2", "D6",
      ("C30", "C31", "R42", "R43", "C32", "R44", "R45", "R46", "C33", "R47", "R48", "C34", "C35", "C36", "C37"))

# ================================================================== row 4: DAC | audio filter
frame("USB audio DAC and buttons", 20.32, 215.9, 214.63, 287.02, "PCM2704C, self-powered from 3.3 V. SW1-SW3 are the HID buttons with 3.3k pull-downs.")
place("U2", 49.53, 254.0, refpos=(36.83, 233.68), valpos=(49.53, 233.68))
place("Y1", 90.17, 238.76, refpos=(90.17, 232.41), valpos=(90.17, 234.95), just=None)
row(("R7", "C10", "C9", "C4", "C5", "C6", "C7", "C8"), 109.22, 238.76, 12.7)
row(("R1", "R2", "R8", "R9", "R10", "R11"), 86.36, 266.7, 11.43)
for sw, x, y in (("SW1", 167.64, 261.62), ("SW2", 167.64, 273.05), ("SW3", 198.12, 261.62)):
    place(sw, x, y, refpos=(x, y - 5.08), valpos=(x, y + 2.54), just=None, hide_val=True)

frame("Audio filter and level", 218.44, 215.9, 297.18, 287.02, "330 R + 22 n low-pass, 10k / 2.7k divider, 220 n coupling.")
row(("R13", "C11", "R15", "R16", "C14"), 228.6, 238.76, 12.7)
row(("R12", "C12", "R14", "R17", "C13"), 228.6, 267.97, 12.7)
text("Left channel", 228.6, 252.73, 1.3); text("Right channel", 228.6, 282.575, 1.3)

missing = [(r, u) for r in insts for u in insts[r] if (r, u) not in done]
assert not missing, missing
tail = "\n\t(sheet_instances\n\t\t(path \"/\"\n\t\t\t(page \"1\")\n\t\t)\n\t)\n\t(embedded_fonts no)\n)\n"
open(DST, "w").write(head + "\n\t" + "\n\t".join(out) + tail)
print("written", len(out), "items;", len(insts), "parts")
