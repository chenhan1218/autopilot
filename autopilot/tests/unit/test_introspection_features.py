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

import sys
import tempfile
import shutil
import os.path

from mock import patch, Mock, MagicMock
from textwrap import dedent
from testtools import TestCase
from testtools.matchers import (
    Equals,
    IsInstance,
    Not,
    NotEquals,
    Raises,
    raises,
)
from six import StringIO, u, PY3
from contextlib import contextmanager
if PY3:
    from contextlib import ExitStack
else:
    from contextlib2 import ExitStack


from autopilot.exceptions import StateNotFoundError
from autopilot.introspection import (
    _check_process_and_pid_details,
    _get_application_name_from_dbus_address,
    _get_search_criteria_string_representation,
    _maybe_filter_connections_by_app_name,
    CustomEmulatorBase,
    get_proxy_object_for_existing_process,
    ProcessSearchError,
)
from autopilot.introspection import backends
from autopilot.introspection import _object_registry as object_registry
from autopilot.introspection import _xpathselect as xpathselect
from autopilot.introspection.dbus import (
    _object_passes_filters,
    DBusIntrospectionObject,
)
from autopilot.introspection.qt import QtObjectProxyMixin
import autopilot.introspection as _i
from autopilot.utilities import sleep


class IntrospectionFeatureTests(TestCase):

    def test_custom_emulator_base_does_not_have_id(self):
        self.assertThat(hasattr(CustomEmulatorBase, '_id'), Equals(False))

    def test_derived_emulator_bases_do_have_id(self):
        class MyEmulatorBase(CustomEmulatorBase):
            pass
        self.assertThat(hasattr(MyEmulatorBase, '_id'), Equals(True))

    def test_derived_children_have_same_id(self):
        class MyEmulatorBase(CustomEmulatorBase):
            pass

        class MyEmulator(MyEmulatorBase):
            pass

        class MyEmulator2(MyEmulatorBase):
            pass

        self.assertThat(MyEmulatorBase._id, Equals(MyEmulator._id))
        self.assertThat(MyEmulatorBase._id, Equals(MyEmulator2._id))

    def test_children_have_different_ids(self):
        class MyEmulatorBase(CustomEmulatorBase):
            pass

        class MyEmulatorBase2(CustomEmulatorBase):
            pass

        self.assertThat(MyEmulatorBase._id, NotEquals(MyEmulatorBase2._id))


class ClientSideFilteringTests(TestCase):

    def get_empty_fake_object(self):
        return type(
            'EmptyObject',
            (object,),
            {'no_automatic_refreshing': MagicMock()}
        )

    def test_object_passes_filters_disables_refreshing(self):
        obj = self.get_empty_fake_object()
        _object_passes_filters(obj)

        obj.no_automatic_refreshing.assert_called_once_with()
        self.assertTrue(
            obj.no_automatic_refreshing.return_value.__enter__.called
        )

    def test_object_passes_filters_works_with_no_filters(self):
        obj = self.get_empty_fake_object()
        self.assertTrue(_object_passes_filters(obj))

    def test_object_passes_filters_fails_when_attr_missing(self):
        obj = self.get_empty_fake_object()
        self.assertFalse(_object_passes_filters(obj, foo=123))

    def test_object_passes_filters_fails_when_attr_has_wrong_value(self):
        obj = self.get_empty_fake_object()
        obj.foo = 456
        self.assertFalse(_object_passes_filters(obj, foo=123))

    def test_object_passes_filters_succeeds_with_one_correct_parameter(self):
        obj = self.get_empty_fake_object()
        obj.foo = 123
        self.assertTrue(_object_passes_filters(obj, foo=123))


