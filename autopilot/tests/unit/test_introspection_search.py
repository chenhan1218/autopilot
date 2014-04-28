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

from dbus import DBusException
from mock import patch, Mock
from six import u
from testtools import TestCase
from testtools.matchers import (
    Contains,
    Equals,
    MatchesAll,
    Not,
    raises,
)

from autopilot.exceptions import ProcessSearchError
import autopilot.introspection.utilities as _u
from autopilot.introspection import _search as _s


def ListContainsAll(value_list):
    """Returns a MatchesAll matcher for comparing a list."""
    return MatchesAll(*map(Contains, value_list))


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

    def test_filter_returning_False_results_in_failure(self):
        class FalseFilter(object):
            @classmethod
            def matches(cls, dbus_connection, params):
                return False

        self.assertFalse(
            _s.matches([FalseFilter], None, None)
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


class MatchesConnectionHasPathWithAPInterfaceTests(TestCase):
    """Tests specific to the MatchesConnectionHasPid filter."""

    def test_raises_ValueError_when_missing_path_param(self):
        dbus_connection = ("bus", "name")
        self.assertThat(
            lambda: _s.MatchesConnectionHasPathWithAPInterface.matches(
                dbus_connection,
                {}
            ),
            raises(ValueError("Filter was expecting 'path' parameter"))
        )

    @patch.object(_s.dbus, "Interface")
    def test_returns_True_on_success(self, Interface):
        bus_obj = Mock()
        connection_name = "name"
        path = "path"
        dbus_connection = (bus_obj, connection_name)

        self.assertTrue(
            _s.MatchesConnectionHasPathWithAPInterface.matches(
                dbus_connection,
                dict(path=path)
            )
        )

        bus_obj.get_object.assert_called_once_with("name", path)

    @patch.object(_s.dbus, "Interface")
    def test_returns_False_on_dbus_exception(self, Interface):
        bus_obj = Mock()
        connection_name = "name"
        path = "path"
        dbus_connection = (bus_obj, connection_name)

        Interface.side_effect = DBusException()

        self.assertFalse(
            _s.MatchesConnectionHasPathWithAPInterface.matches(
                dbus_connection,
                dict(path=path)
            )
        )

        bus_obj.get_object.assert_called_once_with("name", path)


class MatchesConnectionHasPidTests(TestCase):
    """Tests specific to the MatchesConnectionHasPid filter."""

    def test_raises_when_missing_param(self):
        self.assertThat(
            lambda: _s.MatchesConnectionHasPid.matches(None, {}),
            raises(KeyError('pid'))
        )

    def test_returns_False_when_should_ignore_pid(self):
        dbus_connection = ("bus", "org.freedesktop.DBus")
        params = dict(pid=None)
        self.assertFalse(
            _s.MatchesConnectionHasPid.matches(dbus_connection, params)
        )

    @patch.object(
        _s.MatchesConnectionHasPid,
        '_should_ignore_pid',
        return_value=False
    )
    def test_returns_True_when_bus_pid_matches(self, p):
        connection_pid = self.getUniqueInteger()
        dbus_connection = ("bus", "org.freedesktop.DBus")
        params = dict(pid=connection_pid)
        with patch.object(
            _s,
            '_get_bus_connections_pid',
            return_value=connection_pid
        ):
            self.assertTrue(
                _s.MatchesConnectionHasPid.matches(dbus_connection, params)
            )

    @patch.object(
        _s.MatchesConnectionHasPid,
        '_should_ignore_pid',
        return_value=False
    )
    def test_returns_False_with_DBusException(self, p):
        connection_pid = self.getUniqueInteger()
        dbus_connection = ("bus", "org.freedesktop.DBus")
        params = dict(pid=connection_pid)
        with patch.object(
            _s,
            '_get_bus_connections_pid',
            side_effect=DBusException()
        ):
            self.assertFalse(
                _s.MatchesConnectionHasPid.matches(dbus_connection, params)
            )

    def test_should_ignore_pid_returns_True_with_connection_name(self):
        self.assertTrue(
            _s.MatchesConnectionHasPid._should_ignore_pid(
                None,
                "org.freedesktop.DBus",
                None
            )
        )

    def test_should_ignore_pid_returns_True_when_pid_is_our_pid(self):
        with patch.object(
                _s.MatchesConnectionHasPid,
                '_bus_pid_is_our_pid',
                return_value=True
        ):
            self.assertTrue(
                _s.MatchesConnectionHasPid._should_ignore_pid(None, None, None)
            )

    def test_should_ignore_pid_returns_False_when_pid_is_our_pid(self):
        with patch.object(
                _s.MatchesConnectionHasPid,
                '_bus_pid_is_our_pid',
                return_value=False
        ):
            self.assertFalse(
                _s.MatchesConnectionHasPid._should_ignore_pid(None, None, None)
            )


class MatchesConnectionHasAppNameTests(TestCase):
    """Tests specific to the MatchesConnectionHasPid filter."""

    def test_raises_when_missing_app_name_param(self):
        self.assertThat(
            lambda: _s.MatchesConnectionHasAppName.matches(None, {}),
            raises(KeyError('application_name'))
        )


class FilterHelpersTests(TestCase):

    def test_param_to_filter_includes_all(self):
        search_parameters = dict(application_name=True, pid=True, path=True)
        matchers = _s._filter_function_from_search_params(search_parameters)

        self.assertThat(
            matchers.args[0],
            ListContainsAll([
                _s.MatchesConnectionHasAppName,
                _s.MatchesConnectionHasPid,
                _s.MatchesConnectionHasPathWithAPInterface,
            ])
        )


class FindMatchingConnectionsTests(TestCase):

    """Testing the behaviour of _find_matching_connections and helper methods
    used within.

    """

    def test_unchecked_connection_names_returns_all_buses_initially(self):
        mock_connection_list = ['conn1', 'conn2', 'conn3']
        dbus_bus = Mock()
        dbus_bus.list_names = Mock(return_value=mock_connection_list)

        self.assertThat(
            _s._get_buses_unchecked_connection_names(dbus_bus),
            ListContainsAll(mock_connection_list)
        )

    def test_unchecked_connection_names_returns_only_unseen_connections(self):
        mock_connection_list = ['conn1', 'conn2', 'conn3']
        dbus_bus = Mock()
        dbus_bus.list_names = Mock(return_value=mock_connection_list)

        self.assertThat(
            _s._get_buses_unchecked_connection_names(dbus_bus, ['conn3']),
            ListContainsAll(['conn1', 'conn2'])
        )

    def test_unchecked_connection_names_returns_empty_list_when_all_seen(self):
        mock_connection_list = ['conn1', 'conn2', 'conn3']
        dbus_bus = Mock()
        dbus_bus.list_names = Mock(return_value=mock_connection_list)

        self.assertThat(
            _s._get_buses_unchecked_connection_names(
                dbus_bus,
                mock_connection_list
            ),
            Equals([])
        )


class ProcessAndPidErrorCheckingTests(TestCase):

    def test_raises_ProcessSearchError_when_process_is_not_running(self):
        with patch.object(_u, '_pid_is_running') as pir:
            pir.return_value = False

            self.assertThat(
                lambda: _s._check_process_and_pid_details(pid=123),
                raises(ProcessSearchError("PID 123 could not be found"))
            )

    def test_raises_RuntimeError_when_pid_and_process_disagree(self):
        mock_process = Mock()
        mock_process.pid = 1

        self.assertThat(
            lambda: _s._check_process_and_pid_details(mock_process, 2),
            raises(RuntimeError("Supplied PID and process.pid do not match."))
        )

    def test_returns_pid_when_specified(self):
        expected = self.getUniqueInteger()
        with patch.object(_u, '_pid_is_running') as pir:
            pir.return_value = True

            observed = _s._check_process_and_pid_details(pid=expected)

        self.assertEqual(expected, observed)

    def test_returns_process_pid_attr_when_specified(self):
        fake_process = Mock()
        fake_process.pid = self.getUniqueInteger()

        with patch.object(_u, '_pid_is_running') as pir:
            pir.return_value = True
            observed = _s._check_process_and_pid_details(fake_process)

        self.assertEqual(fake_process.pid, observed)

    def test_returns_None_when_neither_parameters_present(self):
        self.assertEqual(
            None,
            _s._check_process_and_pid_details()
        )

    def test_returns_pid_when_both_specified(self):
        fake_process = Mock()
        fake_process.pid = self.getUniqueInteger()
        with patch.object(_u, '_pid_is_running') as pir:
            pir.return_value = True
            observed = _s._check_process_and_pid_details(
                fake_process,
                fake_process.pid
            )
        self.assertEqual(fake_process.pid, observed)


class ProcessSearchErrorStringRepTests(TestCase):

    """Various tests for the _get_search_criteria_string_representation
    function.

    """

    def test_get_string_rep_defaults_to_empty_string(self):
        observed = _s._get_search_criteria_string_representation()
        self.assertEqual("", observed)

    def test_pid(self):
        self.assertEqual(
            u('pid = 123'),
            _s._get_search_criteria_string_representation(pid=123)
        )

    def test_dbus_bus(self):
        self.assertEqual(
            u("dbus bus = 'foo'"),
            _s._get_search_criteria_string_representation(dbus_bus='foo')
        )

    def test_connection_name(self):
        self.assertEqual(
            u("connection name = 'foo'"),
            _s._get_search_criteria_string_representation(
                connection_name='foo'
            )
        )

    def test_object_path(self):
        self.assertEqual(
            u("object path = 'foo'"),
            _s._get_search_criteria_string_representation(object_path='foo')
        )

    def test_application_name(self):
        self.assertEqual(
            u("application name = 'foo'"),
            _s._get_search_criteria_string_representation(
                application_name='foo'
            )
        )

    def test_process_object(self):
        class FakeProcess(object):

            def __repr__(self):
                return 'foo'
        process = FakeProcess()
        self.assertEqual(
            u("process object = 'foo'"),
            _s._get_search_criteria_string_representation(process=process)
        )

    def test_all_parameters_combined(self):
        class FakeProcess(object):

            def __repr__(self):
                return 'foo'
        process = FakeProcess()
        observed = _s._get_search_criteria_string_representation(
            pid=123,
            dbus_bus='session_bus',
            connection_name='com.Canonical.Unity',
            object_path='/com/Canonical/Autopilot',
            application_name='MyApp',
            process=process
        )
        expected = "pid = 123, dbus bus = 'session_bus', " \
            "connection name = 'com.Canonical.Unity', " \
            "object path = '/com/Canonical/Autopilot', " \
            "application name = 'MyApp', process object = 'foo'"
        self.assertEqual(expected, observed)
