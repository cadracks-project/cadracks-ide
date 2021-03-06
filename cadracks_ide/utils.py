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

r"""CadRacks IDE ui utilities"""

from os.path import isdir

from corelib.core.files import p_


def path_to_file(p_root, p_rel):
    r"""Workaround PyInstaller inability to deal with the __file__ symbol"""
    try:
        p = p_(p_root, "./%s" % p_rel)
    except ValueError:
        p = p_rel

    return p


def get_file_extension(filename):
    """Return the file extension, including the point (.)

    Parameters
    ----------
    filename : str
        The name of the file which extension we are interested in.
        It can be a standalone file name or a path to the file.

    """
    if not isdir(filename):  # check if directory
        index = filename.rfind('.')  # search for the last period
        if index > -1:
            return filename[index:].strip().lower()
        return ''
    else:
        return 'directory'
