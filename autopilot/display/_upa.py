# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2012-2013 Canonical
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


import logging

from autopilot.display import Display as DisplayBase
from autopilot.platform import image_codename
import subprocess


def query_resolution():
    try:
        return _get_fbset_resolution()
    except Exception as e:
        return _get_hardcoded_resolution()


def _get_fbset_resolution():
    """Return the resolution, as determined by fbset, or None."""
    fbset_output = _get_fbset_output()
    for line in fbset_output.split('\n'):
        line = line.strip()
        if line.startswith('Mode'):
            quoted_resolution = line.split()[1]
            resolution_string = quoted_resolution.strip('"')
            return tuple(int(piece) for piece in resolution_string.split('x'))
    raise RuntimeError("No modes found from fbset output")


def _get_fbset_output():
    return subprocess.check_output(["fbset", "-s", "-x"]).decode().strip()


def _get_hardcoded_resolution():
    name = image_codename()

    resolutions = {
        "generic": (480, 800),
        "mako": (768, 1280),
        "maguro": (720, 1280),
        "manta": (2560, 1600),
        "grouper": (800, 1280),
    }

    if name not in resolutions:
        raise NotImplementedError(
            'Device "{}" is not supported by Autopilot.'.format(name))

    return resolutions[name]


logger = logging.getLogger(__name__)


class Display(DisplayBase):
    """The base class/inteface for the display devices"""

    def __init__(self):
        self._X, self._Y = query_resolution()
        super(Display, self).__init__()

    def get_num_screens(self):
        """Get the number of screens attached to the PC."""
        return 1

    def get_primary_screen(self):
        """Returns an integer of which screen is considered the primary"""
        return 0

    def get_screen_width(self):
        return self._X

    def get_screen_height(self):
        return self._Y

    def get_screen_geometry(self, screen_number):
        """Get the geometry for a particular screen.

        :return: Tuple containing (x, y, width, height).

        """
        return (0, 0, self._X, self._Y)
