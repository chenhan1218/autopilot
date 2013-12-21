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
from testtools.matchers import (
    Contains,
    Equals,
    IsInstance,
    Not,
    Raises,
    raises,
)
from mock import Mock, patch

from autopilot.application import (
    ClickApplicationLauncher,
    NormalApplicationLauncher,
)
from autopilot.application._environment import UpstartApplicationEnvironment
from autopilot.utilities import sleep

from autopilot.application._launcher import (
    ApplicationLauncher,
    get_application_launcher_wrapper,
    launch_process,
    _attempt_kill_pid,
    _get_app_env_from_string_hint,
    _get_application_environment,
    _get_click_app_id,
    _get_click_app_pid,
    _get_click_app_status,
    _get_click_application_log_content_object,
    _kill_pid,
    _launch_click_app,
    _raise_if_not_empty,
)

from autopilot.application._environment import (
    GtkApplicationEnvironment,
    QtApplicationEnvironment,
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

    @patch('autopilot.application._launcher._kill_process')
    def test_kill_process_and_attach_logs(self, patched_kill_proc):
        mock_addDetail = Mock()
        app_launcher = NormalApplicationLauncher(mock_addDetail)

        patched_kill_proc.return_value = ("stdout", "stderr", 0)

        with patch(
            'autopilot.application._launcher.text_content'
        ) as text_content:
            app_launcher._kill_process_and_attach_logs(0)
            self.assertThat(mock_addDetail.call_count, Equals(3))
            mock_addDetail.assert_called_with('process-stderr', text_content())


class ClickApplicationLauncherTests(TestCase):

    def test_raises_exception_on_unknown_kwargs(self):
        self.assertThat(
            lambda: ClickApplicationLauncher(Mock(), unknown=True),
            raises(ValueError("Unknown keyword arguments: 'unknown'."))
        )

    @patch.object(UpstartApplicationEnvironment, 'prepare_environment')
    def test_prepare_environment_called(self, prep_env):
        with patch(
            'autopilot.application._launcher._get_click_app_id'
        ) as get_click_app_id:
            get_click_app_id.return_value = "app_id"
            launcher = self.useFixture(ClickApplicationLauncher(Mock()))
            launcher._launch_click_app = Mock()

            launcher.launch("package_id", "app_name")
            prep_env.assert_called_with("app_id", "app_name")

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

    @patch(
        'autopilot.application._launcher.os.path.expanduser',
        new=lambda *args: "/home/autopilot/.cache/upstart/"
    )
    def test_get_click_application_log_content_object(self):
        with patch(
                'autopilot.application._launcher.content_from_file'
        ) as from_file:
            _get_click_application_log_content_object("foo"),
            from_file.assert_called_with_args(
                "/home/autopilot/.cache/upstart/application-click-foo.log"
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

    @patch('autopilot.application._launcher._attempt_kill_pid')
    def test_kill_pid_succeeds(self, patched_killpg):
        with patch(
            'autopilot.application._launcher._is_process_running'
        ) as proc_running:
            proc_running.return_value = False

            _kill_pid(0)
            proc_running.assert_called_once_with(0)

    @patch('autopilot.application._launcher._attempt_kill_pid')
    def test_kill_pid_kills_again_after_10_tries(self, patched_killpid):
        sleep.enable_mock()
        self.addCleanup(sleep.disable_mock)

        with patch(
            'autopilot.application._launcher._is_process_running'
        ) as proc_running:
            import signal

            proc_running.return_value = True

            _kill_pid(0)
            proc_running.assert_called_with(0)
            self.assertThat(proc_running.call_count, Equals(10))
            self.assertThat(patched_killpid.call_count, Equals(2))
            patched_killpid.assert_called_with(0, signal.SIGKILL)

    @patch('autopilot.application._launcher.os.killpg')
    def test_attempt_kill_pid_logs_if_process_already_exited(self, killpg):
        killpg.side_effect = OSError()

        with patch('autopilot.application._launcher.logger') as patched_log:
            _attempt_kill_pid(0)
            patched_log.info.assert_called_with(
                "Appears process has already exited."
            )

    @patch('autopilot.application._launcher.subprocess')
    def test_launch_process_uses_arguments(self, subprocess):
        launch_process("testapp", ["arg1", "arg2"])

        self.assertThat(
            subprocess.Popen.call_args_list[0][0],
            Contains(['testapp', 'arg1', 'arg2'])
        )

    @patch('autopilot.application._launcher.subprocess')
    def test_launch_process_default_capture_is_false(self, subprocess):
        launch_process("testapp", [])

        self.assertThat(
            subprocess.Popen.call_args[1]['stderr'],
            Equals(None)
        )
        self.assertThat(
            subprocess.Popen.call_args[1]['stdout'],
            Equals(None)
        )

    @patch('autopilot.application._launcher.subprocess')
    def test_launch_process_can_set_capture_output(self, subprocess):
        launch_process("testapp", [], capture_output=True)

        self.assertThat(
            subprocess.Popen.call_args[1]['stderr'],
            Not(Equals(None))
        )
        self.assertThat(
            subprocess.Popen.call_args[1]['stdout'],
            Not(Equals(None))
        )

    @patch('autopilot.application._launcher.subprocess')
    def test_get_application_launcher_wrapper_finds_qt(self, subprocess):
        subprocess.check_output.return_value = "LIBQTCORE"
        self.assertThat(
            get_application_launcher_wrapper("/fake/app/path"),
            IsInstance(QtApplicationEnvironment)
        )

    @patch('autopilot.application._launcher.subprocess')
    def test_get_application_launcher_wrapper_finds_gtk(self, subprocess):
        subprocess.check_output.return_value = "LIBGTK"
        self.assertThat(
            get_application_launcher_wrapper("/fake/app/path"),
            IsInstance(GtkApplicationEnvironment)
        )
