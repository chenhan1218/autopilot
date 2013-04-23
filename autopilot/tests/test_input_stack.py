# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2012 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.

import json
import os
from tempfile import mktemp
from testtools.matchers import IsInstance, Equals
from unittest import SkipTest

from autopilot.testcase import AutopilotTestCase, multiply_scenarios
from autopilot.input import Keyboard
from autopilot.matchers import Eventually


class InputStackKeyboardBase(AutopilotTestCase):

    scenarios = [
        ('X11', dict(backend='X11')),
        ('UInput', dict(backend='UInput')),
        ]

    def setUp(self):
        super(InputStackKeyboardBase, self).setUp()
        if self.backend == 'UInput' and not os.access('/dev/uinput', os.W_OK):
            raise SkipTest("UInput backend currently requires write access to /dev/uinput")


class InputStackKeyboardCreationTests(InputStackKeyboardBase):


    def test_can_create_backend(self):
        keyboard = Keyboard.create(self.backend)
        self.assertThat(keyboard, IsInstance(Keyboard))


class InputStackKeyboardTypingTests(InputStackKeyboardBase):

    scenarios = multiply_scenarios(
        InputStackKeyboardBase.scenarios,
        [
            ('lower_alpha', dict(input='abcdefghijklmnopqrstuvwxyz')),
            ('upper_alpha', dict(input='ABCDEFGHIJKLMNOPQRSTUVWXYZ')),
            ('numeric', dict(input='0123456789')),
            ('punctuation', dict(input='`~!@#$%^&*()_-+={}[]|\\:;"\'<>,.?/'))
        ]
        )

    def start_mock_app(self):
        window_spec_file = mktemp(suffix='.json')
        window_spec = { "Contents": "TextEdit" }
        json.dump(
            window_spec,
            open(window_spec_file, 'w')
            )

        return self.launch_test_application('window-mocker', window_spec_file)

    def pick_app_launcher(self, app_path):
        # force Qt app introspection:
        from autopilot.introspection.qt import QtApplicationLauncher
        return QtApplicationLauncher()

    def test_some_text(self):
        app_proxy = self.start_mock_app()
        text_edit = app_proxy.select_single('QTextEdit')

        # make sure the text edit has keyboard focus:
        self.mouse.move_to_object(text_edit)
        self.mouse.click()

        # create keyboard and type the text.
        keyboard = Keyboard.create(self.backend)
        keyboard.type(self.input, 0.01)

        self.assertThat(text_edit.plainText, Eventually(Equals(self.input)))

