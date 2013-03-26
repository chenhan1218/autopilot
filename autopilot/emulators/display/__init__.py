# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2013 Canonical
# Author: Christopher Lee
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.

from collections import OrderedDict
from autopilot.utilities import get_debug_logger


def get_display(preferred_variant=""):
    """Get an instance of the Display class.

    If variant is specified, it should be a string that specifies a backend to
    use. However, this hint can be ignored - autopilot will prefer to return a
    variant other than the one requested, rather than fail to return anything at
    all.

    If autopilot cannot instantate any of the possible backends, a RuntimeError
    will be raised.
    """
    def get_x11_display():
        from autopilot.emulators.display._X11 import Display
        return Display()

    def get_upa_display():
        from autopilot.emulators.display._upa import Display
        return Display()

    variants = OrderedDict()
    variants['X11'] = get_x11_display
    variants['UPA'] = get_upa_display
    return _pick_variant(variants, preferred_variant)


def _pick_variant(variants, preferred_variant):
    possible_backends = variants.keys()
    get_debug_logger().debug("Possible variants: %s", ','.join(possible_backends))
    if preferred_variant in possible_backends:
        possible_backends.sort(lambda a,b: -1 if a == preferred_variant else 0)
    failure_reasons = []
    for be in possible_backends:
        try:
            return variants[be]()
        except Exception as e:
            get_debug_logger().warning("Can't create variant %s: %r", be, e)
            failure_reasons.append('%s: %r' % (be, e))
    raise RuntimeError("Unable to instantiate any backends\n%s" % '\n'.join(failure_reasons))


def is_rect_on_screen(self, screen_number, rect):
    """Returns True if *rect* is **entirely** on the specified screen, with no overlap."""

    if type(rect) is not tuple or len(rect) != 4:
        raise TypeError("rect must be a tuple of 4 int elements.")

    (x, y, w, h) = rect
    (mx, my, mw, mh) = get_display().get_screen_geometry(screen_number)
    return (x >= mx and x + w <= mx + mw and y >= my and y + h <= my + mh)


def is_point_on_screen(self, screen_number, point):
    """Returns True if *point* is on the specified screen.

    *point* must be an iterable type with two elements: (x, y)

    """
    x, y = point
    (mx, my, mw, mh) = get_display().get_screen_geometry(screen_number)
    return (x >= mx and x < mx + mw and y >= my and y < my + mh)


def is_point_on_any_screen(self, point):
    """Returns true if *point* is on any currently configured screen."""
    return any([is_point_on_screen(m, point) for m in range(get_display().get_num_screens())])


# This the interface that the concrete implementations will use.
class Display:
    """The base class/inteface for the display devices"""

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

    def move_mouse_to_screen(self, screen_number):
        """Move the mouse to the center of the specified screen."""
        raise NotImplementedError("You cannot use this class directly.")

    # This should be moved elsewhere.
    def drag_window_to_screen(self, window, screen):
        """Drags *window* to *screen*

        :param BamfWindow window: The window to drag
        :param integer monitor: The screen to drag the *window* to
        :raises: **TypeError** if *window* is not a BamfWindow

        """
        raise NotImplementedError("You cannot use this class directly.")
