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

from argparse import Namespace
from mock import Mock, patch
import six
from testtools import TestCase
from testtools.matchers import Equals, raises
if six.PY3:
    from contextlib import ExitStack
else:
    from contextlib2 import ExitStack

from autopilot import run
from autopilot.run import (
    _get_applications_full_path,
    _application_name_is_full_path,
    _get_app_name_and_args,
)



class RunUtilityFunctionTests(TestCase):

    @patch('autopilot.run.autopilot.globals.set_debug_profile_fixture')
    def test_sets_when_correct_profile_found(self, patched_set_fixture):
        mock_profile = Mock()
        mock_profile.name = "verbose"
        parsed_args = Namespace(debug_profile="verbose")

        with patch.object(
                run, 'get_all_debug_profiles', lambda: {mock_profile}):

            run._configure_debug_profile(parsed_args)
            patched_set_fixture.assert_called_once_with(mock_profile)

    @patch('autopilot.run.autopilot.globals.set_debug_profile_fixture')
    def test_does_nothing_when_no_profile_found(self, patched_set_fixture):
        mock_profile = Mock()
        mock_profile.name = "verbose"
        parsed_args = Namespace(debug_profile="normal")

        with patch.object(
                run, 'get_all_debug_profiles', lambda: {mock_profile}):

            run._configure_debug_profile(parsed_args)
        self.assertFalse(patched_set_fixture.called)

    @patch('autopilot.run.autopilot.globals')
    def test_timeout_values_set_with_long_profile(self, patched_globals):
        args = Namespace(timeout_profile='long')
        run._configure_timeout_profile(args)

        patched_globals.set_default_timeout_period.assert_called_once_with(
            20.0
        )
        patched_globals.set_long_timeout_period.assert_called_once_with(30.0)

    @patch('autopilot.run.autopilot.globals')
    def test_timeout_value_not_set_with_normal_profile(self, patched_globals):
        args = Namespace(timeout_profile='normal')
        run._configure_timeout_profile(args)

        self.assertFalse(patched_globals.set_default_timeout_period.called)
        self.assertFalse(patched_globals.set_long_timeout_period.called)

    @patch('autopilot.run.autopilot.globals')
    def test_configure_video_recording_not_called(self, patched_globals):
        args = Namespace(record_directory='', record=False, record_options='')
        run._configure_video_recording(args)

        self.assertFalse(patched_globals._configure_video_recording.called)

    @patch.object(run, '_have_video_recording_facilities', new=lambda: True)
    def test_configure_video_recording_called_with_record_set(self):
        args = Namespace(record_directory='', record=True, record_options='')
        with patch('autopilot.run.autopilot.globals') as patched_globals:
            run._configure_video_recording(args)
            patched_globals.configure_video_recording.assert_called_once_with(
                True,
                '/tmp/autopilot',
                ''
            )

    @patch.object(run, '_have_video_recording_facilities', new=lambda: True)
    def test_configure_video_record_directory_imples_record(self):
        token = self.getUniqueString()
        args = Namespace(
            record_directory=token,
            record=False,
            record_options=''
        )
        with patch('autopilot.run.autopilot.globals') as patched_globals:
            run._configure_video_recording(args)
            patched_globals.configure_video_recording.assert_called_once_with(
                True,
                token,
                ''
            )

    @patch.object(run, '_have_video_recording_facilities', new=lambda: False)
    def test_configure_video_recording_raises_RuntimeError(self):
        args = Namespace(record_directory='', record=True, record_options='')
        self.assertThat(
            lambda: run._configure_video_recording(args),
            raises(
                RuntimeError(
                    "The application 'recordmydesktop' needs to be installed "
                    "to record failing jobs."
                )
            )
        )

    def test_video_record_check_calls_subprocess_with_correct_args(self):
        with patch.object(run.subprocess, 'call') as patched_call:
            run._have_video_recording_facilities()
            patched_call.assert_called_once_with(
                ['which', 'recordmydesktop'],
                stdout=run.subprocess.PIPE
            )

    def test_video_record_check_returns_true_on_zero_return_code(self):
        with patch.object(run.subprocess, 'call') as patched_call:
            patched_call.return_value = 0
            self.assertTrue(run._have_video_recording_facilities())

    def test_video_record_check_returns_false_on_nonzero_return_code(self):
        with patch.object(run.subprocess, 'call') as patched_call:
            patched_call.return_value = 1
            self.assertFalse(run._have_video_recording_facilities())


