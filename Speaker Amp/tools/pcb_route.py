#!/usr/bin/env python3
"""Small two-layer grid router for low-current signal nets (run with KiCad's python).
usage: pcb_route.py in.kicad_pcb drc.rpt out.kicad_pcb [width_mm] [skip,nets] [only,nets]
Reads the unconnected pairs from a kicad-cli DRC report and connects each with an
A* search on a 0.1 mm grid, honouring clearance to all other copper, holes and the
board edge. Existing copper is never moved."""
import sys, re, heapq, math, pcbnew

src, rpt, dst = sys.argv[1:4]
W = float(sys.argv[4]) if len(sys.argv) > 4 else 0.2
SKIP = set(sys.argv[5].split(",")) if len(sys.argv) > 5 else set()
ONLY = set(sys.argv[6].split(",")) if len(sys.argv) > 6 else None
CLR = 0.2
G = 0.1                                   # grid pitch, mm
VIA_D, VIA_H = 0.6, 0.3
b = pcbnew.LoadBoard(src)
mm = lambda v: v / 1e6
M = pcbnew.FromMM
bb = b.GetBoardEdgesBoundingBox()
X0, Y0 = mm(bb.GetLeft()) - 1, mm(bb.GetTop()) - 1
NX = int((mm(bb.GetWidth()) + 2) / G) + 1
NY = int((mm(bb.GetHeight()) + 2) / G) + 1
F, B = pcbnew.F_Cu, pcbnew.B_Cu
FREE, BLOCK = 0, -1
# owner[layer][iy*NX+ix]: 0 free, -1 blocked, n = only net n may use it. "t" grids are for track centres, "v" for via centres.
own_t = [[FREE] * (NX * NY) for _ in range(2)]
own_v = [[FREE] * (NX * NY) for _ in range(2)]


def mark(grid, x1, y1, x2, y2, r, net, rect=False):
    """inflate segment (or rectangle x1..x2,y1..y2) by r and claim cells for net"""
    lox, hix = min(x1, x2) - r, max(x1, x2) + r
    loy, hiy = min(y1, y2) - r, max(y1, y2) + r
    ix0, ix1 = max(0, int(math.floor((lox - X0) / G))), min(NX - 1, int(math.ceil((hix - X0) / G)))
    iy0, iy1 = max(0, int(math.floor((loy - Y0) / G))), min(NY - 1, int(math.ceil((hiy - Y0) / G)))
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    for iy in range(iy0, iy1 + 1):
        y = Y0 + iy * G
        row = iy * NX
        for ix in range(ix0, ix1 + 1):
            x = X0 + ix * G
            if rect:
                ex = max(min(x1, x2) - x, 0, x - max(x1, x2)); ey = max(min(y1, y2) - y, 0, y - max(y1, y2))
                if ex * ex + ey * ey > r * r:
                    continue
            else:
                t = 0 if L2 == 0 else max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / L2))
                px, py = x1 + t * dx - x, y1 + t * dy - y
                if px * px + py * py > r * r:
                    continue
            c = grid[row + ix]
            if c == FREE:
                grid[row + ix] = net
            elif c != net:
                grid[row + ix] = BLOCK


prims = {}


def cells_of(a, r, rect):
    x1, y1, x2, y2 = a
    out = []
    ix0, ix1 = int(math.floor((min(x1, x2) - r - X0) / G)), int(math.ceil((max(x1, x2) + r - X0) / G))
    iy0, iy1 = int(math.floor((min(y1, y2) - r - Y0) / G)), int(math.ceil((max(y1, y2) + r - Y0) / G))
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    for iy in range(iy0, iy1 + 1):
        y = Y0 + iy * G
        for ix in range(ix0, ix1 + 1):
            x = X0 + ix * G
            if rect:
                if min(x1, x2) - 0.01 <= x <= max(x1, x2) + 0.01 and min(y1, y2) - 0.01 <= y <= max(y1, y2) + 0.01:
                    out.append((ix, iy))
            else:
                t = 0 if L2 == 0 else max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / L2))
                if (x1 + t * dx - x) ** 2 + (y1 + t * dy - y) ** 2 <= (r + 0.03) ** 2:
                    out.append((ix, iy))
    return out


