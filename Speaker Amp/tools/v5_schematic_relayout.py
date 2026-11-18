#!/usr/bin/env python3
"""Redraw the Speaker Amp V5 schematic: one sheet, functional blocks, each chip WIRED to
its own passives, net labels only between blocks and for power rails.
usage: sch_hybrid.py in.kicad_sch netlist.xml out.kicad_sch
Symbols keep their UUID, reference, value, footprint and fields (PCB link preserved).
Connectivity comes from the input netlist and is not changed."""
import re, sys, uuid
import xml.etree.ElementTree as ET

SRC, NETXML, DST = sys.argv[1:4]
s = open(SRC).read()
ROOT = re.search(r'\(uuid "([^"]+)"\)', s).group(1)
U = lambda: str(uuid.uuid4())
RAILS = {"+12V", "+3.3V", "VBUS_A", "VBUS_B", "VAUX", "VREF", "TH_MED", "TH_HIGH"}   # always drawn as labels
P = 10.16            # column pitch for parts hanging off a pin


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


netof, members = {}, {}
for n in ET.parse(NETXML).getroot().iter("net"):
    nm = n.get("name")
    disp = None if nm.startswith("unconnected-") else ("GND" if nm == "GND" else nm.lstrip("/"))
    for node in n.iter("node"):
        netof[(node.get("ref"), node.get("pin"))] = disp
        if disp:
            members.setdefault(disp, set()).add(node.get("ref"))

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
    insts.setdefault(ref, {})[unit] = dict(lib=m.group(1), uuid=re.search(r'\(uuid "([^"]+)"\)', blk).group(1),
                                           props=re.findall(r'\(property "([^"]+)" "((?:[^"\\]|\\.)*)"', blk))
_lp = {}


def lib_pins(lib_id):
    if lib_id in _lp:
        return _lp[lib_id]
    b = block_at(lib_block, lib_block.find(f'(symbol "{lib_id}"'))
    out = {}
    for m in re.finditer(r'\(symbol "[^"]*_(\d+)_(\d+)"', b):
        sub = block_at(b, m.start())
        for p in re.finditer(r'\(pin\s+\w+\s+\w+\s*\(at\s+([\d\.\-]+)\s+([\d\.\-]+)\s+(\d+)\)', sub):
            num = re.search(r'\(number\s+"([^"]*)"', block_at(sub, p.start())).group(1)
            out.setdefault(num, []).append((int(m.group(1)), float(p.group(1)), float(p.group(2)), int(p.group(3))))
    _lp[lib_id] = out
    return out


def unit_pins(ref, unit):
    pl = lib_pins(insts[ref][unit]["lib"])
    r = {}
    for n, ps in pl.items():
        ps = [p for p in ps if p[0] in (0, unit)]
        if ps:
            r[n] = ps[0][1:]
    return r


OUT0 = {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}       # outward direction of a pin, unrotated


def xf(rot, px, py, ang):
    """lib pin (px, py, angle) -> screen offset and outward direction for a symbol rotated by rot"""
    off = {0: (px, -py), 90: (-py, -px), 180: (-px, py), 270: (py, px)}[rot]
    dx, dy = OUT0[ang]
    out = {0: (dx, dy), 90: (dy, -dx), 180: (-dx, -dy), 270: (-dy, dx)}[rot]
    return off, out


LAB = {(-1, 0): 180, (1, 0): 0, (0, -1): 90, (0, 1): 270}
GNDR = {(0, 1): 0, (0, -1): 180, (-1, 0): 270, (1, 0): 90}
out, placed, done = [], set(), set()
cnt = {"pwr": 0, "flg": 0}
BLOCK_OF = {}


def wire(x1, y1, x2, y2):
    if (x1, y1) != (x2, y2):
        out.append(f'(wire\n\t\t(pts\n\t\t\t(xy {fmt(x1)} {fmt(y1)}) (xy {fmt(x2)} {fmt(y2)})\n\t\t)\n\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n\t\t)\n\t\t(uuid "{U()}")\n\t)')


