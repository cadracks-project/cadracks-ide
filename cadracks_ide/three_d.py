# coding: utf-8

# Copyright 2018-2019 Guillaume Florent

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

r"""3D visualization of geometry"""

from __future__ import division

import imp
from os.path import isdir, splitext
# from random import randint
import logging
import json
import math

import wx
from OCC.Core.gp import gp_Pnt, gp_Vec
from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRepBndLib import brepbndlib_Add

from corelib.core.python_ import is_valid_python
from aocutils.display.wx_viewer import Wx3dViewer, colour_wx_to_occ
from aocutils.analyze.bounds import BoundingBox
# from aocutils.brep.edge_make import edge
from aocxchange.step import StepImporter
from aocxchange.iges import IgesImporter
from aocxchange.stl import StlImporter

from cadracks_core.factories import anchorable_part_from_py_script, \
    anchorable_part_from_stepzip, anchorable_part_from_library
from cadracks_core.anchors import AnchorTransformation, Anchor

from cadracks_ide.sequences import color_from_sequence

logger = logging.getLogger(__name__)

# Hack to workaround issue #629 of PythonOCC
extra_info = {}


def display_extra_info(shp, *kwargs):
    r"""Display extra info (properties) about a shape

    The message box is triggered by a shape selection in the viewer

    Parameters
    ----------
    shp : list
        List of selected shapes
    kwargs : dict

    """

    for shape in shp:
        message = ["%s" % shp, ""]

        bbox = Bnd_Box()
        brepbndlib_Add(shape, bbox)
        xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()
        dx = xmax - xmin
        dy = ymax - ymin
        dz = zmax - zmin
        message.append("Bounding box :")
        message.append("  dx=%f, dy=%f, dz=%f." % (dx, dy, dz))
        message.append("Bounding box center :")
        message.append("  x=%f, y=%f, z=%f" % (xmin + dx/2., ymin + dy/2., zmin + dz/2.))

        message.append("")

        for prop_name, prop_value in extra_info[shape].items():
            message.append(" %s : %s %s" % (prop_name,
                                            str(prop_value["value"]),
                                            "[" + prop_value["unit"] + "]" if prop_value["unit"] is not None else ""))

        _ = wx.MessageBox("\n".join(message),
                          caption="Part Info",
                          style=wx.OK | wx.ICON_INFORMATION)


