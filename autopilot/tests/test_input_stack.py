# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2012 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.

import os
from testtools.matchers import IsInstance
from unittest import SkipTest

from autopilot.testcase import AutopilotTestCase
from autopilot.input import Keyboard

class InputStackKeyboardTests(AutopilotTestCase):

    scenarios = [
        ('X11', dict(backend='X11')),
        ('UInput', dict(backend='UInput')),
        ]

    def setUp(self):
        super(InputStackKeyboardTests, self).setUp()
        if self.backend == 'UInput' and not os.access('/dev/uinput', os.W_OK):
            raise SkipTest("UInput backend currently requires write access to /dev/uinput")


    def test_can_create_backend(self):
        keyboard = Keyboard.create(self.backend)
        self.assertThat(keyboard, IsInstance(Keyboard))
