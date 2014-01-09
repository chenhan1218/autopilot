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

import subprocess
from testtools import TestCase
from testtools.matchers import (
    Contains,
    Equals,
    IsInstance,
    Not,
    Raises,
    raises,
)
from textwrap import dedent
from mock import Mock, patch

from autopilot.application import (
    ClickApplicationLauncher,
    NormalApplicationLauncher,
)
from autopilot.application._environment import (
    GtkApplicationEnvironment,
    QtApplicationEnvironment,
    UpstartApplicationEnvironment,
)
import autopilot.application._launcher as _l
from autopilot.application._launcher import (
    ApplicationLauncher,
    get_application_launcher_wrapper,
    launch_process,
    _attempt_kill_pid,
    _get_app_env_from_string_hint,
    _get_application_environment,
    _get_application_path,
    _get_click_app_id,
    _get_click_app_pid,
    _get_click_app_status,
    _get_click_application_log_content_object,
    _get_click_application_log_path,
    _get_click_manifest,
    _is_process_running,
    _kill_pid,
    _kill_process,
    _launch_click_app,
    _raise_if_not_empty,
)
from autopilot.utilities import sleep


class ApplicationLauncherTests(TestCase):
    def test_raises_on_attempt_to_use_launch(self):
        self.assertThat(
            lambda: ApplicationLauncher(self.addDetail).launch(),
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
            lambda: NormalApplicationLauncher(self.addDetail, **test_kwargs),
            Not(Raises())
        )

    def test_raises_value_error_on_unknown_kwargs(self):
        self.assertThat(
            lambda: NormalApplicationLauncher(self.addDetail, unknown=True),
            raises(ValueError("Unknown keyword arguments: 'unknown'."))
        )

    def test_kill_process_and_attach_logs(self):
        mock_addDetail = Mock()
        app_launcher = NormalApplicationLauncher(mock_addDetail)

        with patch.object(
            _l, '_kill_process', return_value=("stdout", "stderr", 0)
        ):
            app_launcher._kill_process_and_attach_logs(0)

            call_args = [
                (b[0][0], b[0][1].as_text())
                for b in mock_addDetail.call_args_list
            ]

            self.assertThat(call_args, Contains(('process-return-code', '0')))
            self.assertThat(call_args, Contains(('process-stdout', 'stdout')))
            self.assertThat(call_args, Contains(('process-stderr', 'stderr')))

    def test_setup_environment_returns_modified_args(self):
        app_launcher = NormalApplicationLauncher(self.addDetail)
        app_launcher.useFixture = Mock(return_value=QtApplicationEnvironment())

        with patch.object(_l, '_get_application_environment'):
            app_launcher._setup_environment("/"),
            self.assertThat(
                app_launcher._setup_environment("/"),
                Equals(("/", ["-testability"]))
            )

    def test_launch_calls_returns_process_id(self):
        with patch.object(_l, '_get_application_path', return_value=""):
            app_launcher = NormalApplicationLauncher(self.addDetail)
            app_launcher._setup_environment = Mock(return_value=("", "",))
            app_launcher._launch_application_process = Mock(
                return_value=Mock(pid=123)
            )

            self.assertThat(app_launcher.launch(""), Equals(123))

    def test_launch_application_process(self):
        launcher = NormalApplicationLauncher(self.addDetail)
        launcher.setUp()

        expected_process_return = self.getUniqueString()
        with patch.object(
            _l, 'launch_process', return_value=expected_process_return
        ) as patched_launch_process:
            process = launcher._launch_application_process("/foo/bar")

            self.assertThat(process, Equals(expected_process_return))
            self.assertThat(
                [f[0] for f in launcher._cleanups._cleanups],
                Contains(launcher._kill_process_and_attach_logs)
            )
            patched_launch_process.assert_called_with(
                "/foo/bar",
                (),
                launcher.capture_output,
                cwd=launcher.cwd
            )


