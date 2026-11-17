#!/usr/bin/env python3
"""Rework Speaker Amp schematic: remove CH221K PD trigger, add two-port 5V USB-C
input with per-port TPS61376 boost (input-current-limited) to +12V."""
import re, sys, uuid

SRC, DST = sys.argv[1], sys.argv[2]
KLIB = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols/"
s = open(SRC).read()
ROOT = re.search(r'\(uuid "([^"]+)"\)', s).group(1)
U = lambda: str(uuid.uuid4())


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


# ---------------------------------------------------------------- lib symbols
TPS = '''(symbol "TPS61376"
		(exclude_from_sim no)
		(in_bom yes)
		(on_board yes)
		(property "Reference" "U"
			(at -10.16 11.43 0)
			(effects (font (size 1.27 1.27)) (justify left))
		)
		(property "Value" "TPS61376"
			(at 1.27 11.43 0)
			(effects (font (size 1.27 1.27)) (justify left))
		)
		(property "Footprint" "SpeakerAmp:TPS61376_RYH0013A"
			(at 0 -17.78 0)
			(effects (font (size 1.27 1.27)) (hide yes))
		)
		(property "Datasheet" "https://www.ti.com/lit/gpn/tps61376"
			(at 0 -20.32 0)
			(effects (font (size 1.27 1.27)) (hide yes))
		)
		(property "Description" "23V in, 25V out, 4.5A boost converter with input average current limit and true load disconnect, VQFN-HR-13"
			(at 0 -22.86 0)
			(effects (font (size 1.27 1.27)) (hide yes))
		)
		(symbol "TPS61376_0_1"
			(rectangle (start -10.16 10.16) (end 10.16 -10.16)
				(stroke (width 0.254) (type default))
				(fill (type background))
			)
		)
		(symbol "TPS61376_1_1"
			(pin power_in line (at -12.7 7.62 0) (length 2.54) (name "VIN" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
			(pin input line (at -12.7 5.08 0) (length 2.54) (name "EN/UVLO" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
			(pin input line (at -12.7 2.54 0) (length 2.54) (name "ISEL" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
			(pin passive line (at -12.7 0 0) (length 2.54) (name "ILIM" (effects (font (size 1.27 1.27)))) (number "10" (effects (font (size 1.27 1.27)))))
			(pin passive line (at -12.7 -2.54 0) (length 2.54) (name "COMP" (effects (font (size 1.27 1.27)))) (number "9" (effects (font (size 1.27 1.27)))))
			(pin input line (at -12.7 -5.08 0) (length 2.54) (name "FB" (effects (font (size 1.27 1.27)))) (number "8" (effects (font (size 1.27 1.27)))))
			(pin passive line (at 12.7 7.62 180) (length 2.54) (name "SW" (effects (font (size 1.27 1.27)))) (number "6" (effects (font (size 1.27 1.27)))))
			(pin passive line (at 12.7 5.08 180) (length 2.54) (name "BOOT" (effects (font (size 1.27 1.27)))) (number "13" (effects (font (size 1.27 1.27)))))
			(pin passive line (at 12.7 2.54 180) (length 2.54) (name "VP" (effects (font (size 1.27 1.27)))) (number "5" (effects (font (size 1.27 1.27)))))
			(pin power_in line (at 12.7 0 180) (length 2.54) (name "VOUT" (effects (font (size 1.27 1.27)))) (number "4" (effects (font (size 1.27 1.27)))))
			(pin power_out line (at 12.7 -5.08 180) (length 2.54) (name "VCC" (effects (font (size 1.27 1.27)))) (number "11" (effects (font (size 1.27 1.27)))))
			(pin power_in line (at -2.54 -12.7 90) (length 2.54) (name "PGND" (effects (font (size 1.27 1.27)))) (number "7" (effects (font (size 1.27 1.27)))))
			(pin power_in line (at 2.54 -12.7 90) (length 2.54) (name "AGND" (effects (font (size 1.27 1.27)))) (number "12" (effects (font (size 1.27 1.27)))))
		)
		(embedded_fonts no)
	)'''


def kicad_lib_symbol(lib, name):
    t = open(KLIB + lib + ".kicad_sym").read()
    i = t.find(f'\n\t(symbol "{name}"')
    assert i >= 0, (lib, name)
    b = block_at(t, i + 1)
    assert '(extends' not in b
    return b.replace(f'(symbol "{name}"', f'(symbol "{lib}:{name}"', 1)


