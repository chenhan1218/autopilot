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

from gi.repository import Gdk
import logging
import os
import subprocess
from time import sleep

from autopilot.emulators.bamf import BamfWindow
from autopilot.utilities import Silence
from Xlib import X, XK
from Xlib.display import Display
from Xlib.ext.xtest import fake_input


_PRESSED_KEYS = []
_PRESSED_MOUSE_BUTTONS = []
_DISPLAY = None
logger = logging.getLogger(__name__)


def get_display():
    """Get the Xlib display object, creating it (silently) if it doesn't exist."""
    global _DISPLAY
    if _DISPLAY is None:
        with Silence():
            _DISPLAY = Display()
    return _DISPLAY


def reset_display():
    global _DISPLAY
    _DISPLAY = None


class Keyboard(object):
    """Wrapper around xlib to make faking keyboard input possible."""

    _special_X_keysyms = {
        ' ' : "space",
        '\t' : "Tab",
        '\n' : "Return",  # for some reason this needs to be cr, not lf
        '\r' : "Return",
        '\e' : "Escape",
        '!' : "exclam",
        '#' : "numbersign",
        '%' : "percent",
        '$' : "dollar",
        '&' : "ampersand",
        '"' : "quotedbl",
        '\'' : "apostrophe",
        '(' : "parenleft",
        ')' : "parenright",
        '*' : "asterisk",
        '=' : "equal",
        '+' : "plus",
        ',' : "comma",
        '-' : "minus",
        '.' : "period",
        '/' : "slash",
        ':' : "colon",
        ';' : "semicolon",
        '<' : "less",
        '>' : "greater",
        '?' : "question",
        '@' : "at",
        '[' : "bracketleft",
        ']' : "bracketright",
        '\\' : "backslash",
        '^' : "asciicircum",
        '_' : "underscore",
        '`' : "grave",
        '{' : "braceleft",
        '|' : "bar",
        '}' : "braceright",
        '~' : "asciitilde"
        }

    _keysym_translations = {
        'Control' : 'Control_L',
        'Ctrl' : 'Control_L',
        'Alt' : 'Alt_L',
        'AltR': 'Alt_R',
        'Super' : 'Super_L',
        'Shift' : 'Shift_L',
        'Enter' : 'Return',
        'Space' : ' ',
    }

    def __init__(self):
        self.shifted_keys = [k[1] for k in get_display()._keymap_codes if k]

    def press(self, keys, delay=0.2):
        """Send key press events only.

        :param string keys: Keys you want pressed.

        Example:

        >>> press('Alt+F2')

        presses the 'Alt' and 'F2' keys.

        """
        if not isinstance(keys, basestring):
            raise TypeError("'keys' argument must be a string.")
        logger.debug("Pressing keys %r with delay %f", keys, delay)
        for key in self.__translate_keys(keys):
            self.__perform_on_key(key, X.KeyPress)
            sleep(delay)

    def release(self, keys, delay=0.2):
        """Send key release events only.

        :param string keys: Keys you want released.

        Example:

        >>> release('Alt+F2')

        releases the 'Alt' and 'F2' keys.

        """
        if not isinstance(keys, basestring):
            raise TypeError("'keys' argument must be a string.")
        logger.debug("Releasing keys %r with delay %f", keys, delay)
        # release keys in the reverse order they were pressed in.
        keys = self.__translate_keys(keys)
        keys.reverse()
        for key in keys:
            self.__perform_on_key(key, X.KeyRelease)
            sleep(delay)

    def press_and_release(self, keys, delay=0.2):
        """Press and release all items in 'keys'.

        This is the same as calling 'press(keys);release(keys)'.

        :param string keys: Keys you want pressed and released.

        Example:

        >>> press_and_release('Alt+F2')

        presses both the 'Alt' and 'F2' keys, and then releases both keys.

        """

        self.press(keys, delay)
        self.release(keys, delay)

    def type(self, string, delay=0.1):
        """Simulate a user typing a string of text.

        .. note:: Only 'normal' keys can be typed with this method. Control
         characters (such as 'Alt' will be interpreted as an 'A', and 'l',
         and a 't').

        """
        if not isinstance(string, basestring):
            raise TypeError("'keys' argument must be a string.")
        logger.debug("Typing text %r", string)
        for key in string:
            # Don't call press or release here, as they translate keys to keysyms.
            self.__perform_on_key(key, X.KeyPress)
            sleep(delay)
            self.__perform_on_key(key, X.KeyRelease)
            sleep(delay)

    @staticmethod
    def cleanup():
        """Generate KeyRelease events for any un-released keys.

        .. important:: Ensure you call this at the end of any test to release any
         keys that were pressed and not released.

        """
        global _PRESSED_KEYS
        for keycode in _PRESSED_KEYS:
            logger.warning("Releasing key %r as part of cleanup call.", keycode)
            fake_input(get_display(), X.KeyRelease, keycode)
        _PRESSED_KEYS = []

    def __perform_on_key(self, key, event):
        if not isinstance(key, basestring):
            raise TypeError("Key parameter must be a string")

        keycode = 0
        shift_mask = 0

        keycode, shift_mask = self.__char_to_keycode(key)

        if shift_mask != 0:
            fake_input(get_display(), event, 50)

        if event == X.KeyPress:
            logger.debug("Sending press event for key: %s", key)
            _PRESSED_KEYS.append(keycode)
        elif event == X.KeyRelease:
            logger.debug("Sending release event for key: %s", key)
            if keycode in _PRESSED_KEYS:
                _PRESSED_KEYS.remove(keycode)
            else:
                logger.warning("Generating release event for keycode %d that was not pressed.", keycode)

        fake_input(get_display(), event, keycode)
        get_display().sync()

    def __get_keysym(self, key):
        keysym = XK.string_to_keysym(key)
        if keysym == 0:
            # Unfortunately, although this works to get the correct keysym
            # i.e. keysym for '#' is returned as "numbersign"
            # the subsequent display.keysym_to_keycode("numbersign") is 0.
            keysym = XK.string_to_keysym(self._special_X_keysyms[key])
        return keysym

    def __is_shifted(self, key):
        return len(key) == 1 and ord(key) in self.shifted_keys and key != '<'

    def __char_to_keycode(self, key) :
        keysym = self.__get_keysym(key)
        keycode = get_display().keysym_to_keycode(keysym)
        if keycode == 0 :
            logger.warning("Sorry, can't map '%s'", key)

        if (self.__is_shifted(key)) :
            shift_mask = X.ShiftMask
        else :
            shift_mask = 0

        return keycode, shift_mask

    def __translate_keys(self, key_string):
        return [self._keysym_translations.get(k, k) for k in key_string.split('+')]