def junction(x, y):
    out.append(f'(junction\n\t\t(at {fmt(x)} {fmt(y)})\n\t\t(diameter 0)\n\t\t(color 0 0 0 0)\n\t\t(uuid "{U()}")\n\t)')


def label(net, x, y, d=(1, 0)):
    key = (net, round(x, 2), round(y, 2))
    if key in placed:
        return
    placed.add(key)
    rot = LAB[d]
    just = "left bottom" if rot in (0, 90) else "right bottom"
    out.append(f'(label "{net}"\n\t\t(at {fmt(x)} {fmt(y)} {rot})\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify {just})\n\t\t)\n\t\t(uuid "{U()}")\n\t)')


def noconn(x, y):
    key = ("NC", round(x, 2), round(y, 2))
    if key not in placed:
        placed.add(key)
        out.append(f'(no_connect\n\t\t(at {fmt(x)} {fmt(y)})\n\t\t(uuid "{U()}")\n\t)')


def prop(name, val, x, y, hide=False, just=None, ang=0):
    h = "\n\t\t\t(hide yes)" if hide else ""
    j = f"\n\t\t\t\t(justify {just})" if just else ""
    return (f'\t\t(property "{name}" "{val}"\n\t\t\t(at {fmt(x)} {fmt(y)} {ang}){h}\n\t\t\t(show_name no)\n\t\t\t(do_not_autoplace no)\n'
            f'\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t){j}\n\t\t\t)\n\t\t)\n')


def power(lib, x, y, d=(0, 1)):
    k = "pwr" if lib == "power:GND" else "flg"
    cnt[k] += 1
    ref = ("#PWR0%d" if k == "pwr" else "#FLG0%d") % cnt[k]
    rot = GNDR[d] if k == "pwr" else 0
    vx, vy = (x + d[0] * 5.08, y + d[1] * 5.08) if k == "pwr" else (x, y - 5.08)
    t = (f'(symbol\n\t\t(lib_id "{lib}")\n\t\t(at {fmt(x)} {fmt(y)} {rot})\n\t\t(unit 1)\n\t\t(body_style 1)\n\t\t(exclude_from_sim no)\n'
         f'\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(in_pos_files yes)\n\t\t(dnp no)\n\t\t(uuid "{U()}")\n')
    t += prop("Reference", ref, x, y + 6.35, hide=True) + prop("Value", "GND" if k == "pwr" else "PWR_FLAG", vx, vy, hide=(k == "pwr" and d != (0, 1)))
    t += prop("Footprint", "", x, y, hide=True) + prop("Datasheet", "", x, y, hide=True) + prop("Description", "Power symbol", x, y, hide=True)
    t += f'\t\t(pin "1"\n\t\t\t(uuid "{U()}")\n\t\t)\n'
    t += (f'\t\t(instances\n\t\t\t(project "Speaker Amp"\n\t\t\t\t(path "/{ROOT}"\n\t\t\t\t\t(reference "{ref}")\n\t\t\t\t\t(unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)')
    out.append(t)


def gnd(x, y, d=(0, 1)):
    key = ("GND", round(x, 2), round(y, 2))
    if key not in placed:
        placed.add(key)
        power("power:GND", x, y, d)


def flag(net, x, y):
    power("power:PWR_FLAG", x, y)
    if net == "GND":
        gnd(x, y)
    else:
        label(net, x, y, (1, 0))