new_libs = {
    "SpeakerAmp:TPS61376": TPS.replace('(symbol "TPS61376"', '(symbol "SpeakerAmp:TPS61376"', 1),
    "Comparator:LM339": kicad_lib_symbol("Comparator", "LM339"),
    "Reference_Voltage:TL431DBZ": kicad_lib_symbol("Reference_Voltage", "TL431DBZ"),
    "Diode:BAT54C": kicad_lib_symbol("Diode", "BAT54C"),
    "Device:L": kicad_lib_symbol("Device", "L"),
    "Device:D_Schottky": kicad_lib_symbol("Device", "D_Schottky"),
}
li = s.find("(lib_symbols")
lib_block = block_at(s, li)
ins = "".join("\n\t\t" + b.replace("\n", "\n\t") for k, b in new_libs.items() if f'(symbol "{k}"' not in lib_block)
lib_block2 = lib_block[:-1].rstrip() + ins + "\n\t)"
s = s.replace(lib_block, lib_block2, 1)
lib_block = lib_block2


def lib_pins(lib_id):
    """-> {pin_number: (unit, x, y, angle)}"""
    i = lib_block.find(f'(symbol "{lib_id}"')
    b = block_at(lib_block, i)
    out = {}
    for m in re.finditer(r'\(symbol "[^"]*_(\d+)_(\d+)"', b):
        sub = block_at(b, m.start())
        unit = int(m.group(1))
        for p in re.finditer(r'\(pin\s+\w+\s+\w+\s*\(at\s+([\d\.\-]+)\s+([\d\.\-]+)\s+(\d+)\)', sub):
            pb = block_at(sub, p.start())
            num = re.search(r'\(number\s+"([^"]*)"', pb).group(1)
            out[num] = (unit, float(p.group(1)), float(p.group(2)), int(p.group(3)))
    return out


# ---------------------------------------------------------------- removals
def remove_symbol(ref):
    global s
    i = s.find(f'(property "Reference" "{ref}"')
    assert i >= 0, ref
    j = s.rfind('(symbol', 0, i)
    b = block_at(s, j)
    s = s.replace(b, "", 1)


def remove_wire(x1, y1, x2, y2):
    global s
    for a, b in (((x1, y1), (x2, y2)), ((x2, y2), (x1, y1))):
        m = re.search(r'\(wire\s*\(pts\s*\(xy %s %s\)\s*\(xy %s %s\)' % (re.escape(fmt(a[0])), re.escape(fmt(a[1])), re.escape(fmt(b[0])), re.escape(fmt(b[1]))), s)
        if m:
            s = s.replace(block_at(s, m.start()), "", 1)
            return
    raise SystemExit(f"wire not found {x1,y1,x2,y2}")


def remove_junction(x, y):
    global s
    m = re.search(r'\(junction\s*\(at %s %s\)' % (re.escape(fmt(x)), re.escape(fmt(y))), s)
    assert m, (x, y)
    s = s.replace(block_at(s, m.start()), "", 1)


def remove_label(name, x, y):
    global s
    m = re.search(r'\(label "%s"\s*\(at %s %s ' % (re.escape(name), re.escape(fmt(x)), re.escape(fmt(y))), s)
    assert m, name
    s = s.replace(block_at(s, m.start()), "", 1)


for r in ("U4", "R5", "R6"):
    remove_symbol(r)
for w in [
    (118.11, 175.26, 139.7, 175.26),      # U4 GND
    (129.54, 165.1, 118.11, 165.1), (137.16, 165.1, 138.43, 165.1), (138.43, 165.1, 138.43, 172.72), (138.43, 172.72, 139.7, 172.72),  # R5 / VDD
    (138.43, 177.8, 139.7, 177.8), (138.43, 191.77, 138.43, 177.8),   # PG
    (157.48, 175.26, 162.56, 175.26),     # CC2
    (157.48, 177.8, 165.1, 177.8),        # CC1
    (157.48, 172.72, 180.34, 172.72), (180.34, 172.72, 180.34, 179.07),  # CFG
    (171.45, 186.69, 180.34, 186.69),     # R6 gnd
    (107.95, 101.6, 107.95, 116.84),      # F1 -> +12V rail (now broken: F1 feeds VBUS_A)
]:
    remove_wire(*w)
for j in [(118.11, 175.26), (118.11, 165.1), (162.56, 175.26), (165.1, 177.8)]:
    remove_junction(*j)
remove_label("+12V", 107.95, 106.68)

