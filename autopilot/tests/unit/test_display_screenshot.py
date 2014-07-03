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

"""Unit tests for the display screenshot functionality."""

import subprocess
import tempfile
from testtools import TestCase
from testtools.matchers import Contains, Equals, MatchesRegex, Not, StartsWith
from textwrap import dedent
from unittest.mock import Mock, patch

import autopilot.display._screenshot as _ss
from autopilot.testcase import AutopilotTestCase


class ScreenShotTests(TestCase):

    def test_get_screenshot_data_raises_RuntimeError_on_unknown_display(self):
        self.assertRaises(RuntimeError, lambda: _ss.get_screenshot_data(""))

    def test_screenshot_taken_when_test_expected_fails(self):
        class InnerTest(AutopilotTestCase):
            def test_foo(self):
                self.fail()

        test = InnerTest('test_foo')
        test.take_screenshot = Mock()

        test_run = test.run()

        self.assertFalse(test_run.wasSuccessful())
        self.assertTrue(test.take_screenshot.called)

    def test_screenshot_taken_when_test_expected_fails(self):
        class InnerTest(AutopilotTestCase):
            def test_foo(self):
                self.fail()

        test = InnerTest('test_foo')
        test.take_screenshot = Mock()

        test_run = test.run()

        self.assertFalse(test_run.wasSuccessful())
        self.assertTrue(test.take_screenshot.called)

    def test_screenshot_not_taken_when_test_passes(self):
        class InnerTest(AutopilotTestCase):
            def test_foo(self):
                pass

        test = InnerTest('test_foo')
        test.take_screenshot = Mock()

        test_run = test.run()

        self.assertTrue(test_run.wasSuccessful())
        self.assertFalse(test.take_screenshot.called)

    def test_screenshot_not_taken_when_test_skipped(self):
        class InnerTest(AutopilotTestCase):
            def test_foo(self):
                self.skip("")

        test = InnerTest('test_foo')
        test.take_screenshot = Mock()

        test_run = test.run()

        self.assertTrue(test_run.wasSuccessful())
        self.assertFalse(test.take_screenshot.called)


class X11ScreenShotTests(TestCase):

    def test_is_x11_check_returns_True_on_success(self):
        with patch.object(_ss.subprocess, 'check_call'):
            self.assertTrue(_ss._display_is_x11())

    def test_is_x11_check_returns_True_on_failure(self):
        with patch.object(_ss.subprocess, 'check_call') as cc:
            cc.side_effect = FileNotFoundError
            self.assertFalse(_ss._display_is_x11())

    @patch.object(_ss, 'logger')
    def test_failing_x11_check_logs_message(self, patched_logger):
        with patch.object(_ss.subprocess, 'check_call') as cc:
            cc.side_effect = FileNotFoundError
            self.assertFalse(_ss._display_is_x11())
        patched_logger.debug.assert_called_once_with(
            "Checking for X11. xset command failed or not found."
        )

    def test_save_gdk_pixbuf_to_fileobject_raises_if_save_failed(self):
        pixbuf_obj = Mock()
        pixbuf_obj.save_to_bufferv.return_value = (False, None)

        self.assertRaises(
            RuntimeError,
            lambda: _ss._save_gdk_pixbuf_to_fileobject(pixbuf_obj)
        )

    @patch.object(_ss, 'logger')
    def test_save_gdk_pixbuf_to_fileobject_logs_if_save_failed(self, p_log):
        pixbuf_obj = Mock()
        pixbuf_obj.save_to_bufferv.return_value = (False, None)

        self.assertRaises(
            RuntimeError,
            lambda: _ss._save_gdk_pixbuf_to_fileobject(pixbuf_obj)
        )

        p_log.error.assert_called_once_with("Unable to write image data.")

    def test_save_gdk_pixbuf_to_fileobject_returns_data_object(self):
        expected_data = b"Tests Rock"
        pixbuf_obj = Mock()
        pixbuf_obj.save_to_bufferv.return_value = (True, expected_data)

        data_object = _ss._save_gdk_pixbuf_to_fileobject(pixbuf_obj)

        self.assertThat(data_object, Not(Equals(None)))
        self.assertEqual(data_object.tell(), 0)
        self.assertEqual(data_object.getvalue(), expected_data)


class MirScreenShotTests(TestCase):

    @patch.object(_ss.subprocess, 'check_output')
    def test_is_mir_check_returns_True_on_success(self, check_output):
        check_output.return_value = dedent("""
        32610 ?        S      0:00 [kworker/1:0]
         2017 ?        Sl     0:14 unity-system-compositor --spinner=/usr/bin/
        """)

        self.assertTrue(_ss._display_is_mir())

    @patch.object(_ss.subprocess, 'check_output')
    def test_is_mir_check_returns_False_on_success(self, check_output):
        check_output.return_value = ""
        self.assertFalse(_ss._display_is_mir())

    def test_take__screenshot_raises_when_binary_not_available(self):
        with patch.object(_ss.subprocess, 'check_call') as check_call:
            check_call.side_effect = FileNotFoundError()

            try:
                _ss._take_mirscreencast_screenshot()
                self.fail("No exception was raised")
            except FileNotFoundError as e:
                self.assertThat(
                    e.args,
                    Contains("The utility 'mirscreencast' is not available.")
                )
            else:
                self.fail("Expected exception was not caught")

    def test_take_screenshot_raises_when_screenshot_fails(self):
        with patch.object(_ss.subprocess, 'check_call') as check_call:
            check_call.side_effect = subprocess.CalledProcessError(None, None)

            try:
                _ss._take_mirscreencast_screenshot()
                self.fail("No exception was raised")
            except subprocess.CalledProcessError as e:
                self.assertThat(
                    e.args,
                    Contains("Failed to take screenshot.")
                )
            else:
                self.fail("Expected exception was not caught")

    def test_take_screenshot_returns_resulting_filename(self):
        with patch.object(_ss.subprocess, 'check_call'):
            self.assertThat(
                _ss._take_mirscreencast_screenshot(),
                MatchesRegex(".*ap-screenshot-data-\d+.rgba")
            )

    def test_take_screenshot_filepath_is_in_tmp_dir(self):
        with patch.object(_ss.subprocess, 'check_call'):
            self.assertThat(
                _ss._take_mirscreencast_screenshot(),
                StartsWith(tempfile.gettempdir())
            )

    @patch('autopilot.display._screenshot.open', create=True)
    def test_get_png_from_rgba_file_creates_png_image(self, p_open):
        file_path = self.getUniqueString()
        display_resolution = self.getUniqueInteger()

        with patch.object(_ss, 'Image') as p_image:
            _ss._get_png_from_rgba_file(file_path, display_resolution)
            p_image.frombuffer.assert_called_once_with(
                "RGBA",
                display_resolution,
                p_open.return_value.__enter__().read(),
                "raw",
                "RGBA",
                0,
                1
            )

    @patch('autopilot.display._screenshot.open', create=True)
    def test_get_png_from_rgba_file_returns_0_seek_fileobject(self, p_open):
        file_path = self.getUniqueString()
        display_resolution = self.getUniqueInteger()
        data = b"Testing Data"
        test_save = lambda d, **kw: d.write(data)

        with patch.object(_ss, 'Image') as p_image:
            p_image.frombuffer.return_value.save = test_save
            image_data = _ss._get_png_from_rgba_file(
                file_path,
                display_resolution
            )

            self.assertEqual(image_data.tell(), 0)
            self.assertEqual(image_data.getvalue(), data)
