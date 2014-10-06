# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2014 Canonical
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
from testtools.content_type import ContentType

from autopilot.testcase import AutopilotTestCase


class AutopilotTestCaseScreenshotTests(TestCase):
    def test_screenshot_taken_when_test_fails(self):
        class InnerTest(AutopilotTestCase):
            def test_foo(self):
                self.fail()

        test = InnerTest('test_foo')
        test_run = test.run()

        self.assertFalse(test_run.wasSuccessful())

        screenshot_content = test.getDetails()['FailedTestScreenshot']
        self.assertEqual(
            screenshot_content.content_type,
            ContentType("image", "png")
        )

    def test_take_screenshot(self):
        screenshot_name = self.getUniqueString()

        class InnerTest(AutopilotTestCase):
            def test_foo(self):
                self.take_screenshot(screenshot_name)

        test = InnerTest('test_foo')
        test_run = test.run()

        self.assertTrue(test_run.wasSuccessful())

        screenshot_content = test.getDetails()[screenshot_name]
        self.assertEqual(
            screenshot_content.content_type,
            ContentType("image", "png")
        )
