# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2013 Canonical
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

import json
import os
import subprocess
import tempfile
from tempfile import mktemp
from testtools.matchers import Equals
from textwrap import dedent

from autopilot.matchers import Eventually
from autopilot.testcase import AutopilotTestCase
from autopilot.introspection.dbus import CustomEmulatorBase


class EmulatorBase(CustomEmulatorBase):
    pass


class IntrospectionFeatureTests(AutopilotTestCase):
    """Test various features of the introspection code."""

    def start_mock_app(self, emulator_base):
        window_spec_file = mktemp(suffix='.json')
        window_spec = { "Contents": "MouseTest" }
        json.dump(
            window_spec,
            open(window_spec_file, 'w')
            )
        self.addCleanup(os.remove, window_spec_file)

        return self.launch_test_application(
            'window-mocker',
            window_spec_file,
            app_type='qt',
            emulator_base=emulator_base,
            )

    def test_can_select_custom_emulators_by_name(self):
        """Must be able to select a custom emulator type by name."""
        class MouseTestWidget(EmulatorBase):
            pass

        app = self.start_mock_app(EmulatorBase)
        test_widget = app.select_single('MouseTestWidget')

        self.assertThat(type(test_widget), Equals(MouseTestWidget))

    def test_can_select_custom_emulators_by_type(self):
        """Must be able to select a custom emulator type by type."""
        class MouseTestWidget(EmulatorBase):
            pass

        app = self.start_mock_app(EmulatorBase)
        test_widget = app.select_single(MouseTestWidget)

        self.assertThat(type(test_widget), Equals(MouseTestWidget))

    def test_can_access_custom_emulator_properties(self):
        """Must be able to access properties of a custom emulator."""
        class MouseTestWidget(EmulatorBase):
            pass

        app = self.start_mock_app(EmulatorBase)
        test_widget = app.select_single(MouseTestWidget)

        self.assertThat(test_widget.visible, Eventually(Equals(True)))


class QMLCustomEmulatorTestCase(AutopilotTestCase):
    """Test the introspection of a QML application with a custom emulator."""

    def test_can_access_custom_emulator_properties_twice(self):
        """Must be able to run more than one test with a custom emulator."""

        class InnerTestCase(AutopilotTestCase):
            class QQuickView(EmulatorBase):
                pass

            test_qml = dedent("""\
                import QtQuick 2.0

                Rectangle {
                }

                """)

            def launch_test_qml(self):
                arch = subprocess.check_output(
                    ["dpkg-architecture", "-qDEB_HOST_MULTIARCH"]).strip()
                qml_path = tempfile.mktemp(suffix='.qml')
                open(qml_path, 'w').write(self.test_qml)
                self.addCleanup(os.remove, qml_path)
                return self.launch_test_application(
                    "/usr/lib/" + arch + "/qt5/bin/qmlscene",
                    qml_path,
                    emulator_base=EmulatorBase)

            def test_custom_emulator(self):
                app = self.launch_test_qml()
                test_widget = app.select_single(InnerTestCase.QQuickView)
                self.assertThat(test_widget.visible, Eventually(Equals(True)))

        result1 = InnerTestCase('test_custom_emulator').run()
        self.assertThat(result1.wasSuccessful(), Equals(True))
        result2 = InnerTestCase('test_custom_emulator').run()
        self.assertThat(result2.wasSuccessful(), Equals(True))

