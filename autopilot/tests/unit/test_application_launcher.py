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

import os
import signal
import subprocess
from testtools import TestCase
from testtools.matchers import (
    Contains,
    Equals,
    IsInstance,
    MatchesListwise,
    Not,
    Raises,
    raises,
)
from testtools.content import text_content
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

            self.assertThat(
                mock_addDetail.call_args_list,
                MatchesListwise([
                    Equals([('process-return-code', text_content('0')), {}]),
                    Equals([('process-stdout', text_content('stdout')), {}]),
                    Equals([('process-stderr', text_content('stderr')), {}]),
                    ])
                )

    def test_setup_environment_returns_prepare_environment_return_value(self):
        token = self.getUniqueString()
        fake_env = Mock()
        fake_env.prepare_environment.return_value = token

        app_launcher = NormalApplicationLauncher(self.addDetail)
        app_launcher.setUp()

        with patch.object(
            _l, '_get_application_environment', return_value=fake_env
        ):
            self.assertThat(
                app_launcher._setup_environment(self.getUniqueString()),
                Equals(token)
            )

    def test_launch_returns_process_id(self):
        app_launcher = NormalApplicationLauncher(self.addDetail)

        with patch.object(_l, '_get_application_path', return_value=""):
            app_launcher._setup_environment = Mock(return_value=("", "",))
            app_launcher._launch_application_process = Mock(
                return_value=Mock(pid=123)
            )

            self.assertThat(app_launcher.launch(""), Equals(123))

    def test_launch_application_process(self):
        """The _launch_application_process method must return the process
        object, must add the _kill_process_and_attach_logs method to the
        fixture cleanups, and must call the launch_process function with the
        correct arguments.
        """
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
        with patch.object(_l, '_get_click_app_id', return_value="app_id"):
            launcher = ClickApplicationLauncher(self.addDetail)
            launcher.setUp()
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

    def test_get_click_application_log_path_formats_correct_path(self):
        path_token = self.getUniqueString()
        expected = os.path.join(path_token, "application-click-foo.log")

        with patch.object(_l.os.path, 'expanduser', return_value=path_token):
            self.assertThat(
                _get_click_application_log_path("foo"),
                Equals(expected)
            )

    def test_get_click_application_log_content_object_returns_content_object(self):  # NOQA
        with patch.object(_l, 'content_from_file') as from_file:
            self.assertThat(
                _get_click_application_log_content_object("foo"),
                Equals(from_file())
            )

    @patch.object(_l, '_launch_click_app', return_value=123)
    def test_launch_click_app_returns_pid(self, patched_launch_click_app):
        launcher = ClickApplicationLauncher(self.addDetail)
        launcher._add_click_launch_cleanup = Mock()

        with patch.object(_l, 'logger'):
            self.assertThat(
                launcher._launch_click_app("appid"),
                Equals(123)
            )

    def test_add_click_launch_cleanup_queues_correct_cleanup_steps(self):
        test_app_name = self.getUniqueString()
        test_app_pid = self.getUniqueInteger()
        launcher = ClickApplicationLauncher(self.addDetail)
        launcher.setUp()
        launcher._add_click_launch_cleanup(test_app_name, test_app_pid)

        self.assertThat(
            launcher._cleanups._cleanups,
            MatchesListwise([
                Equals((_kill_pid, (test_app_pid,), {})),
                Equals((launcher._add_log_cleanup, (test_app_name,), {})),
            ])
        )

    def test_add_click_launch_cleanup_provides_correct_details(self):
        launcher = ClickApplicationLauncher(self.addDetail)
        launcher.addCleanup = Mock()
        test_app_id = self.getUniqueString()
        test_app_pid = self.getUniqueInteger()

        launcher._add_click_launch_cleanup(test_app_id, test_app_pid)
        launcher.addCleanup.assert_any_call(_kill_pid, test_app_pid)
        launcher.addCleanup.assert_any_call(
            launcher._add_log_cleanup,
            test_app_id
        )

    def test_add_log_cleanup_adds_details(self):
        mock_addDetail = Mock()
        launcher = ClickApplicationLauncher(mock_addDetail)
        with patch.object(
            _l, '_get_click_application_log_content_object'
        ) as log_content:
            launcher._add_log_cleanup("appid")

            mock_addDetail.assert_called_with("Application Log", log_content())


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

    def test_get_click_app_status(self):
        with patch.object(_l, '_call_upstart_with_args') as call_upstart:
            _get_click_app_status("app_id")
            call_upstart.assert_called_with(
                "status",
                "application-click",
                "APP_ID=app_id"
            )

    def test_get_click_app_pid(self):
        with patch.object(_l.subprocess, 'check_output') as check_output:
            check_output.return_value = """
            application-click (com.autopilot.testing.test_app_id)
            dummy/data\napplication-click (blah) dummy/data\napplication-click
            (com.autopilot.testing.test_app_id) start/running, process 1234
            """
            self.assertThat(
                _get_click_app_pid("test_app_id"),
                Equals(1234)
            )

    def test_get_click_app_pid_raises_runtimeerror_with_no_status(self):
        test_app_id = self.getUniqueString()
        expected_error = "Could not find autopilot interface for click "\
                         "package '%s' after 10 seconds." % test_app_id
        with sleep.mocked():
            with patch.object(_l, '_get_click_app_status', return_value=""):
                self.assertThat(
                    lambda: _get_click_app_pid(test_app_id),
                    raises(RuntimeError(expected_error))
                )

    def test_get_click_app_pid_tries_10_times_and_raises(self):
        test_app_name = self.getUniqueString()
        expected_error = "Could not find autopilot interface for click "\
                         "package '%s' after 10 seconds." % test_app_name
        with sleep.mocked():
            with patch.object(
                    _l, '_get_click_app_status',
                    side_effect=subprocess.CalledProcessError(1, "")
            ):
                self.assertThat(
                    lambda: _get_click_app_pid(test_app_name),
                    raises(RuntimeError(expected_error))
                )
                self.assertThat(
                    sleep.total_time_slept(),
                    Equals(10)
                )

    @patch('autopilot.application._launcher.subprocess.check_output')
    def test_launch_click_app_starts_application(self, check_output):
        test_app_name = self.getUniqueString()
        with patch.object(
            _l, '_get_click_app_pid'
        ) as patched_get_click_app_pid:
            _launch_click_app(test_app_name)

            check_output.assert_called_with([
                "/sbin/start",
                "application",
                "APP_ID=%s" % test_app_name,
            ])
            patched_get_click_app_pid.assert_called_with(test_app_name)

    def test_get_app_env_from_string_hint_returns_qt_env(self):
        self.assertThat(
            _get_app_env_from_string_hint('QT'),
            IsInstance(QtApplicationEnvironment)
        )

    def test_get_app_env_from_string_hint_returns_gtk_env(self):
        self.assertThat(
            _get_app_env_from_string_hint('GTK'),
            IsInstance(GtkApplicationEnvironment)
        )

    def test_get_app_env_from_string_hint_raises_on_unknown(self):
        self.assertThat(
            lambda: _get_app_env_from_string_hint('FOO'),
            raises(ValueError("Unknown hint string: FOO"))
        )

    def test_get_application_environment_uses_app_hint_argument(self):
        with patch.object(_l, '_get_app_env_from_string_hint') as from_hint:
            _get_application_environment(app_hint="app_hint")
            from_hint.assert_called_with("app_hint")

    def test_get_application_environment_uses_app_path_argument(self):
        with patch.object(
            _l, 'get_application_launcher_wrapper'
        ) as patched_wrapper:
            _get_application_environment(app_path="app_path")
            patched_wrapper.assert_called_with("app_path")

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
        unknown_app_hint = self.getUniqueString()
        with patch.object(
            _l, '_get_app_env_from_string_hint',
            side_effect=ValueError()
        ):
            self.assertThat(
                lambda: _get_application_environment(
                    app_hint=unknown_app_hint
                ),
                raises(RuntimeError(
                    "Autopilot could not determine the correct introspection "
                    "type to use. You can specify one by overriding the "
                    "AutopilotTestCase.pick_app_launcher method."
                ))
            )

    def test_get_application_environment_raises_on_app_path_error(self):
        unknown_app_path = self.getUniqueString()
        with patch.object(
            _l, 'get_application_launcher_wrapper', side_effect=RuntimeError()
        ):
            self.assertThat(
                lambda: _get_application_environment(
                    app_path=unknown_app_path
                ),
                raises(RuntimeError(
                    "Autopilot could not determine the correct introspection "
                    "type to use. You can specify one by overriding the "
                    "AutopilotTestCase.pick_app_launcher method."
                ))
            )

    @patch.object(_l, '_attempt_kill_pid')
    def test_kill_pid_succeeds(self, patched_killpg):
        with patch.object(
            _l, '_is_process_running', return_value=False
        ) as proc_running:
            _kill_pid(0)
            proc_running.assert_called_once_with(0)
            patched_killpg.assert_called_once_with(0)

    @patch.object(_l, '_attempt_kill_pid')
    def test_kill_pid_kills_again_after_10_tries(self, patched_killpid):
        with sleep.mocked():
            with patch.object(
                _l, '_is_process_running', return_value=True
            ) as proc_running:
                _kill_pid(0)
                proc_running.assert_called_with(0)
                self.assertThat(proc_running.call_count, Equals(10))
                self.assertThat(patched_killpid.call_count, Equals(2))
                patched_killpid.assert_called_with(0, signal.SIGKILL)

    @patch.object(_l.os, 'killpg')
    def test_attempt_kill_pid_logs_if_process_already_exited(self, killpg):
        killpg.side_effect = OSError()

        with patch.object(_l, 'logger') as patched_log:
            _attempt_kill_pid(0)
            patched_log.info.assert_called_with(
                "Appears process has already exited."
            )

    @patch.object(_l, '_attempt_kill_pid')
    def test_kill_process_succeeds(self, patched_kill_pid):
        mock_process = Mock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = ("", "",)

        with patch.object(
            _l, '_is_process_running', return_value=False
        ):
            self.assertThat(_kill_process(mock_process), Equals(("", "", 0)))

    @patch.object(_l, '_attempt_kill_pid')
    def test_kill_process_tries_again(self, patched_kill_pid):
        with sleep.mocked():
            mock_process = Mock()
            mock_process.pid = 123
            mock_process.communicate.return_value = ("", "",)

            with patch.object(
                _l, '_is_process_running', return_value=True
            ) as proc_running:
                _kill_process(mock_process)

                self.assertThat(proc_running.call_count, Equals(10))
                self.assertThat(patched_kill_pid.call_count, Equals(2))
                patched_kill_pid.assert_called_with(123, signal.SIGKILL)

    @patch.object(_l.subprocess, 'Popen')
    def test_launch_process_uses_arguments(self, popen):
        launch_process("testapp", ["arg1", "arg2"])

        self.assertThat(
            popen.call_args_list[0][0],
            Contains(['testapp', 'arg1', 'arg2'])
        )

    @patch.object(_l.subprocess, 'Popen')
    def test_launch_process_default_capture_is_false(self, popen):
        launch_process("testapp", [])

        self.assertThat(
            popen.call_args[1]['stderr'],
            Equals(None)
        )
        self.assertThat(
            popen.call_args[1]['stdout'],
            Equals(None)
        )

    @patch.object(_l.subprocess, 'Popen')
    def test_launch_process_can_set_capture_output(self, popen):
        launch_process("testapp", [], capture_output=True)

        self.assertThat(
            popen.call_args[1]['stderr'],
            Not(Equals(None))
        )
        self.assertThat(
            popen.call_args[1]['stdout'],
            Not(Equals(None))
        )

    @patch.object(_l.subprocess, 'check_output')
    def test_get_application_launcher_wrapper_finds_qt(self, check_output):
        check_output.return_value = "LIBQTCORE"
        self.assertThat(
            get_application_launcher_wrapper("/fake/app/path"),
            IsInstance(QtApplicationEnvironment)
        )

    @patch.object(_l.subprocess, 'check_output')
    def test_get_application_launcher_wrapper_finds_gtk(self, check_output):
        check_output.return_value = "LIBGTK"
        self.assertThat(
            get_application_launcher_wrapper("/fake/app/path"),
            IsInstance(GtkApplicationEnvironment)
        )

    @patch.object(_l.subprocess, 'check_output')
    def test_get_application_path_returns_stripped_path(self, check_output):
        check_output.return_value = "/foo/bar   "

        self.assertThat(_get_application_path("bar"), Equals('/foo/bar'))
        check_output.assert_called_with(
            ['which', 'bar'], universal_newlines=True
        )

    def test_get_application_path_raises_when_cant_find_app(self):
        test_path = self.getUniqueString()
        expected_error = "Unable to find path for application {app}: Command"\
                         " '['which', '{app}']' returned non-zero exit "\
                         "status 1".format(app=test_path)
        with patch.object(_l.subprocess, 'check_output') as check_output:
            check_output.side_effect = subprocess.CalledProcessError(
                1,
                ['which', test_path]
            )

            self.assertThat(
                lambda: _get_application_path(test_path),
                raises(ValueError(expected_error))
            )

    def test_get_application_launcher_wrapper_raises_runtimeerror(self):
        test_path = self.getUniqueString()
        expected_error = "Command '['ldd', '%s']' returned non-zero exit"\
                         " status 1" % test_path
        with patch.object(_l.subprocess, 'check_output') as check_output:
            check_output.side_effect = subprocess.CalledProcessError(
                1,
                ['ldd', test_path]
            )

            self.assertThat(
                lambda: get_application_launcher_wrapper(test_path),
                raises(RuntimeError(expected_error))
            )

    def test_get_application_launcher_wrapper_returns_none_for_unknown(self):
        with patch.object(_l.subprocess, 'check_output') as check_output:
            check_output.return_value = self.getUniqueString()
            self.assertThat(
                get_application_launcher_wrapper(""), Equals(None)
            )

    def test_get_click_manifest_returns_python_object(self):
        example_manifest = """
            [{
                "description": "Calculator application",
                "framework": "ubuntu-sdk-13.10",
                "hooks": {
                    "calculator": {
                        "apparmor": "apparmor/calculator.json",
                        "desktop": "ubuntu-calculator-app.desktop"
                    }
                },
                "icon": "calculator64.png"
            }]
        """
        with patch.object(_l.subprocess, 'check_output') as check_output:
            check_output.return_value = example_manifest
            self.assertThat(_get_click_manifest(), IsInstance(list))

    @patch.object(_l.psutil, 'pid_exists')
    def test_is_process_running_checks_with_pid(self, pid_exists):
        pid_exists.return_value = True
        self.assertThat(_is_process_running(123), Equals(True))
        pid_exists.assert_called_with(123)
