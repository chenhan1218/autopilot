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


from __future__ import absolute_import

from autopilot.testcase import AutopilotTestCase
from testtools.matchers import raises
from mock import patch


class ApplicationSupportTests(AutopilotTestCase):

    def test_launch_with_bad_types_raises_typeerror(self):
        """Calling launch_test_application with something other than a string
        must raise a TypeError"""

        self.assertThat(
            lambda: self.launch_test_application(1), raises(TypeError))
        self.assertThat(
            lambda: self.launch_test_application(True), raises(TypeError))
        self.assertThat(
            lambda: self.launch_test_application(1.0), raises(TypeError))
        self.assertThat(
            lambda: self.launch_test_application(object()), raises(TypeError))
        self.assertThat(
            lambda: self.launch_test_application(None), raises(TypeError))
        self.assertThat(
            lambda: self.launch_test_application([]), raises(TypeError))
        self.assertThat(
            lambda: self.launch_test_application((None,)), raises(TypeError))

    def test_launch_raises_ValueError_on_unknown_kwargs(self):
        """launch_test_application must raise ValueError when given unknown
        keyword arguments.

        """
        fn = lambda: self.launch_test_application(
            'gedit', arg1=123, arg2='asd')
        self.assertThat(
            fn,
            raises(ValueError("Unknown keyword arguments: 'arg1', 'arg2'.")))

    def test_launch_raises_ValueError_on_unknown_kwargs_with_known(self):
        """launch_test_application must raise ValueError when given unknown
        keyword arguments.

        """
        fn = lambda: self.launch_test_application(
            'gedit', arg1=123, arg2='asd', launch_dir='/')
        self.assertThat(
            fn,
            raises(ValueError("Unknown keyword arguments: 'arg1', 'arg2'.")))

    @patch('autopilot.testcase._get_click_manifest', new=lambda: [])
    def test_launch_click_package_raises_runtimeerror_on_missing_package(self):
        """launch_click_package must raise a RuntimeError if the requested
        package id is not found in the click manifest.

        """
        fn = lambda: self.launch_click_package("com.ubuntu.something")
        self.assertThat(
            fn,
            raises(
                RuntimeError(
                    "Unable to find package 'com.ubuntu.something' in the "
                    "click manifest."
                )
            )
        )

    @patch('autopilot.testcase._get_click_manifest')
    def test_launch_click_package_raises_runtimeerror_on_wrong_app(self, cm):
        """launch_click_package must raise a RuntimeError if the requested
        package id is not found in the click manifest.

        """
        cm.return_value = [{'name': 'foo', 'hooks': {}}]
        fn = lambda: self.launch_click_package("foo", "bar")
        self.assertThat(
            fn,
            raises(
                RuntimeError(
                    "Application 'bar' is not present within the click package"
                    " 'foo'."
                )
            )
        )
