$fn=40;
part="base";
if(part=="base") difference(){union(){difference(){
translate([0, 0, 0]) cube([112, 72, 27]);
translate([2, 2, 2]) cube([108, 68, 26]);
translate([-1, 11, 11]) cube([4, 13, 8]);
translate([96, 69, 12]) cube([13, 4, 6]);
}
translate([5,5,0]) cylinder(h=27,r=3);
translate([107,5,0]) cylinder(h=27,r=3);
translate([5,67,0]) cylinder(h=27,r=3);
translate([107,67,0]) cylinder(h=27,r=3);
}
translate([5,5,17]) cylinder(h=11,r=0.82);
translate([107,5,17]) cylinder(h=11,r=0.82);
translate([5,67,17]) cylinder(h=11,r=0.82);
translate([107,67,17]) cylinder(h=11,r=0.82);
} else difference(){
translate([0, 0, 0]) cube([112, 72, 2]);
translate([82,17,-1]) cylinder(h=4,r=3.55);
translate([96,17,-1]) cylinder(h=4,r=3.55);
translate([79,43,-1]) cylinder(h=4,r=2.0);
translate([70,43,-1]) cylinder(h=4,r=2.5);
translate([5,5,-1]) cylinder(h=4,r=1.15);
translate([107,5,-1]) cylinder(h=4,r=1.15);
translate([5,67,-1]) cylinder(h=4,r=1.15);
translate([107,67,-1]) cylinder(h=4,r=1.15);
}