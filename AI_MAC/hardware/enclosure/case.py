"""Build the serviceable enclosure as STL and an editable OpenSCAD model."""
from pathlib import Path
import struct
import numpy as np
from manifold3d import Manifold as M

HERE=Path(__file__).resolve().parent
# Each solid is (lower corner XYZ, size XYZ) in millimetres.
body=[((0,0,0),(112,72,27))]
cut=[((2,2,2),(108,68,26)), ((-1,11,11),(4,13,8)), ((96,69,12),(13,4,6))]
# Four M2 screw towers; lid attaches to their pilot holes.
posts=[(5,5),(107,5),(5,67),(107,67)]
def cube(spec):
    pos,size=spec
    return M.cube(size).translate(pos)
def tube(x,y,z,h,r):
    return M.cylinder(h,r,r,40).translate((x,y,z))
base=cube(body[0])
for box in cut:base-=cube(box)
for x,y in posts: base+=tube(x,y,0,27,3)
for x,y in posts: base-=tube(x,y,17,11,.82)
holes=[(82,17,3.55),(96,17,3.55),(79,43,2.0),(70,43,2.5)]
lid=cube(((0,0,0),(112,72,2)))
for x,y,r in holes+[(x,y,1.15) for x,y in posts]:lid-=tube(x,y,-1,4,r)
def stl(solid,name):
    mesh=solid.to_mesh()
    p=np.asarray(mesh.vert_properties)[:,:3]
    with (HERE/name).open("wb") as f:
        f.write(b"VoiceCard millimetres".ljust(80,b"\0"));f.write(struct.pack("<I",len(mesh.tri_verts)))
        for tri in mesh.tri_verts:
            v=p[tri]; normal=np.cross(v[1]-v[0],v[2]-v[0]);normal/=np.linalg.norm(normal)
            f.write(struct.pack("<12fH",*normal,*v.flatten(),0))
    assert solid.volume()>0 and solid.status().name=="NoError"
stl(base,"base.stl");stl(lid,"lid.stl")
def scube(spec):
    pos,size=spec
    return f"translate({list(pos)}) cube({list(size)});"
def scyl(x,y,z,h,r):
    return f"translate([{x},{y},{z}]) cylinder(h={h},r={r});"
scad=["$fn=40;",'part="base";','if(part=="base") difference(){union(){difference(){',scube(body[0]),*[scube(b) for b in cut],"}",*[scyl(x,y,0,27,3) for x,y in posts],"}",*[scyl(x,y,17,11,.82) for x,y in posts],"} else difference(){",scube(((0,0,0),(112,72,2))),*[scyl(x,y,-1,4,r) for x,y,r in holes+[(x,y,1.15) for x,y in posts]],"}"]
(HERE/"case.scad").write_text("\n".join(scad),encoding="ascii")

