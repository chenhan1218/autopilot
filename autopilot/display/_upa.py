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
import subprocess


def query_resolution():
    try:
        FBSET = subprocess.check_output(["fbset", "-s", "-x"]).decode().strip()
    except OSError:
        try:
            DEVICE = subprocess.check_output(
                ["/usr/bin/getprop", "ro.product.device"]).decode().strip()
        except OSError:
            DEVICE = ''

        RESOLUTIONS = {
            "generic": (480, 800),
            "mako": (768, 1280),
            "maguro": (720, 1280),
            "manta": (2560, 1600),
            "grouper": (800, 1280),
        }

        if DEVICE not in RESOLUTIONS:
            raise NotImplementedError(
                'Device "{}" is not supported by Autopilot.'.format(DEVICE))

        return RESOLUTIONS[DEVICE]
    else:
        return tuple([int(i) for i in
                      FBSET.splitlines()[0].split('"')[1].split('x')])


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
