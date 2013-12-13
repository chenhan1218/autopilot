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

from mock import patch
from testtools import TestCase

from autopilot.application._environment import (
    UpstartApplicationEnvironment,
)


class UpstartApplicationEnvironmentTests(TestCase):
    def setUp(self):
        super(UpstartApplicationEnvironmentTests, self).setUp()
        self.app_environment = self.useFixture(UpstartApplicationEnvironment())

    @patch('autopilot.application._environment._call_upstart_with_args')
    def test_does_not_alter_app(self, patched_call_upstart):
        fake_app = self.getUniqueString()
        app, args = self.app_environment.prepare_environment(fake_app, [])
        self.assertEqual(fake_app, app)

    @patch('autopilot.application._environment._call_upstart_with_args')
    def test_does_not_alter_arguments(self, patched_call_upstart):
        fake_app = self.getUniqueString()
        app, args = self.app_environment.prepare_environment(fake_app, [])
        self.assertEqual([], args)

    @patch('autopilot.application._environment._call_upstart_with_args')
    def test_patches_env(self, patched_call_upstart):
        fake_app = self.getUniqueString()
        import ipdb; ipdb.set_trace()

        app, args = self.app_environment.prepare_environment(fake_app, [])

        patched_call_upstart.called_with_args('QT_LOAD_TESTABILITY', 1)

    @patch('autopilot.application._environment._call_upstart_with_args')
    def test_unpatches_env(self, patched_call_upstart):
        fake_app = self.getUniqueString()

        app, args = self.app_environment.prepare_environment(fake_app, [])

        self.app_environment.cleanUp()
        patched_call_upstart.called_with_args('QT_LOAD_TESTABILITY')
