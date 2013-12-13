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

from testtools import TestCase
from testtools.matchers import Not, raises
from mock import Mock, patch

from autopilot.application import ClickApplicationLauncher
from autopilot.application._launcher import (
    _get_click_app_id,
    _raise_if_not_empty,
)


class ApplicationLauncherTests(TestCase):
    pass


class ClickApplicationLauncherTests(TestCase):

    def test_raises_exception_on_unknown_kwargs(self):
        self.assertThat(
            lambda: ClickApplicationLauncher(Mock(), unknown=True),
            raises(ValueError("Unknown keyword arguments: 'unknown'."))
        )

    @patch(
        'autopilot.application._launcher._get_click_manifest', new=lambda: [])
    def test_get_click_app_id_raises_runtimeerror_on_missing_package(self):
        """_get_click_app_id must raise a RuntimeError if the requested
        package id is not found in the click manifest.

        """
        self.assertThat(
            lambda: _get_click_app_id("com.autopilot.testing"),
            raises(
                RuntimeError(
                    "Unable to find package 'com.autopilot.testing' in the "
                    "click manifest."
                )
            )
        )

    @patch('autopilot.application._launcher._get_click_manifest')
    def test_get_click_app_id_raises_runtimeerror_on_wrong_app(self, cm):
        """get_click_app_id must raise a RuntimeError if the requested
        application is not found within the click package.

        """
        cm.return_value = [{'name': 'com.autopilot.testing', 'hooks': {}}]

        self.assertThat(
            lambda: _get_click_app_id("com.autopilot.testing", "bar"),
            raises(
                RuntimeError(
                    "Application 'bar' is not present within the click package"
                    " 'com.autopilot.testing'."
                )
            )
        )


class ApplicationLauncherInternalTests(TestCase):

    def test_raise_if_not_empty_raises_on_nonempty_dict(self):
        populated_dict = dict(testing=True)
        self.assertThat(
            lambda: _raise_if_not_empty(populated_dict),
            raises(ValueError("Unknown keyword arguments: testing."))
        )

    def test_raise_if_not_empty_does_not_raise_on_empty(self):
        empty_dict = dict()
        self.assertThat(
            lambda: _raise_if_not_empty(empty_dict),
            Not(raises())
        )