# C16 bulk cap value
i = s.find('(property "Reference" "C16"')
k = s.find('(property "Value" "470u"', i)
assert 0 < k - i < 600
s = s[:k] + '(property "Value" "2200u 16V"' + s[k + len('(property "Value" "470u"'):]

# ---------------------------------------------------------------- generators
out = []
placed = set()


def wire(x1, y1, x2, y2):
    out.append(f'(wire\n\t\t(pts\n\t\t\t(xy {fmt(x1)} {fmt(y1)}) (xy {fmt(x2)} {fmt(y2)})\n\t\t)\n\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n\t\t)\n\t\t(uuid "{U()}")\n\t)')


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


def prop(name, val, x, y, hide=False, just=None, rot=0):
    h = "\n\t\t\t(hide yes)" if hide else ""
    j = f"\n\t\t\t\t(justify {just})" if just else ""
    val = val.replace('"', "'")
    return (f'\t\t(property "{name}" "{val}"\n\t\t\t(at {fmt(x)} {fmt(y)} {rot}){h}\n\t\t\t(show_name no)\n\t\t\t(do_not_autoplace no)\n'
            f'\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t){j}\n\t\t\t)\n\t\t)\n')


DESCR = {"Device:R": "Resistor", "Device:C": "Unpolarized capacitor", "Device:L": "Inductor", "Device:D_Schottky": "Schottky diode",
         "Device:Polyfuse": "Resettable fuse, polymeric positive temperature coefficient", "Device:D_TVS": "Bidirectional transient-voltage-suppression diode",
         "power:GND": "Power symbol creates a global label with name 'GND' , ground", "power:PWR_FLAG": "Special symbol for telling ERC where power comes from"}
pwr_n = [max(int(x) for x in re.findall(r'"#PWR0*(\d+)"', s))]
flg_n = [max(int(x) for x in re.findall(r'"#FLG0*(\d+)"', s))]


def symbol(lib_id, ref, value, fp, x, y, rot=0, unit=1, refpos=None, valpos=None, just="left", hide_ref=False, hide_val=False, extra=None, pins=None):
    pl = lib_pins(lib_id)
    mine = [n for n, (u, *_r) in pl.items() if u in (0, unit)] if pins is None else pins
    rp = refpos or (x + 2.54, y - 1.27)
    vp = valpos or (x + 2.54, y + 1.27)
    t = (f'(symbol\n\t\t(lib_id "{lib_id}")\n\t\t(at {fmt(x)} {fmt(y)} {rot})\n\t\t(unit {unit})\n\t\t(body_style 1)\n\t\t(exclude_from_sim no)\n'
         f'\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(in_pos_files yes)\n\t\t(dnp no)\n\t\t(uuid "{U()}")\n')
    t += prop("Reference", ref, rp[0], rp[1], hide=hide_ref, just=just)
    t += prop("Value", value, vp[0], vp[1], hide=hide_val, just=just)
    t += prop("Footprint", fp, x, y, hide=True)
    t += prop("Datasheet", (extra or {}).pop("Datasheet", ""), x, y, hide=True)
    t += prop("Description", (extra or {}).pop("Description", DESCR.get(lib_id, "")), x, y, hide=True)
    for kx, vx in (extra or {}).items():
        t += prop(kx, vx, x, y, hide=True)
    for n in mine:
        t += f'\t\t(pin "{n}"\n\t\t\t(uuid "{U()}")\n\t\t)\n'
    t += (f'\t\t(instances\n\t\t\t(project "Speaker Amp"\n\t\t\t\t(path "/{ROOT}"\n\t\t\t\t\t(reference "{ref}")\n\t\t\t\t\t(unit {unit})\n'
          f'\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)')
    out.append(t)
    return {n: (x + px, y - py, ang) for n, (u, px, py, ang) in pl.items() if u in (0, unit)}


def gnd(x, y, rot=0):
    key = ("GND", round(x, 2), round(y, 2))
    if key in placed:
        return
    placed.add(key)
    pwr_n[0] += 1
    off = {0: (0, 5.08), 180: (0, -5.08), 90: (5.08, 0), 270: (-5.08, 0)}[rot]
    symbol("power:GND", f"#PWR0{pwr_n[0]}", "GND", "", x, y, rot=rot, refpos=(x, y + 6.35), valpos=(x + off[0], y + off[1]), just=None, hide_ref=True)


