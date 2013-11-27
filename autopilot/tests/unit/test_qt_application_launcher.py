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

from autopilot.introspection.qt import QtApplicationLauncher


class QtApplicationLauncherTests(TestCase):

    def setUp(self):
        super(QtApplicationLauncherTests, self).setUp()
        self.app_launcher = QtApplicationLauncher()

    def test_does_no_alter_app(self):
        fake_app = self.getUniqueString()
        app, args = self.app_launcher.prepare_environment(fake_app, [])
        self.assertEqual(fake_app, app)

    def test_inserts_testability_with_no_args(self):
        app, args = self.app_launcher.prepare_environment('some_app', [])
        self.assertEqual(['-testability'], args)

    def test_inserts_testability_before_normal_argument(self):
        app, args = self.app_launcher.prepare_environment('app', ['-l'])
        self.assertEqual(['-testability', '-l'], args)

    def test_inserts_testability_after_qt_version_arg(self):
        app, args = self.app_launcher.prepare_environment('app', ['-qt=qt5'])
        self.assertEqual(['-qt=qt5', '-testability'], args)

    def test_does_not_insert_testability_if_already_present(self):
        app, args = self.app_launcher.prepare_environment('app', ['-testability'])
        self.assertEqual(['-testability'], args)
