# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2012 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.

from testtools.matchers import IsInstance

from autopilot.testcase import AutopilotTestCase
from autopilot.input import Keyboard

class InputStackKeyboardTests(AutopilotTestCase):

    scenarios = [
        ('X11', dict(backend='X11')),
        ('UInput', dict(backend='UInput')),
        ]

    def test_can_create_backend(self):
        keyboard = Keyboard.create(self.backend)
        self.assertThat(keyboard, IsInstance(Keyboard))
