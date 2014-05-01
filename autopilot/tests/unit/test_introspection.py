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

from __future__ import absolute_import

from dbus import String
from mock import patch, Mock
from testtools import TestCase
from testtools.matchers import (
    Equals,
    IsInstance,
    raises,
)
from six import u, PY3
from contextlib import contextmanager
if PY3:
    from contextlib import ExitStack
else:
    from contextlib2 import ExitStack

from autopilot.introspection import (
    _check_process_and_pid_details,
    _get_application_name_from_dbus_address,
    _get_search_criteria_string_representation,
    _maybe_filter_connections_by_app_name,
    get_proxy_object_for_existing_process,
    ProcessSearchError,
)
from autopilot.introspection.qt import QtObjectProxyMixin
import autopilot.introspection as _i


class ProcessSearchErrorStringRepTests(TestCase):

    """Various tests for the _get_search_criteria_string_representation
    function.

    """

    def test_get_string_rep_defaults_to_empty_string(self):
        observed = _get_search_criteria_string_representation()
        self.assertEqual("", observed)

    def test_pid(self):
        self.assertEqual(
            u('pid = 123'),
            _get_search_criteria_string_representation(pid=123)
        )

    def test_dbus_bus(self):
        self.assertEqual(
            u("dbus bus = 'foo'"),
            _get_search_criteria_string_representation(dbus_bus='foo')
        )

    def test_connection_name(self):
        self.assertEqual(
            u("connection name = 'foo'"),
            _get_search_criteria_string_representation(connection_name='foo')
        )

    def test_object_path(self):
        self.assertEqual(
            u("object path = 'foo'"),
            _get_search_criteria_string_representation(object_path='foo')
        )

    def test_application_name(self):
        self.assertEqual(
            u("application name = 'foo'"),
            _get_search_criteria_string_representation(application_name='foo')
        )

    def test_process_object(self):
        class FakeProcess(object):

            def __repr__(self):
                return 'foo'
        process = FakeProcess()
        self.assertEqual(
            u("process object = 'foo'"),
            _get_search_criteria_string_representation(process=process)
        )

    def test_all_parameters_combined(self):
        class FakeProcess(object):

            def __repr__(self):
                return 'foo'
        process = FakeProcess()
        observed = _get_search_criteria_string_representation(
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


class ProcessAndPidErrorCheckingTests(TestCase):

    def test_raises_ProcessSearchError_when_process_is_not_running(self):
        with patch('autopilot.introspection._pid_is_running') as pir:
            pir.return_value = False

            self.assertThat(
                lambda: _check_process_and_pid_details(pid=123),
                raises(ProcessSearchError("PID 123 could not be found"))
            )

    def test_raises_RuntimeError_when_pid_and_process_disagree(self):
        mock_process = Mock()
        mock_process.pid = 1

        self.assertThat(
            lambda: _check_process_and_pid_details(mock_process, 2),
            raises(RuntimeError("Supplied PID and process.pid do not match."))
        )

    def test_returns_pid_when_specified(self):
        expected = self.getUniqueInteger()
        with patch('autopilot.introspection._pid_is_running') as pir:
            pir.return_value = True

            observed = _check_process_and_pid_details(pid=expected)

        self.assertEqual(expected, observed)

    def test_returns_process_pid_attr_when_specified(self):
        fake_process = Mock()
        fake_process.pid = self.getUniqueInteger()

        with patch('autopilot.introspection._pid_is_running') as pir:
            pir.return_value = True
            observed = _check_process_and_pid_details(fake_process)

        self.assertEqual(fake_process.pid, observed)

    def test_returns_None_when_neither_parameters_present(self):
        self.assertEqual(
            None,
            _check_process_and_pid_details()
        )

    def test_returns_pid_when_both_specified(self):
        fake_process = Mock()
        fake_process.pid = self.getUniqueInteger()
        with patch('autopilot.introspection._pid_is_running') as pir:
            pir.return_value = True
            observed = _check_process_and_pid_details(
                fake_process,
                fake_process.pid
            )
        self.assertEqual(fake_process.pid, observed)


class ApplicationFilteringTests(TestCase):

    def get_mock_dbus_address_with_application_name(slf, app_name):
        mock_dbus_address = Mock()
        mock_dbus_address.introspection_iface.GetState.return_value = (
            ('/' + app_name, {}),
        )
        return mock_dbus_address

    def test_can_extract_application_name(self):
        mock_connection = self.get_mock_dbus_address_with_application_name(
            'SomeAppName'
        )
        self.assertEqual(
            'SomeAppName',
            _get_application_name_from_dbus_address(mock_connection)
        )

    def test_maybe_filter_returns_addresses_when_app_name_not_specified(self):
        self.assertEqual(
            [],
            _maybe_filter_connections_by_app_name(None, [])
        )

    def test_maybe_filter_works_with_partial_match(self):
        mock_connections = [
            self.get_mock_dbus_address_with_application_name('Match'),
            self.get_mock_dbus_address_with_application_name('Mismatch'),
        ]
        expected = mock_connections[:1]
        observed = _maybe_filter_connections_by_app_name(
            'Match',
            mock_connections
        )
        self.assertEqual(expected, observed)

    def test_maybe_filter_works_with_no_match(self):
        mock_connections = [
            self.get_mock_dbus_address_with_application_name('Mismatch1'),
            self.get_mock_dbus_address_with_application_name('Mismatch2'),
        ]
        expected = []
        observed = _maybe_filter_connections_by_app_name(
            'Match',
            mock_connections
        )
        self.assertEqual(expected, observed)

    def test_maybe_filter_works_with_full_match(self):
        mock_connections = [
            self.get_mock_dbus_address_with_application_name('Match'),
            self.get_mock_dbus_address_with_application_name('Match'),
        ]
        expected = mock_connections
        observed = _maybe_filter_connections_by_app_name(
            'Match',
            mock_connections
        )
        self.assertEqual(expected, observed)


class ProxyObjectGenerationTests(TestCase):

    @contextmanager
    def mock_all_child_calls(self):
        mock_dict = {}
        with ExitStack() as all_the_mocks:
            mock_dict['check_process'] = all_the_mocks.enter_context(
                patch(
                    'autopilot.introspection._check_process_and_pid_details'
                )
            )
            mock_dict['get_addresses'] = all_the_mocks.enter_context(
                patch(
                    'autopilot.introspection.'
                    '_get_dbus_addresses_from_search_parameters'
                )
            )
            mock_dict['filter_addresses'] = all_the_mocks.enter_context(
                patch(
                    'autopilot.introspection.'
                    '_maybe_filter_connections_by_app_name'
                )
            )
            mock_dict['make_proxy_object'] = all_the_mocks.enter_context(
                patch(
                    'autopilot.introspection._make_proxy_object'
                )
            )
            yield mock_dict

    def test_makes_child_calls(self):
        """Mock out all child functions, and assert that they're called.

        This test is somewhat ugly, and should be refactored once the search
        criteria has been refactored into a separate object, rather than a
        bunch of named parameters.

        """
        with self.mock_all_child_calls() as mocks:
            fake_address_list = [Mock()]
            mocks['get_addresses'].return_value = fake_address_list
            mocks['filter_addresses'].return_value = fake_address_list

            get_proxy_object_for_existing_process()

            self.assertEqual(
                1,
                mocks['check_process'].call_count
            )
            self.assertEqual(
                1,
                mocks['get_addresses'].call_count
            )
            self.assertEqual(
                1,
                mocks['make_proxy_object'].call_count
            )

    def test_raises_ProcessSearchError(self):
        """Function must raise ProcessSearchError if no addresses are found.

        This test is somewhat ugly, and should be refactored once the search
        criteria has been refactored into a separate object, rather than a
        bunch of named parameters.

        """
        with self.mock_all_child_calls() as mocks:
            fake_address_list = [Mock()]
            mocks['check_process'].return_value = 123
            mocks['get_addresses'].return_value = fake_address_list
            mocks['filter_addresses'].return_value = []

            self.assertThat(
                lambda: get_proxy_object_for_existing_process(),
                raises(
                    ProcessSearchError(
                        "Search criteria (pid = 123, dbus bus = 'session', "
                        "object path = "
                        "'/com/canonical/Autopilot/Introspection') returned "
                        "no results"
                    )
                )
            )

    def test_raises_RuntimeError(self):
        """Function must raise RuntimeError if several addresses are found.

        This test is somewhat ugly, and should be refactored once the search
        criteria has been refactored into a separate object, rather than a
        bunch of named parameters.

        """
        with self.mock_all_child_calls() as mocks:
            fake_address_list = [Mock(), Mock()]
            mocks['get_addresses'].return_value = fake_address_list
            mocks['filter_addresses'].return_value = fake_address_list

            self.assertThat(
                lambda: get_proxy_object_for_existing_process(),
                raises(
                    RuntimeError(
                        "Search criteria (pid = 1, dbus bus = 'session', "
                        "object path = "
                        "'/com/canonical/Autopilot/Introspection') "
                        "returned multiple results"
                    )
                )
            )


class MakeProxyClassObjectTests(TestCase):

    class BaseOne(object):
        pass

    class BaseTwo(object):
        pass

    def test_merges_multiple_proxy_bases(self):
        cls = _i._make_proxy_class_object(
            "MyProxy",
            (self.BaseOne, self.BaseTwo)
        )
        self.assertThat(
            len(cls.__bases__),
            Equals(1)
        )
        self.assertThat(cls.__bases__[0].__name__, Equals("MyProxyBase"))

    def test_uses_class_name(self):
        cls = _i._make_proxy_class_object(
            "MyProxy",
            (self.BaseOne, self.BaseTwo)
        )
        self.assertThat(cls.__name__, Equals("MyProxy"))


class GetDetailsFromStateDataTests(TestCase):

    fake_state_data = (String('/some/path'), dict(foo=123))

    def test_returns_classname(self):
        class_name, _, _ = _i._get_details_from_state_data(
            self.fake_state_data
        )
        self.assertThat(class_name, Equals('path'))

    def test_returns_path(self):
        _, path, _ = _i._get_details_from_state_data(self.fake_state_data)
        self.assertThat(path, Equals(b'/some/path'))

    def test_returned_path_is_bytestring(self):
        _, path, _ = _i._get_details_from_state_data(self.fake_state_data)
        self.assertThat(path, IsInstance(type(b'')))

    def test_returns_state_dict(self):
        _, _, state = _i._get_details_from_state_data(self.fake_state_data)
        self.assertThat(state, Equals(dict(foo=123)))


class FooTests(TestCase):

    fake_data_with_ap_interface = """
        <!DOCTYPE node PUBLIC
            "-//freedesktop//DTD D-BUS Object Introspection 1.0//EN"
            "http://www.freedesktop.org/standards/dbus/1.0/introspect.dtd">
        <!-- GDBus 2.39.92 -->
        <node>
          <interface name="com.canonical.Autopilot.Introspection">
            <method name="GetState">
              <arg type="s" name="piece" direction="in">
              </arg>
              <arg type="a(sv)" name="state" direction="out">
              </arg>
            </method>
            <method name="GetVersion">
              <arg type="s" name="version" direction="out">
              </arg>
            </method>
          </interface>
        </node>
    """

    fake_data_with_ap_and_qt_interfaces = """
        <!DOCTYPE node PUBLIC
            "-//freedesktop//DTD D-BUS Object Introspection 1.0//EN"
            "http://www.freedesktop.org/standards/dbus/1.0/introspect.dtd">
        <node>
            <interface name="com.canonical.Autopilot.Introspection">
                <method name='GetState'>
                    <arg type='s' name='piece' direction='in' />
                    <arg type='a(sv)' name='state' direction='out' />
                </method>
                <method name='GetVersion'>
                    <arg type='s' name='version' direction='out' />
                </method>
            </interface>
            <interface name="com.canonical.Autopilot.Qt">
                <method name='RegisterSignalInterest'>
                    <arg type='i' name='object_id' direction='in' />
                    <arg type='s' name='signal_name' direction='in' />
                </method>
                <method name='GetSignalEmissions'>
                    <arg type='i' name='object_id' direction='in' />
                    <arg type='s' name='signal_name' direction='in' />
                    <arg type='i' name='sigs' direction='out' />
                </method>
                <method name='ListSignals'>
                    <arg type='i' name='object_id' direction='in' />
                    <arg type='as' name='signals' direction='out' />
                </method>
                <method name='ListMethods'>
                    <arg type='i' name='object_id' direction='in' />
                    <arg type='as' name='methods' direction='out' />
                </method>
                <method name='InvokeMethod'>
                    <arg type='i' name='object_id' direction='in' />
                    <arg type='s' name='method_name' direction='in' />
                    <arg type='av' name='arguments' direction='in' />
                </method>
            </interface>
        </node>
    """

    def test_raises_RuntimeError_when_no_interface_is_found(self):
        self.assertThat(
            lambda: _i._get_proxy_bases_from_introspection_xml(""),
            raises(RuntimeError("Could not find Autopilot interface."))
        )

    def test_returns_ApplicationProxyObject_claws_for_base_interface(self):
        self.assertThat(
            _i._get_proxy_bases_from_introspection_xml(
                self.fake_data_with_ap_interface
            ),
            Equals((_i.ApplicationProxyObject,))
        )

    def test_returns_both_base_and_qt_interface(self):
        self.assertThat(
            _i._get_proxy_bases_from_introspection_xml(
                self.fake_data_with_ap_and_qt_interfaces
            ),
            Equals((_i.ApplicationProxyObject, QtObjectProxyMixin))
        )


class ExtendProxyBasesWithEmulatorBaseTests(TestCase):

    def test_default_emulator_base_name(self):
        bases = _i._extend_proxy_bases_with_emulator_base(tuple(), None)
        self.assertThat(len(bases), Equals(1))
        self.assertThat(bases[0].__name__, Equals("DefaultEmulatorBase"))
        self.assertThat(bases[0].__bases__[0], Equals(_i.CustomEmulatorBase))

    def test_appends_custom_emulator_base(self):
        existing_bases = ('token',)
        custom_emulator_base = Mock()
        new_bases = _i._extend_proxy_bases_with_emulator_base(
            existing_bases,
            custom_emulator_base
        )
        self.assertThat(
            new_bases,
            Equals(existing_bases + (custom_emulator_base,))
        )
