import sys, json, pcbnew
b = pcbnew.LoadBoard(sys.argv[1]); ren = json.load(open(sys.argv[2])); n = 0
for old, new in ren.items():
    ni = b.FindNet(old)
    if ni is not None:
        ni.SetNetname(new); n += 1
b.Save(sys.argv[3]); print("renamed", n, "nets")
