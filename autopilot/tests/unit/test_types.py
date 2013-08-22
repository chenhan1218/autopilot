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

from datetime import datetime
from testscenarios import TestWithScenarios
from testtools import TestCase
from testtools.matchers import Equals, IsInstance, NotEquals
import dbus

from autopilot.introspection.types import (
    Color,
    DateTime,
    PlainType,
    Point,
    Rectangle,
    Size,
    Time
)


class FakeObject(object):

    def __init__(self):
        self.get_new_state_called = False
        self.set_properties_called = False

    def get_new_state(self):
        self.get_new_state_called = True

    def _set_properties(self, state):
        self.set_properties_called = True


class PlainTypeTests(TestWithScenarios, TestCase):

    scenarios = [
        ('bool true', dict(t=dbus.Boolean, v=True)),
        ('bool false', dict(t=dbus.Boolean, v=False)),
        ('int16 +ve', dict(t=dbus.Int16, v=123)),
        ('int16 -ve', dict(t=dbus.Int16, v=-23000)),
        ('int32 +ve', dict(t=dbus.Int32, v=30000000)),
        ('int32 -ve', dict(t=dbus.Int32, v=-3002050)),
        ('int64 +ve', dict(t=dbus.Int64, v=234234002050)),
        ('int64 -ve', dict(t=dbus.Int64, v=-234234002050)),
        ('string', dict(t=dbus.String, v="Hello World")),
    ]

    def test_can_construct(self):
        p = PlainType(self.t(self.v))

        self.assertThat(p, Equals(self.v))
        self.assertThat(hasattr(p, 'wait_for'), Equals(True))
        self.assertThat(p, IsInstance(self.t))


class RectangleTypeTests(TestCase):

    def test_can_construct_rectangle(self):
        r = Rectangle(1, 2, 3, 4)
        self.assertThat(r, IsInstance(dbus.Array))

    def test_rectangle_has_xywh_properties(self):
        r = Rectangle(1, 2, 3, 4)

        self.assertThat(r.x, Equals(1))
        self.assertThat(r.y, Equals(2))
        self.assertThat(r.w, Equals(3))
        self.assertThat(r.width, Equals(3))
        self.assertThat(r.h, Equals(4))
        self.assertThat(r.height, Equals(4))

    def test_rectangle_has_slice_access(self):
        r = Rectangle(1, 2, 3, 4)

        self.assertThat(r[0], Equals(1))
        self.assertThat(r[1], Equals(2))
        self.assertThat(r[2], Equals(3))
        self.assertThat(r[3], Equals(4))

    def test_equality_with_rectangle(self):
        r1 = Rectangle(1, 2, 3, 4)
        r2 = Rectangle(1, 2, 3, 4)

        self.assertThat(r1, Equals(r2))

    def test_equality_with_list(self):
        r1 = Rectangle(1, 2, 3, 4)
        r2 = [1, 2, 3, 4]

        self.assertThat(r1, Equals(r2))


class PointTypeTests(TestCase):

    def test_can_construct_point(self):
        r = Point(1, 2)
        self.assertThat(r, IsInstance(dbus.Array))

    def test_point_has_xy_properties(self):
        r = Point(1, 2)

        self.assertThat(r.x, Equals(1))
        self.assertThat(r.y, Equals(2))

    def test_point_has_slice_access(self):
        r = Point(1, 2)

        self.assertThat(r[0], Equals(1))
        self.assertThat(r[1], Equals(2))

    def test_equality_with_point(self):
        p1 = Point(1, 2)
        p2 = Point(1, 2)

        self.assertThat(p1, Equals(p2))

    def test_equality_with_list(self):
        p1 = Point(1, 2)
        p2 = [1, 2]

        self.assertThat(p1, Equals(p2))


class SizeTypeTests(TestCase):

    def test_can_construct_size(self):
        r = Size(1, 2)
        self.assertThat(r, IsInstance(dbus.Array))

    def test_size_has_wh_properties(self):
        r = Size(1, 2)

        self.assertThat(r.w, Equals(1))
        self.assertThat(r.width, Equals(1))
        self.assertThat(r.h, Equals(2))
        self.assertThat(r.height, Equals(2))

    def test_size_has_slice_access(self):
        r = Size(1, 2)

        self.assertThat(r[0], Equals(1))
        self.assertThat(r[1], Equals(2))

    def test_equality_with_size(self):
        s1 = Size(50, 100)
        s2 = Size(50, 100)

        self.assertThat(s1, Equals(s2))

    def test_equality_with_list(self):
        s1 = Size(50, 100)
        s2 = [50, 100]

        self.assertThat(s1, Equals(s2))


class ColorTypeTests(TestCase):

    def test_can_construct_color(self):
        r = Color(123, 234, 55, 255)
        self.assertThat(r, IsInstance(dbus.Array))

    def test_color_has_rgba_properties(self):
        r = Color(123, 234, 55, 255)

        self.assertThat(r.red, Equals(123))
        self.assertThat(r.green, Equals(234))
        self.assertThat(r.blue, Equals(55))
        self.assertThat(r.alpha, Equals(255))

    def test_color_has_slice_access(self):
        r = Color(123, 234, 55, 255)

        self.assertThat(r[0], Equals(123))
        self.assertThat(r[1], Equals(234))
        self.assertThat(r[2], Equals(55))
        self.assertThat(r[3], Equals(255))

    def test_eqiality_with_color(self):
        c1 = Color(123, 234, 55, 255)
        c2 = Color(123, 234, 55, 255)

        self.assertThat(c1, Equals(c2))

    def test_eqiality_with_list(self):
        c1 = Color(123, 234, 55, 255)
        c2 = [123, 234, 55, 255]

        self.assertThat(c1, Equals(c2))


class DateTimeTests(TestCase):

    def test_can_construct_datetime(self):
        dt = DateTime(1377209927)
        self.assertThat(dt, IsInstance(dbus.Array))

    def test_datetime_has_slice_access(self):
        dt = DateTime(1377209927)

        self.assertThat(dt[0], Equals(1377209927))

    def test_datetime_has_properties(self):
        dt = DateTime(1377209927)

        self.assertThat(dt.timestamp, Equals(1377209927))
        self.assertThat(dt.year, Equals(2013))
        self.assertThat(dt.month, Equals(8))
        self.assertThat(dt.day, Equals(22))
        self.assertThat(dt.hour, Equals(22))
        self.assertThat(dt.minute, Equals(18))
        self.assertThat(dt.second, Equals(47))

    def test_equality_with_datetime(self):
        dt1 = DateTime(1377209927)
        dt2 = DateTime(1377209927)

        self.assertThat(dt1, Equals(dt2))

    def test_equality_with_list(self):
        dt1 = DateTime(1377209927)
        dt2 = [1377209927]

        self.assertThat(dt1, Equals(dt2))

    def test_equality_with_datetime(self):
        dt1 = DateTime(1377209927)
        dt2 = datetime.utcfromtimestamp(1377209927)
        dt3 = datetime.utcfromtimestamp(1377209928)

        self.assertThat(dt1, Equals(dt2))
        self.assertThat(dt1, NotEquals(dt3))

