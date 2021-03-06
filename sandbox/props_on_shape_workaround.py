#!/usr/bin/env python
# coding: utf-8

# Copyright 2018-2019 Guillaume Florent, Thomas Paviot

# This file is part of cadracks-ide.
#
# cadracks-ide is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# cadracks-ide is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with cadracks-ide.  If not, see <https://www.gnu.org/licenses/>.

from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeTorus
from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRepBndLib import brepbndlib_Add
from OCC.Display.SimpleGui import init_display

attached_text = {}


def print_xy_click(shp, *kwargs):
    for shape in shp:
        print("Shape selected: ", shape)
    print(kwargs)


def compute_bbox(shp, *kwargs):
    print("Compute bbox for %s " % shp)
    for shape in shp:
        bbox = Bnd_Box()
        brepbndlib_Add(shape, bbox)
        xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()
        dx = xmax - xmin
        dy = ymax - ymin
        dz = zmax - zmin
        print("Selected shape bounding box : dx=%f, dy=%f, dz=%f." % (dx, dy, dz))
        print("               bounding box center: x=%f, y=%f, z=%f" % (xmin + dx/2.,
                                                                        ymin + dy/2.,
                                                                        zmin + dz/2.))
        print(attached_text[shape])

display, start_display, add_menu, add_function_to_menu = init_display()
# register callbacks
display.register_select_callback(print_xy_click)
display.register_select_callback(compute_bbox)
# creating geometry
my_torus = BRepPrimAPI_MakeBox(10., 20., 30.).Shape()
my_box = BRepPrimAPI_MakeTorus(30., 5.).Shape()

attached_text[my_torus] = "Hello from Torus"
attached_text[my_box] = "Hello from Box"
# and finally display geometry
display.DisplayShape(my_torus)
display.DisplayShape(my_box, update=True)
start_display()