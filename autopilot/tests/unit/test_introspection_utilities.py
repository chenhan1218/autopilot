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

from testtools import TestCase

from autopilot.introspection.dbus import raises
from autopilot.introspection.utilities import (
    display_util,
    process_util,
    sort_util,
)

from autopilot.tests.unit.introspection_base import get_mock_object


PROCESS_NAME = 'dummy_process'
PROCESS_WITH_SINGLE_INSTANCE = [{'name': PROCESS_NAME, 'pid': -80}]
PROCESS_WITH_MULTIPLE_INSTANCES = [
    PROCESS_WITH_SINGLE_INSTANCE[0],
    {'name': PROCESS_NAME, 'pid': -81}
]

# A list containing a single coordinate parameter in a sequence
DUMMY_COORDS = [15, 1, 20]


class ProcessUtilitiesTestCase(TestCase):

    def test_passing_non_running_process_raises(self):
        self.assertRaises(
            ValueError,
            process_util._query_pids_for_process,
            PROCESS_NAME
        )

    def test_passing_running_process_not_raises(self):
        with process_util.mocked(PROCESS_WITH_SINGLE_INSTANCE):
            self.assertFalse(
                raises(
                    ValueError,
                    process_util._query_pids_for_process,
                    PROCESS_NAME
                )
            )

    def test_passing_integer_raises(self):
        self.assertRaises(
            ValueError,
            process_util._query_pids_for_process,
            911
        )

    def test_pid_for_process_is_int(self):
        with process_util.mocked(PROCESS_WITH_SINGLE_INSTANCE):
            self.assertIsInstance(
                process_util.get_pid_for_process(PROCESS_NAME),
                int
            )

    def test_pids_for_process_is_list(self):
        with process_util.mocked(PROCESS_WITH_MULTIPLE_INSTANCES):
            self.assertIsInstance(
                process_util.get_pids_for_process(PROCESS_NAME),
                list
            )

    def test_passing_process_with_multiple_pids_raises(self):
        with process_util.mocked(PROCESS_WITH_MULTIPLE_INSTANCES):
            self.assertRaises(
                ValueError,
                process_util.get_pid_for_process,
                PROCESS_NAME
            )


class SortUtilitiesTestCase(TestCase):

    def _get_x_cordinates_from_object_list(self, objects):
        return [obj.globalRect.x for obj in objects]

    def _get_y_cordinates_from_object_list(self, objects):
        return [obj.globalRect.y for obj in objects]

    def test_sort_by_x(self):
        objects = [get_mock_object(x=x) for x in DUMMY_COORDS]
        with display_util.mocked():
            sorted_objects = sort_util.order_by_x_coord(objects)
            self.assertEquals(len(sorted_objects), len(DUMMY_COORDS))
            self.assertEquals(
                self._get_x_cordinates_from_object_list(sorted_objects),
                sorted(DUMMY_COORDS)
            )

    def test_sort_by_y(self):
        objects = [get_mock_object(y=y) for y in DUMMY_COORDS]
        with display_util.mocked():
            sorted_objects = sort_util.order_by_y_coord(objects)
            self.assertEquals(len(sorted_objects), len(DUMMY_COORDS))
            self.assertEquals(
                self._get_y_cordinates_from_object_list(sorted_objects),
                sorted(DUMMY_COORDS)
            )
