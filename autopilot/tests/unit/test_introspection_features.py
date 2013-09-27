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


from mock import patch
from testtools import TestCase
from testtools.matchers import Equals, NotEquals
from testscenarios import TestWithScenarios


from autopilot.introspection.dbus import (
    CustomEmulatorBase,
    DBusIntrospectionObject,
    _is_valid_server_side_filter_param,
)


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
        ('invalid value', dict(key='key', value='v  e', result=False)),
        ('invalid value2', dict(key='key', value='v?e', result=False)),
        ('invalid value3', dict(key='key', value='1/2', result=False)),
        ('invalid value type', dict(key='key', value=False, result=False)),
    ]

    def test_valid_server_side_param(self):
        self.assertThat(
            _is_valid_server_side_filter_param(self.key, self.value),
            Equals(self.result)
        )


class DBusIntrospectionObjectTests(TestCase):

    def test_can_access_path_attribute(self):
        fake_object = DBusIntrospectionObject(
            dict(id=123, path='/some/path'),
            '/'
        )
        with fake_object.no_automatic_refreshing():
            self.assertThat(fake_object.path, Equals('/some/path'))

    @patch('autopilot.introspection.dbus.logger')
    def test_large_query_returns_log_warnings(self, mock_logger):
        """Queries that return large numbers of items must cause a log warning.

        'large' is defined as more than 15.

        """
        with patch.object(DBusIntrospectionObject, '_Backend') as p:
            p.introspection_iface.GetState.return_value = \
                [('/path', {}) for i in range(16)]
            DBusIntrospectionObject.get_state_by_path('some_query')

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
        with patch.object(DBusIntrospectionObject, '_Backend') as p:
            p.introspection_iface.GetState.return_value = \
                [('/path', {}) for i in range(15)]
            DBusIntrospectionObject.get_state_by_path('some_query')

        self.assertThat(mock_logger.warning.called, Equals(False))
