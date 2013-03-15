# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2013 Canonical
# Author: Christopher Lee
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.

import logging

from autopilot.emulators.display import Display as DisplayBase

logger = logging.getLogger(__name__)

class Display(DisplayBase):
    """The base class/inteface for the display devices"""

    class BlacklistedDriverError(RuntimeError):
        """Cannot set primary monitor when running drivers listed in the driver blacklist."""

    def get_num_screens(self):
        """Get the number of screens attached to the PC."""
        return 1

    def get_primary_screen(self):
        """Returns an integer of which screen is considered the primary"""
        return 0

    def get_screen_width(self):
        return 1

    def get_screen_height(self):
        return 1

    def get_screen_geometry(self, screen_number):
        """Get the geometry for a particular screen.

        :return: Tuple containing (x, y, width, height).

        """
        return(1, 1, 1, 1)

    #should this be here or else where?
    def move_mouse_to_screen(self, screen_number):
        """Move the mouse to the center of the specified screen."""
        pass

    # This should be moved elsewhere.
    def drag_window_to_screen(self, window, screen):
        """Drags *window* to *screen*

        :param BamfWindow window: The window to drag
        :param integer screen: The monitor to drag the *window* to
        :raises: **TypeError** if *window* is not a BamfWindow

        """
        pass
