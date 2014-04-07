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

from autopilot.testcase import AutopilotTestCase
from autopilot.introspection._search import FilterDecision

from mock import Mock
from testtools.matchers import (
    Equals,
    raises,
)


class FilterDecisionSetupTests(AutopilotTestCase):
    def test_must_subclass_FilterDecison(self):
        test_filter = FilterDecision()
        self.assertThat(
            lambda: test_filter(None, None),
            raises(NotImplementedError)
        )

    def test_setting_up_actions_via_init(self):
        on_success = Mock()
        on_failure = Mock()
        on_na = Mock()

        test_filter = FilterDecision(on_success, on_failure, on_na)

        self.assertThat(test_filter._on_success, Equals(on_success))
        self.assertThat(test_filter._on_failure, Equals(on_failure))
        self.assertThat(test_filter._on_not_applicable, Equals(on_na))

    def test_add_on_success_works(self):
        on_success = Mock()
        test_filter = FilterDecision()
        test_filter.add_on_success(on_success)

        self.assertThat(test_filter._on_success, Equals(on_success))

    def test_add_on_not_applicable_works(self):
        on_not_applicable = Mock()
        test_filter = FilterDecision()
        test_filter.add_on_not_applicable(on_not_applicable)

        self.assertThat(
            test_filter._on_not_applicable,
            Equals(on_not_applicable)
        )

    def test_add_on_failure_works(self):
        on_failure = Mock()
        test_filter = FilterDecision()
        test_filter.add_on_failure(on_failure)

        self.assertThat(test_filter._on_failure, Equals(on_failure))

    def test_default_actions_success(self):
        test_filter = FilterDecision()
        self.assertThat(test_filter._on_success({}), Equals((True, {})))

    def test_default_actions_failure(self):
        test_filter = FilterDecision()
        self.assertThat(test_filter._on_failure({}), Equals((False, {})))

    def test_default_actions_not_applicable(self):
        test_filter = FilterDecision()
        self.assertThat(
            test_filter._on_not_applicable({}),
            Equals((False, {}))
        )


class FilterDecisionDecisionTests(AutopilotTestCase):
    class TestFilterDecision(FilterDecision):
        def __call__(self, dbus_address, params):
            if params.get('must_pass', False):
                return self._on_success(dbus_address, params)
            elif params.get('must_fail', False):
                return self._on_failure(dbus_address, params)
            elif params.get('not_applicable', False):
                return self._on_not_applicable(dbus_address, params)

    def test_success_returns_true_and_params(self):
        dbus_connection = None
        params = dict(must_pass=True)
        test_filter = self.TestFilterDecision()

        self.assertThat(
            test_filter(dbus_connection, params),
            Equals((True, params))
        )

    def test_failure_returns_false_and_params(self):
        dbus_connection = None
        params = dict(must_fail=True)
        test_filter = self.TestFilterDecision()

        self.assertThat(
            test_filter(dbus_connection, params),
            Equals((False, params))
        )

    def test_not_applicable_returns_false_and_params(self):
        dbus_connection = None
        params = dict(not_applicable=True)
        test_filter = self.TestFilterDecision()

        self.assertThat(
            test_filter(dbus_connection, params),
            Equals((False, params))
        )