def flag(net, x, y):
    flg_n[0] += 1
    symbol("power:PWR_FLAG", f"#FLG0{flg_n[0]}", "PWR_FLAG", "", x, y, refpos=(x, y - 1.9), valpos=(x, y - 5.08), just=None, hide_ref=True)
    label(net, x, y, 0)


LROT = {0: 180, 180: 0, 270: 90, 90: 270}      # pin angle -> label rotation
GROT = {90: 0, 270: 180, 0: 270, 180: 90}      # pin angle -> GND symbol rotation


def connect(pins, nets, lrot=None):
    for n, net in nets.items():
        x, y, ang = pins[n]
        if net is None:
            noconn(x, y)
        elif net == "GND":
            gnd(x, y, GROT[ang])
        else:
            label(net, x, y, (lrot or {}).get(n, LROT[ang]))


R0805 = "Resistor_SMD:R_0805_2012Metric"
C0805 = "Capacitor_SMD:C_0805_2012Metric"
C1206 = "Capacitor_SMD:C_1206_3216Metric"


def two(lib, ref, val, fp, x, y, top, bot, lcsc=None, left=False, lrot=None):
    kw = dict(refpos=(x - 2.54, y - 1.27), valpos=(x - 2.54, y + 1.27), just="right") if left else {}
    p = symbol(lib, ref, val, fp, x, y, extra=({"LCSC Part": lcsc} if lcsc else None), **kw)
    # pin at top has angle 270
    tp = [n for n, v in p.items() if v[2] == 270][0]
    bp = [n for n, v in p.items() if v[2] == 90][0]
    connect(p, {tp: top, bp: bot}, lrot)
    return p


def R(ref, val, x, y, top, bot, lcsc=None, **k):
    return two("Device:R", ref, val, R0805, x, y, top, bot, lcsc, **k)


def C(ref, val, x, y, top, bot, fp=C0805, lcsc=None, **k):
    return two("Device:C", ref, val, fp, x, y, top, bot, lcsc, **k)


# ---------------------------------------------------------------- edits to the existing port-A section
label("+12V", 109.22, 101.6, 0)
label("VBUS_A", 107.95, 116.84, 0)
label("CC1_A", 147.32, 132.08, 0)
label("CC2_A", 147.32, 134.62, 0)
wire(138.43, 191.77, 138.43, 194.31)          # LED resistor R20 now returns to GND
gnd(138.43, 194.31)

# ---------------------------------------------------------------- CC current-advertisement sensing (top of sheet)
p = symbol("Diode:BAT54C", "D3", "BAT54C", "Package_TO_SOT_SMD:SOT-23", 40.64, 33.02, refpos=(40.64, 26.67), valpos=(40.64, 29.21), just=None, extra={"LCSC Part": "C22466350"})
connect(p, {"1": "VBUS_A", "2": "VBUS_B", "3": "VAUX"}, {"3": 270})
flag("VAUX", 55.88, 27.94)
C("C18", "100n", 60.96, 35.56, "VAUX", "GND")
R("R21", "680", 73.66, 35.56, "VAUX", "VREF")
p = symbol("Reference_Voltage:TL431DBZ", "U4", "TL431", "Package_TO_SOT_SMD:SOT-23", 86.36, 45.72, refpos=(86.36, 50.8), valpos=(86.36, 53.34), just=None, extra={"LCSC Part": "C181103"})
connect(p, {"1": "VREF", "2": "VREF", "3": "GND"})
R("R22", "18k", 101.6, 33.02, "VREF", "TH_HIGH", left=True, lrot={"2": 0})
R("R23", "3k", 101.6, 40.64, "TH_HIGH", "TH_MED", left=True, lrot={"1": 0, "2": 0})
R("R24", "3.3k", 101.6, 48.26, "TH_MED", "GND", left=True, lrot={"1": 0})

LM = "Comparator:LM339"
SO14 = "Package_SO:SOIC-14_3.9x8.7mm_P1.27mm"
lmp = lib_pins(LM)
unit_of = {n: u for n, (u, *_r) in lmp.items()}


def comp(out_pin, x, y, plus, minus, outnet):
    u = unit_of[out_pin]
    p = symbol(LM, "U5", "LM339", SO14, x, y, unit=u, refpos=(x, y - 7.62), valpos=(x, y + 7.62), just=None, extra={"LCSC Part": "C7948"})
    nm = {}
    for n, (px, py, ang) in p.items():
        if n == out_pin:
            nm[n] = outnet
        elif py < y:           # '+' input is drawn above centre
            nm[n] = plus
        else:
            nm[n] = minus
    connect(p, nm)


