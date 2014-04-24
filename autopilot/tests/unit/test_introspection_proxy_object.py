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

from autopilot.introspection import _proxy_object as _po

from mock import Mock
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
