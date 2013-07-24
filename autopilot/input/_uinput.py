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


"""UInput device drivers."""

from autopilot.input import Keyboard as KeyboardBase
from autopilot.input import Touch as TouchBase
from autopilot.input._common import get_center_point
import autopilot.platform

import logging
from time import sleep
from evdev import UInput, ecodes as e
import os.path

logger = logging.getLogger(__name__)

PRESS = 1
RELEASE = 0

_PRESSED_KEYS = []


def _get_devnode_path():
    """Provide a fallback uinput node for devices which don't support udev"""
    devnode = '/dev/autopilot-uinput'
    if not os.path.exists(devnode):
        devnode = '/dev/uinput'
    return devnode


class Keyboard(KeyboardBase):

    _device = UInput(devnode=_get_devnode_path())

    def _emit(self, event, value):
        Keyboard._device.write(e.EV_KEY, event, value)
        Keyboard._device.syn()

    def _sanitise_keys(self, keys):
        if keys == '+':
            return [keys]
        else:
            return keys.split('+')

    def press(self, keys, delay=0.1):
        """Send key press events only.

        The 'keys' argument must be a string of keys you want
        pressed. For example:

        press('Alt+F2')

        presses the 'Alt' and 'F2' keys.

        """
        if not isinstance(keys, basestring):
            raise TypeError("'keys' argument must be a string.")

        for key in self._sanitise_keys(keys):
            for event in Keyboard._get_events_for_key(key):
                logger.debug("Pressing %s (%r)", key, event)
                _PRESSED_KEYS.append(event)
                self._emit(event, PRESS)
                sleep(delay)

    def release(self, keys, delay=0.1):
        """Send key release events only.

        The 'keys' argument must be a string of keys you want
        released. For example:

        release('Alt+F2')

        releases the 'Alt' and 'F2' keys.

        Keys are released in the reverse order in which they are specified.

        """
        if not isinstance(keys, basestring):
            raise TypeError("'keys' argument must be a string.")

        for key in reversed(self._sanitise_keys(keys)):
            for event in Keyboard._get_events_for_key(key):
                logger.debug("Releasing %s (%r)", key, event)
                if event in _PRESSED_KEYS:
                    _PRESSED_KEYS.remove(event)
                self._emit(event, RELEASE)
                sleep(delay)

    def press_and_release(self, keys, delay=0.1):
        """Press and release all items in 'keys'.

        This is the same as calling 'press(keys);release(keys)'.

        The 'keys' argument must be a string of keys you want
        pressed and released.. For example:

        press_and_release('Alt+F2')

        presses both the 'Alt' and 'F2' keys, and then releases both keys.

        """
        logger.debug("Pressing and Releasing: %s", keys)
        self.press(keys, delay)
        self.release(keys, delay)

    def type(self, string, delay=0.1):
        """Simulate a user typing a string of text.

        Only 'normal' keys can be typed with this method. Control characters
        (such as 'Alt' will be interpreted as an 'A', and 'l', and a 't').

        """
        if not isinstance(string, basestring):
            raise TypeError("'keys' argument must be a string.")
        logger.debug("Typing text %r", string)
        for key in string:
            self.press(key, delay)
            self.release(key, delay)

    @classmethod
    def on_test_end(cls, test_instance):
        """Generate KeyRelease events for any un-released keys.

        Make sure you call this at the end of any test to release
        any keys that were pressed and not released.

        """
        global _PRESSED_KEYS
        if len(_PRESSED_KEYS) == 0:
            return

        def _release(event):
            Keyboard._device.write(e.EV_KEY, event, RELEASE)
            Keyboard._device.syn()
        for event in _PRESSED_KEYS:
            logger.warning("Releasing key %r as part of cleanup call.", event)
            _release(event)
        _PRESSED_KEYS = []

    @staticmethod
    def _get_events_for_key(key):
        """Return a list of events required to generate 'key' as an input.

        Multiple keys will be returned when the key specified requires more
        than one keypress to generate (for example, upper-case letters).

        """
        events = []
        if key.isupper() or key in _SHIFTED_KEYS:
            events.append(e.KEY_LEFTSHIFT)
        keyname = _UINPUT_CODE_TRANSLATIONS.get(key.upper(), key)
        evt = getattr(e, 'KEY_' + keyname.upper(), None)
        if evt is None:
            raise ValueError("Unknown key name: '%s'" % key)
        events.append(evt)
        return events


last_tracking_id = 0


def get_next_tracking_id():
    global last_tracking_id
    last_tracking_id += 1
    return last_tracking_id