class DBusIntrospectionObjectTests(TestCase):

    def test_can_access_path_attribute(self):
        fake_object = DBusIntrospectionObject(
            dict(id=[0, 123], path=[0, '/some/path']),
            b'/root',
            Mock()
        )
        with fake_object.no_automatic_refreshing():
            self.assertThat(fake_object.path, Equals('/some/path'))

    @patch('autopilot.introspection.dbus._logger')
    def test_large_query_returns_log_warnings(self, mock_logger):
        """Queries that return large numbers of items must cause a log warning.

        'large' is defined as more than 15.

        """
        fake_object = DBusIntrospectionObject(
            dict(id=[0, 123], path=[0, '/some/path']),
            b'/root',
            Mock()
        )
        fake_object._backend.introspection_iface.GetState.return_value = \
            [(b'/root/path', {}) for i in range(16)]
        fake_object.get_state_by_path(b'some_query')

        mock_logger.warning.assert_called_once_with(
            "Your query '%s' returned a lot of data (%d items). This "
            "is likely to be slow. You may want to consider optimising"
            " your query to return fewer items.",
            b"some_query",
            16)

    @patch('autopilot.introspection.dbus._logger')
    def test_small_query_returns_dont_log_warnings(self, mock_logger):
        """Queries that return small numbers of items must not log a warning.

        'small' is defined as 15 or fewer.

        """
        fake_object = DBusIntrospectionObject(
            dict(id=[0, 123], path=[0, '/some/path']),
            b'/root',
            Mock()
        )
        fake_object._backend.introspection_iface.GetState.return_value = \
            [(b'/root/path', {}) for i in range(15)]
        fake_object.get_state_by_path(b'some_query')

        self.assertThat(mock_logger.warning.called, Equals(False))

    def test_wait_until_destroyed_works(self):
        """wait_until_destroyed must return if no new state is found."""
        fake_object = DBusIntrospectionObject(
            dict(id=[0, 123]),
            b'/root',
            Mock()
        )
        fake_object._backend.introspection_iface.GetState.return_value = []

        self.assertThat(fake_object.wait_until_destroyed, Not(Raises()))

    def test_wait_until_destroyed_raises_RuntimeError(self):
        """wait_until_destroyed must raise RuntimeError if the object
        persists.

        """
        fake_state = dict(id=[0, 123])
        fake_object = DBusIntrospectionObject(
            fake_state,
            b'/root',
            Mock()
        )
        fake_object._backend.introspection_iface.GetState.return_value = \
            [fake_state]

        with sleep.mocked():
            self.assertThat(
                lambda: fake_object.wait_until_destroyed(timeout=1),
                raises(
                    RuntimeError("Object was not destroyed after 1 seconds")
                ),
            )

    def _print_test_fake_object(self):
        """common fake object for print_tree tests"""

        fake_object = DBusIntrospectionObject(
            dict(id=[0, 123], path=[0, '/some/path'], text=[0, 'Hello']),
            b'/some/path',
            Mock()
        )
        # get_properties() always refreshes state, so can't use
        # no_automatic_refreshing()
        fake_object.refresh_state = lambda: None
        fake_object.get_state_by_path = lambda query: []
        return fake_object

    def test_print_tree_stdout(self):
        """print_tree with default output (stdout)"""

        fake_object = self._print_test_fake_object()
        orig_sys_stdout = sys.stdout
        sys.stdout = StringIO()
        try:
            fake_object.print_tree()
            result = sys.stdout.getvalue()
        finally:
            sys.stdout = orig_sys_stdout

        self.assertEqual(result, dedent("""\
            == /some/path ==
            id: 123
            path: '/some/path'
            text: 'Hello'
            """))

    def test_print_tree_exception(self):
        """print_tree with StateNotFound exception"""

        fake_object = self._print_test_fake_object()
        child = Mock()
        child.print_tree.side_effect = StateNotFoundError('child')

        with patch.object(fake_object, 'get_children', return_value=[child]):
            out = StringIO()
            print_func = lambda: fake_object.print_tree(out)
            self.assertThat(print_func, Not(Raises(StateNotFoundError)))
            self.assertEqual(out.getvalue(), dedent("""\
            == /some/path ==
            id: 123
            path: '/some/path'
            text: 'Hello'
            Error: Object not found with name 'child'.
            """))

    def test_print_tree_fileobj(self):
        """print_tree with file object output"""

        fake_object = self._print_test_fake_object()
        out = StringIO()

        fake_object.print_tree(out)

        self.assertEqual(out.getvalue(), dedent("""\
            == /some/path ==
            id: 123
            path: '/some/path'
            text: 'Hello'
            """))

    def test_print_tree_path(self):
        """print_tree with file path output"""

        fake_object = self._print_test_fake_object()
        workdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, workdir)
        outfile = os.path.join(workdir, 'widgets.txt')

        fake_object.print_tree(outfile)

        with open(outfile) as f:
            result = f.read()
        self.assertEqual(result, dedent("""\
            == /some/path ==
            id: 123
            path: '/some/path'
            text: 'Hello'
            """))


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

    fake_state_data = ('/some/path', dict(foo=123))

    def test_returns_classname(self):
        class_name, _, _ = _i._get_details_from_state_data(
            self.fake_state_data
        )
        self.assertThat(class_name, Equals('path'))

    def test_returns_path(self):
        _, path, _ = _i._get_details_from_state_data(self.fake_state_data)
        self.assertThat(path, Equals('/some/path'))

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