def emit(ref, unit, x, y, rot, refpos, valpos, just="left", hide_val=False):
    inst = insts[ref][unit]
    ang = 90 if rot in (90, 270) else 0
    if just == "left" and rot == 180:
        just = "right"
    if just == "left" and rot in (90, 270):      # sideways parts: centred text, pushed clear of the body
        just = None
        refpos = (refpos[0] + 3.81, refpos[1]); valpos = (valpos[0] + 3.81, valpos[1])
    t = (f'(symbol\n\t\t(lib_id "{inst["lib"]}")\n\t\t(at {fmt(x)} {fmt(y)} {rot})\n\t\t(unit {unit})\n\t\t(body_style 1)\n\t\t(exclude_from_sim no)\n'
         f'\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(in_pos_files yes)\n\t\t(dnp no)\n\t\t(uuid "{inst["uuid"]}")\n')
    for name, val in inst["props"]:
        if name == "Reference":
            t += prop(name, val, refpos[0], refpos[1], just=just, ang=ang)
        elif name == "Value":
            t += prop(name, val, valpos[0], valpos[1], hide=hide_val, just=just, ang=ang)
        else:
            t += prop(name, val, x, y, hide=True)
    for n in unit_pins(ref, unit):
        t += f'\t\t(pin "{n}"\n\t\t\t(uuid "{U()}")\n\t\t)\n'
    t += (f'\t\t(instances\n\t\t\t(project "Speaker Amp"\n\t\t\t\t(path "/{ROOT}"\n\t\t\t\t\t(reference "{ref}")\n\t\t\t\t\t(unit {unit})\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)')
    out.append(t)
    done.add((ref, unit))


def terminate(net, x, y, d, here):
    """end of a part or pin that is not wired on: ground symbol, no-connect, or a label"""
    if net is None:
        noconn(x, y)
    elif net == "GND":
        gnd(x, y, d)
    else:
        label(net, x, y, d)


def two_pin(ref):
    pins = unit_pins(ref, 1)
    assert len(pins) == 2, ref
    return pins


def hang(ref, x, ytop, home_pin, chain=True):
    """hang a two-pin part down from (x, ytop) with home_pin on top; returns the far-end net (already terminated)"""
    pins = two_pin(ref)
    other = [n for n in pins if n != home_pin][0]
    for rot in (0, 180, 90, 270):
        (ox, oy), _ = xf(rot, *pins[home_pin])
        (px, py), _ = xf(rot, *pins[other])
        if abs(ox) < 0.01 and oy < 0 and abs(px) < 0.01 and py > 0:
            break
    else:
        raise SystemExit("cannot hang " + ref)
    cy = ytop - oy
    emit(ref, 1, x, cy, rot, (x + 2.54, cy - 1.27), (x + 2.54, cy + 1.27), hide_val=ref.startswith("SW"))
    ybot = cy + py
    far = netof.get((ref, other))
    # private two-part net (e.g. the RC of a compensation network): carry on downwards
    if chain and far and far != "GND" and far not in RAILS:
        rest_ = [r for r in members[far] if r != ref and (r, 1) not in done and r in insts and len(unit_pins(r, 1)) == 2 and BLOCK_OF.get(r) == BLOCK_OF.get(ref)]
        if len(members[far]) == 2 and len(rest_) == 1:
            nxt = rest_[0]
            hp = [n for n in two_pin(nxt) if netof.get((nxt, n)) == far][0]
            hang(nxt, x, ybot, hp, chain=False)
            label(far, x, ybot, (-1, 0))
            return
    terminate(far, x, ybot, (0, 1), ref)


