import sys
from pathlib import Path
p = Path(sys.argv[1]); capval = sys.argv[2]
s = p.read_text()
anchor = chr(60) + "Param name=" + chr(34) + "DynamicCLCoeff" + chr(34) + " value=" + chr(34) + "2" + chr(34) + "/" + chr(62)
assert s.count(anchor) == 1, "anchor count=%d" % s.count(anchor)
inject = anchor + "\n    " + chr(60) + "Param name=" + chr(34) + "DynamicCLForceCap" + chr(34) + " value=" + chr(34) + capval + chr(34) + "/" + chr(62)
s = s.replace(anchor, inject)
p.write_text(s)
print("injected DynamicCLForceCap=" + capval)
