# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2013 Canonical
# Author: Christopher Lee
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.

import logging

from autopilot.display import Display as DisplayBase
from upa import get_resolution

logger = logging.getLogger(__name__)

class Display(DisplayBase):
    """The base class/inteface for the display devices"""

    def get_num_screens(self):
        """Get the number of screens attached to the PC."""
        return 1

    def get_primary_screen(self):
        """Returns an integer of which screen is considered the primary"""
        return 0

    def get_screen_width(self):
        return get_resolution()[0]

    def get_screen_height(self):
        return get_resolution()[1]

    def get_screen_geometry(self, screen_number):
        """Get the geometry for a particular screen.

        :return: Tuple containing (x, y, width, height).

        """
        res = get_resolution()
        return (0, 0, res[0], res[1])
