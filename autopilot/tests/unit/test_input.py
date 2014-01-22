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

    def test_press_key_should_emit_write_and_syn(self):
        keyboard = self._get_keyboard_with_mocked_backend()
        keyboard.press('KEY_A')
        self._assert_key_press_emitted_write_and_syn(keyboard, 'KEY_A')

    def _get_keyboard_with_mocked_backend(self):
        keyboard = _uinput._UInputKeyboardDevice(device_class=mock.Mock)
        keyboard._device.mock_add_spec(uinput.UInput, spec_set=True)
        return keyboard

    def _assert_key_press_emitted_write_and_syn(self, keyboard, key):
        self._assert_emitted_write_and_syn(keyboard, key, self._PRESS_VALUE)

    def _assert_emitted_write_and_syn(self, keyboard, key, value):
        key_ecode = ecodes.ecodes.get(key)
        expected_calls = [
            mock.call.write(ecodes.EV_KEY, key_ecode, value),
            mock.call.syn()
        ]

        self.assertEqual(expected_calls, keyboard._device.mock_calls)

    def test_press_key_should_append_leading_string(self):
        keyboard = self._get_keyboard_with_mocked_backend()
        keyboard.press('A')
        self._assert_key_press_emitted_write_and_syn(keyboard, 'KEY_A')

    def test_press_key_should_ignore_case(self):
        keyboard = self._get_keyboard_with_mocked_backend()
        keyboard.press('a')
        self._assert_key_press_emitted_write_and_syn(keyboard, 'KEY_A')

    def test_press_unexisting_key_should_raise_error(self):
        keyboard = self._get_keyboard_with_mocked_backend()
        error = self.assertRaises(
            ValueError, keyboard.press, 'unexisting')

        self.assertEqual('Unknown key name: unexisting.', str(error))

    def test_release_not_pressed_key_should_raise_error(self):
        keyboard = self._get_keyboard_with_mocked_backend()
        error = self.assertRaises(
            ValueError, keyboard.release, 'A')

        self.assertEqual("Key 'A' not pressed.", str(error))

    def test_release_key_should_emit_write_and_syn(self):
        keyboard = self._get_keyboard_with_mocked_backend()
        self._press_key_and_reset_mock(keyboard, 'KEY_A')

        keyboard.release('KEY_A')
        self._assert_key_release_emitted_write_and_syn(keyboard, 'KEY_A')

    def _press_key_and_reset_mock(self, keyboard, key):
        keyboard.press(key)
        keyboard._device.reset_mock()

    def _assert_key_release_emitted_write_and_syn(self, keyboard, key):
        self._assert_emitted_write_and_syn(keyboard, key, self._RELEASE_VALUE)

    def test_release_key_should_append_leading_string(self):
        keyboard = self._get_keyboard_with_mocked_backend()
        self._press_key_and_reset_mock(keyboard, 'KEY_A')

        keyboard.release('A')
        self._assert_key_release_emitted_write_and_syn(keyboard, 'KEY_A')

    def test_release_key_should_ignore_case(self):
        keyboard = self._get_keyboard_with_mocked_backend()
        self._press_key_and_reset_mock(keyboard, 'KEY_A')

        keyboard.release('a')
        self._assert_key_release_emitted_write_and_syn(keyboard, 'KEY_A')

    def test_release_unexisting_key_should_raise_error(self):
        keyboard = self._get_keyboard_with_mocked_backend()
        error = self.assertRaises(
            ValueError, keyboard.release, 'unexisting')

        self.assertEqual('Unknown key name: unexisting.', str(error))

    def test_release_pressed_keys_without_pressed_keys_should_do_nothing(self):
        keyboard = self._get_keyboard_with_mocked_backend()
        keyboard.release_pressed_keys()
        self.assertEqual([], keyboard._device.mock_calls)

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

        keyboard = self._get_keyboard_with_mocked_backend()
        self._press_key_and_reset_mock(keyboard, 'KEY_A')
        self._press_key_and_reset_mock(keyboard, 'KEY_B')

        keyboard.release_pressed_keys()

        self.assertEqual(expected_calls, keyboard._device.mock_calls)

    def test_release_pressed_keys_already_released(self):
        expected_calls = []
        keyboard = self._get_keyboard_with_mocked_backend()
        keyboard.press('KEY_A')
        keyboard.release_pressed_keys()
        keyboard._device.reset_mock()

        keyboard.release_pressed_keys()
        self.assertEqual(expected_calls, keyboard._device.mock_calls)


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
        # Mock the sleeps so we don't have to spend time actually sleeping.
        self.addCleanup(utilities.sleep.disable_mock)
        utilities.sleep.enable_mock()

    def _set_keyboard_device(self, device):
        _uinput.Keyboard._device = device

    def test_press(self):
        expected_calls = [
            mock.call.press(arg) for arg in self.expected_calls_args]
        keyboard = self._get_keyboard_with_mocked_backend()
        keyboard.press(self.keys)

        self.assertEqual(expected_calls, keyboard._device.mock_calls)

    def _get_keyboard_with_mocked_backend(self):
        _uinput.Keyboard._device = None
        keyboard = _uinput.Keyboard(device_class=mock.Mock)
        keyboard._device.mock_add_spec(
            _uinput._UInputKeyboardDevice, spec_set=True)
        return keyboard

    def test_release(self):
        keyboard = self._get_keyboard_with_mocked_backend()
        keyboard.press(self.keys)
        keyboard._device.reset_mock()

        expected_calls = [
            mock.call.release(arg) for arg in
            reversed(self.expected_calls_args)]
        keyboard.release(self.keys)

        self.assertEqual(
            expected_calls, keyboard._device.mock_calls)

    def test_press_and_release(self):
        expected_press_calls = [
            mock.call.press(arg) for arg in self.expected_calls_args]
        expected_release_calls = [
            mock.call.release(arg) for arg in
            reversed(self.expected_calls_args)]

        keyboard = self._get_keyboard_with_mocked_backend()
        keyboard.press_and_release(self.keys)

        self.assertEqual(
            expected_press_calls + expected_release_calls,
            keyboard._device.mock_calls)


