# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2012 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.

from __future__ import absolute_import

from os import remove
from tempfile import mktemp
from testtools.matchers import Equals
from time import sleep

from autopilot.testcase import AutopilotTestCase
import logging
logger = logging.getLogger(__name__)

class KeyboardTests(AutopilotTestCase):

    """Tests for the Keyboard class."""

    scenarios = [
        ('lower_alpha', dict(input='abcdefghijklmnopqrstuvwxyz')),
        ('upper_alpha', dict(input='ABCDEFGHIJKLMNOPQRSTUVWXYZ')),
        ('numeric', dict(input='0123456789')),
        ('punctuation', dict(input='`~!@#$%^&*()_-+={}[]|\\:;"\'<>,.?/'))
    ]

    def test_keyboard_types_correct_characters(self):
        """Verify that the keyboard.type method types what we expect."""
        self.process_manager.start_app_window('Terminal')
        filename = mktemp()
        self.keyboard.type('''python -c "open('%s','w').write(raw_input())"''' % filename)
        self.keyboard.press_and_release('Enter')
        self.addCleanup(remove, filename)
        sleep(1)
        self.keyboard.type(self.input, 0.01)
        self.keyboard.press_and_release('Enter')

        self.assertThat(open(filename).read(), Equals(self.input))

    def test_keyboard_press_and_release_types_correct_characters(self):
        """Verify that the Keyboard.press_and_release method types what we
        expect.

        """
        self.process_manager.start_app_window('Terminal')
        filename = mktemp()
        self.keyboard.type('''python -c "open('%s','w').write(raw_input())"''' % filename)
        self.keyboard.press_and_release('Enter')
        self.addCleanup(remove, filename)
        sleep(1)
        for character in self.input:
            self.keyboard.press_and_release(character, 0.01)
        self.keyboard.press_and_release('Enter')

        self.assertThat(open(filename).read(), Equals(self.input))

