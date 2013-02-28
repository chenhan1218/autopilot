# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2013 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.


"""UInput device drivers."""

from autopilot.emulators.input import Keyboard as KeyboardBase
import logging
from time import sleep
from evdev import AbsData, InputDevice, UInput, ecodes as e
import os.path

logger = logging.getLogger(__name__)

PRESS = 1
RELEASE = 0

PRESSED_KEYS = []

class Keyboard(KeyboardBase):

    def __init__(self):
        try:
            self._device = UInput()
        except:
            logger.warning("uinput not available")

    def _emit(self, event, value):
        self._device.write(e.EV_KEY, event, value)
        self._device.syn()

    def press(self, keys, delay=0.1):
        """Send key press events only.

        The 'keys' argument must be a string of keys you want
        pressed. For example:

        press('Alt+F2')

        presses the 'Alt' and 'F2' keys.

        """
        if not isinstance(keys, basestring):
            raise TypeError("'keys' argument must be a string.")

        for key in keys.split('+'):
            for event in _get_events_for_key(key):
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
        # logger.debug("Releasing keys %r with delay %f", keys, delay)
        # # release keys in the reverse order they were pressed in.
        # keys = self.__translate_keys(keys)
        for key in reversed(keys.split('+')):
            for event in _get_events_for_key(key):
                self._emit(event, RELEASE)
                sleep(delay)

    def press_and_release(self, keys, delay=0.1):
        """Press and release all items in 'keys'.

        This is the same as calling 'press(keys);release(keys)'.

        The 'keys' argument must be a string of keys you want
        pressed and released.. For example:

        press_and_release('Alt+F2'])

        presses both the 'Alt' and 'F2' keys, and then releases both keys.

        """

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

    @staticmethod
    def cleanup():
        """Generate KeyRelease events for any un-released keys.

        Make sure you call this at the end of any test to release
        any keys that were pressed and not released.

        """
        # global _PRESSED_KEYS
        # for keycode in _PRESSED_KEYS:
        #     logger.warning("Releasing key %r as part of cleanup call.", keycode)
        #     fake_input(get_display(), X.KeyRelease, keycode)
        # _PRESSED_KEYS = []

last_tracking_id = 0
def get_next_tracking_id():
    global last_tracking_id
    last_tracking_id += 1
    return last_tracking_id

def create_touch_device(res_x=None, res_y=None):
    """Create and return a UInput touch device.

    If res_x and res_y are not specified, they will be queried from X11.

    The following needs to go into /system/usr/idc/autopilot-finger.idc

    # Copyright (C) 2011 The Android Open Source Project
    #
    # Licensed under the Apache License, Version 2.0 (the "License");
    # you may not use this file except in compliance with the License.
    # You may obtain a copy of the License at
    #
    #      http://www.apache.org/licenses/LICENSE-2.0
    #
    # Unless required by applicable law or agreed to in writing, software
    # distributed under the License is distributed on an "AS IS" BASIS,
    # WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    # See the License for the specific language governing permissions and
    # limitations under the License.

    #
    # Input Device Calibration File for the Tuna touch screen.
    #

    device.internal = 1

    # Basic Parameters
    touch.deviceType = touchScreen
    touch.orientationAware = 1

    # Size
    touch.size.calibration = diameter
    touch.size.scale = 10
    touch.size.bias = 0
    touch.size.isSummed = 0

    # Pressure
    # Driver reports signal strength as pressure.
    #
    # A normal thumb touch typically registers about 200 signal strength
    # units although we don't expect these values to be accurate.
    touch.pressure.calibration = amplitude
    touch.pressure.scale = 0.005

    # Orientation
    touch.orientation.calibration = none
    """

    # FIXME: remove the harcoded values and determine ScreenGeometry without X11
    res_x = 720
    res_y = 1280

    if res_x is None or res_y is None:
        from autopilot.emulators.X11 import ScreenGeometry
        sg = ScreenGeometry()
        res_x = sg.get_screen_width()
        res_y = sg.get_screen_height()

    cap_mt = {
        e.EV_ABS : [
            (e.ABS_X, AbsData(0, res_x, 0, 0)),
            (e.ABS_Y, AbsData(0, res_y, 0, 0)),
            (e.ABS_PRESSURE, AbsData(0, 65535, 0, 0)),
            (e.ABS_DISTANCE, AbsData(0, 65535, 0, 0)),
            (e.ABS_TOOL_WIDTH, AbsData(0, 65535, 0, 0)),
            (e.ABS_MT_POSITION_X, AbsData(0, res_x, 0, 0)),
            (e.ABS_MT_POSITION_Y, AbsData(0, res_y, 0, 0)),
            (e.ABS_MT_TOUCH_MAJOR, AbsData(0, 30, 0, 0)),
            (e.ABS_MT_TRACKING_ID, AbsData(0, 65535, 0, 0)),
            (e.ABS_MT_PRESSURE, (0, 255, 0, 0)),
            (e.ABS_MT_SLOT, (0, 9, 0, 0)),
        ],
        e.EV_KEY: [
            e.BTN_TOOL_FINGER,
        ]
    }

    try:
        device = UInput(cap_mt, name='autopilot-finger', version=0x2)
        return device
    except:
        logger.warning("Failed to open uinput device. Finger will not be available")
        return None