def comb(ref, unit, x, y, refpos=None, valpos=None, hide_val=False, first=15.24, tail=True, skip=()):
    """place an IC (or connector) and wire the passives of each side pin onto a horizontal stub from that pin"""
    emit(ref, unit, x, y, 0, refpos or (x - 10.16, y - 11.43), valpos or (x + 1.27, y - 11.43), hide_val=hide_val)
    pins = unit_pins(ref, unit)
    blk = BLOCK_OF[ref]
    sides = {(-1, 0): {}, (1, 0): {}}
    seen = set()
    for n, (px, py, ang) in pins.items():
        (ox, oy), d = xf(0, px, py, ang)
        gx, gy = x + ox, y + oy
        net = netof.get((ref, n))
        if (round(gx, 2), round(gy, 2)) in seen:
            continue
        seen.add((round(gx, 2), round(gy, 2)))
        if d in sides and net and net != "GND" and net not in RAILS and net not in skip:
            sides[d][(gy, gx)] = net
        else:
            terminate(net, gx, gy, d, ref)
    stubbed = set()
    for d, sp in sides.items():
        col = 0
        for (gy, gx) in sorted(sp, reverse=True):               # bottom pin first: it gets the nearest columns
            net = sp[(gy, gx)]
            parts = []
            if net not in stubbed:
                for r in sorted(members[net], key=lambda r: (re.match(r"[A-Z]+", r).group(0), int(re.search(r"\d+", r).group(0)))):
                    if r == ref or (r, 1) in done or r not in insts or BLOCK_OF.get(r) != blk or len(insts[r]) != 1 or len(unit_pins(r, 1)) != 2:
                        continue
                    parts.append(r)
            leaves = sum(1 for v in netof.values() if v == net) > 1 + len(parts)
            if not parts:
                terminate(net, gx, gy, d, ref)
                continue
            stubbed.add(net)
            xs = []
            for r in parts:
                if (r, 1) in done:
                    continue
                cx = gx + d[0] * (first + col * P)
                col += 1
                hp = [n for n in two_pin(r) if netof.get((r, n)) == net][0]
                hang(r, cx, gy, hp)
                xs.append(cx)
            wire(gx, gy, xs[-1], gy)
            for cx in xs[:-1]:
                junction(cx, gy)
            label(net, gx + d[0] * 1.27, gy, d)
    return


def bus(net, x, y, refs, lab=True):
    """parts that share a net but hang off no chip: a short horizontal wire with the parts hanging from it"""
    xs = []
    for i, r in enumerate(refs):
        cx = x + 7.62 + i * P
        hp = [n for n in two_pin(r) if netof.get((r, n)) == net][0]
        hang(r, cx, y, hp)
        xs.append(cx)
    wire(x, y, xs[-1], y)
    for cx in xs[:-1]:
        junction(cx, y)
    label(net, x, y, (-1, 0))


def lone(ref, x, y):
    """a part with a rail on both ends (decoupling): vertical, both ends labelled / grounded"""
    pins = two_pin(ref)
    top = sorted(pins, key=lambda n: (netof.get((ref, n)) == "GND", n))[0]
    for rot in (0, 180, 90, 270):
        (ox, oy), _ = xf(rot, *pins[top])
        if abs(ox) < 0.01 and oy < 0:
            break
    emit(ref, 1, x, y, rot, (x + 2.54, y - 1.27), (x + 2.54, y + 1.27))
    for n, (px, py, ang) in pins.items():
        (ox, oy), d = xf(rot, px, py, ang)
        terminate(netof.get((ref, n)), x + ox, y + oy, d, ref)


def plain(ref, unit, x, y, refpos=None, valpos=None, hide_val=False, just="left"):
    """place a symbol unrotated with a label / ground / no-connect on every pin"""
    emit(ref, unit, x, y, 0, refpos or (x + 2.54, y - 1.27), valpos or (x + 2.54, y + 1.27), just=just, hide_val=hide_val)
    for n, (px, py, ang) in unit_pins(ref, unit).items():
        (ox, oy), d = xf(0, px, py, ang)
        terminate(netof.get((ref, n)), x + ox, y + oy, d, ref)


def text(t, x, y, size=1.5):
    out.append(f'(text "{t}"\n\t\t(exclude_from_sim no)\n\t\t(at {fmt(x)} {fmt(y)} 0)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size {size} {size})\n\t\t\t)\n\t\t\t(justify left bottom)\n\t\t)\n\t\t(uuid "{U()}")\n\t)')


def frame(title, x1, y1, x2, y2, note=""):
    out.append(f'(rectangle\n\t\t(start {fmt(x1)} {fmt(y1)})\n\t\t(end {fmt(x2)} {fmt(y2)})\n\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type dash)\n\t\t)\n\t\t(fill\n\t\t\t(type none)\n\t\t)\n\t\t(uuid "{U()}")\n\t)')
    text(title, x1 + 1.27, y1 + 3.6, 2.0)
    if note:
        text(note, x1 + 1.27, y1 + 6.4, 1.2)


