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
from tempfile import mktemp
from testtools.matchers import Equals

from autopilot.testcase import AutopilotTestCase
from autopilot.introspection.dbus import CustomEmulatorBase


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

    def test_can_provide_custom_emulators(self):
        """Must be able to provide custom emulator classes for classes in the
        introspection tree.

        """

        class EmulatorBase(CustomEmulatorBase):
            pass

        class MouseTestWidget(EmulatorBase):
            pass

        app = self.start_mock_app(EmulatorBase)
        test_widget = app.select_single('MouseTestWidget')

        self.assertThat(type(test_widget), Equals(MouseTestWidget))

