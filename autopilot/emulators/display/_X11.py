# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2013 Canonical
# Author: Christopher Lee
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.

import logging

from autopilot.emulators.bamf import BamfWindow
from autopilot.emulators.display import Display as DisplayBase

logger = logging.getLogger(__name__)

class Display(DisplayBase):
    def __init__(self):
        # Note: MUST import these here, rather than at the top of the file. Why?
        # Because sphinx imports these modules to build the API documentation,
        # which in turn tries to import Gdk, which in turn fails because there's
        # no DISPlAY environment set in the package builder.
        from gi.repository import Gdk
        self._default_screen = Gdk.Screen.get_default()
        self._blacklisted_drivers = ["NVIDIA"]

    def get_num_screens(self):
        """Get the number of screens attached to the PC."""
        return self._default_screen.get_n_monitors()

    def get_primary_screen(self):
        """Returns an integer of which screen is considered the primary"""
        return self._default_screen.get_primary_monitor()

    def get_screen_width(self, screen_number=0):
        # return self._default_screen.get_width()
        return self.get_screen_geometry(screen_number)[2]

    def get_screen_height(self, screen_number=0):
        #return self._default_screen.get_height()
        return self.get_screen_geometry(screen_number)[3]

    def get_screen_geometry(self, screen_number):
        """Get the geometry for a particular screen.

        :return: Tuple containing (x, y, width, height).

        """
        if screen_number < 0 or screen_number >= self.get_num_screens():
            raise ValueError('Specified screen number is out of range.')
        rect = self._default_screen.get_monitor_geometry(screen_number)
        return (rect.x, rect.y, rect.width, rect.height)

    def move_mouse_to_screen(self, screen_number):
        """Move the mouse to the center of the specified screen."""
        geo = self.get_screen_geometry(screen_number)
        x = geo[0] + (geo[2] / 2)
        y = geo[1] + (geo[3] / 2)
        #dont animate this or it might not get there due to barriers
        Mouse().move(x, y, False)

    # This should be moved elsewhere.
    def drag_window_to_screen(self, window, screen):
        """Drags *window* to *screen*

        :param BamfWindow window: The window to drag
        :param integer screen: The screen to drag the *window* to
        :raises: **TypeError** if *window* is not a BamfWindow

        """
        if not isinstance(window, BamfWindow):
            raise TypeError("Window must be a BamfWindow")

        if window.monitor == screen:
            logger.debug("Window %r is already on screen %d." % (window.x_id, screen))
            return

        assert(not window.is_maximized)
        (win_x, win_y, win_w, win_h) = window.geometry
        (mx, my, mw, mh) = self.get_screen_geometry(screen)

        logger.debug("Dragging window %r to screen %d." % (window.x_id, screen))

        mouse = Mouse()
        keyboard = Keyboard()
        mouse.move(win_x + win_w/2, win_y + win_h/2)
        keyboard.press("Alt")
        mouse.press()
        keyboard.release("Alt")

        # We do the movements in two steps, to reduce the risk of being
        # blocked by the pointer barrier
        target_x = mx + mw/2
        target_y = my + mh/2
        mouse.move(win_x, target_y, rate=20, time_between_events=0.005)
        mouse.move(target_x, target_y, rate=20, time_between_events=0.005)
        mouse.release()
