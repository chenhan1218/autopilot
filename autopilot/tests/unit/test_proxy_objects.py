# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2012-2013 Canonical
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

from dbus import DBusException, SessionBus
from testtools import TestCase
from testtools.matchers import Equals
from mock import patch, Mock

from autopilot.introspection import (
    _connection_matches_pid,
    _get_possible_connections,
    _connection_has_path,
    _match_connection,
    _bus_pid_is_our_pid,
)


class ProxyObjectTests(TestCase):
    fake_bus = "fake_bus"
    fake_connection_name = "fake_connection_name"
    fake_path = "fake_path"
    fake_pid = 123

    @patch('autopilot.introspection._check_connection_has_ap_interface')
    def test_connection_has_path_succeeds_with_valid_connection_path(
            self, patched_fn):
        result = _connection_has_path(
            self.fake_bus, self.fake_connection_name, self.fake_path)

        patched_fn.assert_called_once_with(
            self.fake_bus, self.fake_connection_name, self.fake_path)
        self.assertThat(result, Equals(True))

    @patch('autopilot.introspection._check_connection_has_ap_interface',
           side_effect=DBusException)
    def test_connection_has_path_fails_with_invalid_connection_name(
            self, patched_fn):
        result = _connection_has_path(
            self.fake_bus, self.fake_connection_name, self.fake_path)

        patched_fn.assert_called_once_with(
            self.fake_bus, self.fake_connection_name, self.fake_path)
        self.assertThat(result, Equals(False))

    @patch('autopilot.introspection._get_child_pids', return_value=[])
    def test_connection_matches_pid_matches_pid_returns_true(
            self, child_pid_fn):
        """_connection_matches_pid must return True if the passed pid matches
        the buses Unix pid.

        """
        matching_pid = 1
        with patch('autopilot.introspection._get_bus_connections_pid',
                   return_value=matching_pid) as bus_pid_fn:
            result = _connection_matches_pid(
                self.fake_bus, self.fake_connection_name, matching_pid)

            child_pid_fn.assert_called_with(matching_pid)
            bus_pid_fn.assert_called_with(
                self.fake_bus, self.fake_connection_name)
            self.assertThat(result, Equals(True))

    @patch('autopilot.introspection._get_child_pids')
    @patch('autopilot.introspection._get_bus_connections_pid')
    def test_connection_matches_pid_child_pid_returns_true(
            self, bus_connection_pid_fn, child_pid_fn):
        """_connection_matches_pid must return True if the passed pid doesn't
        match but a child pid of the pids' process does.

        """
        parent_pid = 1
        child_pid = 2

        child_pid_fn.return_value = [child_pid]
        bus_connection_pid_fn.return_value = child_pid

        result = _connection_matches_pid(
            self.fake_bus, self.fake_connection_name, parent_pid)

        child_pid_fn.assert_called_with(parent_pid)
        bus_connection_pid_fn.assert_called_with(
            self.fake_bus, self.fake_connection_name)
        self.assertThat(result, Equals(True))

    @patch('autopilot.introspection._get_child_pids')
    @patch('autopilot.introspection._get_bus_connections_pid')
    def test_connection_matches_pid_doesnt_match_with_no_children_pids(
            self, bus_connection_pid_fn, child_pid_fn):
        """_connection_matches_pid must return False if passed pid doesn't
        match.

        """
        non_matching_pid = 10

        child_pid_fn.return_value = []
        bus_connection_pid_fn.return_value = 0

        result = _connection_matches_pid(
            self.fake_bus, self.fake_connection_name, non_matching_pid)

        child_pid_fn.assert_called_with(non_matching_pid)
        bus_connection_pid_fn.assert_called_with(
            self.fake_bus, self.fake_connection_name)
        self.assertThat(result, Equals(False))

    @patch('autopilot.introspection._get_child_pids')
    @patch('autopilot.introspection._get_bus_connections_pid')
    def test_connection_matches_pid_with_no_matching_children_pids(
            self, bus_connection_pid_fn, child_pid_fn):
        """_connection_matches_pid must return False if neither passed pid or
        pids' processes children match.

        """
        non_matching_pid = 10

        child_pid_fn.return_value = [1, 2, 3, 4]
        bus_connection_pid_fn.return_value = 0

        result = _connection_matches_pid(
            self.fake_bus, self.fake_connection_name, non_matching_pid)

        child_pid_fn.assert_called_with(non_matching_pid)
        bus_connection_pid_fn.assert_called_with(
            self.fake_bus, self.fake_connection_name)
        self.assertThat(result, Equals(False))

    @patch('autopilot.introspection._connection_matches_pid')
    @patch('autopilot.introspection._connection_has_path')
    def test_match_connection_succeeds_with_connection_path_no_pid(
            self, conn_has_path_fn, conn_matches_pid_fn):
        conn_has_path_fn.return_value = True
        conn_matches_pid_fn.side_effect = Exception("Shouldn't be called")

        result = _match_connection(
            self.fake_bus, None, self.fake_path, self.fake_connection_name)

        conn_has_path_fn.assert_called_with(
            self.fake_bus, self.fake_connection_name, self.fake_path)
        self.assertThat(conn_matches_pid_fn.called, Equals(False))
        self.assertThat(result, Equals(True))

    @patch('autopilot.introspection._connection_matches_pid')
    @patch('autopilot.introspection._connection_has_path')
    def test_match_connection_succeeds_with_connection_path_and_pid_match(
            self, conn_has_path_fn, conn_matches_pid_fn):
        test_pid = 1
        conn_matches_pid_fn.return_value = True
        conn_has_path_fn.return_value = True

        result = _match_connection(
            self.fake_bus, test_pid, self.fake_path, self.fake_connection_name)

        conn_matches_pid_fn.assert_called_once_with(
            self.fake_bus, self.fake_connection_name, test_pid)
        self.assertThat(result, Equals(True))

    @patch('autopilot.introspection._connection_matches_pid')
    @patch('autopilot.introspection._connection_has_path')
    def test_match_connection_fails_path_matches_but_no_pid_match(
            self, conn_has_path_fn, conn_matches_pid_fn):
        test_pid = 0

        conn_has_path_fn.return_value = True
        conn_matches_pid_fn.return_value = False

        result = _match_connection(
            self.fake_bus, test_pid, self.fake_path, self.fake_connection_name)

        conn_matches_pid_fn.assert_called_once_with(
            self.fake_bus, self.fake_connection_name, test_pid)
        self.assertThat(result, Equals(False))

    @patch('autopilot.introspection._connection_matches_pid')
    @patch('autopilot.introspection._connection_has_path')
    def test_match_connection_fails_no_path_match_but_pid_match(
            self, conn_has_path_fn, conn_matches_pid_fn):
        test_pid = 0

        conn_has_path_fn.return_value = False
        conn_matches_pid_fn.return_value = True

        result = _match_connection(
            self.fake_bus, test_pid, self.fake_path, self.fake_connection_name)
        conn_matches_pid_fn.assert_called_once_with(
            self.fake_bus, self.fake_connection_name, test_pid)

        conn_matches_pid_fn.assert_called_once_with(
            self.fake_bus, self.fake_connection_name, test_pid)
        self.assertThat(result, Equals(False))

    @patch('autopilot.introspection._connection_matches_pid')
    @patch('autopilot.introspection._bus_pid_is_our_pid')
    def test_connection_matches_pid_ignores_dbus_daemon(
            self, bus_pid_is_our_pid, conn_matches_pid_fn):
        _connection_matches_pid(SessionBus(), 'org.freedesktop.DBus', 123)

        self.assertThat(bus_pid_is_our_pid.called, Equals(False))
        self.assertThat(conn_matches_pid_fn.called, Equals(False))

    @patch('autopilot.introspection._bus_pid_is_our_pid')
    def test_match_connection_fails_bus_pid_is_our_pid(self, bus_pid_fn):
        test_pid = 0
        bus_pid_fn.return_value = True

        result = _match_connection(
            self.fake_bus, test_pid, self.fake_path, self.fake_connection_name)

        bus_pid_fn.assert_called_once_with(
            self.fake_bus, self.fake_connection_name, test_pid)
        self.assertThat(result, Equals(False))

    @patch('autopilot.introspection._get_bus_connections_pid')
    @patch('os.getpid')
    def test_bus_pid_is_our_pid_returns_true_when_pids_match(
            self, getpid_fn, get_bus_conn_pid_fn):
        script_pid = 0

        getpid_fn.return_value = script_pid
        get_bus_conn_pid_fn.return_value = script_pid

        result = _bus_pid_is_our_pid(
            self.fake_bus, self.fake_connection_name, script_pid)

        get_bus_conn_pid_fn.assert_called_with(
            self.fake_bus, self.fake_connection_name)
        self.assertThat(result, Equals(True))

    @patch('autopilot.introspection._get_bus_connections_pid')
    @patch('os.getpid')
    def test_bus_pid_is_our_pid_returns_false_when_pids_dont_match(
            self, getpid_fn, get_bus_conn_pid_fn):
        script_pid = 0

        getpid_fn.return_value = script_pid
        get_bus_conn_pid_fn.return_value = 3

        result = _bus_pid_is_our_pid(
            self.fake_bus, self.fake_connection_name, script_pid)

        get_bus_conn_pid_fn.assert_called_with(
            self.fake_bus, self.fake_connection_name)
        self.assertThat(result, Equals(False))

    def test_get_possible_connections_returns_all_with_none_arg(self):
        all_connections = ["com.test.something", ":1.234"]

        test_bus = Mock(spec_set=["list_names"])
        test_bus.list_names.return_value = all_connections

        results = _get_possible_connections(test_bus, None)

        self.assertThat(results, Equals(all_connections))

    def test_get_possible_connections_returns_matching_connection(self):
        matching_connection_name = "com.test.success"
        all_connections = [
            "com.test.something", matching_connection_name, ":1.234"]

        test_bus = Mock(spec_set=["list_names"])
        test_bus.list_names.return_value = all_connections

        results = _get_possible_connections(test_bus, matching_connection_name)

        self.assertThat(results, Equals([matching_connection_name]))

    def test_get_possible_connections_raises_error_with_no_match(self):
        non_matching_connection_name = "com.test.failure"

        test_bus = Mock(spec_set=["list_names"])
        test_bus.list_names.return_value = ["com.test.something", ":1.234"]

        results = _get_possible_connections(
            test_bus, non_matching_connection_name)
        self.assertThat(results, Equals([]))
