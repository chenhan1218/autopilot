# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2012 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.

import os
from tempfile import mktemp
from testtools.matchers import IsInstance
from textwrap import dedent
from unittest import SkipTest

from autopilot.testcase import AutopilotTestCase
from autopilot.input import Keyboard

simple_qml = dedent("""\
    import QtQuick 2.0

    Rectangle {
        width: 800
        height: 600

        TextEdit {
            id: text_edit1
            objectName: test_text
            anchors.fill: parent
            text: qsTr("Text Edit")
            font.pixelSize: 12
        }
    }
    """)


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

    def start_qml_app(self, qml_string):
        qml_file = mktemp(suffix='.qml')
        with open(qml_file, 'w') as f:
            f.write(qml_string)
            self.addCleanup(os.remove, qml_file)
        return self.launch_test_application('/usr/bin/qmlscene', qml_file)

    def test_some_text(self):
        app_proxy = self.start_qml_app(simple_qml)