class ClickApplicationLauncherTests(TestCase):

    def test_raises_exception_on_unknown_kwargs(self):
        self.assertThat(
            lambda: ClickApplicationLauncher(self.addDetail, unknown=True),
            raises(ValueError("Unknown keyword arguments: 'unknown'."))
        )

    @patch.object(UpstartApplicationEnvironment, 'prepare_environment')
    def test_prepare_environment_called(self, prep_env):
        with patch(
            'autopilot.application._launcher._get_click_app_id'
        ) as get_click_app_id:
            get_click_app_id.return_value = "app_id"
            launcher = self.useFixture(
                ClickApplicationLauncher(self.addDetail)
            )
            launcher._launch_click_app = Mock()

            launcher.launch("package_id", "app_name")
            prep_env.assert_called_with("app_id", "app_name")

    def test_get_click_app_id_raises_runtimeerror_on_empty_manifest(self):
        """_get_click_app_id must raise a RuntimeError if the requested
        package id is not found in the click manifest.

        """
        with patch.object(_l, '_get_click_manifest', return_value=[]):
            self.assertThat(
                lambda: _get_click_app_id("com.autopilot.testing"),
                raises(
                    RuntimeError(
                        "Unable to find package 'com.autopilot.testing' in "
                        "the click manifest."
                    )
                )
            )

    def test_get_click_app_id_raises_runtimeerror_on_missing_package(self):
        with patch.object(_l, '_get_click_manifest') as cm:
            cm.return_value = [
                {
                    'name': 'com.not.expected.name',
                    'hooks': {'bar': {}}, 'version': '1.0'
                }
            ]

            self.assertThat(
                lambda: _get_click_app_id("com.autopilot.testing"),
                raises(
                    RuntimeError(
                        "Unable to find package 'com.autopilot.testing' in "
                        "the click manifest."
                    )
                )
            )

    def test_get_click_app_id_raises_runtimeerror_on_wrong_app(self):
        """get_click_app_id must raise a RuntimeError if the requested
        application is not found within the click package.

        """
        with patch.object(_l, '_get_click_manifest') as cm:
            cm.return_value = [{'name': 'com.autopilot.testing', 'hooks': {}}]

            self.assertThat(
                lambda: _get_click_app_id("com.autopilot.testing", "bar"),
                raises(
                    RuntimeError(
                        "Application 'bar' is not present within the click "
                        "package 'com.autopilot.testing'."
                    )
                )
            )

    def test_get_click_app_id_returns_id(self):
        with patch.object(_l, '_get_click_manifest') as cm:
            cm.return_value = [
                {
                'name': 'com.autopilot.testing',
                    'hooks': {'bar': {}}, 'version': '1.0'
                }
            ]

            self.assertThat(
                _get_click_app_id("com.autopilot.testing", "bar"),
                Equals("com.autopilot.testing_bar_1.0")
            )

    def test_get_click_app_id_returns_id_without_appid_passed(self):
        with patch.object(_l, '_get_click_manifest') as cm:
            cm.return_value = [
                {
                    'name': 'com.autopilot.testing',
                    'hooks': {'bar': {}}, 'version': '1.0'
                }
            ]

            self.assertThat(
                _get_click_app_id("com.autopilot.testing"),
                Equals("com.autopilot.testing_bar_1.0")
            )

    @patch(
        'autopilot.application._launcher.os.path.expanduser',
        new=lambda *args: "/home/autopilot/.cache/upstart/"
    )
    def test_get_click_application_log_path(self):
        self.assertThat(
            _get_click_application_log_path("foo"),
            Equals("/home/autopilot/.cache/upstart/application-click-foo.log")
        )

    def test_get_click_application_log_content_object(self):
        with patch(
                'autopilot.application._launcher.content_from_file'
        ) as from_file:
            _get_click_application_log_content_object("foo"),
            from_file.assert_called_with_args(
                "/home/autopilot/.cache/upstart/application-click-foo.log"
            )

    @patch('autopilot.application._launcher._launch_click_app')
    def test_launch_click_app_returns_pid(self, patched_launch_click_app):
        launcher = ClickApplicationLauncher(self.addDetail)
        launcher._add_click_launch_cleanup = Mock()
        patched_launch_click_app.return_value = 123

        with patch('autopilot.application._launcher.logger'):
            self.assertThat(
                launcher._launch_click_app("appid"),
                Equals(123)
            )

    def test_add_click_launch_cleanup(self):
        launcher = ClickApplicationLauncher(self.addDetail)
        launcher.setUp()
        launcher._add_click_launch_cleanup("appid", 123)

        queued_methods = [f[0] for f in launcher._cleanups._cleanups]
        self.assertThat(queued_methods, Contains(_kill_pid))
        self.assertThat(queued_methods, Contains(launcher._add_log_cleanup))

    def test_add_click_launch_cleanup_provides_correct_details(self):
        launcher = ClickApplicationLauncher(self.addDetail)
        launcher.addCleanup = Mock()
        launcher._add_click_launch_cleanup("appid", 123)

        launcher.addCleanup.assert_any_call(_kill_pid, 123)
        launcher.addCleanup.assert_any_call(launcher._add_log_cleanup, "appid")

    def test_add_log_cleanup_adds_details(self):
        launcher = ClickApplicationLauncher(self.addDetail)
        with patch(
            'autopilot.application._launcher.'
            '_get_click_application_log_content_object'
        ):
            launcher._add_log_cleanup("appid")
            self.assertThat(
                self._TestCase__details, Contains("Application Log")
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

    @patch('autopilot.application._environment.subprocess')
    def test_get_click_app_pid(self, patched_subproc):
        patched_subproc.check_output.return_value = dedent(
            """application-click (com.autopilot.testing.test_app_id)
            dummy/data\napplication-click (blah) dummy/data\napplication-click
            (com.autopilot.testing.test_app_id) start/running, process 1234"""
        )
        self.assertThat(
            _get_click_app_pid("test_app_id"),
            Equals(1234)
        )

    def test_get_click_app_pid_raises_runtimeerror_with_no_status(self):
        sleep.enable_mock()
        self.addCleanup(sleep.disable_mock)

        with patch(
            'autopilot.application._launcher._get_click_app_status'
        ) as get_status:
            get_status.return_value = ""

            self.assertThat(
                lambda: _get_click_app_pid("appid"),
                raises(
                    RuntimeError(
                        "Could not find autopilot interface for click package "
                        "'appid' after 10 seconds."
                    )
                )
            )

    def test_get_click_app_pid_tries_10_times_and_raises(self):
        sleep.enable_mock()
        self.addCleanup(sleep.disable_mock)

        with patch(
            'autopilot.application._launcher._get_click_app_status'
        ) as get_status:
            get_status.side_effect = subprocess.CalledProcessError(1, "")

            self.assertThat(
                lambda: _get_click_app_pid("appid"),
                raises(
                    RuntimeError(
                        "Could not find autopilot interface for click package "
                        "'appid' after 10 seconds."
                    )
                )
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

    def test_get_app_env_from_string_hint_raises_on_unknown(self):
        self.assertThat(
            lambda: _get_app_env_from_string_hint('FOO'),
            raises(ValueError("Unknown hint string: FOO"))
        )

    @patch('autopilot.application._launcher._get_app_env_from_string_hint')
    def test_get_application_environment_uses_app_hint(self, from_hint):
        _get_application_environment(app_hint="app_hint"),
        from_hint.called_with_args("app_hint")

    @patch('autopilot.application._launcher.get_application_launcher_wrapper')
    def test_get_application_environment_uses_app_path(self, patched_wrapper):
        _get_application_environment(app_path="app_path"),
        patched_wrapper.called_with_args("app_path")

    def test_get_application_environment_raises_runtime_with_no_args(self):
        self.assertThat(
            lambda: _get_application_environment(),
            raises(
                ValueError(
                    "Must specify either app_hint or app_path."
                )
            )
        )

    def test_get_application_environment_raises_on_app_hint_error(self):
        with patch(
            'autopilot.application._launcher._get_app_env_from_string_hint'
        ) as get_app_env:
            get_app_env.side_effect = ValueError()
            self.assertThat(
                lambda: _get_application_environment(app_hint="foo"),
                raises(RuntimeError(
                    "Autopilot could not determine the correct introspection "
                    "type to use. You can specify one by overriding the "
                    "AutopilotTestCase.pick_app_launcher method."
                ))
            )

    def test_get_application_environment_raises_on_app_path_error(self):
        with patch(
            'autopilot.application._launcher.get_application_launcher_wrapper'
        ) as launcher:
            launcher.side_effect = RuntimeError()
            self.assertThat(
                lambda: _get_application_environment(app_path="/foo/bar"),
                raises(RuntimeError(
                    "Autopilot could not determine the correct introspection "
                    "type to use. You can specify one by overriding the "
                    "AutopilotTestCase.pick_app_launcher method."
                ))
            )

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

    @patch('autopilot.application._launcher._attempt_kill_pid')
    def test_kill_process_succeeds(self, patched_kill_pid):
        mock_process = Mock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = ("", "",)

        with patch(
            'autopilot.application._launcher._is_process_running'
        ) as proc_running:
            proc_running.return_value = False
            self.assertThat(_kill_process(mock_process), Equals(("", "", 0)))

    @patch('autopilot.application._launcher._attempt_kill_pid')
    def test_kill_process_tries_again(self, patched_kill_pid):
        sleep.enable_mock()
        self.addCleanup(sleep.disable_mock)

        mock_process = Mock()
        mock_process.pid = 123
        mock_process.communicate.return_value = ("", "",)

        with patch(
            'autopilot.application._launcher._is_process_running'
        ) as proc_running:
            import signal
            proc_running.return_value = True

            _kill_process(mock_process)

            self.assertThat(proc_running.call_count, Equals(10))
            self.assertThat(patched_kill_pid.call_count, Equals(2))
            patched_kill_pid.assert_called_with(123, signal.SIGKILL)

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

    def test_get_application_path_returns_stripped_path(self):
        with patch('autopilot.application._launcher.subprocess') as sub_proc:
            sub_proc.check_output.return_value = "/foo/bar   "

            self.assertThat(_get_application_path("bar"), Equals('/foo/bar'))
            sub_proc.called_with_args(['which', 'bar'], True)

    def test_get_application_path_raises_when_cant_find_app(self):
        with patch(
            'autopilot.application._launcher.subprocess.check_output'
        ) as check_output:
            check_output.side_effect = subprocess.CalledProcessError(
                1,
                ['which', 'bar']
            )

            self.assertThat(
                lambda: _get_application_path("bar"),
                raises(
                    ValueError(
                        "Unable to find path for application bar: Command"
                        " '['which', 'bar']' returned non-zero exit status 1"
                    )
                )
            )

    def test_get_application_launcher_wrapper_raises_runtimeerror(self):
        with patch(
            'autopilot.application._launcher.subprocess.check_output'
        ) as check_output:
            check_output.side_effect = subprocess.CalledProcessError(
                1,
                ['ldd', '/foo/bar']
            )

            self.assertThat(
                lambda: get_application_launcher_wrapper("/foo/bar"),
                raises(
                    RuntimeError(
                        "Command '['ldd', '/foo/bar']' returned non-zero exit"
                        " status 1"
                    )
                )
            )

    def test_get_application_launcher_wrapper_returns_none_for_unknown(self):
        with patch(
            'autopilot.application._launcher.subprocess.check_output'
        ) as check_output:
            check_output.return_value = "foo"
            self.assertThat(
                get_application_launcher_wrapper("/foo/bar"), Equals(None)
            )

    def test_get_click_manifest_returns_python_object(self):

        example_manifest = dedent("""[{
            "description": "Calculator application",
            "framework": "ubuntu-sdk-13.10",
            "hooks": {
            "calculator": {
                "apparmor": "apparmor/calculator.json",
                "desktop": "ubuntu-calculator-app.desktop"
            }
            },
            "icon": "calculator64.png"
            }]""")
        with patch(
            'autopilot.application._launcher.subprocess.check_output'
        ) as check_output:
            check_output.return_value = example_manifest
            self.assertThat(_get_click_manifest(), IsInstance(list))

    @patch('autopilot.application._launcher.psutil.pid_exists')
    def test_is_process_running_checks_with_pid(self, pid_exists):
        pid_exists.return_value = True
        self.assertThat(_is_process_running(123), Equals(True))
        pid_exists.assert_called_with(123)