def cluster(net, x, y):
    """all grid cells of the net's copper that are electrically joined to the copper at (x, y)"""
    cu = {}
    for layers, kind, a, hw in prims.get(net, []):
        if kind == "rect":      # pads may be round or oval: only the inscribed core counts as "touching"
            mx, my = (a[0] + a[2]) / 2, (a[1] + a[3]) / 2
            a = (mx + (a[0] - mx) * 0.6, my + (a[1] - my) * 0.6, mx + (a[2] - mx) * 0.6, my + (a[3] - my) * 0.6)
        for c in cells_of(a, hw, kind == "rect"):
            for l in layers:
                cu[(l,) + c] = len(layers) > 1 or cu.get((l,) + c, False)
    sx, sy = cell(x, y)
    seeds = [k for k in cu if abs(k[1] - sx) <= 3 and abs(k[2] - sy) <= 3]
    seen = set(seeds); st = list(seeds)
    while st:
        l, cx, cy = st.pop()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                k = (l, cx + dx, cy + dy)
                if k in cu and k not in seen:
                    seen.add(k); st.append(k)
        k = (1 - l, cx, cy)
        if cu[(l, cx, cy)] and k in cu and k not in seen:
            seen.add(k); st.append(k)
    return seen


def claim(layers, kind, a, net, hw):
    """register a copper object: kind 'seg' (x1,y1,x2,y2) or 'rect'; hw = half width of the object itself (seg)"""
    prims.setdefault(net, []).append((tuple(layers), kind, a, hw))
    for l in layers:
        mark(own_t[l], *a, hw + CLR + W / 2 - 0.001, net, rect=(kind == "rect"))
        mark(own_v[l], *a, hw + CLR + VIA_D / 2 - 0.001, net, rect=(kind == "rect"))


LIDX = {F: 0, B: 1}
for f in b.GetFootprints():
    for p in f.Pads():
        n = p.GetNetCode() if p.GetNetCode() > 0 else BLOCK
        ls = [i for l, i in LIDX.items() if p.IsOnLayer(l)]
        bx = p.GetBoundingBox()
        if ls:
            claim(ls, "rect", (mm(bx.GetLeft()), mm(bx.GetTop()), mm(bx.GetRight()), mm(bx.GetBottom())), n, 0)
        if p.HasHole():
            c = p.GetPosition(); h = mm(max(p.GetDrillSize().x, p.GetDrillSize().y)) / 2
            for l in (0, 1):
                mark(own_t[l], mm(c.x), mm(c.y), mm(c.x), mm(c.y), h + 0.25 + W / 2, n)
                mark(own_v[l], mm(c.x), mm(c.y), mm(c.x), mm(c.y), h + 0.3 + VIA_D / 2, n)
for t in b.GetTracks():
    n = t.GetNetCode()
    s, e = t.GetStart(), t.GetEnd()
    if t.GetClass() == "PCB_VIA":
        claim([0, 1], "seg", (mm(s.x), mm(s.y), mm(s.x), mm(s.y)), n, mm(t.GetWidth(F)) / 2)
    elif t.GetLayer() in LIDX:
        claim([LIDX[t.GetLayer()]], "seg", (mm(s.x), mm(s.y), mm(e.x), mm(e.y)), n, mm(t.GetWidth()) / 2)
# board edge: keep copper 0.5 mm away
for d in b.GetDrawings():
    if d.GetLayerName() == "Edge.Cuts":
        o = d.GetPolyShape().Outline(0)
        pts = [(mm(o.CPoint(i).x), mm(o.CPoint(i).y)) for i in range(o.PointCount())]
        for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
            for l in (0, 1):
                mark(own_t[l], x1, y1, x2, y2, 0.55 + W / 2, BLOCK)
                mark(own_v[l], x1, y1, x2, y2, 0.55 + VIA_D / 2, BLOCK)

