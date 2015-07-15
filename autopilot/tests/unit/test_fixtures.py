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


from testtools import TestCase
from testtools.matchers import (
    Not,
    Raises,
)
from mock import patch
import autopilot._fixtures as ap_fixtures


class FixtureWithDirectAddDetailTests(TestCase):

    def test_sets_caseAddDetail_method(self):
        fixture = ap_fixtures.FixtureWithDirectAddDetail(self.addDetail)
        self.assertEqual(fixture.caseAddDetail, self.addDetail)

    def test_can_construct_without_arguments(self):
        fixture = ap_fixtures.FixtureWithDirectAddDetail()
        self.assertEqual(fixture.caseAddDetail, fixture.addDetail)


class GSettingsAccessTests(TestCase):

    def test_incorrect_schema_doesnt_raise_exception(self):
        self.assertThat(
            lambda: ap_fixtures.get_gsettings_value('foo', 'bar'),
            Not(Raises())
        )

    def test_get_value_returns_expected_value(self):
        with patch.object(ap_fixtures.subprocess, 'check_output') as check_out:
            check_out.return_value = 'buzz'
            self.assertEqual(
                ap_fixtures.get_gsettings_value('foo', 'bar'),
                'buzz'
            )

    def test_get_value_strips_newline(self):
        with patch.object(ap_fixtures.subprocess, 'check_output') as check_out:
            check_out.return_value = 'buzz\n'
            self.assertEqual(
                ap_fixtures.get_gsettings_value('foo', 'bar'),
                'buzz'
            )

class OSKAlwaysEnabledTests(TestCase):

    def test_sets_stayhidden_to_false(self):
        with patch.object(ap_fixtures, 'set_gsettings_value') as set_gsetting:
            with ap_fixtures.OSKAlwaysEnabled():
                set_gsetting.assert_called_once_with(
                    'com.canonical.keyboard.maliit',
                    'stay-hidden',
                    'false'
                )

    def test_resets_value_to_original(self):
        with patch.object(ap_fixtures, 'set_gsettings_value') as set_gset:
            with patch.object(ap_fixtures, 'get_gsettings_value') as get_gset:
                get_gset.return_value = 'foo'
                with ap_fixtures.OSKAlwaysEnabled():
                    pass
                set_gset.assert_called_with(
                    'com.canonical.keyboard.maliit',
                    'stay-hidden',
                    'foo'
                )