assert lmp["5"][2] > 0 and lmp["4"][2] < 0     # pin 5 is '+', pin 4 is '-'
comp("2", 139.7, 30.48, "CCS_A", "TH_MED", "ISEL_A")       # >= 1.5 A advertised on port A
comp("1", 139.7, 50.8, "TH_HIGH", "CCS_A", "HIGH_A")       # 3 A advertised on port A (active low)
comp("13", 195.58, 30.48, "CCS_B", "TH_MED", "ISEL_B")
comp("14", 195.58, 50.8, "TH_HIGH", "CCS_B", "HIGH_B")
u5 = [u for n, (u, *_r) in lmp.items() if n == "3"][0]
p = symbol(LM, "U5", "LM339", SO14, 167.64, 40.64, unit=u5, refpos=(171.45, 39.37), valpos=(171.45, 41.91), extra={"LCSC Part": "C7948"})
connect(p, {"3": "VAUX", "12": "GND"})

y = 71.12
for (pfx, x0, refs) in (("A", 119.38, ("R25", "R26", "C19", "R27", "R28")), ("B", 177.8, ("R29", "R30", "C20", "R31", "R32"))):
    R(refs[0], "47k", x0, y, f"CC1_{pfx}", f"CCS_{pfx}")
    R(refs[1], "47k", x0 + 10.16, y, f"CC2_{pfx}", f"CCS_{pfx}")
    C(refs[2], "470n", x0 + 20.32, y, f"CCS_{pfx}", "GND", lcsc="C123623")
    R(refs[3], "100k", x0 + 30.48, y, "VREF", f"ISEL_{pfx}")
    R(refs[4], "10M", x0 + 40.64, y, f"ISEL_{pfx}", f"CCS_{pfx}", lcsc="C2933281")

# ---------------------------------------------------------------- port B (power-only USB-C)
USBC = "Connector:USB_C_Receptacle_USB2.0_16P"
p = symbol(USBC, "J5", "USB_C_Receptacle_USB2.0_16P", "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12", 40.64, 251.46,
           refpos=(40.64, 228.6), valpos=(40.64, 231.14), just=None,
           extra={"Datasheet": "https://www.usb.org/sites/default/files/documents/usb_type-c.zip", "Description": "USB 2.0-only 16P Type-C Receptacle connector (power only)"})
nm = {}
for n in p:
    if n in ("A4", "A9", "B4", "B9"):
        nm[n] = "VBUSB_RAW"
    elif n in ("A1", "A12", "B1", "B12", "SH"):
        nm[n] = "GND"
    elif n == "A5":
        nm[n] = "CC1_B"
    elif n == "B5":
        nm[n] = "CC2_B"
    else:
        nm[n] = None
connect(p, nm)
flag("VBUSB_RAW", 104.14, 276.86)
two("Device:Polyfuse", "F2", "Polyfuse", "Fuse:Fuse_1812_4532Metric", 71.12, 248.92, "VBUS_B", "VBUSB_RAW")
p = symbol("Device:D_TVS", "D4", "SMBJ15A", "Diode_SMD:D_SMB", 96.52, 238.76, refpos=(96.52, 233.68), valpos=(96.52, 236.22), just=None)
ks = sorted(p, key=lambda n: p[n][0])
connect(p, {ks[0]: "VBUSB_RAW", ks[1]: "GND"})
C("C21", "1u", 109.22, 248.92, "VBUSB_RAW", "GND")
R("R33", "5.1k", 81.28, 266.7, "CC1_B", "GND")
R("R34", "5.1k", 91.44, 266.7, "CC2_B", "GND")
flag("VBUS_B", 104.14, 262.89)

