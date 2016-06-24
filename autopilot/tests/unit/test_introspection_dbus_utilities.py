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

from autopilot.introspection.dbus_utilities import sort_util
from autopilot.introspection.utilities import display_util
from autopilot.tests.unit.introspection_base import get_mock_object

# A list containing a single coordinate parameter in a sequence
DUMMY_COORDS = [15, 1, 20]


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
