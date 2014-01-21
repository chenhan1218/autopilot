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

import mock
import testscenarios
from evdev import ecodes, uinput
from testtools import TestCase
from testtools.matchers import raises

from autopilot.input import _uinput
from autopilot.input._common import get_center_point
from autopilot import utilities


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

    @mock.patch('autopilot.input._common.logger')
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

    @mock.patch('autopilot.input._common.logger')
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

    @mock.patch('autopilot.input._common.logger')
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


class UInputKeyboardDeviceTestCase(TestCase):
    """Test the integration with evdev.UInput for the keyboard."""

    _PRESS_VALUE = 1
    _RELEASE_VALUE = 0

    def setUp(self):
        super(UInputKeyboardDeviceTestCase, self).setUp()
        self.keyboard = _uinput._UInputKeyboardDevice(device_class=mock.Mock)
        self.keyboard._device.mock_add_spec(uinput.UInput, spec_set=True)

    def test_press_key_should_emit_write_and_syn(self):
        self.keyboard.press('KEY_A')
        self._assert_key_press_emitted_write_and_syn('KEY_A')

    def _assert_key_press_emitted_write_and_syn(self, key):
        self._assert_emitted_write_and_syn(key, self._PRESS_VALUE)

    def _assert_emitted_write_and_syn(self, key, value):
        key_ecode = ecodes.ecodes.get(key)
        expected_calls = [
            mock.call.write(ecodes.EV_KEY, key_ecode, value),
            mock.call.syn()
        ]

        self.assertEqual(expected_calls, self.keyboard._device.mock_calls)

    def test_press_key_should_append_leading_string(self):
        self.keyboard.press('A')
        self._assert_key_press_emitted_write_and_syn('KEY_A')

    def test_press_key_should_ignore_case(self):
        self.keyboard.press('a')
        self._assert_key_press_emitted_write_and_syn('KEY_A')

    def test_press_unexisting_key_should_raise_error(self):
        error = self.assertRaises(
            ValueError, self.keyboard.press, 'unexisting')

        self.assertEqual('Unknown key name: unexisting.', str(error))

    def test_release_not_pressed_key_should_raise_error(self):
        error = self.assertRaises(
            ValueError, self.keyboard.release, 'A')

        self.assertEqual("Key 'A' not pressed.", str(error))

    def test_release_key_should_emit_write_and_syn(self):
        self._press_key_and_reset_mock('KEY_A')

        self.keyboard.release('KEY_A')
        self._assert_key_release_emitted_write_and_syn('KEY_A')

    def _press_key_and_reset_mock(self, key):
        self.keyboard.press(key)
        self.keyboard._device.reset_mock()

    def _assert_key_release_emitted_write_and_syn(self, key):
        self._assert_emitted_write_and_syn(key, self._RELEASE_VALUE)

    def test_release_key_should_append_leading_string(self):
        self._press_key_and_reset_mock('KEY_A')

        self.keyboard.release('A')
        self._assert_key_release_emitted_write_and_syn('KEY_A')

    def test_release_key_should_ignore_case(self):
        self._press_key_and_reset_mock('KEY_A')

        self.keyboard.release('a')
        self._assert_key_release_emitted_write_and_syn('KEY_A')

    def test_release_unexisting_key_should_raise_error(self):
        error = self.assertRaises(
            ValueError, self.keyboard.release, 'unexisting')

        self.assertEqual('Unknown key name: unexisting.', str(error))

    def test_release_pressed_keys_without_pressed_keys_should_do_nothing(self):
        self.keyboard.release_pressed_keys()
        self.assertEqual([], self.keyboard._device.mock_calls)

    def test_release_pressed_keys_with_pressed_keys(self):
        expected_calls = [
            mock.call.write(
                ecodes.EV_KEY, ecodes.ecodes.get('KEY_A'),
                self._RELEASE_VALUE),
            mock.call.syn(),
            mock.call.write(
                ecodes.EV_KEY, ecodes.ecodes.get('KEY_B'),
                self._RELEASE_VALUE),
            mock.call.syn()
        ]

        self._press_key_and_reset_mock('KEY_A')
        self._press_key_and_reset_mock('KEY_B')

        self.keyboard.release_pressed_keys()

        self.assertEqual(expected_calls, self.keyboard._device.mock_calls)


class UInputKeyboardTestCase(testscenarios.TestWithScenarios, TestCase):
    """Test UInput Keyboard helper for autopilot tests."""

    scenarios = [
        ('single key', dict(keys='a', expected_calls_args=['a'])),
        ('upper-case letter', dict(
            keys='A', expected_calls_args=['KEY_LEFTSHIFT', 'A'])),
        ('key combination', dict(
            keys='a+b', expected_calls_args=['a', 'b']))
    ]

    def setUp(self):
        super(UInputKeyboardTestCase, self).setUp()
        # Return to the original device after the test.
        self.addCleanup(self._set_keyboard_device, _uinput.Keyboard._device)
        self.keyboard = _uinput.Keyboard(device_class=mock.Mock)
        self.keyboard._device.mock_add_spec(
            _uinput._UInputKeyboardDevice, spec_set=True)
        # Mock the sleeps so we don't have to spend time actually sleeping.
        self.addCleanup(utilities.sleep.disable_mock)
        utilities.sleep.enable_mock()

        self.keyboard._device.reset_mock()

    def _set_keyboard_device(self, device):
        _uinput.Keyboard._device = device

    def test_press(self):
        expected_calls = [
            mock.call.press(arg) for arg in self.expected_calls_args]
        self.keyboard.press(self.keys)

        self.assertEqual(expected_calls, self.keyboard._device.mock_calls)

    def test_release(self):
        self.keyboard.press(self.keys)
        self.keyboard._device.reset_mock()

        expected_calls = [
            mock.call.release(arg) for arg in
            reversed(self.expected_calls_args)]
        self.keyboard.release(self.keys)

        self.assertEqual(
            expected_calls, self.keyboard._device.mock_calls)

    def test_press_and_release(self):
        expected_press_calls = [
            mock.call.press(arg) for arg in self.expected_calls_args]
        expected_release_calls = [
            mock.call.release(arg) for arg in
            reversed(self.expected_calls_args)]

        self.keyboard.press_and_release(self.keys)

        self.assertEqual(
            expected_press_calls + expected_release_calls,
            self.keyboard._device.mock_calls)
