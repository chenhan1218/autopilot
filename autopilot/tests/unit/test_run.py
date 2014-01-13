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

from argparse import Namespace
from mock import Mock, patch
from testtools import TestCase

from autopilot import run


class RunUtilityFunctionTests(TestCase):

    @patch('autopilot.run.autopilot.globals.set_debug_profile_fixture')
    def test_sets_when_correct_profile_found(self, patched_set_fixture):
        mock_profile = Mock()
        mock_profile.name = "verbose"
        parsed_args = Namespace(debug_profile="verbose")

        with patch.object(
                run, 'get_all_debug_profiles', lambda: {mock_profile}):

            run._configure_debug_profile(parsed_args)
            patched_set_fixture.assert_called_once_with(mock_profile)

    @patch('autopilot.run.autopilot.globals.set_debug_profile_fixture')
    def test_does_nothing_when_no_profile_found(self, patched_set_fixture):
        mock_profile = Mock()
        mock_profile.name = "verbose"
        parsed_args = Namespace(debug_profile="normal")

        with patch.object(
                run, 'get_all_debug_profiles', lambda: {mock_profile}):

            run._configure_debug_profile(parsed_args)
        self.assertFalse(patched_set_fixture.called)
