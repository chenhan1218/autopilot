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

from testscenarios import TestWithScenarios
from testtools import TestCase
from testtools.matchers import Equals, IsInstance
import dbus

from autopilot.introspection.types import (
    PlainType,
    Rectangle,
    Point,
    Size,
    Color,
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
        """Must be able to create a PlainType instance from a parent instance."""
        obj = FakeObject()
        p = PlainType(self.t(self.v))

        self.assertThat(p, Equals(self.v))
        self.assertThat(hasattr(p, 'wait_for'), Equals(True))
        self.assertThat(p, IsInstance(self.t))



class RectangleTypeTests(TestCase):

    def test_can_construct_rectangle(self):
        obj = FakeObject()
        r = Rectangle([1,2,3,4])
        self.assertThat(r, IsInstance(dbus.Array))

    def test_rectangle_has_xywh_properties(self):
        obj = FakeObject()
        r = Rectangle([1,2,3,4])

        self.assertThat(r.x, Equals(1))
        self.assertThat(r.y, Equals(2))
        self.assertThat(r.w, Equals(3))
        self.assertThat(r.h, Equals(4))

    def test_rectangle_has_slice_access(self):
        obj = FakeObject()
        r = Rectangle([1,2,3,4])

        self.assertThat(r[0], Equals(1))
        self.assertThat(r[1], Equals(2))
        self.assertThat(r[2], Equals(3))
        self.assertThat(r[3], Equals(4))


class PointTypeTests(TestCase):

    def test_can_construct_point(self):
        r = Point([1,2,3,4])
        self.assertThat(r, IsInstance(dbus.Array))

    def test_point_has_xy_properties(self):
        r = Point([1,2])

        self.assertThat(r.x, Equals(1))
        self.assertThat(r.y, Equals(2))

    def test_point_has_slice_access(self):
        r = Point([1,2])

        self.assertThat(r[0], Equals(1))
        self.assertThat(r[1], Equals(2))


class SizeTypeTests(TestCase):

    def test_can_construct_size(self):
        r = Size([1,2,3,4])
        self.assertThat(r, IsInstance(dbus.Array))

    def test_size_has_wh_properties(self):
        r = Size([1,2])

        self.assertThat(r.w, Equals(1))
        self.assertThat(r.h, Equals(2))

    def test_size_has_slice_access(self):
        r = Size([1,2])

        self.assertThat(r[0], Equals(1))
        self.assertThat(r[1], Equals(2))



class ColorTypeTests(TestCase):

    def test_can_construct_color(self):
        r = Color([123,234,55,255])
        self.assertThat(r, IsInstance(dbus.Array))

    def test_color_has_rgba_properties(self):
        r = Color([123,234,55,255])

        self.assertThat(r.red, Equals(123))
        self.assertThat(r.green, Equals(234))
        self.assertThat(r.blue, Equals(55))
        self.assertThat(r.alpha, Equals(255))

    def test_color_has_slice_access(self):
        r = Color([123,234,55,255])

        self.assertThat(r[0], Equals(123))
        self.assertThat(r[1], Equals(234))
        self.assertThat(r[2], Equals(55))
        self.assertThat(r[3], Equals(255))