class Mouse(object):
    """Wrapper around xlib to make moving the mouse easier."""

    @property
    def x(self):
        """Mouse position X coordinate."""
        return self.position()[0]

    @property
    def y(self):
        """Mouse position Y coordinate."""
        return self.position()[1]

    def press(self, button=1):
        """Press mouse button at current mouse location."""
        logger.debug("Pressing mouse button %d", button)
        _PRESSED_MOUSE_BUTTONS.append(button)
        fake_input(get_display(), X.ButtonPress, button)
        get_display().sync()

    def release(self, button=1):
        """Releases mouse button at current mouse location."""
        logger.debug("Releasing mouse button %d", button)
        if button in _PRESSED_MOUSE_BUTTONS:
            _PRESSED_MOUSE_BUTTONS.remove(button)
        else:
            logger.warning("Generating button release event or button %d that was not pressed.", button)
        fake_input(get_display(), X.ButtonRelease, button)
        get_display().sync()

    def click(self, button=1, press_duration=0.10):
        """Click mouse at current location."""
        self.press(button)
        sleep(press_duration)
        self.release(button)

    def move(self, x, y, animate=True, rate=10, time_between_events=0.01):
        """Moves mouse to location (x, y).

        Callers should avoid specifying the *rate* or *time_between_events*
        parameters unless they need a specific rate of movement.

        """
        logger.debug("Moving mouse to position %d,%d %s animation.", x, y,
            "with" if animate else "without")

        def perform_move(x, y, sync):
            fake_input(get_display(), X.MotionNotify, sync, X.CurrentTime, X.NONE, x=x, y=y)
            get_display().sync()
            sleep(time_between_events)

        if not animate:
            perform_move(x, y, False)
            return

        dest_x, dest_y = x, y
        curr_x, curr_y = self.position()
        coordinate_valid = ScreenGeometry().is_point_on_any_monitor((x,y))

        while curr_x != dest_x or curr_y != dest_y:
            dx = abs(dest_x - curr_x)
            dy = abs(dest_y - curr_y)

            intx = float(dx) / max(dx, dy)
            inty = float(dy) / max(dx, dy)

            step_x = min(rate * intx, dx)
            step_y = min(rate * inty, dy)

            if dest_x < curr_x:
                step_x *= -1
            if dest_y < curr_y:
                step_y *= -1

            perform_move(step_x, step_y, True)
            if coordinate_valid:
                curr_x, curr_y = self.position()
            else:
                curr_x += step_x
                curr_y += step_y

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
        try:
            x,y,w,h = object_proxy.globalRect
            logger.debug("Moving to object's globalRect coordinates.")
            self.move(x+w/2, y+h/2)
            return
        except AttributeError:
            pass
        except (TypeError, ValueError):
            raise ValueError("Object '%r' has globalRect attribute, but it is not of the correct type" % object_proxy)

        try:
            x,y = object_proxy.center_x, object_proxy.center_y
            logger.debug("Moving to object's center_x, center_y coordinates.")
            self.move(x,y)
            return
        except AttributeError:
            pass
        except (TypeError, ValueError):
            raise ValueError("Object '%r' has center_x, center_y attributes, but they are not of the correct type" % object_proxy)

        try:
            x,y,w,h = object_proxy.x, object_proxy.y, object_proxy.w, object_proxy.h
            logger.debug("Moving to object's center point calculated from x,y,w,h attributes.")
            self.move(x+w/2,y+h/2)
            return
        except AttributeError:
            raise ValueError("Object '%r' does not have any recognised position attributes" % object_proxy)
        except (TypeError, ValueError):
            raise ValueError("Object '%r' has x,y attribute, but they are not of the correct type" % object_proxy)

    def position(self):
        """
        Returns the current position of the mouse pointer.

        :return: (x,y) tuple
        """

        coord = get_display().screen().root.query_pointer()._data
        x, y = coord["root_x"], coord["root_y"]
        return x, y

    @staticmethod
    def cleanup():
        """Put mouse in a known safe state."""
        global _PRESSED_MOUSE_BUTTONS
        for btn in _PRESSED_MOUSE_BUTTONS:
            logger.debug("Releasing mouse button %d as part of cleanup", btn)
            fake_input(get_display(), X.ButtonRelease, btn)
        _PRESSED_MOUSE_BUTTONS = []
        sg = ScreenGeometry()
        sg.move_mouse_to_monitor(0)


class ScreenGeometry:
    """Get details about screen geometry."""

    class BlacklistedDriverError(RuntimeError):
        """Cannot set primary monitor when running drivers listed in the driver blacklist."""

    def __init__(self):
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
