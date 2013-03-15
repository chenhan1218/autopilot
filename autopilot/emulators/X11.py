# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2010 Canonical
# Author: Alex Launi
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.
#
# This script is designed to run unity in a test drive manner. It will drive
# X and test the GL calls that Unity makes, so that we can easily find out if
# we are triggering graphics driver/X bugs.

"""A collection of emulators for X11 - namely keyboards and mice.

In the future we may also need other devices.

"""

from __future__ import absolute_import

import logging
import os
import subprocess

from autopilot.emulators.bamf import BamfWindow
from autopilot.emulators.input import get_keyboard, get_mouse
from autopilot.utilities import deprecated


logger = logging.getLogger(__name__)


def reset_display():
    from autopilot.emulators.input._X11 import reset_display
    reset_display()


# Keyboard and Mouse are no longer here. This is for backwards compatibility,
# but will eventually dissapear.
@deprecated('autopilot.emulators.input.get_keyboard')
def Keyboard():
    return get_keyboard()


@deprecated('autopilot.emulators.input.get_mouse')
def Mouse():
    return get_mouse()


@deprecated('autopilot.emulators.display.get_display')
class ScreenGeometry:
    """Get details about screen geometry."""

    class BlacklistedDriverError(RuntimeError):
        """Cannot set primary monitor when running drivers listed in the driver blacklist."""

    def __init__(self):
        # Note: MUST import these here, rather than at the top of the file. Why?
        # Because sphinx imports these modules to build the API documentation,
        # which in turn tries to import Gdk, which in turn fails because there's
        # no DISPlAY environment set in the package builder.
        from gi.repository import Gdk
        self._default_screen = Gdk.Screen.get_default()
        self._blacklisted_drivers = ["NVIDIA"]

    def get_num_monitors(self):
        """Get the number of monitors attached to the PC."""
        return self._default_screen.get_n_monitors()

    def get_primary_monitor(self):
        return self._default_screen.get_primary_monitor()

    def set_primary_monitor(self, monitor):
        """Set *monitor* to be the primary monitor.

        :param int monitor: Must be between 0 and the number of configured
         monitors.
        :raises: **ValueError** if an invalid monitor is specified.
        :raises: **BlacklistedDriverError** if your video driver does not
         support this.

        """
        try:
            glxinfo_out = subprocess.check_output("glxinfo")
        except OSError, e:
            raise OSError("Failed to run glxinfo: %s. (do you have mesa-utils installed?)" % e)

        for dri in self._blacklisted_drivers:
            if dri in glxinfo_out:
                raise ScreenGeometry.BlacklistedDriverError('Impossible change the primary monitor for the given driver')

        if monitor < 0 or monitor >= self.get_num_monitors():
            raise ValueError('Monitor %d is not in valid range of 0 <= monitor < %d.' % (self.get_num_monitors()))

        monitor_name = self._default_screen.get_monitor_plug_name(monitor)

        if not monitor_name:
            raise ValueError('Could not get monitor name from monitor number %d.' % (monitor))

        ret = os.spawnlp(os.P_WAIT, "xrandr", "xrandr", "--output", monitor_name, "--primary")

        if ret != 0:
            raise RuntimeError('Xrandr can\'t set the primary monitor. error code: %d' % (ret))

    def get_screen_width(self):
        return self._default_screen.get_width()

    def get_screen_height(self):
        return self._default_screen.get_height()

    def get_monitor_geometry(self, monitor_number):
        """Get the geometry for a particular monitor.

        :return: Tuple containing (x, y, width, height).

        """
        if monitor_number < 0 or monitor_number >= self.get_num_monitors():
            raise ValueError('Specified monitor number is out of range.')
        rect = self._default_screen.get_monitor_geometry(monitor_number)
        return (rect.x, rect.y, rect.width, rect.height)

    def is_rect_on_monitor(self, monitor_number, rect):
        """Returns True if *rect* is **entirely** on the specified monitor, with no overlap."""

        if type(rect) is not tuple or len(rect) != 4:
            raise TypeError("rect must be a tuple of 4 int elements.")

        (x, y, w, h) = rect
        (mx, my, mw, mh) = self.get_monitor_geometry(monitor_number)
        return (x >= mx and x + w <= mx + mw and y >= my and y + h <= my + mh)

    def is_point_on_monitor(self, monitor_number, point):
        """Returns True if *point* is on the specified monitor.

        *point* must be an iterable type with two elements: (x, y)

        """
        x,y = point
        (mx, my, mw, mh) = self.get_monitor_geometry(monitor_number)
        return (x >= mx and x < mx + mw and y >= my and y < my + mh)

    def is_point_on_any_monitor(self, point):
        """Returns true if *point* is on any currently configured monitor."""
        return any([self.is_point_on_monitor(m, point) for m in range(self.get_num_monitors())])

    def move_mouse_to_monitor(self, monitor_number):
        """Move the mouse to the center of the specified monitor."""
        geo = self.get_monitor_geometry(monitor_number)
        x = geo[0] + (geo[2] / 2)
        y = geo[1] + (geo[3] / 2)
        #dont animate this or it might not get there due to barriers
        Mouse().move(x, y, False)

    def drag_window_to_monitor(self, window, monitor):
        """Drags *window* to *monitor*

        :param BamfWindow window: The window to drag
        :param integer monitor: The monitor to drag the *window* to
        :raises: **TypeError** if *window* is not a BamfWindow

        """
        if not isinstance(window, BamfWindow):
            raise TypeError("Window must be a BamfWindow")

        if window.monitor == monitor:
            logger.debug("Window %r is already on monitor %d." % (window.x_id, monitor))
            return

        assert(not window.is_maximized)
        (win_x, win_y, win_w, win_h) = window.geometry
        (mx, my, mw, mh) = self.get_monitor_geometry(monitor)

        logger.debug("Dragging window %r to monitor %d." % (window.x_id, monitor))

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
