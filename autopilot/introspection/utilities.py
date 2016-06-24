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

from contextlib import contextmanager
import sys

from dbus import Interface
import os.path

from autopilot.display import is_point_on_any_screen
from autopilot.utilities import process_iter


CO_ORD_MAX = (sys.maxsize, sys.maxsize)


def _pid_is_running(pid):
    """Check for the existence of a currently running PID.

    :returns: **True** if PID is running **False** otherwise.
    """
    return os.path.exists("/proc/%d" % pid)


def _get_bus_connections_pid(bus, connection_name):
    """Returns the pid for the connection **connection_name** on **bus**

    :raises: **DBusException** if connection_name is invalid etc.

    """
    bus_obj = bus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus')
    bus_iface = Interface(bus_obj, 'org.freedesktop.DBus')
    return bus_iface.GetConnectionUnixProcessID(connection_name)


def translate_state_keys(state_dict):
    """Translates the *state_dict* passed in so the keys are usable as python
    attributes."""
    return {k.replace('-', '_'): v for k, v in state_dict.items()}


class ProcessUtil:
    """Helper class to manipulate running processes."""

    @contextmanager
    def mocked(self, fake_processes):
        """Enable mocking for the ProcessUtil class

        Also mocks all calls to autopilot.utilities.process_iter.
        One may use it like::

            from autopilot.introspection.utilities import ProcessUtil

            process_util = ProcessUtil()
            with process_util.mocked([{'pid': -9, 'name': 'xx'}]):
                self.assertThat(
                    process_util.get_pid_for_process('xx'),
                    Equals(-9)
                    )
                )

        """
        process_iter.enable_mock(fake_processes)
        try:
            yield self
        finally:
            process_iter.disable_mock()

    def _query_pids_for_process(self, process_name):
        if not isinstance(process_name, str):
            raise ValueError('Process name must be a string.')

        pids = [process.pid for process in process_iter()
                if process.name() == process_name]

        if not pids:
            raise ValueError('Process \'{}\' not running'.format(process_name))

        return pids

    def get_pid_for_process(self, process_name):
        """Returns the PID associated with a process name.

        :param process_name: Process name to get PID for. This must
            be a string.

        :return: PID of the requested process.
        """
        pids = self._query_pids_for_process(process_name)
        if len(pids) > 1:
            raise ValueError(
                'More than one PID exists for process \'{}\''.format(
                    process_name
                )
            )

        return pids[0]

    def get_pids_for_process(self, process_name):
        """Returns PID(s) associated with a process name.

        :param process_name: Process name to get PID(s) for.

        :return: A list containing the PID(s) of the requested process.
        """
        return self._query_pids_for_process(process_name)

process_util = ProcessUtil()


class SortUtil:
    """
    Helper class to sort autopilot dbus objects based on their
    co-ordinates.
    """

    def order_by_x_coord(self, dbus_object_list, include_off_screen=False):
        """Sort the dbus objects list by x co-ordinate.

        Sort the dbus objects by x co-ordinate. This is normally used to
        sort results retrieved by calling *select_many* on a proxy object.

        :param dbus_object_list: list of dbus objects to sort.

        :param include_off_screen: Whether to include off-screen elements.

        :return: sorted list of elements.
        """
        return self._order_by_key(
            dbus_object_list=dbus_object_list,
            sort_key=self._get_x_and_y,
            include_off_screen=include_off_screen
        )

    def order_by_y_coord(self, dbus_object_list, include_off_screen=False):
        """Sort the dbus objects list by y co-ordinate.

        Sort the dbus objects by y co-ordinate. This is normally used to
        sort results retrieved by calling *select_many* on a proxy object.

        :param dbus_object_list: list of dbus objects to sort.

        :param include_off_screen: Whether to include off-screen elements.

        :return: sorted list of elements.
        """
        return self._order_by_key(
            dbus_object_list=dbus_object_list,
            sort_key=self._get_y_and_x,
            include_off_screen=include_off_screen
        )

    def _order_by_key(self, dbus_object_list, sort_key, include_off_screen):
        objects = [obj for obj in dbus_object_list if
                   self._filter_object(obj, include_off_screen)]
        return sorted(objects, key=sort_key)

    def _filter_object(self, obj, include_off_screen):
        from autopilot.introspection import is_element
        if is_element(obj.refresh_state):
            point = self._get_x_and_y(obj)
            if include_off_screen or display_util.is_point_on_any_screen(
                    point):
                return obj
        return None

    def _get_y_and_x(self, item):
        """Return y and x co-ordinates for specified object.

        :param item: Item to check
        :return: (y, x) co-ordinates
        """
        from autopilot.introspection import is_element
        if is_element(item.refresh_state):
            return item.globalRect.y, item.globalRect.x

        # Trying to sort an object that no longer exists,
        # return a dummy key value so this item is sorted last
        return CO_ORD_MAX

    def _get_x_and_y(self, item):
        """Return x and y co-ordinates for specified object.

        :param item: Item to check
        :return: (x, y) co-ordinates
        """
        from autopilot.introspection import is_element
        if is_element(item.refresh_state):
            return item.globalRect.x, item.globalRect.y

        # Trying to sort an object that no longer exists,
        # return a dummy key value so this item is sorted last
        return CO_ORD_MAX

sort_util = SortUtil()


class MockableDisplayUtil:
    """Helper class to mock autopilot.display."""

    def __init__(self):
        self._mocked = False

    @contextmanager
    def mocked(self):
        """Enable mocking for MockableDisplayUtil class.

        One may use it like::

            display_util = MockableDisplayUtil()
            with display_util.mocked() as mocked_display_util:
                point = 120, 10
                self.assertTrue(
                    mocked_display_util.is_point_on_any_screen(point)
                )
        """
        try:
            self.enable_mock()
            yield self
        finally:
            self.disable_mock()

    def enable_mock(self):
        self._mocked = True

    def disable_mock(self):
        self._mocked = False

    def is_point_on_any_screen(self, point):
        if not self._mocked:
            return is_point_on_any_screen(point)
        else:
            return True

display_util = MockableDisplayUtil()
