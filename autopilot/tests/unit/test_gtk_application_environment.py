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

from autopilot.application.environment._gtk import GtkApplicationEnvironment


class GtkApplicationEnvironmentTests(TestCase):

    def setUp(self):
        super(GtkApplicationEnvironmentTests, self).setUp()
        self.app_environment = GtkApplicationEnvironment()

    def test_does_not_alter_app(self):
        fake_app = self.getUniqueString()
        app, args = self.app_environment.prepare_environment(fake_app, [])
        self.assertEqual(fake_app, app)

    @patch("autopilot.application.environment._gtk.os")
    def test_modules_patched(self, patched_os):
        patched_os.getenv.return_value = ""
        fake_app = self.getUniqueString()
        app, args = self.app_environment.prepare_environment(fake_app, [])

        patched_os.putenv.assert_called_once_with('GTK_MODULES', ':autopilot')

    @patch("autopilot.application.environment._gtk.os")
    def test_modules_not_patched_twice(self, patched_os):
        patched_os.getenv.return_value = "autopilot"
        fake_app = self.getUniqueString()
        app, args = self.app_environment.prepare_environment(fake_app, [])

        self.assertFalse(patched_os.putenv.called)
