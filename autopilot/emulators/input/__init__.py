# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2013 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.

from collections import OrderedDict
from autopilot.utilities import get_debug_logger

"""Autopilot unified input system.

This package provides input methods for various platforms. Autopilot aims to
provide an appropriate implementation for the currently running system. For
example, not all systems have an X11 stack running: on those systems, autopilot
will instantiate a Keyboard class that uses something other than X11 to generate
key events (possibly UInput).

Test authors are encouraged to instantiate the input devices they need for their
tests using the get_keyboard and get_mouse methods directly. In the case where
these methods don't do the right thing, authors may access the underlying input
systems directly. However, these are not documented, and are liable to change
without notice.

"""


def get_keyboard(preferred_variant=""):
    """Get an instance of the Keyboard class.

    If variant is specified, it should be a string that specifies a backend to
    use. However, this hint can be ignored - autopilot will prefer to return a
    keyboard variant other than the one requested, rather than fail to return
    anything at all.

    If autopilot cannot instantate any of the possible backends, a RuntimeError
    will be raised.
    """
    def get_x11_kb():
        from autopilot.emulators.input._X11 import Keyboard
        return Keyboard()
    def get_uinput_kb():
        from autopilot.emulators.input._uinput import Keyboard
        return Keyboard()

    variants = OrderedDict()
    variants['X11'] = get_x11_kb
    variants['UInput'] = get_uinput_kb
    return _pick_variant(variants, preferred_variant)


def get_mouse(preferred_variant=""):
    """Get an instance of the Mouse class.

    If variant is specified, it should be a string that specifies a backend to
    use. However, this hint can be ignored - autopilot will prefer to return a
    mouse variant other than the one requested, rather than fail to return
    anything at all.

    If autopilot cannot instantate any of the possible backends, a RuntimeError
    will be raised.
    """
    def get_x11_mouse():
        from autopilot.emulators.input._X11 import Mouse
        return Mouse()

    variants = OrderedDict()
    variants['X11'] = get_x11_mouse
    return _pick_variant(variants, preferred_variant)


def _pick_variant(variants, preferred_variant):
    possible_backends = variants.keys()
    get_debug_logger().debug("Possible keyboard variants: %s", ','.join(possible_backends))
    if preferred_variant in possible_backends:
        possible_backends.sort(lambda a,b: -1 if a == preferred_variant else 0)
    failure_reasons = []
    for be in possible_backends:
        try:
            return variants[be]()
        except Exception as e:
            get_debug_logger().warning("Can't create keyboard variant %s: %r", be, e)
            failure_reasons.append('%s: %r' % (be, e))
    raise RuntimeError("Unable to instantiate any Keyboard backends\n%s" % '\n'.join(failure_reasons))


class Keyboard(object):

    """A base class for all keyboard-type devices."""

    def press(self, keys, delay=0.2):
        """Send key press events only.

        :param string keys: Keys you want pressed.

        Example:

        >>> press('Alt+F2')

        presses the 'Alt' and 'F2' keys.

        """
        raise NotImplementedError("You cannot use this class directly.")

    def release(self, keys, delay=0.2):
        """Send key release events only.

        :param string keys: Keys you want released.

        Example:

        >>> release('Alt+F2')

        releases the 'Alt' and 'F2' keys.

        """
        raise NotImplementedError("You cannot use this class directly.")

    def press_and_release(self, keys, delay=0.2):
        """Press and release all items in 'keys'.

        This is the same as calling 'press(keys);release(keys)'.

        :param string keys: Keys you want pressed and released.

        Example:

        >>> press_and_release('Alt+F2')

        presses both the 'Alt' and 'F2' keys, and then releases both keys.

        """

        raise NotImplementedError("You cannot use this class directly.")

    def type(self, string, delay=0.1):
        """Simulate a user typing a string of text.

        .. note:: Only 'normal' keys can be typed with this method. Control
         characters (such as 'Alt' will be interpreted as an 'A', and 'l',
         and a 't').

        """
        raise NotImplementedError("You cannot use this class directly.")

    @staticmethod
    def cleanup():
        """Generate KeyRelease events for any un-released keys.

        .. important:: Ensure you call this at the end of any test to release any
         keys that were pressed and not released.

        """
        raise NotImplementedError("You cannot use this class directly.")


class Mouse(object):
    """A base class for all mouse-type classes."""

    @property
    def x(self):
        """Mouse position X coordinate."""
        raise NotImplementedError("You cannot use this class directly.")

    @property
    def y(self):
        """Mouse position Y coordinate."""
        return self.position()[1]

    def press(self, button=1):
        """Press mouse button at current mouse location."""
        raise NotImplementedError("You cannot use this class directly.")

    def release(self, button=1):
        """Releases mouse button at current mouse location."""
        raise NotImplementedError("You cannot use this class directly.")

    def click(self, button=1, press_duration=0.10):
        """Click mouse at current location."""
        raise NotImplementedError("You cannot use this class directly.")

    def move(self, x, y, animate=True, rate=10, time_between_events=0.01):
        """Moves mouse to location (x, y).

        Callers should avoid specifying the *rate* or *time_between_events*
        parameters unless they need a specific rate of movement.

        """
        raise NotImplementedError("You cannot use this class directly.")

    def move_to_object(self, object_proxy):
        """Attempts to move the mouse to 'object_proxy's centre point.

        It does this by looking for several attributes, in order. The first
        attribute found will be used. The attributes used are (in order):

         * globalRect (x,y,w,h)
         * center_x, center_y
         * x, y, w, h

        :raises: **ValueError** if none of these attributes are found, or if an
         attribute is of an incorrect type.

        """
        raise NotImplementedError("You cannot use this class directly.")

    def position(self):
        """
        Returns the current position of the mouse pointer.

        :return: (x,y) tuple
        """
        raise NotImplementedError("You cannot use this class directly.")

    def drag(self, x1, y1, x2, y2):
        """Performs a press, move and release
        This is to keep a common API between Mouse and Finger as long as possible"""
        raise NotImplementedError("You cannot use this class directly.")

    @staticmethod
    def cleanup():
        """Put mouse in a known safe state."""
        raise NotImplementedError("You cannot use this class directly.")