def find_touch_device():
    """Return a list of touch devices found on the local machine.

    :returns: A list of evdev.inputDevice objects, possibly an empty list.

    """
    def device_cmp(dev_a, dev_b):
        def get_track_slot(dev):
            capabilities = dev.capabilities()
            for track_feature in capabilities[e.EV_ABS]:
                if track_feature[0] == e.ABS_MT_SLOT:
                    return track_feature[1][1]
        return get_track_slot(dev_a) < get_track_slot(dev_b)

    i = 0
    touch_devices = []
    while True:
        path = '/dev/input/event%d' % (i)
        if not os.path.exists(path):
            break

        dev = InputDevice(path)
        capabilities = dev.capabilities()
        if e.EV_ABS in capabilities:
            touch_devices.append(dev)
        i += 1
    touch_devices.sort(device_cmp)
    return touch_devices


"""
Multiouch notes:
----------------

We're simulating a class of device that can track multiple touches, and keep
them separate. This is how most modern track devices work anyway. The device
is created with a capability to track a certain number of distinct touches at
once. This is the ABS_MT_SLOT capability. Since our target device can track 9
separate touches, we'll do the same.

Each finger contact starts by registering a slot number (0-8) with a tracking
Id. The Id should be unique for this touch - this can be an auto-inctrementing
integer. The very first packets to tell the kernel that we have a touch happening
should look like this:

   ABS_MT_SLOT 0
   ABS_MT_TRACKING_ID 45
   ABS_MT_POSITION_X x[0]
   ABS_MT_POSITION_Y y[0]

This associates Tracking id 45 (could be any number) with slot 0. Slot 0 can now
not be use by any other touch until it is released.

If we want to move this contact's coordinates, we do this:

   ABS_MT_SLOT 0
   ABS_MT_POSITION_X 123
   ABS_MT_POSITION_Y 234

Technically, the 'SLOT 0' part isn't needed, since we're already in slot 0, but
it doesn't hurt to have it there.

To lift the contact, we simply specify a tracking Id of -1:

   ABS_MT_SLOT 0
   ABS_MT_TRACKING_ID -1

The initial association between slot and tracking Id is made when the 'finger'
first makes contact with the device (well, not technically true, but close
enough). Multiple touches can be active simultaniously, as long as they all have
unique slots, and tracking Ids. The simplest way to think about this is that the
SLOT refers to a finger number, and the TRACKING_ID identifies a unique touch
for the duration of it's existance.

"""