def create_touch_device(res_x=None, res_y=None):
    """Create and return a UInput touch device.

    If res_x and res_y are not specified, they will be queried from the system.

    """

    if res_x is None or res_y is None:
        from autopilot.display import Display
        display = Display.create()
        # TODO: This calculation needs to become part of the display module:
        l = r = t = b = 0
        for screen in range(display.get_num_screens()):
            geometry = display.get_screen_geometry(screen)
            if geometry[0] < l:
                l = geometry[0]
            if geometry[1] < t:
                t = geometry[1]
            if geometry[0] + geometry[2] > r:
                r = geometry[0] + geometry[2]
            if geometry[1] + geometry[3] > b:
                b = geometry[1] + geometry[3]
        res_x = r - l
        res_y = b - t

    # android uses BTN_TOOL_FINGER, whereas desktop uses BTN_TOUCH. I have no
    # idea why...
    touch_tool = e.BTN_TOOL_FINGER
    if autopilot.platform.model() == 'Desktop':
        touch_tool = e.BTN_TOUCH

    cap_mt = {
        e.EV_ABS: [
            (e.ABS_X, (0, res_x, 0, 0)),
            (e.ABS_Y, (0, res_y, 0, 0)),
            (e.ABS_PRESSURE, (0, 65535, 0, 0)),
            (e.ABS_MT_POSITION_X, (0, res_x, 0, 0)),
            (e.ABS_MT_POSITION_Y, (0, res_y, 0, 0)),
            (e.ABS_MT_TOUCH_MAJOR, (0, 30, 0, 0)),
            (e.ABS_MT_TRACKING_ID, (0, 65535, 0, 0)),
            (e.ABS_MT_PRESSURE, (0, 255, 0, 0)),
            (e.ABS_MT_SLOT, (0, 9, 0, 0)),
        ],
        e.EV_KEY: [
            touch_tool,
        ]
    }

    return UInput(cap_mt, name='autopilot-finger', version=0x2,
                  devnode=_get_devnode_path())

_touch_device = create_touch_device()

# Multiouch notes:
# ----------------

# We're simulating a class of device that can track multiple touches, and keep
# them separate. This is how most modern track devices work anyway. The device
# is created with a capability to track a certain number of distinct touches at
# once. This is the ABS_MT_SLOT capability. Since our target device can track 9
# separate touches, we'll do the same.

# Each finger contact starts by registering a slot number (0-8) with a tracking
# Id. The Id should be unique for this touch - this can be an
# auto-inctrementing integer. The very first packets to tell the kernel that
# we have a touch happening should look like this:

#    ABS_MT_SLOT 0
#    ABS_MT_TRACKING_ID 45
#    ABS_MT_POSITION_X x[0]
#    ABS_MT_POSITION_Y y[0]

# This associates Tracking id 45 (could be any number) with slot 0. Slot 0 can
# now not be use by any other touch until it is released.

# If we want to move this contact's coordinates, we do this:

#    ABS_MT_SLOT 0
#    ABS_MT_POSITION_X 123
#    ABS_MT_POSITION_Y 234

# Technically, the 'SLOT 0' part isn't needed, since we're already in slot 0,
# but it doesn't hurt to have it there.

# To lift the contact, we simply specify a tracking Id of -1:

#    ABS_MT_SLOT 0
#    ABS_MT_TRACKING_ID -1

# The initial association between slot and tracking Id is made when the
# 'finger' first makes contact with the device (well, not technically true,
# but close enough). Multiple touches can be active simultaniously, as long
# as they all have unique slots, and tracking Ids. The simplest way to think
# about this is that the SLOT refers to a finger number, and the TRACKING_ID
# identifies a unique touch for the duration of it's existance.

_touch_fingers_in_use = []


def _get_touch_finger():
    """Claim a touch finger id for use.

    :raises: RuntimeError if no more fingers are available.

    """
    global _touch_fingers_in_use

    for i in range(9):
        if i not in _touch_fingers_in_use:
            _touch_fingers_in_use.append(i)
            return i
    raise RuntimeError("All available fingers have been used already.")


def _release_touch_finger(finger_num):
    """Relase a previously-claimed finger id.

    :raises: RuntimeError if the finger given was never claimed, or was already
    released.

    """
    global _touch_fingers_in_use

    if finger_num not in _touch_fingers_in_use:
        raise RuntimeError(
            "Finger %d was never claimed, or has already been released." %
            (finger_num))
    _touch_fingers_in_use.remove(finger_num)
    assert(finger_num not in _touch_fingers_in_use)