# ---------------------------------------------------------------- boost converters
def boost(pfx, x0, y, uy, uref, lref, dref, rs, cs, fb_bot, fb_lcsc):
    xs = [x0 + 10.16 * i for i in range(15)]
    V = f"VBUS_{pfx}"
    C(cs[0], "22u 25V", xs[0], y, V, "GND", fp=C1206, lcsc="C12891")
    C(cs[1], "100n", xs[1], y, V, "GND")
    R(rs[0], "220k", xs[2], y, V, f"EN_{pfx}")
    R(rs[1], "56k", xs[3], y, f"EN_{pfx}", "GND", lcsc="C17756")
    C(cs[2], "100n", xs[4], y, f"EN_{pfx}", "GND")
    R(rs[2], "30.9k", xs[5], y, f"ILIM_{pfx}", "GND", lcsc="C2933411")
    R(rs[3], "30k", xs[6], y, f"ILIM_{pfx}", f"HIGH_{pfx}")
    R(rs[4], "80.6k", xs[7], y, f"COMP_{pfx}", f"CZ_{pfx}", lcsc="C2960781")
    C(cs[3], "22n", xs[8], y, f"CZ_{pfx}", "GND")
    R(rs[5], "1M", xs[9], y, "+12V", f"FB_{pfx}")
    R(rs[6], fb_bot, xs[10], y, f"FB_{pfx}", "GND", lcsc=fb_lcsc)
    C(cs[4], "4.7u", xs[11], y, f"VCC_{pfx}", "GND", lcsc="C1746")
    C(cs[5], "470n", xs[12], y, f"BOOT_{pfx}", f"SW_{pfx}", lcsc="C123623")
    C(cs[6], "22u 25V", xs[13], y, "+12V", "GND", fp=C1206, lcsc="C12891")
    C(cs[7], "22u 25V", xs[14], y, "+12V", "GND", fp=C1206, lcsc="C12891")
    ux = x0 + 20.32
    p = symbol("SpeakerAmp:TPS61376", uref, "TPS61376", "SpeakerAmp:TPS61376_RYH0013A", ux, uy, refpos=(ux - 10.16, uy - 11.43), valpos=(ux + 1.27, uy - 11.43),
               extra={"Datasheet": "https://www.ti.com/lit/gpn/tps61376", "Description": "Boost converter with input average current limit and load disconnect", "MPN": "TPS61376RYHR", "LCSC Part": "C7073367"})
    connect(p, {"1": V, "2": f"EN_{pfx}", "3": f"ISEL_{pfx}", "10": f"ILIM_{pfx}", "9": f"COMP_{pfx}", "8": f"FB_{pfx}",
                "6": f"SW_{pfx}", "13": f"BOOT_{pfx}", "5": f"VP_{pfx}", "4": "+12V", "11": f"VCC_{pfx}", "7": "GND", "12": "GND"})
    two("Device:L", lref, "4.7u", "Inductor_SMD:L_Changjiang_FXL0630", ux + 33.02, uy, V, f"SW_{pfx}", lcsc="C167220")
    dx = ux + 50.8
    p = symbol("Device:D_Schottky", dref, "SS34", "Diode_SMD:D_SMA", dx, uy, refpos=(dx, uy - 5.08), valpos=(dx, uy - 2.54), just=None, extra={"LCSC Part": "C7420365"})
    connect(p, {"1": "+12V", "2": f"VP_{pfx}"})


boost("A", 119.38, 233.68, 264.16, "U6", "L1", "D5", ("R35", "R36", "R37", "R38", "R39", "R40", "R41"), ("C22", "C23", "C24", "C25", "C26", "C27", "C28", "C29"), "93.1k", "C2933511")
boost("B", 236.22, 35.56, 66.04, "U7", "L2", "D6", ("R42", "R43", "R44", "R45", "R46", "R47", "R48"), ("C30", "C31", "C32", "C33", "C34", "C35", "C36", "C37"), "88.7k", "C5121549")
flag("VBUS_A", 104.14, 213.36)

# notes
def text(t, x, y):
    out.append(f'(text "{t}"\n\t\t(exclude_from_sim no)\n\t\t(at {fmt(x)} {fmt(y)} 0)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.5 1.5)\n\t\t\t)\n\t\t\t(justify left bottom)\n\t\t)\n\t\t(uuid "{U()}")\n\t)')


text("USB-C current sensing: CCS = (CC1+CC2)/2. Above TH_MED (0.34 V) the source offers 1.5 A, above TH_HIGH (0.65 V) it offers 3 A", 30.48, 17.78)
text("Port B: power-only USB-C (5 V)", 30.48, 223.52)
text("Boost A (data port J1): 5 V -> 11.7 V. Input limit 0.35 A / 1.4 A / 2.84 A", 119.38, 218.44)
text("Boost B (power port J5): 5 V -> 12.3 V, takes the load first. Input limit 0.35 A / 1.4 A / 2.84 A", 236.22, 17.78)

idx = s.rfind('(sheet_instances')
s = s[:idx] + "\n\t".join(out) + "\n\t" + s[idx:]
open(DST, "w").write(s)
print("ok", len(out), "items")
