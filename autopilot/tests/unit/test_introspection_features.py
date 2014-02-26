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

from mock import patch, Mock
from textwrap import dedent
from testtools import TestCase
from testtools.matchers import (
    Equals,
    Not,
    NotEquals,
    Raises,
    raises,
)
from testscenarios import TestWithScenarios
from six import StringIO, u, PY3
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
from autopilot.introspection.dbus import (
    _get_filter_string_for_key_value_pair,
    _is_valid_server_side_filter_param,
    _get_proxy_object_class,
    CustomEmulatorBase,
    DBusIntrospectionObject,
)
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


class ServerSideParamMatchingTests(TestWithScenarios, TestCase):

    """Tests for the server side matching decision function."""

    scenarios = [
        ('should work', dict(key='keyname', value='value', result=True)),
        ('invalid key', dict(key='k  e', value='value', result=False)),
        ('string value', dict(key='key', value='v  e', result=True)),
        ('string value2', dict(key='key', value='v?e', result=True)),
        ('string value3', dict(key='key', value='1/2."!@#*&^%', result=True)),
        ('bool value', dict(key='key', value=False, result=True)),
        ('int value', dict(key='key', value=123, result=True)),
        ('int value2', dict(key='key', value=-123, result=True)),
        ('float value', dict(key='key', value=1.0, result=False)),
        ('dict value', dict(key='key', value={}, result=False)),
        ('obj value', dict(key='key', value=TestCase, result=False)),
        ('int overflow 1', dict(key='key', value=-2147483648, result=True)),
        ('int overflow 2', dict(key='key', value=-2147483649, result=False)),
        ('int overflow 3', dict(key='key', value=2147483647, result=True)),
        ('int overflow 4', dict(key='key', value=2147483648, result=False)),
    ]

    def test_valid_server_side_param(self):
        self.assertThat(
            _is_valid_server_side_filter_param(self.key, self.value),
            Equals(self.result)
        )


class ServerSideParameterFilterStringTests(TestWithScenarios, TestCase):

    scenarios = [
        ('bool true', dict(k='visible', v=True, r="visible=True")),
        ('bool false', dict(k='visible', v=False, r="visible=False")),
        ('int +ve', dict(k='size', v=123, r="size=123")),
        ('int -ve', dict(k='prio', v=-12, r="prio=-12")),
        ('simple string', dict(k='Name', v="btn1", r="Name=\"btn1\"")),
        ('string space', dict(k='Name', v="a b  c ", r="Name=\"a b  c \"")),
        ('str escapes', dict(
            k='a',
            v="\a\b\f\n\r\t\v\\",
            r=r'a="\x07\x08\x0c\n\r\t\x0b\\"')),
        ('escape quotes', dict(k='b', v="'", r='b="\\' + "'" + '"')),
    ]

    def test_query_string(self):
        s = _get_filter_string_for_key_value_pair(self.k, self.v)
        self.assertThat(s, Equals(self.r))


