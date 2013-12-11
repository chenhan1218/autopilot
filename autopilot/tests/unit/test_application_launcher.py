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

from testtools import TestCase
from mock import patch

from autopilot.application.launcher import ApplicationLauncher


class ApplicationLauncherTests(TestCase):

    @patch(
        'autopilot.application.launcher._traditional.NormalApplicationLauncher'
    )
    def test_create_returns_gtk_launcher(self, patched_launcher):
        app_launcher = ApplicationLauncher.create(application="fakeapp")
        self.assertEqual(patched_launcher(), app_launcher)

    @patch(
        'autopilot.application.launcher._click.ClickApplicationLauncher'
    )
    def test_create_returns_click_launcher(self, patched_launcher):
        app_launcher = ApplicationLauncher.create(
            package_id="com.autopilot.fake"
        )
        self.assertEqual(patched_launcher(), app_launcher)
