#!/usr/bin/env python
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

r"""Main UI for CadRacks IDE"""

import sys
import platform
import logging
from os.path import exists
import configobj

import wx
import wx.aui
import wx.lib.agw.aui
from wx.adv import AboutDialogInfo, AboutBox

from cadracks_ide.utils import path_to_file

import cadracks_ide
from cadracks_ide.model import Model

from cadracks_ide.three_d import ThreeDPanel
from cadracks_ide.code import CodePanel
# from cadracks_ide.graph import GraphPanel
from cadracks_ide.tree import Tree
from corelib.ui.wx_.log import LogPanel

logger = logging.getLogger(__name__)


class CadracksIdeFrame(wx.Frame):
    r"""Main application frame

    Parameters
    ----------
    parent : None
    model : cadracks_ide.model.Model
        The application model.
    config : configobj.ConfigObj or None
        The application options

    """

    PANE_CODE_NAME = "Code"
    PANE_3D_NAME = "3d"
    # PANE_GRAPH_NAME = "Graph"
    PANE_TREE_NAME = "Tree"
    PANE_LOG_NAME = "Log"
    PANES = [PANE_CODE_NAME,
             PANE_3D_NAME,
             # PANE_GRAPH_NAME,
             PANE_TREE_NAME,
             PANE_LOG_NAME]

    def __init__(self, parent, model, config, size=(1200, 800)):
        # logger.debug("Initializing WaterlineUiFrame")
        wx.Frame.__init__(self,
                          parent,
                          -1,
                          "CadRacks IDE",
                          style=wx.DEFAULT_FRAME_STYLE,
                          size=size)

        if platform.system() == "Linux":
            self.Show()

        # Application icon
        ico = path_to_file(__file__, "cadracks-ide.ico")

        self.SetIcon(wx.Icon(wx.IconLocation(filename=ico, num=0)))
        self.Bind(wx.EVT_CLOSE, self.on_close)

        # Config
        self.config = config
        try:
            frame_maximize = True if self.config["frame"]["maximize"] == "True" else False
            self.confirm_close = True if self.config["frame"]["confirm_close"] == "True" else False
            # self.project_default_dir = self.config["app"]["default_dir"]
            self.viewer_background_colour = tuple([float(el) for el in self.config["viewer"]["viewer_background_colour"]])
            self.objects_transparency = float(self.config["viewer"]["objects_transparency"])
            self.text_height = int(self.config["viewer"]["text_height"])
            self.text_colour = tuple([float(el) for el in self.config["viewer"]["text_colour"]])
        except (TypeError, KeyError):
            frame_maximize = True
            self.confirm_close = True
            # self.project_default_dir = ""
            self.viewer_background_colour = (50., 50., 50.)
            self.objects_transparency = 0.2
            self.text_height = 20
            self.text_colour = (0, 0, 0)
            # Report the problem
            msg = "No config loaded (wrong ini file name or missing key), " \
                  "using program defaults"
            wx.MessageBox(msg, 'Warning', wx.OK | wx.ICON_WARNING)

        self.model = model

        # Panels
        self.log_panel = LogPanel(self,
                                  threadsafe=False,
                                  format_='%(asctime)s :: %(levelname)6s :: '
                                          '%(name)20s :: %(lineno)3d :: '
                                          '%(message)s')
        logger.info("Starting CadRacks IDE ...")
        self.three_d_panel = \
            ThreeDPanel(self,
                        model,
                        viewer_background_color=self.viewer_background_colour,
                        object_transparency=self.objects_transparency,
                        text_height=self.text_height,
                        text_colour=self.text_colour)
        self.code_panel = CodePanel(self, self.model)
        # self.graph_panel = GraphPanel(self, self.model,
        #                               viewer_background_color=self.viewer_background_colour,
        #                               object_transparency=self.objects_transparency,
        #                               text_height=self.text_height,
        #                               text_colour=self.text_colour)
        # self.tree_panel = Tree(self, self.model, root_directory=self.project_default_dir)
        self.tree_panel = Tree(self, self.model)

        # Menus, status bar ...
        self.init_ui()

        # AUI manager
        self._mgr = wx.lib.agw.aui.AuiManager()
        self._mgr.SetManagedWindow(self)  # notify AUI which frame to use

        self._mgr.AddPane(self.three_d_panel,
                          wx.lib.agw.aui.AuiPaneInfo().Right().
                          Name(CadracksIdeFrame.PANE_3D_NAME).Caption("3D").
                          MinSize(wx.Size(400, 200)).MaximizeButton(True).Resizable(True))
        # self._mgr.AddPane(self.graph_panel,
        #                   wx.lib.agw.aui.AuiPaneInfo().Right().
        #                   Name(CadracksIdeFrame.PANE_GRAPH_NAME).Caption("Graph").
        #                   MinSize(wx.Size(400, 100)).MaximizeButton(True).Resizable(True))
        self._mgr.AddPane(self.tree_panel,
                          wx.lib.agw.aui.AuiPaneInfo().Left().
                          Name(CadracksIdeFrame.PANE_TREE_NAME).Caption("Tree").
                          MinSize(wx.Size(400, 100)).MaximizeButton(True).Resizable(True))
        self._mgr.AddPane(self.log_panel,
                          wx.lib.agw.aui.AuiPaneInfo().Left().
                          Name(CadracksIdeFrame.PANE_LOG_NAME).Caption("Log").
                          MinSize(wx.Size(400, 100)).MaximizeButton(
                              True).Resizable(True))
        self._mgr.AddPane(self.code_panel,
                          wx.lib.agw.aui.AuiPaneInfo().CenterPane())

        # tell the manager to "commit" all the changes just made

        self._mgr.Update()
        self.three_d_panel.Layout()

        # self.three_d_panel.viewer.Layout()

        # Show and maximize the frame
        self.Show(True)
        if frame_maximize is True:
            self.Maximize(True)  # Use the full screen
        else:
            self.CenterOnScreen()

        self.Bind(wx.EVT_SIZE, self.OnSize)

        logger.info("... done")

    def OnSize(self, event):
        self._mgr.Update()

    def init_ui(self):
        r"""UI elements initialization"""

        menubar = wx.MenuBar()

        # File menu
        file_menu = wx.Menu()
        self.add_menu_item(menu=file_menu,
                           id_=wx.ID_OPEN,
                           text='&Open\tCtrl+O',
                           handler=self.on_open,
                           # icon=p_(__file__, './icons/open.png'),
                           icon=path_to_file(__file__, "icons/open.png"),
                           enabled=True)

        file_menu.AppendSeparator()

        self.add_menu_item(menu=file_menu,
                           id_=wx.ID_CLOSE,
                           text='&Quit\tCtrl+Q',
                           handler=self.on_quit,
                           # icon=p_(__file__, './icons/quit.png'))
                           icon = path_to_file(__file__, 'icons/quit.png'))
        menubar.Append(file_menu, '&File')

        # Windows menu
        windows_menu = wx.Menu()
        for name in CadracksIdeFrame.PANES:
            self.Bind(wx.EVT_MENU,
                      self.on_window_show,
                      windows_menu.Append(wx.ID_ANY, name, "Show " + name))
        menubar.Append(windows_menu, "&Windows")

        # Refresh menu
        refresh_menu = wx.Menu()
        self.add_menu_item(menu=refresh_menu,
                           id_=wx.NewId(),
                           text="Refresh",
                           handler=self.on_refresh,
                           # icon=p_(__file__, './icons/refresh.png'))
                           icon=path_to_file(__file__, 'icons/refresh.png'))
        menubar.Append(refresh_menu, "&Refresh")

        # Help menu
        help_menu = wx.Menu()
        m_about = help_menu.Append(wx.ID_ABOUT,
                                   "&About",
                                   "Information about this program")
        self.Bind(wx.EVT_MENU, self.on_about, m_about)
        menubar.Append(help_menu, "&Help")

        self.SetMenuBar(menubar)

        status_bar = wx.StatusBar(self)
        self.SetStatusBar(status_bar)

    def add_menu_item(self, menu, id_, text, handler, icon=None, enabled=True):
        r"""Add an item to a menu

        Parameters
        ----------
        menu
        id_
        text
        handler
        icon
        enabled : bool
            Should the menu item be enable (True) or
            Disabled (False) when created

        """
        menu_item = wx.MenuItem(parentMenu=menu, id=id_, text=text)
        if icon is not None:
            menu_item.SetBitmap(wx.Bitmap(icon))
        menu.Append(menu_item)
        if enabled is True:
            self.Bind(event=wx.EVT_MENU, handler=handler, id=id_)
        else:
            menu_item.Enable(False)

    # on_*
    # |
    # v

    def on_refresh(self, event):
        r"""Refresh handler"""
        with wx.BusyInfo("Refreshing ...") as _:
            pass

    def on_window_show(self, event):
        r"""Handler that toggles AUI pane, allows to male an AUI pane visible
        again after it has been closed

        Parameters
        ----------
        event : wx event

        """
        name = event.GetEventObject().FindItemById(event.GetId()).GetLabel()

        if self._mgr.GetPane(name).IsShown():
            self._mgr.GetPane(name).Hide()
        else:
            self._mgr.GetPane(name).Show()
        self._mgr.Update()

    @staticmethod
    def on_about(event):
        r"""About has been chosen from the menu

        Parameters
        ----------
        event : wx.Event

        """
        info = AboutDialogInfo()
        info.Name = cadracks_ide.__name__
        info.Version = cadracks_ide.__version__
        info.Copyright = "(C) 2017 2018 2019 CadRacks"
        info.WebSite = (cadracks_ide.__url__, )
        info.Developers = [cadracks_ide.__author__]
        info.License = cadracks_ide.__license__
        AboutBox(info)  # Show the wx.AboutBox

    def on_close(self, event):
        r"""Handle a click on the closing button (upper right cross)
        of the frame

        Parameters
        ----------
        event : wx.event

        """
        if self.confirm_close is True:
            dlg = wx.MessageDialog(self,
                                   "Do you really want to close "
                                   "this application?",
                                   "Confirm Exit",
                                   wx.OK | wx.CANCEL | wx.ICON_QUESTION)
            result = dlg.ShowModal()
            dlg.Destroy()
            if result == wx.ID_OK:
                self.Destroy()
                sys.exit(0)
        else:
            self.Destroy()
            sys.exit(0)

    def on_open(self, e):
        r"""Handler for the Open menu item

        Open a Python file

        Parameters
        ----------
        e : wx.CommandEvent

        """
        dlg = wx.DirDialog(self,
                           message="Choose a project folder",
                           defaultPath="",
                           style=wx.DD_CHANGE_DIR)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            self.model.set_root_folder(path)
            self.model.set_selected(path)
        dlg.Destroy()

    def on_quit(self, e):
        r"""Handler for the Quit menu item

        Parameters
        ----------
        e : wx.CommandEvent

        """
        self.Close()
        self.Destroy()
        sys.exit(0)


