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
from testtools.matchers import Equals, Not, Raises, raises
from mock import Mock, patch

from autopilot.application import (
    ClickApplicationLauncher,
    NormalApplicationLauncher,
)

from autopilot.application._launcher import (
    ApplicationLauncher,
    _get_app_env_from_string_hint,
    _get_application_environment,
    _get_click_app_id,
    _get_click_app_pid,
    _get_click_app_status,
    _launch_click_app,
    _raise_if_not_empty,
)


class ApplicationLauncherTests(TestCase):
    def test_raises_on_attempt_to_use_launch(self):
        self.assertThat(
            lambda: ApplicationLauncher(Mock).launch(),
            raises(
                NotImplementedError("Sub-classes must implement this method.")
            )
        )


class NormalApplicationLauncherTests(TestCase):

    def test_consumes_all_known_kwargs(self):
        test_kwargs = dict(
            app_type=True,
            launch_dir=True,
            capture_output=True,
            dbus_bus=True,
            emulator_base=True
        )
        self.assertThat(
            lambda: NormalApplicationLauncher(Mock(), **test_kwargs),
            Not(Raises())
        )

    def test_raises_value_error_on_unknown_kwargs(self):
        self.assertThat(
            lambda: NormalApplicationLauncher(Mock(), unknown=True),
            raises(ValueError("Unknown keyword arguments: 'unknown'."))
        )


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
            raises(ValueError("Unknown keyword arguments: 'testing'."))
        )

    def test_raise_if_not_empty_does_not_raise_on_empty(self):
        empty_dict = dict()
        self.assertThat(
            lambda: _raise_if_not_empty(empty_dict),
            Not(Raises())
        )

    @patch('autopilot.application._launcher._call_upstart_with_args')
    def test_get_click_app_status(self, patched_call_upstart):
        _get_click_app_status("app_id")
        patched_call_upstart.called_with_args(
            "status",
            "application-click",
            "APP_ID=app_id"
        )

    @patch('autopilot.application._launcher._get_click_app_status')
    def test_get_click_app_pid(self, patched_app_status):
        patched_app_status.return_value = "application-click"\
            " (com.autopilot.testing.test_app_id) start/running, process 1234"
        self.assertThat(
            _get_click_app_pid("test_app_id"),
            Equals(1234)
        )

    @patch('autopilot.application._launcher.subprocess')
    def test_launch_click_app(self, patched_subproc):
        with patch(
            'autopilot.application._launcher._get_click_app_pid'
        ) as patched_get_click_app_pid:
            patched_subproc.check_output.return_value = True
            _launch_click_app("app_id")
            patched_subproc.check_output.assert_called_with_args(
                "/sbin/start",
                "application",
                "APP_ID=app_id",
            )
            patched_get_click_app_pid.called_with_args("app_id")

    @patch('autopilot.application._launcher.QtApplicationEnvironment')
    def test_get_app_env_from_string_hint_returns_qt_env(self, qt_appenv):
        self.assertThat(
            _get_app_env_from_string_hint('QT'),
            Equals(qt_appenv())
        )

    @patch('autopilot.application._launcher.GtkApplicationEnvironment')
    def test_get_app_env_from_string_hint_returns_gtk_env(self, gtk_appenv):
        self.assertThat(
            _get_app_env_from_string_hint('GTK'),
            Equals(gtk_appenv())
        )

    @patch('autopilot.application._launcher._get_app_env_from_string_hint')
    def test_get_application_environment_uses_app_hint(self, from_hint):
        _get_application_environment("app_hint", None),
        from_hint.called_with_args("app_hint")

    @patch('autopilot.application._launcher.get_application_launcher_wrapper')
    def test_get_application_environment_uses_app_path(self, patched_wrapper):
        _get_application_environment(None, "app_path"),
        patched_wrapper.called_with_args("app_path")