class Touch(TouchBase):
    """Low level interface to generate single finger touch events."""

    def __init__(self):
        super(Touch, self).__init__()
        self._touch_finger = None

    @property
    def pressed(self):
        return self._touch_finger is not None

    def tap(self, x, y):
        """Click (or 'tap') at given x and y coordinates."""
        logger.debug("Tapping at: %d,%d", x, y)
        self._finger_down(x, y)
        sleep(0.1)
        self._finger_up()

    def tap_object(self, object):
        """Click (or 'tap') a given object"""
        logger.debug("Tapping object: %r", object)
        x, y = get_center_point(object)
        self.tap(x, y)

    def press(self, x, y):
        """Press and hold a given object or at the given coordinates
        Call release() when the object has been pressed long enough"""
        logger.debug("Pressing at: %d,%d", x, y)
        self._finger_down(x, y)

    def release(self):
        """Release a previously pressed finger"""
        logger.debug("Releasing")
        self._finger_up()

    def drag(self, x1, y1, x2, y2):
        """Perform a drag gesture from (x1,y1) to (x2,y2)"""
        logger.debug("Dragging from %d,%d to %d,%d", x1, y1, x2, y2)
        self._finger_down(x1, y1)

        # Let's drag in 100 steps for now...
        dx = 1.0 * (x2 - x1) / 100
        dy = 1.0 * (y2 - y1) / 100
        cur_x = x1 + dx
        cur_y = y1 + dy
        for i in range(0, 100):
            self._finger_move(int(cur_x), int(cur_y))
            sleep(0.002)
            cur_x += dx
            cur_y += dy
        # Make sure we actually end up at target
        self._finger_move(x2, y2)
        self._finger_up()

    def _finger_down(self, x, y):
        """Internal: moves finger "finger" down on the touchscreen.

        :param x: The finger will be moved to this x coordinate.
        :param y: The finger will be moved to this y coordinate.

        """
        if self._touch_finger is not None:
            raise RuntimeError("Cannot press finger: it's already pressed.")
        self._touch_finger = _get_touch_finger()

        _touch_device.write(e.EV_ABS, e.ABS_MT_SLOT, self._touch_finger)
        _touch_device.write(
            e.EV_ABS, e.ABS_MT_TRACKING_ID, get_next_tracking_id())
        _touch_device.write(e.EV_KEY, e.BTN_TOOL_FINGER, 1)
        _touch_device.write(e.EV_ABS, e.ABS_MT_POSITION_X, int(x))
        _touch_device.write(e.EV_ABS, e.ABS_MT_POSITION_Y, int(y))
        _touch_device.write(e.EV_ABS, e.ABS_MT_PRESSURE, 400)
        _touch_device.syn()

    def _finger_move(self, x, y):
        """Internal: moves finger "finger" on the touchscreen to pos (x,y)
           NOTE: The finger has to be down for this to have any effect."""
        if self._touch_finger is not None:
            _touch_device.write(e.EV_ABS, e.ABS_MT_SLOT, self._touch_finger)
            _touch_device.write(e.EV_ABS, e.ABS_MT_POSITION_X, int(x))
            _touch_device.write(e.EV_ABS, e.ABS_MT_POSITION_Y, int(y))
            _touch_device.syn()

    def _finger_up(self):
        """Internal: moves finger "finger" up from the touchscreen"""
        if self._touch_finger is None:
            raise RuntimeError("Cannot release finger: it's not pressed.")
        _touch_device.write(e.EV_ABS, e.ABS_MT_SLOT, self._touch_finger)
        _touch_device.write(e.EV_ABS, e.ABS_MT_TRACKING_ID, -1)
        _touch_device.write(e.EV_KEY, e.BTN_TOOL_FINGER, 0)
        _touch_device.syn()
        self._touch_finger = _release_touch_finger(self._touch_finger)


# veebers: there should be a better way to handle this.
_SHIFTED_KEYS = "~!@#$%^&*()_+{}|:\"?><"

# The double-ups are due to the 'shifted' keys.
_UINPUT_CODE_TRANSLATIONS = {
    '/': 'SLASH',
    '?': 'SLASH',
    '.': 'DOT',
    ',': 'COMMA',
    '>': 'DOT',
    '<': 'COMMA',
    '\'': 'APOSTROPHE',
    '"': 'APOSTROPHE',
    ';': 'SEMICOLON',
    ':': 'SEMICOLON',
    '\\': 'BACKSLASH',
    '|': 'BACKSLASH',
    ']': 'RIGHTBRACE',
    '[': 'LEFTBRACE',
    '}': 'RIGHTBRACE',
    '{': 'LEFTBRACE',
    '=': 'EQUAL',
    '+': 'EQUAL',
    '-': 'MINUS',
    '_': 'MINUS',
    ')': '0',
    '(': '9',
    '*': '8',
    '&': '7',
    '^': '6',
    '%': '5',
    '$': '4',
    '#': '3',
    '@': '2',
    '!': '1',
    '~': 'GRAVE',
    '`': 'GRAVE',
    ' ': 'SPACE',
    '\t': 'TAB',
    '\n': 'ENTER',
    'CTRL': 'LEFTCTRL',
    'ALT': 'LEFTALT',
    'SHIFT': 'LEFTSHIFT',
}
