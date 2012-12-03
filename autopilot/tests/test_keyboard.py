# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2012 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.

from __future__ import absolute_import

from os import remove
from testtools.matchers import Contains
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
        """Verify that the keyboard types what we expect."""
        term_window = self.start_app_window('Terminal')
        self.keyboard.type('''python -c "open('foo','w').write(raw_input())"''')
        self.keyboard.press_and_release('Enter')
        self.addCleanup(remove, 'foo')
        sleep(1)
        self.keyboard.type(self.input)
        self.keyboard.press_and_release('Enter')

        self.assertThat(open('foo').read(), Contains(self.input))
