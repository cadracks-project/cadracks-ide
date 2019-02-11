# coding: utf-8

r"""Model of the CadRacks IDE app"""

import sys
import logging

from atom.api import Atom
from atom.scalars import Str

logger = logging.getLogger(__name__)


class Model(Atom):
    r"""Model for the CadRacks IDE app"""
    root_folder = Str()
    selected = Str()
    code = Str()

    def set_root_folder(self, root_folder):
        r"""Set the root folder
        
        Parameters
        ----------
        root_folder : str

        """
        logger.debug("Setting the root folder")
        self.root_folder = root_folder
        sys.path.append(root_folder)
        logger.debug("Notify that root folder changed")
        self.notify("root_folder_changed", None)

    def set_selected(self, selected):
        r"""Defines which item is selected in the tree view

        Parameters
        ----------
        selected

        """
        logger.debug("Setting the selected item")
        self.selected = selected
        logger.debug("Notify that selected item changed")
        self.notify("selected_changed", None)
