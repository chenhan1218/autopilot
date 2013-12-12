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
from testtools.matchers import Not, raises
from mock import Mock, patch
import subprocess

from autopilot.application import ApplicationLauncher
from autopilot.application._launcher import _raise_if_not_empty, _get_application_path


class ApplicationLauncherTests(TestCase):
    pass


class ApplicationLauncherInternalTests(TestCase):

    def test_raise_if_not_empty_raises_on_nonempty_dict(self):
        populated_dict = dict(testing=True)
        self.assertThat(
            lambda: _raise_if_not_empty(populated_dict),
            raises(ValueError)
        )

    def test_raise_if_not_empty_does_not_raise_on_empty(self):
        empty_dict = dict()
        self.assertThat(
            lambda: _raise_if_not_empty(empty_dict),
            Not(raises(ValueError))
        )

