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

from autopilot.exceptions import ProcessSearchError
from autopilot.introspection import _proxy_object as _po
import autopilot.introspection.utilities as _u

from mock import Mock, patch
from six import u
from testtools import TestCase
from testtools.matchers import (
    Contains,
    Equals,
    HasLength,
    MatchesAll,
    Not,
    raises,
)


def ListContainsAll(value_list):
    """Returns a MatchesAll matcher for comparing a list."""
    return MatchesAll(*map(Contains, value_list))


class FindMatchingConnectionsTests(TestCase):

    """Testing the behaviour of _find_matching_connections and helper methods
    used within.

    """

    def test_get_buses_unchecked_connection_names_returns_all_buses_initially(self):
        mock_connection_list = ['conn1', 'conn2', 'conn3']
        dbus_bus = Mock()
        dbus_bus.list_name = Mock(return_value=mock_connection_list)

        self.assertThat(
            _po._get_buses_unchecked_connection_names(dbus_bus),
            ListContainsAll(mock_connection_list)
        )

    def test_get_buses_unchecked_connection_names_returns_only_unseen_connections(self):
        mock_connection_list = ['conn1', 'conn2', 'conn3']
        dbus_bus = Mock()
        dbus_bus.list_name = Mock(return_value=mock_connection_list)

        self.assertThat(
            _po._get_buses_unchecked_connection_names(dbus_bus, ['conn3']),
            ListContainsAll(['conn1', 'conn2'])
        )

    def test_get_buses_unchecked_connection_names_returns_empty_list_when_all_seen(self):
        mock_connection_list = ['conn1', 'conn2', 'conn3']
        dbus_bus = Mock()
        dbus_bus.list_name = Mock(return_value=mock_connection_list)

        self.assertThat(
            _po._get_buses_unchecked_connection_names(
                dbus_bus,
                mock_connection_list
            ),
            Equals([])
        )



    # @patch.object(_po, '_get_dbus_bus_from_string', return_value="bus")
    # def test_


class ProcessAndPidErrorCheckingTests(TestCase):

    def test_raises_ProcessSearchError_when_process_is_not_running(self):
        with patch.object(_u, '_pid_is_running') as pir:
            pir.return_value = False

            self.assertThat(
                lambda: _po._check_process_and_pid_details(pid=123),
                raises(ProcessSearchError("PID 123 could not be found"))
            )

    def test_raises_RuntimeError_when_pid_and_process_disagree(self):
        mock_process = Mock()
        mock_process.pid = 1

        self.assertThat(
            lambda: _po._check_process_and_pid_details(mock_process, 2),
            raises(RuntimeError("Supplied PID and process.pid do not match."))
        )

    def test_returns_pid_when_specified(self):
        expected = self.getUniqueInteger()
        with patch.object(_u, '_pid_is_running') as pir:
            pir.return_value = True

            observed = _po._check_process_and_pid_details(pid=expected)

        self.assertEqual(expected, observed)

    def test_returns_process_pid_attr_when_specified(self):
        fake_process = Mock()
        fake_process.pid = self.getUniqueInteger()

        with patch.object(_u, '_pid_is_running') as pir:
            pir.return_value = True
            observed = _po._check_process_and_pid_details(fake_process)

        self.assertEqual(fake_process.pid, observed)

    def test_returns_None_when_neither_parameters_present(self):
        self.assertEqual(
            None,
            _po._check_process_and_pid_details()
        )

    def test_returns_pid_when_both_specified(self):
        fake_process = Mock()
        fake_process.pid = self.getUniqueInteger()
        with patch.object(_u, '_pid_is_running') as pir:
            pir.return_value = True
            observed = _po._check_process_and_pid_details(
                fake_process,
                fake_process.pid
            )
        self.assertEqual(fake_process.pid, observed)


class ProcessSearchErrorStringRepTests(TestCase):

    """Various tests for the _get_search_criteria_string_representation
    function.

    """

    def test_get_string_rep_defaults_to_empty_string(self):
        observed = _po._get_search_criteria_string_representation()
        self.assertEqual("", observed)

    def test_pid(self):
        self.assertEqual(
            u('pid = 123'),
            _po._get_search_criteria_string_representation(pid=123)
        )

    def test_dbus_bus(self):
        self.assertEqual(
            u("dbus bus = 'foo'"),
            _po._get_search_criteria_string_representation(dbus_bus='foo')
        )

    def test_connection_name(self):
        self.assertEqual(
            u("connection name = 'foo'"),
            _po._get_search_criteria_string_representation(connection_name='foo')
        )

    def test_object_path(self):
        self.assertEqual(
            u("object path = 'foo'"),
            _po._get_search_criteria_string_representation(object_path='foo')
        )

    def test_application_name(self):
        self.assertEqual(
            u("application name = 'foo'"),
            _po._get_search_criteria_string_representation(application_name='foo')
        )

    def test_process_object(self):
        class FakeProcess(object):

            def __repr__(self):
                return 'foo'
        process = FakeProcess()
        self.assertEqual(
            u("process object = 'foo'"),
            _po._get_search_criteria_string_representation(process=process)
        )

    def test_all_parameters_combined(self):
        class FakeProcess(object):

            def __repr__(self):
                return 'foo'
        process = FakeProcess()
        observed = _po._get_search_criteria_string_representation(
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