class MakeIntrospectionObjectTests(TestCase):

    """Test selection of custom proxy object class."""

    class DefaultSelector(CustomEmulatorBase):
        pass

    class AlwaysSelected(CustomEmulatorBase):
        @classmethod
        def validate_dbus_object(cls, path, state):
            """Validate always.

            :returns: True

            """
            return True

    class NeverSelected(CustomEmulatorBase):
        @classmethod
        def validate_dbus_object(cls, path, state):
            """Validate never.

            :returns: False

            """
            return False

    def test_class_has_validation_method(self):
        """Verify that a class has a validation method by default."""
        self.assertTrue(callable(self.DefaultSelector.validate_dbus_object))

    @patch.object(backends, '_get_proxy_object_class')
    def test_make_introspection_object(self, gpoc):
        """Verify that make_introspection_object makes the right call."""
        gpoc.return_value = self.DefaultSelector
        fake_id = Mock()
        fake_proxy_type = Mock()
        new_fake = backends.make_introspection_object(
            (b'/Object', {'id': [0, 42]}),
            None,
            fake_id,
            fake_proxy_type,
        )
        self.assertThat(new_fake, IsInstance(self.DefaultSelector))
        gpoc.assert_called_once_with(
            fake_id,
            fake_proxy_type,
            b'/Object',
            {'id': [0, 42]}
        )

    @patch.object(object_registry, '_try_custom_proxy_classes')
    @patch.object(object_registry, '_get_default_proxy_class')
    def test_get_proxy_object_class_return_from_list(self, gdpc, tcpc):
        """_get_proxy_object_class should return the value of
        _try_custom_proxy_classes if there is one."""
        token = self.getUniqueString()
        tcpc.return_value = token
        gpoc_return = object_registry._get_proxy_object_class(
            None,
            None,
            None,
            None
        )

        self.assertThat(gpoc_return, Equals(token))
        self.assertFalse(gdpc.called)

    @patch.object(object_registry, '_try_custom_proxy_classes')
    def test_get_proxy_object_class_send_right_args(self, tcpc):
        """_get_proxy_object_class should send the right arguments to
        _try_custom_proxy_classes."""
        class_dict = {'DefaultSelector': self.DefaultSelector}
        path = '/path/to/DefaultSelector'
        state = {}
        object_registry._get_proxy_object_class(class_dict, None, path, state)
        tcpc.assert_called_once_with(class_dict, path, state)

    @patch.object(object_registry, '_try_custom_proxy_classes')
    def test_get_proxy_object_class_not_handle_error(self, tcpc):
        """_get_proxy_object_class should not handle an exception raised by
        _try_custom_proxy_classes."""
        tcpc.side_effect = ValueError
        self.assertThat(
            lambda: object_registry._get_proxy_object_class(
                None,
                None,
                None,
                None
            ),
            raises(ValueError))

    @patch.object(object_registry, '_try_custom_proxy_classes')
    @patch.object(object_registry, '_get_default_proxy_class')
    @patch.object(object_registry, 'get_classname_from_path')
    def test_get_proxy_object_class_call_default_call(self, gcfp, gdpc, tcpc):
        """_get_proxy_object_class should call _get_default_proxy_class if
        _try_custom_proxy_classes returns None."""
        tcpc.return_value = None
        object_registry._get_proxy_object_class(None, None, None, None)
        self.assertTrue(gdpc.called)

    @patch.object(object_registry, '_try_custom_proxy_classes')
    @patch.object(object_registry, '_get_default_proxy_class')
    def test_get_proxy_object_class_default_args(self, gdpc, tcpc):
        """_get_proxy_object_class should pass the correct arguments to
        _get_default_proxy_class"""
        tcpc.return_value = None
        default = self.DefaultSelector
        path = '/path/to/DefaultSelector'
        object_registry._get_proxy_object_class(None, default, path, None)
        gdpc.assert_called_once_with(
            default,
            xpathselect.get_classname_from_path(path)
        )

    @patch.object(object_registry, '_try_custom_proxy_classes')
    @patch.object(object_registry, '_get_default_proxy_class')
    @patch.object(object_registry, 'get_classname_from_path')
    def test_get_proxy_object_class_default(self, gcfp, gdpc, tcpc):
        """_get_proxy_object_class should return the value of
        _get_default_proxy_class if _try_custom_proxy_classes returns None."""
        token = self.getUniqueString()
        gdpc.return_value = token
        tcpc.return_value = None
        gpoc_return = object_registry._get_proxy_object_class(
            None,
            None,
            None,
            None
        )
        self.assertThat(gpoc_return, Equals(token))

    def test_try_custom_proxy_classes_zero_results(self):
        """_try_custom_proxy_classes must return None if no classes match."""
        proxy_class_dict = {'NeverSelected': self.NeverSelected}
        fake_id = self.getUniqueInteger()
        path = '/path/to/NeverSelected'
        state = {}
        with object_registry.patch_registry({fake_id: proxy_class_dict}):
            class_type = object_registry._try_custom_proxy_classes(
                fake_id,
                path,
                state
            )
        self.assertThat(class_type, Equals(None))

    def test_try_custom_proxy_classes_one_result(self):
        """_try_custom_proxy_classes must return the matching class if there is
        exacly 1."""
        proxy_class_dict = {'DefaultSelector': self.DefaultSelector}
        fake_id = self.getUniqueInteger()
        path = '/path/to/DefaultSelector'
        state = {}
        with object_registry.patch_registry({fake_id: proxy_class_dict}):
            class_type = object_registry._try_custom_proxy_classes(
                fake_id,
                path,
                state
            )
        self.assertThat(class_type, Equals(self.DefaultSelector))

    def test_try_custom_proxy_classes_two_results(self):
        """_try_custom_proxy_classes must raise ValueError if multiple classes
        match."""
        proxy_class_dict = {'DefaultSelector': self.DefaultSelector,
                            'AlwaysSelected': self.AlwaysSelected}
        path = '/path/to/DefaultSelector'
        state = {}
        object_id = self.getUniqueInteger()
        with object_registry.patch_registry({object_id: proxy_class_dict}):
            self.assertThat(
                lambda: object_registry._try_custom_proxy_classes(
                    object_id,
                    path,
                    state
                ),
                raises(ValueError)
            )

    @patch('autopilot.introspection._object_registry.get_debug_logger')
    def test_get_default_proxy_class_logging(self, gdl):
        """_get_default_proxy_class should log a message."""
        object_registry._get_default_proxy_class(self.DefaultSelector, None)
        gdl.assert_called_once_with()

    def test_get_default_proxy_class_base(self):
        """Subclass must return an emulator of base class."""
        class SubclassedProxy(self.DefaultSelector):
            pass

        result = object_registry._get_default_proxy_class(SubclassedProxy, 'Object')
        self.assertTrue(result, Equals(self.DefaultSelector))

    def test_get_default_proxy_class_base_instead_of_self(self):
        """Subclass must not use self if base class works."""
        class SubclassedProxy(self.DefaultSelector):
            pass

        result = object_registry._get_default_proxy_class(
            SubclassedProxy,
            'Object'
        )
        self.assertFalse(issubclass(result, SubclassedProxy))

    def test_get_default_proxy_class(self):
        """Must default to own class if no usable bases present."""
        result = object_registry._get_default_proxy_class(
            self.DefaultSelector,
            'Object'
        )
        self.assertTrue(result, Equals(self.DefaultSelector))

    def test_get_default_proxy_name(self):
        """Must default to own class if no usable bases present."""
        token = self.getUniqueString()
        result = object_registry._get_default_proxy_class(
            self.DefaultSelector,
            token
        )
        self.assertThat(result.__name__, Equals(token))

    def test_validate_dbus_object_matches_on_class_name(self):
        """Validate_dbus_object must match class name."""
        selected = self.DefaultSelector.validate_dbus_object(
            '/DefaultSelector', {})
        self.assertTrue(selected)
