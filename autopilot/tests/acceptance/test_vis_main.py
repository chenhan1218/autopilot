# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2014 Canonical
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

"""Acceptance tests for the autopilot vis tool."""

import sys

from testtools.matchers import Equals

from autopilot.testcase import AutopilotTestCase
from autopilot.introspection.dbus import CustomEmulatorBase
from autopilot.application import NormalApplicationLauncher
from autopilot.matchers import Eventually


class VisToolEmulatorBase(CustomEmulatorBase):
    pass


class VisToolLauncher(NormalApplicationLauncher):

    """Override code that prepares application environment.

    The vis tool does not accept the '-testability' argument as the first
    argument, so we override _setup_environment to put the argument in the
    correct place.

    """

    def _setup_environment(self, app_path, *arguments):
        return app_path, arguments + ('-testability',)


class VisAcceptanceTests(AutopilotTestCase):

    def launch_windowmocker(self):
        return self.launch_test_application("window-mocker", app_type="qt")

    def launch_vis(self):
        """Launch both vis and windowmocker.

        Returns proxy objects for both windowmocker and vis.
        """
        launcher = self.useFixture(
            VisToolLauncher(
                self.addDetail,
                app_type="qt",
                emulator_base=VisToolEmulatorBase
            )
        )
        vis_proxy = self._launch_test_application(
            launcher,
            sys.executable,
            "-m"
            "autopilot.run",
            "vis",
        )
        return vis_proxy

    def test_can_select_windowmocker(self):
        wm = self.launch_windowmocker()
        vis = self.launch_vis()
        connection_list = vis.select_single('ConnectionList')
        connection_list.slots.trySetSelectedItem(wm.applicationName)
        self.assertThat(
            connection_list.currentText,
            Eventually(Equals(wm.applicationName))
        )
