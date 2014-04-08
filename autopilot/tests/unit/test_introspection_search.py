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


class FilterTests(TestCase):

    def test_can_provide_list_of_filters_to_FilterRunner(self):
        _s.FilterRunner([PassingFilter])

    def test_passing_empty_filter_list_raises(self):
        self.assertThat(
            lambda: _s.FilterRunner([]),
            raises(ValueError("Filter list must not be empty"))
        )

    def test_matches_returns_True_with_PassingFilter(self):
        runner = _s.FilterRunner([PassingFilter])
        dbus_connection = self.getUniqueString()

        self.assertTrue(runner.matches(dbus_connection, {}))

    def test_matches_returns_False_with_FailingFilter(self):
        runner = _s.FilterRunner([FailingFilter])
        dbus_connection = self.getUniqueString()

        self.assertFalse(runner.matches(dbus_connection, {}))

    def test_fails_when_first_filter_fails(self):
        runner = _s.FilterRunner([FailingFilter, PassingFilter])
        dbus_connection = self.getUniqueString()

        self.assertFalse(runner.matches(dbus_connection, {}))

    def test_fails_when_second_filter_fails(self):
        runner = _s.FilterRunner([PassingFilter, FailingFilter])
        dbus_connection = self.getUniqueString()

        self.assertFalse(runner.matches(dbus_connection, {}))

    def test_passes_when_two_filters_pass(self):
        runner = _s.FilterRunner([PassingFilter, PassingFilter])
        dbus_connection = self.getUniqueString()

        self.assertTrue(runner.matches(dbus_connection, {}))

    def test_fails_when_two_filters_fail(self):
        runner = _s.FilterRunner([FailingFilter, FailingFilter])
        dbus_connection = self.getUniqueString()

        self.assertFalse(runner.matches(dbus_connection, {}))


class FilterPrioritySorterTests(TestCase):

    def test_foo(self):
        runner_class = Mock()

        _s.FilterPrioritySorter(
            [LowPriorityFilter, HighPriorityFilter],
            runner_class
        )

        runner_class.assert_called_once_with(
            [HighPriorityFilter, LowPriorityFilter]
        )

    def test_FilterPrioritySorter_returns_runner_instance(self):
        runner_class = Mock()
        runner = _s.FilterPrioritySorter(
            [LowPriorityFilter, HighPriorityFilter],
            runner_class
        )

        self.assertThat(runner, Equals(runner_class.return_value))


class FilterListGeneratorTests(TestCase):

    def test_FilterListGenerator_raises_with_unknown_search_parameter(self):
        search_parameters = dict(unexpected_key=True)

        self.assertThat(
            lambda: _s.FilterListGenerator(search_parameters, {}),
            raises(
                KeyError(
                    "Search parameter unexpected_key doesn't have a "
                    "corresponding filter in %r" % {}
                )
            )
        )

    def test_FilterListGenerator_returns_filter(self):
        search_parameters = dict(high=True)
        filter_parameter_requirements = dict(
            high=HighPriorityFilter,
        )
        filter_list = _s.FilterListGenerator(
            search_parameters,
            filter_parameter_requirements
        )

        self.assertThat(filter_list, Equals([HighPriorityFilter]))

    def test_FilterListGenerator_returns_only_required_filters(self):
        search_parameters = dict(high=True, passing=True)
        filter_parameter_requirements = dict(
            high=HighPriorityFilter,
            low=LowPriorityFilter,
            passing=PassingFilter,
        )
        filter_list = _s.FilterListGenerator(
            search_parameters,
            filter_parameter_requirements
        )

        self.assertThat(filter_list, Contains(HighPriorityFilter))
        self.assertThat(filter_list, Contains(PassingFilter))

    def test_FilterListGenerator_doesnt_modify_search_parameters(self):
        search_parameters = dict(high=True)
        filter_parameter_requirements = dict(high=HighPriorityFilter)

        _s.FilterListGenerator(
            search_parameters,
            filter_parameter_requirements
        )

        self.assertThat(search_parameters.get('high', None), Not(Equals(None)))