BLOCKS = {
    "usb": "J1 J5 F1 F2 D2 D4 C1 C21 R3 R4 R33 R34",
    "reg": "U1 C2 C3 D1 R20",
    "amp": "U3 C15 C16 C17 R18 R19 J2 J3 J4",
    "cc": "D3 C18 R21 U4 R22 R23 R24 U5 R25 R26 C19 R27 R28 R29 R30 C20 R31 R32",
    "ba": "U6 L1 D5 C22 C23 C24 C25 C26 C27 C28 C29 R35 R36 R37 R38 R39 R40 R41",
    "bb": "U7 L2 D6 C30 C31 C32 C33 C34 C35 C36 C37 R42 R43 R44 R45 R46 R47 R48",
    "dac": "U2 Y1 R7 C9 C10 C4 C5 C6 C7 C8 R1 R2 R8 R9 R10 R11 SW1 SW2 SW3",
    "aud": "R12 R13 R14 R15 R16 R17 C11 C12 C13 C14",
}
for b_, refs in BLOCKS.items():
    for r in refs.split():
        BLOCK_OF[r] = b_
assert set(BLOCK_OF) == set(insts), set(BLOCK_OF) ^ set(insts)

# ================================================================== row 1: USB inputs | 3.3 V | amplifier
frame("USB-C inputs", 20.32, 21.59, 205.74, 86.36, "J1 = data + power, J5 = power only. Each VBUS: TVS and 1u to ground, then the polyfuse to the boost input. 5.1k Rd on each CC.")
comb("J1", 1, 38.1, 55.88, refpos=(30.48, 34.29), hide_val=True)
comb("J5", 1, 130.81, 55.88, refpos=(123.19, 34.29), hide_val=True)

frame("3.3 V regulator and power LED", 209.55, 21.59, 281.94, 86.36)
plain("U1", 1, 245.11, 41.91, refpos=(245.11, 34.29), valpos=(245.11, 36.83), just=None)
lone("C2", 224.79, 46.99); lone("C3", 266.7, 46.99)
bus("LED_K", 219.71, 66.04, ["D1", "R20"], lab=False)
flag("GND", 264.16, 73.66)

frame("Amplifier and outputs", 285.75, 21.59, 400.05, 86.36, "TDA7297 on 12 V. MUTE/STBY sit at half supply; C15 gives a soft start.")
plain("U3", 1, 307.34, 43.18, refpos=(297.18, 53.34), valpos=(304.8, 53.34))
plain("U3", 2, 307.34, 71.12, refpos=(297.18, 78.74), valpos=(304.8, 78.74))
plain("U3", 3, 334.01, 58.42, refpos=(339.09, 57.15), valpos=(339.09, 59.69))
bus("MUTE", 347.98, 38.1, ["R18", "R19", "C15"])
lone("C16", 392.43, 43.18)
lone("C17", 351.79, 73.66)
for r, x, y in (("J2", 387.35, 60.96), ("J3", 387.35, 71.12), ("J4", 387.35, 81.28)):
    plain(r, 1, x, y, refpos=(x + 3.81, y - 1.27), valpos=(x, y + 5.08), hide_val=True)
flag("+12V", 322.58, 84.455)

# ================================================================== row 2: CC current sensing
frame("USB-C current sensing", 20.32, 90.17, 400.05, 143.51,
      "CCS = (CC1 + CC2) / 2. Above TH_MED (0.34 V) the source offers 1.5 A and ISEL goes high. Above TH_HIGH (0.65 V) it offers 3 A and HIGH pulls the second ILIM resistor to ground.")
Y = 105.41
plain("D3", 1, 38.1, Y + 5.08, refpos=(38.1, Y - 1.27), valpos=(38.1, Y + 1.27), just=None)
flag("VAUX", 53.34, Y + 20.32)
lone("C18", 63.5, Y + 6.35); lone("R21", 76.2, Y + 6.35)
plain("U4", 1, 93.98, Y + 13.97, refpos=(93.98, Y + 19.05), valpos=(93.98, Y + 21.59), just=None)
for r, yy in (("R22", Y + 3.81), ("R23", Y + 11.43), ("R24", Y + 19.05)):
    emit(r, 1, 111.76, yy, 0, (109.22, yy - 1.27), (109.22, yy + 1.27), just="right")