class TestRunLaunchApp(TestCase):
    """Tests for the 'autopilot launch' command"""

    def test_can_take_application_args(self):
        pass

    def test_passes_arguments_to_application(self):
        pass

    def test_get_app_name_and_args_returns_app_name_passed_app_name(self):
        app_name = self.getUniqueString()
        launch_args = [app_name]

        self.assertThat(
            _get_app_name_and_args(launch_args),
            Equals((app_name, []))
        )

    def test_get_app_name_and_args_returns_app_name_passed_arg_and_name(self):
        app_name = self.getUniqueString()
        app_arg = [self.getUniqueString()]
        launch_args = [app_name] + app_arg

        self.assertThat(
            _get_app_name_and_args(launch_args),
            Equals((app_name, app_arg))
        )

    def test_get_app_name_and_args_returns_app_name_passed_args_and_name(self):
        app_name = self.getUniqueString()
        app_args = [self.getUniqueString(), self.getUniqueString()]

        launch_args = [app_name] + app_args

        self.assertThat(
            _get_app_name_and_args(launch_args),
            Equals((app_name, app_args))
        )

    def test_application_name_is_full_path_True_when_is_abs_path(self):
        with patch.object(run.os.path, 'isabs', return_value=True):
            self.assertTrue(_application_name_is_full_path(""))

    def test_application_name_is_full_path_True_when_path_exists(self):
        with patch.object(run.os.path, 'exists', return_value=True):
            self.assertTrue(_application_name_is_full_path(""))

    def test_application_name_is_full_path_False_neither_abs_or_exists(self):
        with patch.object(run.os.path, 'exists', return_value=False):
            with patch.object(run.os.path, 'isabs', return_value=False):
                self.assertFalse(_application_name_is_full_path(""))

    def test_get_applications_full_path_returns_same_when_full_path(self):
        app_name = self.getUniqueString()

        with patch.object(
            run,
            '_application_name_is_full_path',
            return_value=True
        ) as is_full_path:
            self.assertThat(
                _get_applications_full_path(app_name),
                Equals(app_name)
            )

class TestProgramTests(TestCase):

    """Tests for the TestProgram class.

    These tests are a little ugly at the moment, and will continue to be so
    until we refactor the run module to make it more testable.

    """

    def test_can_provide_args(self):
        fake_args = Namespace()
        program = run.TestProgram(fake_args)

        self.assertThat(program.args, Equals(fake_args))

    def test_calls_parse_args_by_default(self):
        fake_args = Namespace()
        with patch('run.parse_arguments') as fake_parse_args:
            fake_parse_args.return_value = fake_args
            program = run.TestProgram()

            fake_parse_args.assert_called_once_with()
            self.assertThat(program.args, Equals(fake_args))

    def test_run_calls_setup_logging_with_verbose_arg(self):
        fake_args = Namespace(verbose=1, mode='')
        program = run.TestProgram(fake_args)
        with patch.object(run, 'setup_logging') as patched_setup_logging:
            program.run()

            patched_setup_logging.assert_called_once_with(True)

    def test_list_command_calls_list_tests_method(self):
        fake_args = Namespace(mode='list')
        program = run.TestProgram(fake_args)
        with patch.object(program, 'list_tests') as patched_list_tests:
            program.run()

            patched_list_tests.assert_called_once_with()

    def test_run_command_calls_run_tests_method(self):
        fake_args = Namespace(mode='run')
        program = run.TestProgram(fake_args)
        with patch.object(program, 'run_tests') as patched_run_tests:
            program.run()

            patched_run_tests.assert_called_once_with()

    def test_vis_command_calls_run_vis_method(self):
        fake_args = Namespace(mode='vis')
        program = run.TestProgram(fake_args)
        with patch.object(program, 'run_vis') as patched_run_vis:
            program.run()

            patched_run_vis.assert_called_once_with()

    def test_launch_command_calls_launch_app_method(self):
        fake_args = Namespace(mode='launch')
        program = run.TestProgram(fake_args)
        with patch.object(program, 'launch_app') as patched_launch_app:
            program.run()

            patched_launch_app.assert_called_once_with()

    def test_run_tests_calls_utility_functions(self):
        """The run_tests method must call all the utility functions.

        This test is somewhat ugly, and relies on a lot of mocks. This will be
        cleaned up once run has been completely refactored.

        """
        fake_args = create_default_run_args()
        program = run.TestProgram(fake_args)
        mock_test_result = Mock()
        mock_test_result.wasSuccessful.return_value = True
        mock_test_suite = Mock()
        mock_test_suite.run.return_value = mock_test_result
        mock_construct_test_result = Mock()
        with ExitStack() as stack:
            load_tests = stack.enter_context(
                patch.object(run, 'load_test_suite_from_name')
            )
            fake_construct = stack.enter_context(
                patch.object(run, 'construct_test_result')
            )
            configure_debug = stack.enter_context(
                patch.object(run, '_configure_debug_profile')
            )
            config_timeout = stack.enter_context(
                patch.object(run, '_configure_timeout_profile')
            )
            configure_video = stack.enter_context(
                patch.object(run, '_configure_video_recording')
            )

            load_tests.return_value = (mock_test_suite, False)
            fake_construct.return_value = mock_construct_test_result
            program.run()

            configure_video.assert_called_once_with(fake_args)
            config_timeout.assert_called_once_with(fake_args)
            configure_debug.assert_called_once_with(fake_args)
            fake_construct.assert_called_once_with(fake_args)
            load_tests.assert_called_once_with(fake_args.suite)


def create_default_run_args(**kwargs):
    """Create a an argparse.Namespace object containing arguments required
    to make autopilot.run.TestProgram run a suite of tests.

    Every feature that can be turned off will be. Individual arguments can be
    specified with keyword arguments to this function.
    """
    defaults = dict(
        random_order=False,
        debug_profile='normal',
        timeout_profile='normal',
        record_directory='',
        record=False,
        record_options='',
        verbose=False,
        mode='run',
        suite='foo',
    )
    defaults.update(kwargs)
    return Namespace(**defaults)
