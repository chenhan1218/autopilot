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

from dbus import DBusException
from mock import patch, Mock
from testtools import TestCase
from testtools.matchers import Contains, raises

from autopilot.introspection import _filters as _f, _search as _s


class MatchesConnectionHasPathWithAPInterfaceTests(TestCase):
    """Tests specific to the MatchesConnectionHasPid filter."""

    def test_raises_ValueError_when_missing_path_param(self):
        dbus_connection = ("bus", "name")
        self.assertThat(
            lambda: _f.MatchesConnectionHasPathWithAPInterface.matches(
                dbus_connection,
                {}
            ),
            raises(ValueError("Filter was expecting 'path' parameter"))
        )

    @patch.object(_f.dbus, "Interface")
    def test_returns_True_on_success(self, Interface):
        bus_obj = Mock()
        connection_name = "name"
        path = "path"
        dbus_connection = (bus_obj, connection_name)

        self.assertTrue(
            _f.MatchesConnectionHasPathWithAPInterface.matches(
                dbus_connection,
                dict(path=path)
            )
        )

        bus_obj.get_object.assert_called_once_with("name", path)

    @patch.object(_f.dbus, "Interface")
    def test_returns_False_on_dbus_exception(self, Interface):
        bus_obj = Mock()
        connection_name = "name"
        path = "path"
        dbus_connection = (bus_obj, connection_name)

        Interface.side_effect = DBusException()

        self.assertFalse(
            _f.MatchesConnectionHasPathWithAPInterface.matches(
                dbus_connection,
                dict(path=path)
            )
        )

        bus_obj.get_object.assert_called_once_with("name", path)


class MatchesConnectionHasPidTests(TestCase):
    """Tests specific to the MatchesConnectionHasPid filter."""

    def test_raises_when_missing_param(self):
        self.assertThat(
            lambda: _f.MatchesConnectionHasPid.matches(None, {}),
            raises(KeyError('pid'))
        )

    def test_returns_False_when_should_ignore_pid(self):
        dbus_connection = ("bus", "org.freedesktop.DBus")
        params = dict(pid=None)
        self.assertFalse(
            _f.MatchesConnectionHasPid.matches(dbus_connection, params)
        )

    @patch.object(
        _f.MatchesConnectionHasPid,
        '_should_ignore_pid',
        return_value=False
    )
    def test_returns_True_when_bus_pid_matches(self, p):
        connection_pid = self.getUniqueInteger()
        dbus_connection = ("bus", "org.freedesktop.DBus")
        params = dict(pid=connection_pid)
        with patch.object(
            _f,
            '_get_bus_connections_pid',
            return_value=connection_pid
        ):
            self.assertTrue(
                _f.MatchesConnectionHasPid.matches(dbus_connection, params)
            )

    @patch.object(
        _f.MatchesConnectionHasPid,
        '_should_ignore_pid',
        return_value=False
    )
    def test_returns_False_with_DBusException(self, p):
        connection_pid = self.getUniqueInteger()
        dbus_connection = ("bus", "org.freedesktop.DBus")
        params = dict(pid=connection_pid)
        with patch.object(
            _f,
            '_get_bus_connections_pid',
            side_effect=DBusException()
        ):
            self.assertFalse(
                _f.MatchesConnectionHasPid.matches(dbus_connection, params)
            )

    def test_should_ignore_pid_returns_True_with_connection_name(self):
        self.assertTrue(
            _f.MatchesConnectionHasPid._should_ignore_pid(
                None,
                "org.freedesktop.DBus",
                None
            )
        )

    def test_should_ignore_pid_returns_True_when_pid_is_our_pid(self):
        with patch.object(
                _f.MatchesConnectionHasPid,
                '_bus_pid_is_our_pid',
                return_value=True
        ):
            self.assertTrue(
                _f.MatchesConnectionHasPid._should_ignore_pid(None, None, None)
            )

    def test_should_ignore_pid_returns_False_when_pid_is_our_pid(self):
        with patch.object(
                _f.MatchesConnectionHasPid,
                '_bus_pid_is_our_pid',
                return_value=False
        ):
            self.assertFalse(
                _f.MatchesConnectionHasPid._should_ignore_pid(None, None, None)
            )


class MatchesConnectionHasAppNameTests(TestCase):
    """Tests specific to the MatchesConnectionHasPid filter."""

    def test_raises_when_missing_app_name_param(self):
        self.assertThat(
            lambda: _f.MatchesConnectionHasAppName.matches(None, {}),
            raises(KeyError('application_name'))
        )


class FilterHelpersTests(TestCase):

    def test_param_to_filter_includes_all(self):
        parameters = dict(application_name=True, pid=True, path=True)
        filter_list = _s.FilterListGenerator(
            parameters,
            _f._param_to_filter_map
        )

        self.assertThat(filter_list, Contains(_f.MatchesConnectionHasAppName))
        self.assertThat(filter_list, Contains(_f.MatchesConnectionHasPid))
        self.assertThat(
            filter_list,
            Contains(_f.MatchesConnectionHasPathWithAPInterface)
        )
