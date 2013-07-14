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


from testtools import TestCase
from testtools.matchers import Equals, raises
from mock import patch

from autopilot.input import Pointer, Mouse


class Empty(object):
    pass


def make_fake_object(globalRect=False, center=False, xywh=False):
    obj = Empty()
    if globalRect:
        obj.globalRect = (0, 0, 100, 100)
    if center:
        obj.center_x = 123
        obj.center_y = 345
    if xywh:
        obj.x, obj.y, obj.w, obj.h = (100, 100, 20, 40)
    return obj


class MouseEmulatorTests(TestCase):
    """Tests for the autopilot mouse emulator."""

    def setUp(self):
        super(MouseEmulatorTests, self).setUp()
        self.mouse = Pointer(Mouse.create())

    def tearDown(self):
        super(MouseEmulatorTests, self).tearDown()
        self.mouse = None

    def test_x_y_properties(self):
        """x and y properties must simply return values from the position()
        method."""
        with patch.object(
                self.mouse._device, 'position', return_value=(42, 37)):
            self.assertThat(self.mouse.x, Equals(42))
            self.assertThat(self.mouse.y, Equals(37))

    def test_move_to_object_raises_valueError_on_empty_object(self):
        """Passing an empty object to move_to_object must raise ValueError."""
        obj = make_fake_object()
        fn = lambda: self.mouse.move_to_object(obj)
        expected_exception = ValueError(
            "Object '%r' does not have any recognised position attributes" %
            obj)
        self.assertThat(fn, raises(expected_exception))

    def test_move_to_object_works_with_globalRect_only(self):
        """move_to_object must move to the coordinates set in globalRect
        attribute."""
        obj = make_fake_object(globalRect=True)
        with patch.object(self.mouse, 'move') as move_patch:
            self.mouse.move_to_object(obj)
            move_patch.assert_called_once_with(50, 50)

    def test_move_to_object_works_with_center_only(self):
        """move_to_object must move to the coordinates set in the center_x,
        center_y attributes."""
        obj = make_fake_object(center=True)
        with patch.object(self.mouse, 'move') as move_patch:
            self.mouse.move_to_object(obj)
            move_patch.assert_called_once_with(123, 345)

    def test_move_to_object_works_with_x_y_w_h_only(self):
        """move_to_object must move to the coordinates set in the x, y, w & h
        attributes."""
        obj = make_fake_object(xywh=True)
        with patch.object(self.mouse, 'move') as move_patch:
            self.mouse.move_to_object(obj)
            move_patch.assert_called_once_with(110, 120)

    def test_move_to_object_prefers_globalRect(self):
        """move_to_object must prefer globalRect over the other attributes."""
        obj = make_fake_object(globalRect=True, center=True, xywh=True)
        with patch.object(self.mouse, 'move') as move_patch:
            self.mouse.move_to_object(obj)
            move_patch.assert_called_once_with(50, 50)

    def test_move_to_object_prefers_center(self):
        """move_to_object must prefer center_[xy] to the xywh attributes."""
        obj = make_fake_object(globalRect=False, center=True, xywh=True)
        with patch.object(self.mouse, 'move') as move_patch:
            self.mouse.move_to_object(obj)
            move_patch.assert_called_once_with(123, 345)
