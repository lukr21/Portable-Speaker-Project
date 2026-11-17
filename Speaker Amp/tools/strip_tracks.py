import sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1])
for t in list(b.GetTracks()):
    b.Remove(t)
b.Save(sys.argv[2])
