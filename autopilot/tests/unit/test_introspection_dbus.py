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

import sys
import tempfile
import shutil
import os.path

from mock import patch, Mock
from six import StringIO
from textwrap import dedent
from testtools import TestCase
from testtools.matchers import (
    Equals,
    Not,
    NotEquals,
    Raises,
    raises,
)

from autopilot.exceptions import StateNotFoundError
from autopilot.introspection import CustomEmulatorBase
from autopilot.introspection import dbus
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


class DBusIntrospectionObjectTests(TestCase):

    def test_can_access_path_attribute(self):
        fake_object = dbus.DBusIntrospectionObject(
            dict(id=[0, 123], path=[0, '/some/path']),
            b'/root',
            Mock()
        )
        with fake_object.no_automatic_refreshing():
            self.assertThat(fake_object.path, Equals('/some/path'))

    def test_wait_until_destroyed_works(self):
        """wait_until_destroyed must return if no new state is found."""
        fake_object = dbus.DBusIntrospectionObject(
            dict(id=[0, 123]),
            b'/root',
            Mock()
        )
        fake_object._backend.execute_query_get_data.return_value = []

        fake_object.wait_until_destroyed()
        self.assertThat(fake_object.wait_until_destroyed, Not(Raises()))

    def test_wait_until_destroyed_raises_RuntimeError(self):
        """wait_until_destroyed must raise RuntimeError if the object
        persists.

        """
        fake_state = dict(id=[0, 123])
        fake_object = dbus.DBusIntrospectionObject(
            fake_state,
            b'/root',
            Mock()
        )
        fake_object._backend.execute_query_get_data.return_value = \
            [fake_state]

        with sleep.mocked():
            self.assertThat(
                lambda: fake_object.wait_until_destroyed(timeout=1),
                raises(
                    RuntimeError("Object was not destroyed after 1 seconds")
                ),
            )


class ProxyObjectPrintTreeTests(TestCase):

    def _print_test_fake_object(self):
        """common fake object for print_tree tests"""

        fake_object = dbus.DBusIntrospectionObject(
            dict(id=[0, 123], path=[0, '/some/path'], text=[0, 'Hello']),
            b'/some/path',
            Mock()
        )
        # get_properties() always refreshes state, so can't use
        # no_automatic_refreshing()
        fake_object.refresh_state = lambda: None
        fake_object._execute_query = lambda q: []
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


class GetTypeNameTests(TestCase):

    """Tests for the autopilot.introspection.dbus.get_type_name function."""

    def test_returns_string(self):
        token = self.getUniqueString()
        self.assertEqual(token, dbus.get_type_name(token))

    def test_returns_class_name(self):
        class FooBarBaz(object):
            pass
        self.assertEqual("FooBarBaz", dbus.get_type_name(FooBarBaz))
