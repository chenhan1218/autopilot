# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2013, 2014 Canonical
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

import testscenarios

from mock import call, Mock, patch
from testtools import TestCase
from testtools.matchers import raises

from autopilot.input import _uinput, _X11
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


class X11MouseTestCase(TestCase):

    def setUp(self):
        super(X11MouseTestCase, self).setUp()
        self.mouse = _X11.Mouse()

    def test_drag_should_call_move_with_rate(self):
        expected_first_move_call = call(0, 0)
        expected_second_move_call = call(100, 100, rate=1)
        with patch.object(self.mouse, 'move') as mock_move:
            self.mouse.drag(0, 0, 100, 100, rate=1)

        self.assertEqual(
            [expected_first_move_call, expected_second_move_call],
            mock_move.call_args_list)

    def test_drag_with_default_rate(self):
        expected_first_move_call = call(0, 0)
        expected_second_move_call = call(100, 100, rate=10)
        with patch.object(self.mouse, 'move') as mock_move:
            self.mouse.drag(0, 0, 100, 100)

        self.assertEqual(
            [expected_first_move_call, expected_second_move_call],
            mock_move.call_args_list)


class MockTouch(object):

    def __init__(self):
        super(MockTouch, self).__init__()
        self._mock_manager = Mock()
        self._real_touch = _uinput.Touch()

    def __getattr__(self, name):
        return self._real_touch.__getattribute__(name)

    @property
    def mock_calls(self):
        return self._mock_manager.mock_calls

    def __enter__(self):
        self._start_finger_patchers()
        return self

    def _start_finger_patchers(self):
        self._finger_down_patcher = patch.object(
            self._real_touch, '_finger_down')
        self._mock_manager.attach_mock(
            self._finger_down_patcher.start(), '_finger_down')

        self._finger_up_patcher = patch.object(self._real_touch, '_finger_up')
        self._mock_manager.attach_mock(
            self._finger_up_patcher.start(), '_finger_up')

        self._finger_move_patcher = patch.object(
            self._real_touch, '_finger_move')
        self._mock_manager.attach_mock(
            self._finger_move_patcher.start(), '_finger_move')

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._stop_finger_patchers()

    def _stop_finger_patchers(self):
        self._finger_down_patcher.stop()
        self._finger_up_patcher.stop()
        self._finger_move_patcher.stop()

    def get_finger_move_call_args_list(self):
        return self._mock_manager._finger_move.call_args_list


class UinputTouchTestCase(TestCase):

    def test_drag_finger_actions(self):
        expected_finger_calls = [
            call._finger_down(0, 0),
            call._finger_move(10, 10),
            call._finger_up()
        ]
        with MockTouch() as mock_touch:
            mock_touch.drag(0, 0, 10, 10)
        self.assertEqual(mock_touch.mock_calls, expected_finger_calls)

    def test_drag_should_call_move_with_rate(self):
        expected_move_calls = [call(5, 5), call(10, 10), call(15, 15)]
        with MockTouch() as mock_touch:
            mock_touch.drag(0, 0, 15, 15, rate=5)

        self.assertEqual(
            expected_move_calls, mock_touch.get_finger_move_call_args_list())

    def test_drag_with_default_rate(self):
        expected_move_calls = [call(10, 10), call(20, 20)]
        with MockTouch() as mock_touch:
            mock_touch.drag(0, 0, 20, 20)

        self.assertEqual(
            expected_move_calls, mock_touch.get_finger_move_call_args_list())

    def test_drag_to_same_place_should_not_move(self):
        expected_finger_calls = [
            call._finger_down(0, 0),
            call._finger_up()
        ]
        with MockTouch() as mock_touch:
            mock_touch.drag(0, 0, 0, 0)
        self.assertEqual(mock_touch.mock_calls, expected_finger_calls)


class DragUinputTouchTestCase(testscenarios.TestWithScenarios, TestCase):

    scenarios = [
        ('drag to top', dict(
            start_x=50, start_y=50, stop_x=50, stop_y=30,
            expected_moves=[call(50, 40), call(50, 30)])),
        ('drag to bottom', dict(
            start_x=50, start_y=50, stop_x=50, stop_y=70,
            expected_moves=[call(50, 60), call(50, 70)])),
        ('drag to left', dict(
            start_x=50, start_y=50, stop_x=30, stop_y=50,
            expected_moves=[call(40, 50), call(30, 50)])),
        ('drag to right', dict(
            start_x=50, start_y=50, stop_x=70, stop_y=50,
            expected_moves=[call(60, 50), call(70, 50)])),

        ('drag to top-left', dict(
            start_x=50, start_y=50, stop_x=30, stop_y=30,
            expected_moves=[call(40, 40), call(30, 30)])),
        ('drag to top-right', dict(
            start_x=50, start_y=50, stop_x=70, stop_y=30,
            expected_moves=[call(60, 40), call(70, 30)])),
        ('drag to bottom-left', dict(
            start_x=50, start_y=50, stop_x=30, stop_y=70,
            expected_moves=[call(40, 60), call(30, 70)])),
        ('drag to bottom-right', dict(
            start_x=50, start_y=50, stop_x=70, stop_y=70,
            expected_moves=[call(60, 60), call(70, 70)])),

        ('drag less than rate', dict(
            start_x=50, start_y=50, stop_x=55, stop_y=55,
            expected_moves=[call(55, 55)])),

        ('drag with last move less than rate', dict(
            start_x=50, start_y=50, stop_x=65, stop_y=65,
            expected_moves=[call(60, 60), call(65, 65)])),
    ]

    def test_drag_moves(self):
        with MockTouch() as mock_touch:
            mock_touch.drag(
                self.start_x, self.start_y, self.stop_x, self.stop_y)

        self.assertEqual(
            self.expected_moves, mock_touch.get_finger_move_call_args_list())