cell = lambda x, y: (int(round((x - X0) / G)), int(round((y - Y0) / G)))
NB = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0), (1, 1, 1.42), (1, -1, 1.42), (-1, 1, 1.42), (-1, -1, 1.42)]
VIA_COST, B_PEN = 40.0, 1.15


def route(net, ax, ay, bx_, by_):
    ok = lambda l, i: own_t[l][i] in (FREE, net)
    tx, ty = cell(bx_, by_)
    A = cluster(net, ax, ay); T = cluster(net, bx_, by_)
    if A & T:
        return []
    starts = [k for k in A if ok(k[0], k[2] * NX + k[1])]
    T = {k for k in T if ok(k[0], k[2] * NX + k[1])}
    if not starts or not T:
        return None
    dist, prev, pq = {}, {}, []
    for s_ in starts:
        dist[s_] = 0.0; heapq.heappush(pq, (math.hypot(s_[1] - tx, s_[2] - ty), s_))
    end = None
    while pq:
        f_, cur = heapq.heappop(pq)
        l, x, y = cur
        d = dist[cur]
        if f_ - math.hypot(x - tx, y - ty) > d + 1e-6:
            continue
        if cur in T:
            end = cur; break
        for dx, dy, c in NB:
            nx_, ny_ = x + dx, y + dy
            if not (0 <= nx_ < NX and 0 <= ny_ < NY):
                continue
            i = ny_ * NX + nx_
            if not ok(l, i):
                continue
            if dx and dy and not (ok(l, y * NX + nx_) and ok(l, ny_ * NX + x)):
                continue
            nd = d + c * (B_PEN if l == 1 else 1.0)
            k = (l, nx_, ny_)
            if nd < dist.get(k, 1e18):
                dist[k] = nd; prev[k] = cur
                heapq.heappush(pq, (nd + math.hypot(nx_ - tx, ny_ - ty), k))
        i = y * NX + x
        if own_v[0][i] in (FREE, net) and own_v[1][i] in (FREE, net) and ok(1 - l, i):
            k = (1 - l, x, y)
            nd = d + VIA_COST
            if nd < dist.get(k, 1e18):
                dist[k] = nd; prev[k] = cur
                heapq.heappush(pq, (nd + math.hypot(x - tx, y - ty), k))
    if end is None:
        return None
    path = [end]
    while path[-1] in prev:
        path.append(prev[path[-1]])
    return path[::-1]


def commit(netcode, path):
    ni = b.FindNet(netcode)
    P = lambda x, y: pcbnew.VECTOR2I(M(X0 + x * G), M(Y0 + y * G))
    i = 0
    while i < len(path) - 1:
        l, x, y = path[i]
        l2, x2, y2 = path[i + 1]
        if l2 != l:
            v = pcbnew.PCB_VIA(b); v.SetPosition(P(x, y)); v.SetWidth(F, M(VIA_D)); v.SetDrill(M(VIA_H)); v.SetNet(ni); v.SetLayerPair(F, B)
            b.Add(v)
            claim([0, 1], "seg", (X0 + x * G, Y0 + y * G, X0 + x * G, Y0 + y * G), netcode, VIA_D / 2)
            i += 1
            continue
        dx, dy = x2 - x, y2 - y
        j = i + 1
        while j + 1 < len(path) and path[j + 1][0] == l and (path[j + 1][1] - path[j][1], path[j + 1][2] - path[j][2]) == (dx, dy):
            j += 1
        t = pcbnew.PCB_TRACK(b); t.SetStart(P(x, y)); t.SetEnd(P(path[j][1], path[j][2])); t.SetWidth(M(W))
        t.SetLayer(F if l == 0 else B); t.SetNet(ni); b.Add(t)
        claim([l], "seg", (X0 + x * G, Y0 + y * G, X0 + path[j][1] * G, Y0 + path[j][2] * G), netcode, W / 2)
        i = j


