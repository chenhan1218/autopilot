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

from dbus import DBusException
from testtools import TestCase
from testtools.matchers import Equals, Not, raises
from mock import patch, Mock

from autopilot.introspection import (
    _connection_matches_pid,
    _get_possible_connections,
    _connection_has_path,
    _match_connection,
    _bus_pid_is_our_pid,
    _get_bus_pid,
)

class ProxyObjectTests(TestCase):

    def test_connection_has_path_succeeds_with_valid_connection_path(self):
        with patch('autopilot.introspection._check_connection_has_ap_interface'):
            result = _connection_has_path(None, None, None)
            self.assertThat(result, Equals(True))

    def test_connection_has_path_fails_with_invalid_connection_name(self):
        with patch('autopilot.introspection._check_connection_has_ap_interface', side_effect=DBusException):
            result = _connection_has_path(None, None, None)
            self.assertThat(result, Equals(False))

    def test_connection_matches_pid_matches_pid_returns_true(self):
        """_connection_matches_pid must return True if the passed pid matches
        the buses Unix pid.

        """
        matching_pid = 1
        with patch('autopilot.introspection._get_child_pids', return_value=[]):
            with patch('autopilot.introspection._get_bus_pid', return_value=matching_pid):
                result = _connection_matches_pid(None, "", matching_pid)
                self.assertThat(result, Equals(True))

    def test_connection_matches_pid_child_pid_returns_true(self):
        """_connection_matches_pid must return True if the passed pid doesn't
        match but a child pid of the pids' process does.

        """
        parent_pid = 1
        child_pid = 2

        with patch('autopilot.introspection._get_child_pids', return_value=[2]):
            with patch('autopilot.introspection._get_bus_pid', return_value=child_pid):
                result = _connection_matches_pid(None, "", parent_pid)
                self.assertThat(result, Equals(True))

    def test_connection_matches_pid_doesnt_match_with_no_children_pids(self):
        """_connection_matches_pid must return False if passed pid doesn't
        match.

        """
        non_matching_pid = 10

        with patch('autopilot.introspection._get_child_pids', return_value=[]):
            with patch('autopilot.introspection._get_bus_pid', return_value=0):
                result = _connection_matches_pid(None, "", non_matching_pid)
                self.assertThat(result, Equals(False))

    def test_connection_matches_pid_doesnt_match_with_no_matching_children_pids(self):
        """_connection_matches_pid must return False if neither passed pid or
        pids' processes children match.

        """
        non_matching_pid = 10

        with patch('autopilot.introspection._get_child_pids', return_value=[1,2,3,4]):
            with patch('autopilot.introspection._get_bus_pid', return_value=0):
                result = _connection_matches_pid(None, "", non_matching_pid)
                self.assertThat(result, Equals(False))

    def test_match_connection_succeeds_with_connection_path_no_pid(self):
        with patch('autopilot.introspection._connection_matches_pid', side_effect=Exception("Shouldn't be called")):
            with patch('autopilot.introspection._connection_has_path', return_value=True):
                result = _match_connection(None, None, None, None)
                self.assertThat(result, Equals(True))

    def test_match_connection_succeeds_with_connection_path_and_pid_match(self):
        with patch('autopilot.introspection._connection_matches_pid', return_value=True) as match_pid:
            with patch('autopilot.introspection._connection_has_path', return_value=True):
                test_pid = 1
                result = _match_connection(None, test_pid, None, None)
                match_pid.assert_called_once_with(None, None, test_pid)
                self.assertThat(result, Equals(True))

    def test_match_connection_fails_path_matches_but_no_pid_match(self):
        test_pid = 0

        with patch('autopilot.introspection._connection_matches_pid', return_value=False) as match_pid:
            with patch('autopilot.introspection._connection_has_path', return_value=True):
                result = _match_connection(None, test_pid, None, None)
                match_pid.assert_called_once_with(None, None, test_pid)

                self.assertThat(result, Equals(False))

    def test_match_connection_fails_no_path_match_but_pid_match(self):
        test_pid = 0

        with patch('autopilot.introspection._connection_matches_pid', return_value=True) as match_pid:
            with patch('autopilot.introspection._connection_has_path', return_value=False):
                result = _match_connection(None, test_pid, None, None)
                match_pid.assert_called_once_with(None, None, test_pid)

                self.assertThat(result, Equals(False))


    def test_match_connection_fails_bus_pid_is_our_pid(self):
        test_pid = 0
        with patch('autopilot.introspection._bus_pid_is_our_pid', return_value=True):
            result = _match_connection(None, test_pid, None, None)
            self.assertThat(result, Equals(False))


    def test_bus_pid_is_our_pid_returns_true_when_pids_match(self):
        script_pid = 0
        with patch('autopilot.introspection._get_bus_pid', return_value=script_pid):
            with patch('os.getpid', return_value=script_pid):
                result = _bus_pid_is_our_pid(None, None, script_pid)
                self.assertThat(result, Equals(True))


    def test_bus_pid_is_our_pid_returns_true_when_pids_dont_match(self):
        script_pid = 0
        with patch('autopilot.introspection._get_bus_pid', return_value=3):
            with patch('os.getpid', return_value=script_pid):
                result = _bus_pid_is_our_pid(None, None, script_pid)
                self.assertThat(result, Equals(False))


    def test_get_possible_connections_returns_all_with_none_arg(self):
        all_connections = ["com.test.something", ":1.234"]

        test_bus = Mock(spec_set=["list_names"])
        test_bus.list_names.return_value = all_connections

        results = _get_possible_connections(test_bus, None)

        self.assertThat(results, Equals(all_connections))

    def test_get_possible_connections_returns_matching_connection(self):
        matching_connection_name = "com.test.success"
        all_connections = ["com.test.something", matching_connection_name, ":1.234"]

        test_bus = Mock(spec_set=["list_names"])
        test_bus.list_names.return_value = all_connections

        results = _get_possible_connections(test_bus, matching_connection_name)

        self.assertThat(results, Equals([matching_connection_name]))

    def test_get_possible_connections_raises_error_with_no_match(self):
        non_matching_connection_name = "com.test.failure"

        test_bus = Mock(spec_set=["list_names"])
        test_bus.list_names.return_value = ["com.test.something", ":1.234"]

        fn = lambda: _get_possible_connections(test_bus, non_matching_connection_name)
        self.assertThat(fn, raises(RuntimeError("No connections called com.test.failure found")))
