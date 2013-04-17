# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2013 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.

"""
Autopilot unified input system.
===============================

This package provides input methods for various platforms. Autopilot aims to
provide an appropriate implementation for the currently running system. For
example, not all systems have an X11 stack running: on those systems, autopilot
will instantiate input classes class that use something other than X11 to generate
events (possibly UInput).

Test authors should instantiate the appropriate class using the ``create`` method
on each class. Calling ``create()`` with  no arguments will get an instance of the
specified class that suits the current platform. In this case, autopilot will
do it's best to pick a suitable backend. Calling ``create`` with a backend name
will result in that specific backend type being returned, or, if it cannot be created,
an exception will be raised. For more information on creating backends, see
:ref:`tut-picking-backends`

There are three basic input types available:

 * :class:`Keyboard` - traditional keyboard devices.
 * :class:`Mouse` - traditional mouse devices.
 * :class:`Touch` - single point-of-contact touch device.
 * For multitouch capabilities, see the :mod:`autopilot.gestures` module.

"""

from collections import OrderedDict
from autopilot.utilities import _pick_backend



class Keyboard(object):

    """A simple keyboard device class.

    The keyboard class is used to generate key events while in an autopilot
    test. This class should not be instantiated directly. To get an
    instance of the keyboard class, call :py:meth:`create` instead.

    """

    @staticmethod
    def create(preferred_backend=''):
        """Get an instance of the :py:class:`Keyboard` class.

        For more infomration on picking specific backends, see :ref:`tut-picking-backends`

        :param preferred_backend: A string containing a hint as to which backend
            you would like. Possible backends are:

            * ``X11`` - Generate keyboard events using the X11 client libraries.
            * ``UInput`` - Use UInput kernel-level device driver.

        :raises: RuntimeError if autopilot cannot instantate any of the possible
            backends.
        :raises: RuntimeError if the preferred_backend is specified and is not
            one of the possible backends for this device class.
        :raises: :class:`~autopilot.BackendException` if the preferred_backend is
            set, but that backend could not be instantiated.


        """
        def get_x11_kb():
            from autopilot.input._X11 import Keyboard
            return Keyboard()
        def get_uinput_kb():
            from autopilot.input._uinput import Keyboard
            return Keyboard()

        backends = OrderedDict()
        backends['X11'] = get_x11_kb
        backends['UInput'] = get_uinput_kb
        return _pick_backend(backends, preferred_backend)

    def press(self, keys, delay=0.2):
        """Send key press events only.

        :param keys: Keys you want pressed.
        :param delay: The delay (in Seconds) after pressing the keys before
            returning control to the caller.

        Example:

        >>> press('Alt+F2')

        presses the 'Alt' and 'F2' keys, but does not release them.

        """
        raise NotImplementedError("You cannot use this class directly.")

    def release(self, keys, delay=0.2):
        """Send key release events only.

        :param keys: Keys you want released.
        :param delay: The delay (in Seconds) after releasing the keys before
            returning control to the caller.

        Example:

        >>> release('Alt+F2')

        releases the 'Alt' and 'F2' keys.

        """
        raise NotImplementedError("You cannot use this class directly.")

    def press_and_release(self, keys, delay=0.2):
        """Press and release all items in 'keys'.

        This is the same as calling 'press(keys);release(keys)'.

        :param keys: Keys you want pressed and released.
        :param delay: The delay (in Seconds) after pressing and releasing each
            key.

        Example:

        >>> press_and_release('Alt+F2')

        presses both the 'Alt' and 'F2' keys, and then releases both keys.

        """

        raise NotImplementedError("You cannot use this class directly.")

    def type(self, string, delay=0.1):
        """Simulate a user typing a string of text.

        :param string: The string to text to type.
        :param delay: The delay (in Seconds) after pressing and releasing each
            key. Note that the default value here is shorter than for the press,
            release and press_and_release methods.

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

    """A simple mouse device class.

    The mouse class is used to generate mouse events while in an autopilot
    test. This class should not be instantiated directly however. To get an
    instance of the mouse class, call :py:meth:`create` instead.

    For example, to create a mouse object and click at (100,50):

    >>> mouse = autopilot.input.Mouse.create()
    >>> mouse.move(100, 50)
    >>> mouse.click()

    """

    @staticmethod
    def create(preferred_backend=''):
        """Get an instance of the :py:class:`Mouse` class.

        For more infomration on picking specific backends, see :ref:`tut-picking-backends`

        :param preferred_backend: A string containing a hint as to which backend you
            would like. Possible backends are:

            * ``X11`` - Generate mouse events using the X11 client libraries.

        :raises: RuntimeError if autopilot cannot instantate any of the possible
            backends.
        :raises: RuntimeError if the preferred_backend is specified and is not
            one of the possible backends for this device class.
        :raises: :class:`~autopilot.BackendException` if the preferred_backend is
            set, but that backend could not be instantiated.

        """
        def get_x11_mouse():
            from autopilot.input._X11 import Mouse
            return Mouse()

        backends = OrderedDict()
        backends['X11'] = get_x11_mouse
        return _pick_backend(backends, preferred_backend)

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


class Touch(object):
    """A simple touch driver class.

    This class can be used for any touch events that require a single active
    touch at once. If you want to do complex gestures (including multi-touch
    gestures), look at the :py:mod:`autopilot.gestures` module.

    """

    @staticmethod
    def create(preferred_backend=''):
        """Get an instance of the :py:class:`Touch` class.

        :param preferred_backend: A string containing a hint as to which backend you
            would like. If left blank, autopilot will pick a suitable
            backend for you. Specifying a backend will guarantee that either that
            backend is returned, or an exception is raised.

            possible backends are:

            * ``UInput`` - Use UInput kernel-level device driver.

        :raises: RuntimeError if autopilot cannot instantate any of the possible
            backends.
        :raises: RuntimeError if the preferred_backend is specified and is not
            one of the possible backends for this device class.
        :raises: :class:`~autopilot.BackendException` if the preferred_backend is
            set, but that backend could not be instantiated.


        """
        def get_uinput_touch():
            from autopilot.input._uinput import Touch
            return Touch()

        backends = OrderedDict()
        backends['UInput'] = get_uinput_touch
        return _pick_backend(backends, preferred_backend)

    @property
    def pressed(self):
        """Return True if this touch is currently in use (i.e.- pressed on the
            'screen').

        """
        raise NotImplementedError("You cannot use this class directly.")

    def tap(self, x, y):
        """Click (or 'tap') at given x and y coordinates."""
        raise NotImplementedError("You cannot use this class directly.")

    def tap_object(self, object):
        """Tap the center point of a given object.

        It does this by looking for several attributes, in order. The first
        attribute found will be used. The attributes used are (in order):

         * globalRect (x,y,w,h)
         * center_x, center_y
         * x, y, w, h

        :raises: **ValueError** if none of these attributes are found, or if an
         attribute is of an incorrect type.

         """
        raise NotImplementedError("You cannot use this class directly.")

    def press(self, x, y):
        """Press and hold."""
        raise NotImplementedError("You cannot use this class directly.")

    def release(self):
        """Release a previously pressed finger"""
        raise NotImplementedError("You cannot use this class directly.")

    def drag(self, x1, y1, x2, y2):
        """Perform a drag gesture from (x1,y1) to (x2,y2)"""
        raise NotImplementedError("You cannot use this class directly.")