txt = open(rpt).read()
pairs = re.findall(r"\[unconnected_items\].*?\n.*?\n\s*@\(([\d\.\-]+) mm, ([\d\.\-]+) mm\): (.*?)\n\s*@\(([\d\.\-]+) mm, ([\d\.\-]+) mm\): (.*?)\n", txt)
jobs = []
for ax, ay, ad, bx_, by_, bd in pairs:
    nm = re.search(r"\[([^\]]+)\]", ad).group(1)
    if (nm == "GND" and not ad.startswith("Island")) or nm in SKIP or (ONLY and nm not in ONLY) or "Zone" in ad or "Zone" in bd:
        continue
    jobs.append((math.hypot(float(ax) - float(bx_), float(ay) - float(by_)), nm, float(ax), float(ay), float(bx_), float(by_)))
done = fail = 0
for _, nm, ax, ay, bx_, by_ in sorted(jobs):
    code = b.FindNet(nm).GetNetCode()
    p = route(code, ax, ay, bx_, by_)
    if p == []:
        continue
    if p is None:
        fail += 1; print("FAILED", nm, ax, ay, bx_, by_)
    else:
        commit(code, p); done += 1

# ---- ground stitching: any GND pad the zones could not reach gets a short track to a via into the other plane
def stitch(net, x, y):
    ok = lambda l, i: own_t[l][i] in (FREE, net)
    A = [k for k in cluster(net, x, y) if ok(k[0], k[2] * NX + k[1])]
    if not A:
        return None
    dist = {k: 0.0 for k in A}; prev = {}; pq = [(0.0, k) for k in A]
    heapq.heapify(pq)
    while pq:
        d, cur = heapq.heappop(pq)
        if d > dist[cur] + 1e-9:
            continue
        l, cx, cy = cur
        i = cy * NX + cx
        if own_v[0][i] in (FREE, net) and own_v[1][i] in (FREE, net) and ok(1 - l, i) and d >= 6:
            path = [cur]
            while path[-1] in prev:
                path.append(prev[path[-1]])
            return path[::-1] + [(1 - l, cx, cy)]
        if d > 60:
            break
        for dx, dy, c in NB:
            nx_, ny_ = cx + dx, cy + dy
            if not (0 <= nx_ < NX and 0 <= ny_ < NY) or not ok(l, ny_ * NX + nx_):
                continue
            if dx and dy and not (ok(l, cy * NX + nx_) and ok(l, ny_ * NX + cx)):
                continue
            k = (l, nx_, ny_)
            if d + c < dist.get(k, 1e18):
                dist[k] = d + c; prev[k] = cur; heapq.heappush(pq, (d + c, k))
    return None


gnd = b.FindNet("GND").GetNetCode()
pts = set()
for ax, ay, ad, bx_, by_, bd in pairs:
    for x, y, dsc in ((ax, ay, ad), (bx_, by_, bd)):
        if "[GND]" in dsc and dsc.startswith("Pad"):
            pts.add((float(x), float(y)))
W_SAVE = W
for x, y in ([] if ONLY else sorted(pts)):
    pth = stitch(gnd, x, y)
    if pth is None:
        print("STITCH FAILED", x, y)
    else:
        commit(gnd, pth); print("stitched", x, y)
# pads with a single thermal spoke: connect them solidly instead
for m in re.finditer(r"\[starved_thermal\].*?\n.*?\n.*?\n\s*@\(([\d\.\-]+) mm, ([\d\.\-]+) mm\): Pad (\S+) \[GND\] of (\S+)", txt):
    f = b.FindFootprintByReference(m.group(4))
    for pd in f.Pads():
        if pd.GetNumber() == m.group(3):
            pd.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
b.Save(dst)
print("routed", done, "failed", fail)