label("VREF", 111.76, Y, (0, -1)); label("TH_HIGH", 111.76, Y + 7.62, (1, 0)); label("TH_MED", 111.76, Y + 15.24, (1, 0)); gnd(111.76, Y + 22.86)
pl5 = lib_pins("Comparator:LM339")
spot = {"2": (194.31, Y + 2.54), "1": (194.31, Y + 26.67), "13": (322.58, Y + 2.54), "14": (322.58, Y + 26.67)}
for u in sorted(insts["U5"]):
    key = [n for n, ps in pl5.items() for p in ps if p[0] == u and n in spot]
    if not key:
        plain("U5", u, 251.46, Y + 13.97, refpos=(255.27, Y + 12.7), valpos=(255.27, Y + 15.24))
for k in ("2", "13", "1", "14"):                     # the 1.5 A comparators own the CCS / ISEL parts
    u = [p[0] for p in pl5[k]][0]
    x, y = spot[k]
    comb("U5", u, x, y, refpos=(x - 5.08, y + 7.62), valpos=(x + 2.54, y + 7.62), first=12.7)

# ================================================================== row 3: boost converters
def boost(x0, title, note, U_, lones):
    frame(title, x0, 147.32, x0 + 186.69, 212.09, note)
    comb(U_, 1, x0 + 106.68, 172.72)
    for i, r in enumerate(lones):
        lone(r, x0 + 139.7 + i * P, 198.12)


boost(20.32, "Boost A: J1 (data port), 5 V to 11.7 V", "Input current limit 0.35 / 1.4 / 2.84 A, set by ISEL_A and HIGH_A.", "U6", ("C22", "C23", "C28", "C29"))
boost(213.36, "Boost B: J5 (power port), 5 V to 12.3 V", "Set slightly higher than boost A, so the power-only port carries the load first.", "U7", ("C30", "C31", "C36", "C37"))

# ================================================================== row 4: DAC | audio filter
frame("USB audio DAC and buttons", 20.32, 215.9, 262.89, 287.02, "PCM2704C, self-powered from 3.3 V. SW1-SW3 are the HID buttons, each with a 3.3k pull-down.")
comb("U2", 1, 116.84, 248.92, refpos=(104.14, 229.87), valpos=(116.84, 229.87), first=12.7)
for i, r in enumerate(("C4", "C5", "C6", "C8")):
    lone(r, 220.98 + i * P, 275.59)

frame("Audio filter and level", 266.7, 215.9, 400.05, 251.46, "Per channel: 330 R + 22 n low-pass, 10k / 2.7k divider, 220 n coupling into the amplifier.")
for ch, x in (("L", 276.86), ("R", 340.36)):
    a, d_ = ("R13", "C11", "R15"), ("R16", "C14")
    if ch == "R":
        a, d_ = ("R12", "C12", "R14"), ("R17", "C13")
    bus("Audio_" + ch, x, 232.41, list(a))
    bus("DIV_" + ch, x + 30.48, 232.41, list(d_), lab=True)

# ERC power flags for the rails that enter through connectors, fuses or diodes
for i, n in enumerate(("VBUS_RAW", "VBUSB_RAW", "VBUS_A", "VBUS_B")):
    flag(n, 273.05, 262.89 + i * 7.62)
text("ERC power flags", 269.24, 256.54, 1.3)

missing = [(r, u) for r in insts for u in insts[r] if (r, u) not in done]
assert not missing, missing
tail = "\n\t(sheet_instances\n\t\t(path \"/\"\n\t\t\t(page \"1\")\n\t\t)\n\t)\n\t(embedded_fonts no)\n)\n"
open(DST, "w").write(head + "\n\t" + "\n\t".join(out) + tail)
print("written", len(out), "items;", len(insts), "parts")
