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

from autopilot.introspection import _search as _s

from mock import Mock
from testtools import TestCase
from testtools.matchers import (
    Contains,
    Equals,
    Not,
    raises,
)


class PassingFilter(object):

    @classmethod
    def matches(cls, dbus_connection, params):
        return _s.FilterResult.PASS


class FailingFilter(object):

    @classmethod
    def matches(cls, dbus_connection, params):
        return _s.FilterResult.FAIL


class LowPriorityFilter(object):

    @classmethod
    def priority(cls):
        return 0


class HighPriorityFilter(object):

    @classmethod
    def priority(cls):
        return 10


class MatcherCallableTests(TestCase):

    def test_can_provide_list_of_filters(self):
        _s.matches([PassingFilter], None, None)

    def test_passing_empty_filter_list_raises(self):
        self.assertThat(
            lambda: _s.matches([], None, None),
            raises(ValueError("Filter list must not be empty"))
        )

    def test_matches_returns_True_with_PassingFilter(self):
        self.assertTrue(_s.matches([PassingFilter], None, None))

    def test_matches_returns_False_with_FailingFilter(self):
        self.assertFalse(_s.matches([FailingFilter], None, None))

    def test_fails_when_first_filter_fails(self):
        self.assertFalse(
            _s.matches([FailingFilter, PassingFilter], None, None)
        )

    def test_fails_when_second_filter_fails(self):
        self.assertFalse(
            _s.matches([PassingFilter, FailingFilter], None, None)
        )

    def test_passes_when_two_filters_pass(self):
        self.assertTrue(
            _s.matches([PassingFilter, PassingFilter], None, None)
        )

    def test_fails_when_two_filters_fail(self):
        self.assertFalse(
            _s.matches([FailingFilter, FailingFilter], None, None)
        )

    def test_runner_matches_passes_dbus_connection_to_filter(self):
        DBusConnectionFilter = Mock()
        dbus_connection = ("bus", "connection_name")

        _s.matches([DBusConnectionFilter], dbus_connection, {})

        DBusConnectionFilter.matches.assert_called_once_with(
            dbus_connection, {}
        )


class FilterFunctionGeneratorTests(TestCase):

    """Tests to ensure the correctness of the
    _filter_function_from_search_params function.

    """

    def test_uses_sorted_filter_list(self):
        test_search_parameters = dict(low=True, high=True)
        test_filter_lookup = dict(
            low=LowPriorityFilter,
            high=HighPriorityFilter,
        )

        matcher = _s._filter_function_from_search_params(
            test_search_parameters,
            test_filter_lookup
        )

        self.assertThat(
            matcher.args[0], Equals([HighPriorityFilter, LowPriorityFilter])
        )

    def test_returns_a_callable(self):
        self.assertTrue(
            callable(_s._filter_function_from_search_params({}))
        )

    def test_raises_with_unknown_search_parameter(self):
        search_parameters = dict(unexpected_key=True)
        placeholder_lookup = dict(noop_lookup=True)

        self.assertThat(
            lambda: _s._filter_function_from_search_params(
                search_parameters,
                placeholder_lookup
            ),
            raises(
                KeyError(
                    "Search parameter unexpected_key doesn't have a "
                    "corresponding filter in %r"
                    % placeholder_lookup
                )
            )
        )

    def test_returns_only_required_filters(self):
        search_parameters = dict(high=True, low=True)
        filter_lookup = dict(
            high=HighPriorityFilter,
            low=LowPriorityFilter,
            passing=PassingFilter,
        )

        matcher = _s._filter_function_from_search_params(
            search_parameters,
            filter_lookup
        )

        self.assertThat(
            matcher.args[0], Equals([HighPriorityFilter, LowPriorityFilter])
        )

    def test_creates_unique_list_of_filters(self):
        search_parameters = dict(pid=True, process=True)
        filter_lookup = dict(
            pid=HighPriorityFilter,
            process=HighPriorityFilter
        )
        matcher = _s._filter_function_from_search_params(
            search_parameters,
            filter_lookup
        )
        self.assertThat(
            matcher.args[0], Equals([HighPriorityFilter])
        )

    def test_doesnt_modify_search_parameters(self):
        search_parameters = dict(high=True)
        filter_lookup = dict(high=HighPriorityFilter)

        _s._filter_function_from_search_params(
            search_parameters,
            filter_lookup
        )

        self.assertThat(search_parameters.get('high', None), Not(Equals(None)))