class Finger(object):
    """Low level interface to generate single finger touch events."""

    def __init__(self):
        self.device = create_touch_device()
        if self.device == None:
            raise UInputError
        self.current_x = 0
        self.current_y = 0

    def move(self, x, y):
        """This is a convenience function to keep API compatibility with other pointer input methods"""
        self.current_x = x
        self.current_y = y

    def move_to_object(self, object):
        """This is a convenience function to keep API compatibility with other pointer input methods"""
        self.current_x = object.globalRect[0] + object.globalRect[2] / 2
        self.current_y = object.globalRect[1] + object.globalRect[3] / 2

    def click(self):
        self.tap(self.current_x, self.current_y)

    def tap(self, x, y):
        """Click (or 'tap') at given x and y coordinates."""
        self._finger_down(0, x, y)
        sleep(0.1)
        self._finger_up(0)

    def tap_object(self, object):
        """Click (or 'tap') a given object"""
        self.tap(object.globalRect[0] + object.globalRect[2] / 2, object.globalRect[1] + object.globalRect[3] / 2)

    def press(self, *args):
        """Press and hold a given object or at the given coordinates
        Call release() when the object has been pressed long enough"""
        if len(args) == 2:
            self.current_x = args[0]
            self.current_y = args[1]
        elif len(args) == 0:
            pass
        else:
            raise InvalidArgCount
        self._finger_down(0, self.current_x, self.current_y)

    def release(self):
        """Release a previously pressed finger"""
        self._finger_up(0)


    def drag(self, x1, y1, x2, y2):
        """Perform a drag gesture from (x1,y1) to (x2,y2)"""
        self._finger_down(0, x1, y1)

        # Let's drag in 100 steps for now...
        dx = 1.0 * (x2 - x1) / 100
        dy = 1.0 * (y2 - y1) / 100
        cur_x = x1 + dx
        cur_y = y1 + dy
        for i in range(0, 100):
            self._finger_move(0, int(cur_x), int(cur_y))
            sleep(0.002)
            cur_x += dx
            cur_y += dy
        # Make sure we actually end up at target
        self._finger_move(0, x2, y2)
        self._finger_up(0)

    def pinch(self, center, distance_start, distance_end):
        """Perform a two finger pinch (zoom) gesture
        "center" gives the coordinates [x,y] of the center between the two fingers
        "distance_start" [x,y] values to move away from the center for the start
        "distance_end" [x,y] values to move away from the center for the end
        The fingers will move in 100 steps between the start and the end points.
        If start is smaller than end, the gesture will zoom in, otherwise it
        will zoom out."""

        finger_1_start = [center[0] - distance_start[0], center[1] - distance_start[1]]
        finger_2_start = [center[0] + distance_start[0], center[1] + distance_start[1]]
        finger_1_end = [center[0] - distance_end[0], center[1] - distance_end[1]]
        finger_2_end = [center[0] + distance_end[0], center[1] + distance_end[1]]

        dx = 1.0 * (finger_1_end[0] - finger_1_start[0]) / 100
        dy = 1.0 * (finger_1_end[1] - finger_1_start[1]) / 100

        self._finger_down(0, finger_1_start[0], finger_1_start[1])
        self._finger_down(1, finger_2_start[0], finger_2_start[1])

        finger_1_cur = [finger_1_start[0] + dx, finger_1_start[1] + dy]
        finger_2_cur = [finger_2_start[0] - dx, finger_2_start[1] - dy]

        for i in range(0, 100):
            self._finger_move(0, finger_1_cur[0], finger_1_cur[1])
            self._finger_move(1, finger_2_cur[0], finger_2_cur[1])
            sleep(0.005)

            finger_1_cur = [finger_1_cur[0] + dx, finger_1_cur[1] + dy]
            finger_2_cur = [finger_2_cur[0] - dx, finger_2_cur[1] - dy]

        self._finger_move(0, finger_1_end[0], finger_1_end[1])
        self._finger_move(1, finger_2_end[0], finger_2_end[1])
        self._finger_up(0)
        self._finger_up(1)

    def _finger_down(self, finger, x, y):
        """Internal: moves finger "finger" down to the touchscreen at pos (x,y)"""
        self.device.write(e.EV_ABS, e.ABS_MT_SLOT, finger)
        self.device.write(e.EV_ABS, e.ABS_MT_TRACKING_ID, get_next_tracking_id())
        self.device.write(e.EV_KEY, e.BTN_TOOL_FINGER, 1)
        self.device.write(e.EV_ABS, e.ABS_MT_POSITION_X, x)
        self.device.write(e.EV_ABS, e.ABS_MT_POSITION_Y, y)
        self.device.write(e.EV_ABS, e.ABS_MT_PRESSURE, 400)
        self.device.syn()


    def _finger_move(self, finger, x, y):
        """Internal: moves finger "finger" on the touchscreen to pos (x,y)
           NOTE: The finger has to be down for this to have any effect."""
        self.device.write(e.EV_ABS, e.ABS_MT_SLOT, finger)
        self.device.write(e.EV_ABS, e.ABS_MT_POSITION_X, int(x))
        self.device.write(e.EV_ABS, e.ABS_MT_POSITION_Y, int(y))
        self.device.syn()


    def _finger_up(self, finger):
        """Internal: moves finger "finger" up from the touchscreen"""
        self.device.write(e.EV_ABS, e.ABS_MT_SLOT, finger)
        self.device.write(e.EV_ABS, e.ABS_MT_TRACKING_ID, -1)
        self.device.write(e.EV_KEY, e.BTN_TOOL_FINGER, 0)
        self.device.syn()


class MultiTouch(object):
    """High level interface to generate multi-touch events."""

    # Need to work out a good interface for generating multitouch events...
    # Possibly get users to specify each individual finger tracking path, or
    # possibly specify a gesture by name, with parameters or so?
    #
    # Probably need to specify X & Y resolution as well. Think we can ignore
    # pressure right now.
    #
    # Multi-touch protocol documentation is here:
    #
    # http://www.kernel.org/doc/Documentation/input/multi-touch-protocol.txt



_UINPUT_CODE_TRANSLATIONS = {
    ' ': 'SPACE',
    '\t': 'TAB',
    'CTRL': 'LEFTCTRL',
    'ALT': 'LEFTALT',
    'SHIFT': 'LEFTSHIFT',
}


def _get_events_for_key(key):
    """Return a list of events required to generate 'key' as an input.

    Multiple keys will be returned when the key specified requires more than one
    keypress to generate (for example, upper-case letters).

    """
    events = []
    if key.isupper():
        events.append(e.KEY_LEFTSHIFT)
    keyname = _UINPUT_CODE_TRANSLATIONS.get(key.upper(), key)
    evt = getattr(e, 'KEY_' + keyname.upper(), None)
    if evt is None:
        raise ValueError("Unknown key name: '%s'" % key)
    events.append(evt)
    return events


