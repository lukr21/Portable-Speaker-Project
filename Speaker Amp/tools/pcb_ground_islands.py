import sys, pcbnew
b=pcbnew.LoadBoard(sys.argv[1])
mm=lambda v: round(v/1e6,2)
z=[z for z in b.Zones()][0]
F,B=pcbnew.F_Cu,pcbnew.B_Cu
isl=[]  # (layer, idx, poly)
polys={}
for l in (F,B):
    ps=z.GetFilledPolysList(l); polys[l]=ps
    for i in range(ps.OutlineCount()): isl.append((l,i))
par={k:k for k in isl}
def find(k):
    while par[k]!=k: k=par[k]
    return k
def where(l,pt):
    ps=polys[l]
    for i in range(ps.OutlineCount()):
        if ps.Contains(pt,i,M): return (l,i)
    return None
M=pcbnew.FromMM(0.05)
gnd=b.FindNet("GND").GetNetCode()
def link(items):
    items=[i for i in items if i]
    for a,c in zip(items,items[1:]): par[find(a)]=find(c)
# vias and THT pads join layers
for t in b.GetTracks():
    if t.GetNetCode()==gnd and t.GetClass()=="PCB_VIA": link([where(F,t.GetPosition()),where(B,t.GetPosition())])
for f in b.GetFootprints():
    for p in f.Pads():
        if p.GetNetCode()==gnd and p.HasHole(): link([where(F,p.GetPosition()),where(B,p.GetPosition())])
anchors={}   # island -> list of (x,y) GND copper points inside it
def note(k,pt):
    if k: anchors.setdefault(k,[]).append((pt.x/1e6,pt.y/1e6))
for t in b.GetTracks():
    if t.GetNetCode()!=gnd: continue
    if t.GetClass()=="PCB_VIA":
        note(where(F,t.GetPosition()),t.GetPosition()); note(where(B,t.GetPosition()),t.GetPosition())
    else:
        l=t.GetLayer()
        if l in (F,B):
            ks=[where(l,t.GetStart()),where(l,t.GetEnd())]; link(ks)
for f in b.GetFootprints():
    for p in f.Pads():
        if p.GetNetCode()!=gnd: continue
        for l in (F,B):
            if not p.IsOnLayer(l): continue
            bx=p.GetBoundingBox(); c=p.GetPosition()
            pts=[c,pcbnew.VECTOR2I(bx.GetLeft()-M*4,c.y),pcbnew.VECTOR2I(bx.GetRight()+M*4,c.y),pcbnew.VECTOR2I(c.x,bx.GetTop()-M*4),pcbnew.VECTOR2I(c.x,bx.GetBottom()+M*4)]
            ks=[where(l,q) for q in pts]; link(ks)
            for k in ks: note(k,c)
groups={}
for k in isl: groups.setdefault(find(k),[]).append(k)
big=max(groups.values(),key=len)
print("islands",len(isl),"groups",len(groups))
import math
main=[pt for k in big for pt in anchors.get(k,[])]
out=[]
for g in groups.values():
    if g is big: continue
    pts=[pt for k in g for pt in anchors.get(k,[])]
    if not pts:
        print(" island with no anchor", g); continue
    best=min(((math.hypot(a[0]-m[0],a[1]-m[1]),a,m) for a in pts for m in main))
    print(" isolated group near",best[1],"-> main at",best[2],"dist",round(best[0],2))
    out.append("[unconnected_items]: island\n    x\n    @(%.4f mm, %.4f mm): Island [GND]\n    @(%.4f mm, %.4f mm): Island [GND]\n"%(best[1]+best[2]))
open(sys.argv[2],"w").write("".join(out))
