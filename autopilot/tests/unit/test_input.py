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
from testtools.matchers import raises

from autopilot.input._common import get_center_point


class Empty(object):

    def __repr__(self):
        return "<Empty>"


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


class InputCenterPointTests(TestCase):
    """Tests for the input get_center_point utility."""

    def test_get_center_point_raises_ValueError_on_empty_object(self):
        obj = make_fake_object()
        fn = lambda: get_center_point(obj)
        expected_exception = ValueError(
            "Object '%r' does not have any recognised position attributes" %
            obj)
        self.assertThat(fn, raises(expected_exception))

    def test_get_center_point_works_with_globalRect(self):
        obj = make_fake_object(globalRect=True)
        x, y = get_center_point(obj)

        self.assertEqual(50, x)
        self.assertEqual(50, y)

    def test_raises_ValueError_on_uniterable_globalRect(self):
        obj = Empty()
        obj.globalRect = 123
        expected_exception = ValueError(
            "Object '<Empty>' has globalRect attribute, but it is not of the "
            "correct type"
        )
        self.assertThat(
            lambda: get_center_point(obj),
            raises(expected_exception)
        )

    def test_raises_ValueError_on_too_small_globalRect(self):
        obj = Empty()
        obj.globalRect = (1, 2, 3)
        expected_exception = ValueError(
            "Object '<Empty>' has globalRect attribute, but it is not of the "
            "correct type"
        )
        self.assertThat(
            lambda: get_center_point(obj),
            raises(expected_exception)
        )

    @patch('autopilot.input._common.logger')
    def test_get_center_point_logs_with_globalRect(self, mock_logger):
        obj = make_fake_object(globalRect=True)
        x, y = get_center_point(obj)

        mock_logger.debug.assert_called_once_with(
            "Moving to object's globalRect coordinates."
        )

    def test_get_center_point_works_with_center_points(self):
        obj = make_fake_object(center=True)
        x, y = get_center_point(obj)

        self.assertEqual(123, x)
        self.assertEqual(345, y)

    @patch('autopilot.input._common.logger')
    def test_get_center_point_logs_with_center_points(self, mock_logger):
        obj = make_fake_object(center=True)
        x, y = get_center_point(obj)

        mock_logger.debug.assert_called_once_with(
            "Moving to object's center_x, center_y coordinates."
        )

    def test_get_center_point_works_with_xywh(self):
        obj = make_fake_object(xywh=True)
        x, y = get_center_point(obj)

        self.assertEqual(110, x)
        self.assertEqual(120, y)

    @patch('autopilot.input._common.logger')
    def test_get_center_point_logs_with_xywh(self, mock_logger):
        obj = make_fake_object(xywh=True)
        x, y = get_center_point(obj)

        mock_logger.debug.assert_called_once_with(
            "Moving to object's center point calculated from x,y,w,h "
            "attributes."
        )

    def test_get_center_point_raises_valueError_on_non_numerics(self):
        obj = Empty()
        obj.x, obj.y, obj.w, obj.h = 1, None, True, "oof"
        expected_exception = ValueError(
            "Object '<Empty>' has x,y attribute, but they are not of the "
            "correct type"
        )
        self.assertThat(
            lambda: get_center_point(obj),
            raises(expected_exception)
        )

    def test_get_center_point_prefers_globalRect(self):
        obj = make_fake_object(globalRect=True, center=True, xywh=True)
        x, y = get_center_point(obj)

        self.assertEqual(50, x)
        self.assertEqual(50, y)

    def test_get_center_point_prefers_center_points(self):
        obj = make_fake_object(globalRect=False, center=True, xywh=True)
        x, y = get_center_point(obj)

        self.assertEqual(123, x)
        self.assertEqual(345, y)
