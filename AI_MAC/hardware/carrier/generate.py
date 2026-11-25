"""Generate the two 7-pin XIAO breakout banks and their fabrication artwork (mm)."""
from pathlib import Path
import zipfile

HERE = Path(__file__).resolve().parent
BANKS = [(9, 4, ["REC", "PTT", "D2", "SD_CS", "SDA", "SCL", "D6"]),
         (24.24, 29.24, ["V5_LOCAL", "GND", "3V3", "MOSI", "MISO", "SCK", "D7"])]
W, H = 33.24, 23.24
OUT = HERE / "fab"
OUT.mkdir(exist_ok=True)
board = ['(kicad_pcb (version 20221018) (generator pcbnew) (general (thickness 1.6))',
         '(paper "A4") (layers (0 "F.Cu" signal) (31 "B.Cu" signal) (36 "B.SilkS" user "b.silkscreen") (37 "F.SilkS" user "f.silkscreen") (38 "B.Mask" user) (39 "F.Mask" user) (44 "Edge.Cuts" user))',
         '(setup (pad_to_mask_clearance 0))', '(net 0 "")']
pads, tracks = [], []
for i, (socket, fanout, nets) in enumerate(BANKS):
    for row, net in enumerate(nets):
        number = 1 + 7 * i + row
        board.append(f'(net {number} "{net}")')
        y = 4 + 2.54 * row
        for x, name in [(socket, "J"), (fanout, "W")]:
            ref = f"{name}{number}"
            board.extend([f'(footprint "VoiceCard:ThroughHole" (layer "F.Cu") (at {x} {y})',
                          f'(fp_text reference "{ref}" (at 0 0) (layer "F.SilkS") hide (effects (font (size 1 1) (thickness 0.15))))',
                          f'(fp_text value "{net}" (at 0 0) (layer "F.SilkS") hide (effects (font (size 1 1) (thickness 0.15))))',
                          f'(pad "1" thru_hole circle (at 0 0) (size 1.8 1.8) (drill 1) (layers "*.Cu" "*.Mask") (net {number} "{net}")))'])
            pads.append((x, y))
        tracks.append((socket, y, fanout, y))
        board.append(f'(segment (start {socket} {y}) (end {fanout} {y}) (width 0.55) (layer "F.Cu") (net {number}))')
edges = [(0,0,W,0),(W,0,W,H),(W,H,0,H),(0,H,0,0)]
for x,y,a,b in edges:
    board.append(f'(gr_line (start {x} {y}) (end {a} {b}) (stroke (width 0.05) (type default)) (layer "Edge.Cuts"))')
mark = [(12,2,19,2),(12,2,12,3),(4,2,5,2)]
for x,y,a,b in mark:
    board.append(f'(gr_line (start {x} {y}) (end {a} {b}) (stroke (width 0.2) (type default)) (layer "F.SilkS"))')
(HERE/"carrier.kicad_pcb").write_text("\n".join(board+[')']),encoding="ascii")

def xy(x,y):
    return f"X{round(x*1000000):d}Y{round((H-y)*1000000):d}"
def artwork(ext,diam,flashes,lines):
    data = ["G04 VoiceCard top view; millimetres*", "%FSLAX46Y46*%", "%MOMM*%", "%LPD*%",
            f"%ADD10C,{diam}*%", "%ADD11C,0.550*%", "D10*"]
    data.extend(xy(x,y)+"D03*" for x,y in flashes)
    if flashes: data.append("D11*")
    for x,y,a,b in lines:
        data.extend([xy(x,y)+"D02*",xy(a,b)+"D01*"])
    (OUT/f"carrier.{ext}").write_text("\n".join(data+["M02*",""]),encoding="ascii")
artwork("GTL",1.8,pads,tracks)
artwork("GBL",1.8,pads,[])
for ext in ("GTS","GBS"): artwork(ext,1.9,pads,[])
artwork("GTO",0.2,[],mark)
artwork("GKO",0.05,[],edges)
drill=["M48","METRIC,TZ","T01C1.000","%","G90","T01"]
drill.extend(f"X{x:.3f}Y{H-y:.3f}" for x,y in pads)
(OUT/"carrier-PTH.drl").write_text("\n".join(drill+["M30",""]),encoding="ascii")
with zipfile.ZipFile(HERE/"carrier-gerber.zip","w",zipfile.ZIP_DEFLATED) as z:
    for path in sorted(OUT.iterdir()):z.write(path,path.name)
assert len(set(pads))==28 and len(tracks)==14