class UInputTouchDeviceTestCase(TestCase):
    """Test the integration with evdev.UInput for the touch device."""

    def setUp(self):
        super(UInputTouchDeviceTestCase, self).setUp()
        self._number_of_slots = 9

        # Return to the original fingers after the test.
        self.addCleanup(
            self._set_fingers_in_use,
            _uinput._UInputTouchDevice._touch_fingers_in_use,
            _uinput._UInputTouchDevice._last_tracking_id)

        # Always start the tests without fingers in use.
        _uinput._UInputTouchDevice._touch_fingers_in_use = []
        _uinput._UInputTouchDevice._last_tracking_id = 0

    def _set_fingers_in_use(self, touch_fingers_in_use, last_tracking_id):
        _uinput._UInputTouchDevice._touch_fingers_in_use = touch_fingers_in_use
        _uinput._UInputTouchDevice._last_tracking_id = last_tracking_id

    def test_finger_down_should_use_free_slot(self):
        for slot in range(self._number_of_slots):
            touch = self._get_touch_with_mocked_backend()

            touch.finger_down(0, 0)

            self._assert_finger_down_emitted_write_and_syn(
                touch, slot=slot, tracking_id=mock.ANY, x=0, y=0)

    def _get_touch_with_mocked_backend(self):
        dummy_x_resolution = 100
        dummy_y_resolution = 100
        touch = _uinput._UInputTouchDevice(
            res_x=dummy_x_resolution, res_y=dummy_y_resolution,
            device_class=mock.Mock)
        touch._device.mock_add_spec(uinput.UInput, spec_set=True)
        return touch

    def _assert_finger_down_emitted_write_and_syn(
            self, touch, slot, tracking_id, x, y):
        press_value = 1
        expected_calls = [
            mock.call.write(ecodes.EV_ABS, ecodes.ABS_MT_SLOT, slot),
            mock.call.write(
                ecodes.EV_ABS, ecodes.ABS_MT_TRACKING_ID, tracking_id),
            mock.call.write(
                ecodes.EV_KEY, ecodes.BTN_TOOL_FINGER, press_value),
            mock.call.write(ecodes.EV_ABS, ecodes.ABS_MT_POSITION_X, x),
            mock.call.write(ecodes.EV_ABS, ecodes.ABS_MT_POSITION_Y, y),
            mock.call.write(ecodes.EV_ABS, ecodes.ABS_MT_PRESSURE, 400),
            mock.call.syn()
        ]
        self.assertEqual(expected_calls, touch._device.mock_calls)

    def test_finger_down_without_free_slots_should_raise_error(self):
        # Claim all the available slots.
        for slot in range(self._number_of_slots):
            touch = self._get_touch_with_mocked_backend()
            touch.finger_down(0, 0)

        touch = self._get_touch_with_mocked_backend()

        # Try to use one more.
        error = self.assertRaises(RuntimeError, touch.finger_down, 11, 11)
        self.assertEqual(
            'All available fingers have been used already.', str(error))

    def test_finger_down_should_use_unique_tracking_id(self):
        for number in range(self._number_of_slots):
            touch = self._get_touch_with_mocked_backend()
            touch.finger_down(0, 0)

            self._assert_finger_down_emitted_write_and_syn(
                touch, slot=mock.ANY, tracking_id=number + 1, x=0, y=0)

    def test_finger_down_should_not_reuse_tracking_ids(self):
        # Claim and release all the available slots once.
        for number in range(self._number_of_slots):
            touch = self._get_touch_with_mocked_backend()
            touch.finger_down(0, 0)
            touch.finger_up()

        touch = self._get_touch_with_mocked_backend()

        touch.finger_down(12, 12)
        self._assert_finger_down_emitted_write_and_syn(
            touch, slot=mock.ANY, tracking_id=number + 2, x=12, y=12)

    def test_finger_down_with_finger_pressed_should_raise_error(self):
        touch = self._get_touch_with_mocked_backend()
        touch.finger_down(0, 0)

        error = self.assertRaises(RuntimeError, touch.finger_down, 0, 0)
        self.assertEqual(
            "Cannot press finger: it's already pressed.", str(error))

    def test_finger_move_without_finger_pressed_should_raise_error(self):
        touch = self._get_touch_with_mocked_backend()

        error = self.assertRaises(RuntimeError, touch.finger_move, 10, 10)
        self.assertEqual(
            'Attempting to move without finger being down.', str(error))

    def test_finger_move_should_use_assigned_slot(self):
        for slot in range(self._number_of_slots):
            touch = self._get_touch_with_mocked_backend()
            touch.finger_down(0, 0)
            touch._device.reset_mock()

            touch.finger_move(10, 10)

            self._assert_finger_move_emitted_write_and_syn(
                touch, slot=slot, x=10, y=10)

    def _assert_finger_move_emitted_write_and_syn(self, touch, slot, x, y):
        expected_calls = [
            mock.call.write(ecodes.EV_ABS, ecodes.ABS_MT_SLOT, slot),
            mock.call.write(ecodes.EV_ABS, ecodes.ABS_MT_POSITION_X, x),
            mock.call.write(ecodes.EV_ABS, ecodes.ABS_MT_POSITION_Y, y),
            mock.call.syn()
        ]
        self.assertEqual(expected_calls, touch._device.mock_calls)

    def test_finger_move_should_reuse_assigned_slot(self):
        first_slot = 0
        touch = self._get_touch_with_mocked_backend()
        touch.finger_down(1, 1)
        touch._device.reset_mock()

        touch.finger_move(13, 13)
        self._assert_finger_move_emitted_write_and_syn(
            touch, slot=first_slot, x=13, y=13)
        touch._device.reset_mock()

        touch.finger_move(14, 14)
        self._assert_finger_move_emitted_write_and_syn(
            touch, slot=first_slot, x=14, y=14)

    def test_finger_up_without_finger_pressed_should_raise_error(self):
        touch = self._get_touch_with_mocked_backend()

        error = self.assertRaises(RuntimeError, touch.finger_up)
        self.assertEqual(
            "Cannot release finger: it's not pressed.", str(error))

    def test_finger_up_should_use_assigned_slot(self):
        fingers = []
        for slot in range(self._number_of_slots):
            touch = self._get_touch_with_mocked_backend()
            touch.finger_down(0, 0)
            touch._device.reset_mock()
            fingers.append(touch)

        for slot, touch in enumerate(fingers):
            touch.finger_up()

            self._assert_finger_up_emitted_write_and_syn(touch, slot=slot)

    def _assert_finger_up_emitted_write_and_syn(self, touch, slot):
        lift_tracking_id = -1
        release_value = 0
        expected_calls = [
            mock.call.write(ecodes.EV_ABS, ecodes.ABS_MT_SLOT, slot),
            mock.call.write(
                ecodes.EV_ABS, ecodes.ABS_MT_TRACKING_ID, lift_tracking_id),
            mock.call.write(
                ecodes.EV_KEY, ecodes.BTN_TOOL_FINGER, release_value),
            mock.call.syn()
        ]
        self.assertEqual(expected_calls, touch._device.mock_calls)

    def test_finger_up_should_release_slot(self):
        fingers = []
        # Claim all the available slots.
        for slot in range(self._number_of_slots):
            touch = self._get_touch_with_mocked_backend()
            touch.finger_down(0, 0)
            fingers.append(touch)

        slot_to_reuse = 3
        fingers[slot_to_reuse].finger_up()

        touch = self._get_touch_with_mocked_backend()

        # Try to use one more.
        touch.finger_down(15, 15)
        self._assert_finger_down_emitted_write_and_syn(
            touch, slot=slot_to_reuse, tracking_id=mock.ANY, x=15, y=15)

    def test_pressed_with_finger_down(self):
        touch = self._get_touch_with_mocked_backend()
        touch.finger_down(0, 0)

        self.assertTrue(touch.pressed)

    def test_pressed_without_finger_down(self):
        touch = self._get_touch_with_mocked_backend()
        self.assertFalse(touch.pressed)

    def test_pressed_after_finger_up(self):
        touch = self._get_touch_with_mocked_backend()
        touch.finger_down(0, 0)
        touch.finger_up()

        self.assertFalse(touch.pressed)

    def test_pressed_with_other_finger_down(self):
        other_touch = self._get_touch_with_mocked_backend()
        other_touch.finger_down(0, 0)

        touch = self._get_touch_with_mocked_backend()
        self.assertFalse(touch.pressed)


