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

from autopilot.vis.bus_enumerator._functional import (
    DBusInspector,
    XmlProcessor,
)


class BusEnumeratorDBusInspectorTest(TestCase):

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

    def test_dbus_inspector_calls_handler(self):
        xml_str = dedent(
            '<node>'
            '<interface name="org.autopilot.DBus.example"></interface>'
            '</node>'
        )
        mock_bus = self._make_mock_dbus(xml_str)
        xml_processor = Mock()
        dbus_inspector = DBusInspector(mock_bus)
        dbus_inspector.set_xml_processor(xml_processor)
        dbus_inspector(self._example_connection_name)

        xml_processor.assert_called_with(
            self._example_connection_name,
            "/",
            xml_str
        )


class BusEnumeratorXmlProcessorTest(TestCase):

    _example_connection_name = "com.autopilot.test"

    def test_invalid_xml_doesnt_raise_exception(self):
        xml = "<invalid xml>"
        xml_processor = XmlProcessor()

        xml_processor(self._example_connection_name, "/", xml)

    @patch('autopilot.vis.bus_enumerator._functional.logger')
    def test_invalid_xml_logs_details(self, logger_meth):
        xml = "<invalid xml>"
        xml_processor = XmlProcessor()

        xml_processor(self._example_connection_name, "/", xml)

        logger_meth.warning.assert_called_once_with(
            'Unable to parse XML response for com.autopilot.test (/)'
        )

    def test_on_success_event_called(self):
        xml = dedent(
            '<node>'
            '<interface name="org.autopilot.DBus.example"></interface>'
            '</node>'
        )

        success_callback = Mock()
        xml_processor = XmlProcessor()
        xml_processor.set_success_callback(success_callback)

        xml_processor(self._example_connection_name, "/", xml)

        success_callback.assert_called_with(
            self._example_connection_name,
            "/",
            "org.autopilot.DBus.example",
        )

    def test_nodes_are_recursively_searched(self):
        xml = dedent(
            '<node>'
            '<node name="example">'
            '<interface name="org.autopilot.DBus.example"></interface>'
            '</node>'
            '</node>'
        )
        dbus_inspector = Mock()
        xml_processor = XmlProcessor()
        xml_processor.set_dbus_inspector(dbus_inspector)

        xml_processor(self._example_connection_name, "/", xml)

        dbus_inspector.assert_called_with(
            self._example_connection_name,
            "/example"
        )
