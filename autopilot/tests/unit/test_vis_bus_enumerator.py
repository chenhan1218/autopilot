# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2013 Canonical
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


from mock import patch, Mock
from testtools import TestCase
from textwrap import dedent

from autopilot.vis.bus_enumerator._functional import _start_trawl


class BusEnumeratorTrawlTests(TestCase):

    _example_connection_name = "com.autopilot.test"

    def _make_mock_dbus(self, xml_str=""):
        def _mock_introspect(dbus_interface, reply_handler, error_handler):
            reply_handler(xml_str)
        mock_obj = Mock()
        mock_obj.Introspect = _mock_introspect

        mock_bus = Mock()
        mock_bus.list_names.return_value = [self._example_connection_name]
        mock_bus.get_object.return_value = mock_obj

        return mock_bus

    def test_invalid_xml_doesnt_raise_exception(self):
        mock_bus = self._make_mock_dbus("<invalid xml>")
        _start_trawl(mock_bus, self._example_connection_name, Mock())

    @patch('autopilot.vis.bus_enumerator._functional.logger')
    def test_invalid_xml_logs_details(self, logger_meth):
        mock_bus = self._make_mock_dbus("<invalid xml>")
        _start_trawl(mock_bus, self._example_connection_name, Mock())

        logger_meth.warning.assert_called_once_with(
            'Unable to parse XML response for com.autopilot.test (/)'
        )

    def test_on_success_event_called(self):
        mock_bus = self._make_mock_dbus(dedent(
            '<node>'
            '<interface name="org.autopilot.DBus.example"></interface>'
            '</node>'
        ))

        on_interface_found = Mock()
        _start_trawl(
            mock_bus,
            self._example_connection_name,
            on_interface_found
        )

        on_interface_found.assert_called_with(
            self._example_connection_name,
            '/',
            'org.autopilot.DBus.example'
        )

    def test_nodes_are_recursively_searched(self):
        mock_bus = self._make_mock_dbus(dedent(
            '<node>'
            '<node name="org">'
            '<interface name="org.autopilot.DBus.example"></interface>'
            '</node>'
            '</node>'
        ))

        on_interface_found = Mock()
        _start_trawl(
            mock_bus,
            self._example_connection_name,
            on_interface_found
        )

        on_interface_found.assert_called_with(
            self._example_connection_name,
            '/',
            'org.autopilot.DBus.example'
        )