def get_config():
    r"""Get the ConfigObj object from a cadracks-ide.ini file

    Returns
    -------
    configobj.ConfigObj or None

    """
    inifile = path_to_file(__file__, "cadracks-ide.ini")

    if not exists(inifile):
        logger.warning("No cadracks-ide.ini, using default values")
        return None
    else:
        config = configobj.ConfigObj(inifile)
    return config


def main(width=1200, height=800):
    r"""Launch the main CadRacks IDE UI
    
    Parameters
    ----------
    width : int
        Width of the CadRacks IDE UI frame
    height : int
        Height of the CadRacks IDE UI frame

    """
    app = wx.App()
    # wx.InitAllImageHandlers()
    model = Model()
    frame = CadracksIdeFrame(parent=None,
                             model=model,
                             config=get_config(),
                             size=(width, height))
    frame.Show(True)

    # SafeYield(win, onlyIfNeeded)
    # see https://www.wxpython.org/docs/api/wx-module.html#SafeYield
    wx.SafeYield()

    # frame.runTests()
    app.SetTopWindow(frame)
    app.MainLoop()


if __name__ == '__main__':
    fh = logging.FileHandler('cadracks-ide.log')
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s :: %(levelname)8s :: '
                                  '%(name)35s :: %(message)s')
    fh.setFormatter(formatter)
    main_logger = logging.getLogger()
    main_logger.addHandler(fh)
    main()