class DBusIntrospectionObjectTests(TestCase):

    def test_can_access_path_attribute(self):
        fake_object = DBusIntrospectionObject(
            dict(id=[0, 123], path=[0, '/some/path']),
            '/',
            Mock()
        )
        with fake_object.no_automatic_refreshing():
            self.assertThat(fake_object.path, Equals('/some/path'))

    @patch('autopilot.introspection.dbus.logger')
    def test_large_query_returns_log_warnings(self, mock_logger):
        """Queries that return large numbers of items must cause a log warning.

        'large' is defined as more than 15.

        """
        fake_object = DBusIntrospectionObject(
            dict(id=[0, 123], path=[0, '/some/path']),
            '/',
            Mock()
        )
        fake_object._backend.introspection_iface.GetState.return_value = \
            [('/path', {}) for i in range(16)]
        fake_object.get_state_by_path('some_query')

        mock_logger.warning.assert_called_once_with(
            "Your query '%s' returned a lot of data (%d items). This "
            "is likely to be slow. You may want to consider optimising"
            " your query to return fewer items.",
            "some_query",
            16)

    @patch('autopilot.introspection.dbus.logger')
    def test_small_query_returns_dont_log_warnings(self, mock_logger):
        """Queries that return small numbers of items must not log a warning.

        'small' is defined as 15 or fewer.

        """
        fake_object = DBusIntrospectionObject(
            dict(id=[0, 123], path=[0, '/some/path']),
            '/',
            Mock()
        )
        fake_object._backend.introspection_iface.GetState.return_value = \
            [('/path', {}) for i in range(15)]
        fake_object.get_state_by_path('some_query')

        self.assertThat(mock_logger.warning.called, Equals(False))

    def test_wait_until_destroyed_works(self):
        """wait_until_destroyed must return if no new state is found."""
        fake_object = DBusIntrospectionObject(
            dict(id=[0, 123]),
            '/',
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
            '/',
            Mock()
        )
        fake_object._backend.introspection_iface.GetState.return_value = \
            [fake_state]

        with sleep.mocked():
            self.assertThat(
                lambda: fake_object.wait_until_destroyed(timeout=1),
                raises(
                    RuntimeError("Object was not destroyed after 1 seconds")
                )
            )

    def _print_test_fake_object(self):
        """common fake object for print_tree tests"""

        fake_object = DBusIntrospectionObject(
            dict(id=[0, 123], path=[0, '/some/path'], text=[0, 'Hello']),
            '/some/path',
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


class MakeIntrospectionObjectTests(TestCase):

    class DefaultSelector(CustomEmulatorBase):
        pass

    class AlwaysSelected(CustomEmulatorBase):
        @classmethod
        def validate_dbus_object(cls, path, state):
            return True

    class NeverSelected(CustomEmulatorBase):
        @classmethod
        def validate_dbus_object(cls, path, state):
            return False

    def test_class_has_validation_method(self):
        self.assertThat(callable(self.DefaultSelector.validate_dbus_object),
                        Equals(True))

    def test_select_by_name(self):
        """Correct custom emulator must be returned by name."""
        fake_object = self.DefaultSelector(
            dict(id=[0, 123], path=[0, '/some/path']),
            '/',
            Mock()
        )

        rectangle = fake_object.make_introspection_object(
            ('/DefaultSelector', {'id': [0, 0]}))
        self.assertThat(isinstance(rectangle, self.DefaultSelector),
                        Equals(True))

    def test_select_by_function(self):
        """Correct emulator must be returned by function."""
        object_registry = {'DefaultSelector': self.DefaultSelector}
        self.assertThat(
            _get_proxy_object_class(object_registry,
                                    '/DefaultSelector',
                                    {'id': [0, 0]}),
            Equals(self.DefaultSelector))

    def test_select_function_fails(self):
        """Must return None when all functions return False."""
        object_registry = {'Circle': self.NeverSelected}
        self.assertThat(
            _get_proxy_object_class(object_registry,
                                    '/DefaultSelector',
                                    {'id': [0, 0]}),
            Equals(None))

    def test_multiple_matches(self):
        """Exception must be raised if multiple emulators match."""
        object_registry = {'DefaultSelector': self.DefaultSelector,
                           'Square': self.AlwaysSelected}

        self.assertThat(
            lambda: _get_proxy_object_class(object_registry,
                                            '/DefaultSelector',
                                            {'id': [0, 0]}),
            raises(ValueError)
        )

    def test_no_matches(self):
        """Generic emulator must be used if no emulators match."""
        fake_object = self.NeverSelected(
            dict(id=[0, 123], path=[0, '/some/path']),
            '/',
            Mock()
        )

        rectangle = fake_object.make_introspection_object(
            ('/DefaultSelector', {'id': [0, 0]}))
        self.assertTrue(isinstance(rectangle, CustomEmulatorBase))