class UInputTouchTestCase(TestCase):
    """Test UInput Touch helper for autopilot tests."""

    def setUp(self):
        super(UInputTouchTestCase, self).setUp()
        self.touch = _uinput.Touch(device_class=mock.Mock)
        self.touch._device.mock_add_spec(
            _uinput._UInputTouchDevice, spec_set=True)
        # Mock the sleeps so we don't have to spend time actually sleeping.
        self.addCleanup(utilities.sleep.disable_mock)
        utilities.sleep.enable_mock()

    def test_tap(self):
        expected_calls = [
            mock.call.finger_down(0, 0),
            mock.call.finger_up()
        ]

        self.touch.tap(0, 0)
        self.assertEqual(expected_calls, self.touch._device.mock_calls)

    def test_tap_object(self):
        object_ = type('Dummy', (object,), {'globalRect': (0, 0, 10, 10)})
        expected_calls = [
            mock.call.finger_down(5, 5),
            mock.call.finger_up()
        ]

        self.touch.tap_object(object_)
        self.assertEqual(expected_calls, self.touch._device.mock_calls)

    def test_press(self):
        expected_calls = [mock.call.finger_down(0, 0)]

        self.touch.press(0, 0)
        self.assertEqual(expected_calls, self.touch._device.mock_calls)

    def test_release(self):
        expected_calls = [mock.call.finger_up()]

        self.touch.release()
        self.assertEqual(expected_calls, self.touch._device.mock_calls)

    def test_move(self):
        expected_calls = [mock.call.finger_move(10, 10)]

        self.touch.move(10, 10)
        self.assertEqual(expected_calls, self.touch._device.mock_calls)


class MultipleUInputTouchBackend(_uinput._UInputTouchDevice):

    def __init__(self, res_x=100, res_y=100, device_class=mock.Mock):
        super(MultipleUInputTouchBackend, self).__init__(
            res_x, res_y, device_class)


class MultipleUInputTouchTestCase(TestCase):

    def test_with_multiple_touch(self):
        finger1 = _uinput.Touch(device_class=MultipleUInputTouchBackend)
        finger2 = _uinput.Touch(device_class=MultipleUInputTouchBackend)

        finger1.press(0, 0)
        self.addCleanup(finger1.release)

        self.assertFalse(finger2.pressed)