class ThreeDPanel(Wx3dViewer):
    r"""Panel containing topology information about the loaded shape"""
    def __init__(self,
                 parent,
                 model,
                 viewer_background_color=(50., 50., 50.),
                 object_transparency=0.2, text_height=20,
                 text_colour=(0., 0., 0.)):
        super(ThreeDPanel, self).__init__(
            parent=parent, viewer_background_color=viewer_background_color)

        self.model = model
        self.model.observe("selected_changed", self.on_selected_change)

        self.viewer_display.View.SetBackgroundColor(
            colour_wx_to_occ(viewer_background_color))

        self.objects_transparency = object_transparency
        self.text_height = text_height
        self.text_colour = text_colour

        self.viewer_display.register_select_callback(display_extra_info)

        self.Bind(wx.EVT_SIZE, self.OnSize)

    def OnSize(self, event):
        r"""The panel gets resized"""
        self.Layout()

    def on_selected_change(self, change):
        """Callback function for listener"""

        # TODO: investigate why importing Part
        # at top of file causes an app crash
        from cadracks_core.model import Part

        logger.debug("Selection changed")

        sel = self.model.selected

        logger.debug("sel : %s" % sel)

        if not isdir(sel):
            # what extension ?
            ext = splitext(sel)[1].lower()

            logger.info("File extension : %s" % ext)

            if ext == ".py":
                with open(sel) as f:
                    content = f.read()

                if is_valid_python(content) is True:
                    busy_info = wx.BusyInfo("Loading Python defined geometry ...")
                    try:
                        module_ = imp.load_source(sel, sel)

                        has_shape = hasattr(module_, "__shape__")
                        has_shapes = hasattr(module_, "__shapes__")
                        has_anchors = hasattr(module_, "__anchors__")
                        has_properties = hasattr(module_, "__properties__")
                        has_assembly = hasattr(module_, "__assembly__")
                        has_assemblies = hasattr(module_, "__assemblies__")

                        self.erase_all()

                        if has_shapes is True:
                            logger.info("%s has shapeS" % sel)
                            for i, shape in enumerate(module_.__shapes__):
                                self.display_shape(
                                    shape,
                                    color_=colour_wx_to_occ(
                                        color_from_sequence(i, "colors")))

                        elif has_assembly is True:
                            logger.info("%s has assembly" % sel)
                            try:
                                self.display_assembly(module_.__assembly__)
                                self.viewer_display.FitAll()
                            except KeyError as ke:
                                self.erase_all()
                                logger.exception(ke)

                        elif has_assemblies is True:
                            logger.info("%s has assemblies" % sel)
                            try:
                                self.display_assemblies(module_.__assemblies__)
                                self.viewer_display.FitAll()
                            except KeyError as ke:
                                self.erase_all()
                                logger.exception(ke)
                        # elif has_shape is True and has_anchors is True:
                        elif has_shape is True:
                            if has_anchors is False:
                                logger.info("%s has shape" % sel)
                                self.display_shape(module_.__shape__)
                            else:
                                logger.info("%s has shape and anchors" % sel)
                                p = anchorable_part_from_py_script(sel)
                                self.display_part(p)
                            self.viewer_display.FitAll()
                        else:
                            self.erase_all()
                            logger.warning("Nothing to display")
                    except Exception as e:
                        logger.error(str(e))
                    finally:
                        del busy_info
                else:  # the file is not a valid Python file
                    logger.warning("Not a valid python file")
                    self.erase_all()

            elif ext in [".step", ".stp"]:
                self.erase_all()
                busy_info = wx.BusyInfo("Loading STEP ...")
                try:
                    shapes = StepImporter(sel).shapes
                    logger.info("%i shapes in %s" % (len(shapes), sel))
                    for shape in shapes:
                        color_255 = (255, 255, 255)
                        self.display_shape(shape,
                                           color_=colour_wx_to_occ(color_255),
                                           transparency=0.1)
                        self.viewer_display.FitAll()
                except Exception as e:
                    logger.error(str(e))
                finally:
                    del busy_info

            elif ext in [".iges", ".igs"]:
                self.erase_all()
                busy_info = wx.BusyInfo("Loading IGES ...")
                try:
                    shapes = IgesImporter(sel).shapes
                    logger.info("%i shapes in %s" % (len(shapes), sel))
                    for shape in shapes:
                        color_255 = (51, 255, 255)
                        self.display_shape(shape,
                                           color_=colour_wx_to_occ(color_255),
                                           transparency=0.1)
                        self.viewer_display.FitAll()
                except Exception as e:
                    logger.error(str(e))
                finally:
                    del busy_info

            elif ext == ".stl":
                self.erase_all()
                busy_info = wx.BusyInfo("Loading STL ...")
                try:
                    shape = StlImporter(sel).shape
                    color_255 = (0, 255, 0)
                    self.display_shape(shape,
                                       color_=colour_wx_to_occ(color_255),
                                       transparency=0.1)
                    self.viewer_display.FitAll()
                except Exception as e:
                    logger.error(str(e))
                finally:
                    del busy_info

            elif ext == ".json":  # parts library
                self.erase_all()

                is_library_file = False

                with open(sel) as json_file:
                    if "metadata" in json_file.read():
                        is_library_file = True

                if is_library_file is True:
                    busy_info = wx.BusyInfo("Loading parts library ...")
                    try:
                        with open(sel) as json_file:
                            json_file_content = json.load(json_file)
                            # print(json_file_content["data"].keys())
                            # find the biggest bounding box
                            biggest_bb = [0, 0, 0]
                            # smallest_bb = [0, 0, 0]
                            for i, k in enumerate(json_file_content["data"].keys()):
                                library_part = anchorable_part_from_library(sel, k)
                                bb = BoundingBox(library_part.shape)
                                if bb.x_span > biggest_bb[0]:
                                    biggest_bb[0] = bb.x_span
                                # if bb.x_span < smallest_bb[0]:
                                #     smallest_bb[0] = bb.x_span
                                if bb.y_span > biggest_bb[1]:
                                    biggest_bb[1] = bb.y_span
                                # if bb.y_span < smallest_bb[1]:
                                #     smallest_bb[1] = bb.y_span
                                if bb.z_span > biggest_bb[2]:
                                    biggest_bb[2] = bb.z_span
                                # if bb.z_span < smallest_bb[2]:
                                #     smallest_bb[2] = bb.y_span
                            biggest_dimension = max(biggest_bb)
                            # smallest_dimension = min(smallest_bb)

                            nb_per_row = int(math.sqrt(len(json_file_content["data"].keys())))

                            for i, k in enumerate(json_file_content["data"].keys()):
                                library_part = anchorable_part_from_library(sel, k)
                                x_pos = biggest_dimension*2 * (i % nb_per_row)
                                y_pos = biggest_dimension*2 * (i // nb_per_row)

                                # Translate using an AnchorTransformation
                                library_part.add_matrix_generator(
                                    AnchorTransformation(Anchor(p=(0, 0, 0),
                                                                u=(1, 0, 0),
                                                                v=(0, 1, 0),
                                                                name='a'),
                                                         Anchor(p=(x_pos, y_pos, 0),
                                                                u=(1, 0, 0),
                                                                v=(0, 1, 0),
                                                                name='b')))
                                self.display_part(library_part,
                                                  transparency=0.2,
                                                  anchor_names_height=10)
                                pnt_message = gp_Pnt(x_pos + biggest_dimension / 5,
                                                     y_pos + biggest_dimension / 5,
                                                     0)
                                self.display_message(pnt_message,
                                                     k,
                                                     message_color=(1, 1, 1),
                                                     height=20)
                                self.viewer_display.FitAll()
                    except Exception as e:
                        logger.error(str(e))
                    finally:
                        del busy_info
            elif ext == ".stepzip":
                self.erase_all()
                busy_info = wx.BusyInfo("Loading STEPZIP ...")
                try:
                    self.display_part(anchorable_part_from_stepzip(sel),
                                      transparency=0.2)
                    self.viewer_display.FitAll()
                except Exception as e:
                    logger.error(str(e))
                finally:
                    del busy_info
            else:
                logger.error("File has an extension %s that is not "
                             "handled by the 3D panel" % ext)
                self.erase_all()

        else:  # a directory is selected
            self.erase_all()

        self.Layout()

        logger.debug("code change detected in 3D panel")

    # def _display_anchors(self, anchors):
    #     for k, anchor in anchors.items():
    #         vec_direction = gp_Vec(*anchor["direction"])
    #         vec_direction.Multiply(100. / vec_direction.Magnitude())
    #
    #         to_arrow_cone_start = gp_Vec(vec_direction.X(),
    #                                      vec_direction.Y(),
    #                                      vec_direction.Z())
    #         to_arrow_cone_start.Multiply(4./5.)
    #
    #         arrow_cone = gp_Vec(vec_direction.X(),
    #                             vec_direction.Y(),
    #                             vec_direction.Z())
    #         arrow_cone.Multiply(1./5.)
    #
    #         edge_start = gp_Pnt(*anchor["position"])
    #         edge_end = edge_start.Translated(vec_direction)
    #
    #         # Display the line in yellow
    #         self.display_shape(edge(edge_start, edge_end),
    #                            color_=colour_wx_to_occ((255, 255, 51)))
    #
    #         self.display_vector(
    #             arrow_cone,
    #             gp_Pnt(*anchor["position"]).Translated(to_arrow_cone_start))
    #
    #         self.display_message(gp_Pnt(*anchor["position"]),
    #                              k,
    #                              height=20,
    #                              message_color=(0, 0, 0))

    def display_part(self,
                     part,
                     color_255=None,
                     transparency=0.,
                     anchor_names_height=10.,
                     scale_anchors=1.):
        r"""Display a single Part (shape + anchors)

        Parameters
        ----------
        part : PartGeometryNode
        color_255 : tuple of integers from 0 to 255
        transparency : float from 0 to 1
        anchor_names_height : float
            Height of anchor names in display

        """
        if color_255 is None:
            # by default, always use the same color to view a part
            color_255 = (102, 0, 102)

        # Assignation required to get the shape id, not the Python property id.
        transformed_shape = part.transformed_shape

        self.display_shape(transformed_shape,
                           color_=colour_wx_to_occ(color_255),
                           transparency=transparency)

        extra_info[transformed_shape] = part.properties

        for anchor_name, anchor in part.transformed_anchors.items():
            self.display_vector(gp_Vec(float(anchor.u[0] * scale_anchors),
                                       float(anchor.u[1] * scale_anchors),
                                       float(anchor.u[2] * scale_anchors)),
                                gp_Pnt(float(anchor.p[0]),
                                       float(anchor.p[1]),
                                       float(anchor.p[2])))

            self.display_vector(gp_Vec(float(anchor.v[0] * scale_anchors),
                                       float(anchor.v[1] * scale_anchors),
                                       float(anchor.v[2] * scale_anchors)),
                                gp_Pnt(float(anchor.p[0]),
                                       float(anchor.p[1]),
                                       float(anchor.p[2])))

            self.display_message(gp_Pnt(*anchor.p),
                                 anchor_name,
                                 height=anchor_names_height,
                                 message_color=(0, 0, 0))

    def display_assembly(self, assembly, color_255=None, transparency=0.):
        r"""Display an assembly of parts and assemblies

        Parameters
        ----------
        assembly : AssemblyGeometryNode
        color_255 : tuple, optional
            RGB tuple (from 0 to 255)
            If it is not none, all parts of the assembly are displayed using the
            same color
        transparency : float from 0 to 1

        """
        for i, part in enumerate(assembly._parts):
            color_seq = color_from_sequence(i, "colors")

            c = color_seq if color_255 is None else color_255

            self.display_part(part,
                              color_255=c,
                              transparency=transparency)

    def display_assemblies(self, assemblies, transparency=0.):
        r"""Display a list of assemblies

        Parameters
        ----------
        assemblies : list[Assembly]
        transparency : float from 0 to 1

        """
        for i, assembly in enumerate(assemblies):
            self.display_assembly(assembly,
                                  color_255=color_from_sequence(i, "colors"),
                                  transparency=transparency)
