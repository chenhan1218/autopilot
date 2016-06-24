# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2016 Canonical
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

from autopilot.introspection import is_element
from autopilot.introspection.utilities import display_util, CO_ORD_MAX


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
        if is_element(item.refresh_state):
            return item.globalRect.y, item.globalRect.x

        # Trying to sort an object that no longer exists,
        # may cause sort() to fail, so we return a dummy
        # key value for this item to be sorted last.
        return CO_ORD_MAX

    def _get_x_and_y(self, item):
        """Return x and y co-ordinates for specified object.

        :param item: Item to check
        :return: (x, y) co-ordinates
        """
        if is_element(item.refresh_state):
            return item.globalRect.x, item.globalRect.y

        # Trying to sort an object that no longer exists,
        # may cause sort() to fail, so we return a dummy
        # key value for this item to be sorted last.
        return CO_ORD_MAX

sort_util = SortUtil()
