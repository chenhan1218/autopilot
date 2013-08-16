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

import logging
from time import sleep
from contextlib import contextmanager

from maliit_keyboard.emulators.osk import OSK, OSKUnsupportedKey

from autopilot.input import Keyboard as KeyboardBase


logger = logging.getLogger(__name__)


class Keyboard(KeyboardBase):

    _keyboard = OSK()

    @contextmanager
    def focused_type(self, input_target, pointer=None):
        with super(Keyboard, self).focused_type(input_target, pointer):
            try:
                yield self
            finally:
                self._keyboard.dismiss()

    def press(self, keys, delay=0.2):
        raise NotImplementedError(
            "OSK Backend does not support the press method"
        )

    def release(self, keys, delay=0.2):
        raise NotImplementedError(
            "OSK Backend does not support the release method"
        )

    def press_and_release(self, keys, delay=0.2):
        """Press and release all items in 'keys'.

        The 'keys' argument must be a string of keys you want
        pressed and released.. For example:

        press_and_release('Alt+F2')

        presses both the 'Alt' and 'F2' keys, and then releases both keys.

        """
        for key in self._sanitise_keys(keys):
            try:
                self._keyboard.press_key(key)
                sleep(delay)
            except OSKUnsupportedKey:
                logger.warning(
                    "OSK Backend is unable to type the key '%s" % key
                )

    def type(self, string, delay=0.1):
        """Simulate a user typing a string of text.

        Only 'normal' keys can be typed with this method. Control characters
        (such as 'Alt' will be interpreted as an 'A', and 'l', and a 't').

        The osk class back end will take care of ensureing that capitalized
        keys are in fact capitalized.

        """
        if not isinstance(string, basestring):
            raise TypeError("'string' argument must be a string.")
        logger.debug("Typing text: %s", string)
        self._keyboard.type(string, delay)

    @classmethod
    def on_test_end(cls, test_instance):
        """Dismiss (swipe hide) the keyboard so we're clear for the next
        test.

        """
        logger.debug("Dismissing the OSK with a swipe.")
        cls._keyboard.dismiss()

    def _sanitise_keys(self, keys):
        if keys == '+':
            return [keys]
        else:
            return keys.split('+')
