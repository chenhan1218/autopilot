# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2013 Canonical
# Author: Christopher Lee
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.

"""The display module contaions support for getting screen information."""

from collections import OrderedDict
from autopilot.utilities import _pick_variant
from autopilot.input import Mouse


def is_rect_on_screen(screen_number, rect):
    """Returns True if *rect* is **entirely** on the specified screen, with no overlap."""
    (x, y, w, h) = rect
    (mx, my, mw, mh) = Display.create().get_screen_geometry(screen_number)
    return (x >= mx and x + w <= mx + mw and y >= my and y + h <= my + mh)


def is_point_on_screen(screen_number, point):
    """Returns True if *point* is on the specified screen.

    *point* must be an iterable type with two elements: (x, y)

    """
    x, y = point
    (mx, my, mw, mh) = Display.create().get_screen_geometry(screen_number)
    return (x >= mx and x < mx + mw and y >= my and y < my + mh)


def is_point_on_any_screen(point):
    """Returns true if *point* is on any currently configured screen."""
    return any([is_point_on_screen(m, point) for m in range(Display.create().get_num_screens())])


def move_mouse_to_screen(screen_number):
    """Move the mouse to the center of the specified screen."""
    geo = Display.create().get_screen_geometry(screen_number)
    x = geo[0] + (geo[2] / 2)
    y = geo[1] + (geo[3] / 2)
    #dont animate this or it might not get there due to barriers
    Mouse.create().move(x, y, False)


# veebers TODO: Write this so it's usable.
# def drag_window_to_screen(self, window, screen):
#     """Drags *window* to *screen*

#     :param BamfWindow window: The window to drag
#     :param integer screen: The screen to drag the *window* to
#     :raises: **TypeError** if *window* is not a BamfWindow

#     """
#     if not isinstance(window, BamfWindow):
#         raise TypeError("Window must be a BamfWindow")

#     if window.monitor == screen:
#         logger.debug("Window %r is already on screen %d." % (window.x_id, screen))
#         return

#     assert(not window.is_maximized)
#     (win_x, win_y, win_w, win_h) = window.geometry
#     (mx, my, mw, mh) = self.get_screen_geometry(screen)

#     logger.debug("Dragging window %r to screen %d." % (window.x_id, screen))

#     mouse = Mouse()
#     keyboard = Keyboard()
#     mouse.move(win_x + win_w/2, win_y + win_h/2)
#     keyboard.press("Alt")
#     mouse.press()
#     keyboard.release("Alt")

#     # We do the movements in two steps, to reduce the risk of being
#     # blocked by the pointer barrier
#     target_x = mx + mw/2
#     target_y = my + mh/2
#     mouse.move(win_x, target_y, rate=20, time_between_events=0.005)
#     mouse.move(target_x, target_y, rate=20, time_between_events=0.005)
#     mouse.release()


class Display:
    """The base class/inteface for the display devices"""

    @staticmethod
    def create(preferred_variant=''):
        """Get an instance of the Display class.

        For more infomration on picking specific backends, see :ref:`tut-picking-backends`

        :param preferred_variant: A string containing a hint as to which variant you
            would like.

            possible variants are:

            * ``X11`` - Get display information from X11.
            * ``UPA`` - Get display information from the ubuntu platform API.
        :raises: RuntimeError if autopilot cannot instantate any of the possible
            backends.
        :raises: RuntimeError if the preferred_variant is specified and is not
            one of the possible backends for this device class.
        :raises: :class:`~autopilot.BackendException` if the preferred_variant is
            set, but that variant could not be instantiated.

        """
        def get_x11_display():
            from autopilot.display._X11 import Display
            return Display()

        def get_upa_display():
            from autopilot.display._upa import Display
            return Display()

        variants = OrderedDict()
        variants['X11'] = get_x11_display
        variants['UPA'] = get_upa_display
        return _pick_variant(variants, preferred_variant)

    class BlacklistedDriverError(RuntimeError):
        """Cannot set primary monitor when running drivers listed in the driver blacklist."""

    def get_num_screens(self):
        """Get the number of screens attached to the PC."""
        raise NotImplementedError("You cannot use this class directly.")

    def get_primary_screen(self):
        raise NotImplementedError("You cannot use this class directly.")

    def get_screen_width(self, screen_number=0):
        raise NotImplementedError("You cannot use this class directly.")

    def get_screen_height(self, screen_number=0):
        raise NotImplementedError("You cannot use this class directly.")

    def get_screen_geometry(self, monitor_number):
        """Get the geometry for a particular monitor.

        :return: Tuple containing (x, y, width, height).

        """
        raise NotImplementedError("You cannot use this class directly.")
