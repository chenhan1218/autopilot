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

from codecs import open
from collections import OrderedDict
import cProfile
from datetime import datetime
from imp import find_module
import logging
import os
import os.path
from platform import node
from random import shuffle
import six
import subprocess
import sys
from unittest import TestLoader, TestSuite

from testtools import iterate_tests

from autopilot import get_version_string, parse_arguments
import autopilot.globals
from autopilot._debug import get_all_debug_profiles
from autopilot.testresult import get_output_formats
from autopilot.utilities import DebugLogFilter, LogFormatter
from autopilot.application._launcher import (
    _get_app_env_from_string_hint,
    get_application_launcher_wrapper,
    launch_process,
)


logger = logging.getLogger(__name__)


def setup_logging(verbose):
    """Configure the root logger and verbose logging to stderr."""
    root_logger = get_root_logger()
    root_logger.setLevel(logging.DEBUG)
    if verbose == 0:
        set_null_log_handler(root_logger)
    if verbose >= 1:
        set_stderr_stream_handler(root_logger)
    if verbose >= 2:
        enable_debug_log_messages()
    #log autopilot version
    root_logger.info(get_version_string())


def get_root_logger():
    return logging.getLogger()


def set_null_log_handler(root_logger):
    root_logger.addHandler(logging.NullHandler())


def set_stderr_stream_handler(root_logger):
    formatter = LogFormatter()
    stderr_handler = logging.StreamHandler(stream=sys.stderr)
    stderr_handler.setFormatter(formatter)
    root_logger.addHandler(stderr_handler)


def enable_debug_log_messages():
    DebugLogFilter.debug_log_enabled = True


def construct_test_result(args):
    formats = get_output_formats()
    return formats[args.format](
        stream=get_output_stream(args.format, args.output),
        failfast=args.failfast,
    )


def get_output_stream(format, path):
    """Get an output stream pointing to 'path' that's appropriate for format
    'format'.

    :param format: A string that describes one of the output formats supported
        by autopilot.
    :param path: A path to the file you wish to write, or None to write to
        stdout.

    """
    if path:
        log_file = _get_log_file_path(path)
        if format == 'xml':
            return _get_text_mode_file_stream(log_file)
        elif format == 'text':
            return _get_binary_mode_file_stream(log_file)
        else:
            return _get_raw_binary_mode_file_stream(log_file)
    else:
        return sys.stdout


def _get_text_mode_file_stream(log_file):
    if six.PY2:
        return open(
            log_file,
            'w'
        )
    else:
        return open(
            log_file,
            'w',
            encoding='utf-8',
        )


def _get_binary_mode_file_stream(log_file):
    return open(
        log_file,
        'w',
        encoding='utf-8',
        errors='backslashreplace'
    )


def _get_raw_binary_mode_file_stream(log_file):
    return open(
        log_file,
        'wb'
    )


def _get_log_file_path(requested_path):
    dirname = os.path.dirname(requested_path)
    if dirname != '' and not os.path.exists(dirname):
        os.makedirs(dirname)
    if os.path.isdir(requested_path):
        return _get_default_log_filename(requested_path)
    return requested_path


def _get_default_log_filename(target_directory):
    """Return a filename that's likely to be unique to this test run."""
    default_log_filename = "%s_%s.log" % (
        node(),
        datetime.now().strftime("%d.%m.%y-%H%M%S")
    )
    _print_default_log_path(default_log_filename)
    log_file = os.path.join(target_directory, default_log_filename)
    return log_file


def _print_default_log_path(default_log_filename):
    print("Using default log filename: %s" % default_log_filename)


def get_package_location(import_name):
    """Get the on-disk location of a package from a test id name.

    :raises ImportError: if the name could not be found.
    :returns: path as a string
    """
    top_level_pkg = import_name.split('.')[0]
    _, path, _ = find_module(top_level_pkg, [os.getcwd()] + sys.path)
    return os.path.abspath(
        os.path.join(
            path,
            '..'
        )
    )


def _is_testing_autopilot_module(test_names):
    return (
        os.path.basename(sys.argv[0]) == 'autopilot'
        and any(t.startswith('autopilot') for t in test_names)
    )


def _reexecute_autopilot_using_module():
    autopilot_command = [sys.executable, '-m', 'autopilot.run'] + sys.argv[1:]
    try:
        subprocess.check_call(autopilot_command)
    except subprocess.CalledProcessError as e:
        return e.returncode
    return 0


def _discover_test(test_name):
    """Return tuple of (TestSuite of found test, top_level_dir of test).

    :raises ImportError: if test_name isn't a valid module or test name

    """
    loader = TestLoader()
    top_level_dir = get_package_location(test_name)
    # no easy way to figure out if test_name is a module or a test, so we
    # try to do the discovery first=...
    try:
        test = loader.discover(
            start_dir=test_name,
            top_level_dir=top_level_dir
        )
    except ImportError:
        # and if that fails, we try it as a test id.
        test = loader.loadTestsFromName(test_name)

    return (test, top_level_dir)


def _discover_requested_tests(test_names):
    """Return a collection of tests that are under test_names.

    returns a tuple containig a TestSuite of tests found and a boolean
    depicting wherether any difficulties were encountered while searching
    (namely un-importable module names).

    """
    all_tests = []
    test_package_locations = []
    error_occured = False
    for name in test_names:
        try:
            test, top_level_dir = _discover_test(name)
            all_tests.append(test)
            test_package_locations.append(top_level_dir)
        except ImportError as e:
            _handle_discovery_error(name, e)
            error_occured = True

    _show_test_locations(test_package_locations)

    return (TestSuite(all_tests), error_occured)


def _handle_discovery_error(test_name, exception):
    print("could not import package %s: %s" % (test_name, str(exception)))


def _filter_tests(all_tests, test_names):
    """Filter a given TestSuite for tests starting with any name contained
    within test_names.

    """
    requested_tests = {}
    for test in iterate_tests(all_tests):
        # The test loader returns tests that start with 'unittest.loader' if
        # for whatever reason the test failed to load. We run the tests without
        # the built-in exception catching turned on, so we can get at the
        # raised exception, which we print, so the user knows that something in
        # their tests is broken.
        if test.id().startswith('unittest.loader'):
            test_id = test._testMethodName
            try:
                test.debug()
            except Exception as e:
                print(e)
        else:
            test_id = test.id()
        if any([test_id.startswith(name) for name in test_names]):
            requested_tests[test_id] = test

    return requested_tests


def load_test_suite_from_name(test_names):
    """Return a test suite object given a dotted test names.

    Returns a tuple containing the TestSuite and a boolean indicating wherever
    any issues where encountered during the loading process.

    """
    # The 'autopilot' program cannot be used to run the autopilot test suite,
    # since setuptools needs to import 'autopilot.run', and that grabs the
    # system autopilot package. After that point, the module is loaded and
    # cached in sys.modules, and there's no way to unload a module in python
    # once it's been loaded.
    #
    # The solution is to detect whether we've been started with the 'autopilot'
    # application, *and* whether we're running the autopilot test suite itself,
    # and ≡ that's the case, we re-call autopilot using the standard
    # autopilot.run entry method, and exit with the sub-process' return code.
    if _is_testing_autopilot_module(test_names):
        exit(_reexecute_autopilot_using_module())

    if isinstance(test_names, str):
        test_names = [test_names]
    elif not isinstance(test_names, list):
        raise TypeError("test_names must be either a string or list, not %r"
                        % (type(test_names)))

    all_tests, error_occured = _discover_requested_tests(test_names)
    filtered_tests = _filter_tests(all_tests, test_names)

    return (TestSuite(filtered_tests.values()), error_occured)


def _show_test_locations(test_directories):
    """Print the test directories tests have been loaded from."""
    print("Loading tests from: %s\n" % ",".join(sorted(test_directories)))


def _configure_debug_profile(args):
    for fixture_class in get_all_debug_profiles():
        if args.debug_profile == fixture_class.name:
            autopilot.globals.set_debug_profile_fixture(fixture_class)
            break


def _configure_timeout_profile(args):
    if args.timeout_profile == 'long':
        autopilot.globals.set_default_timeout_period(20.0)
        autopilot.globals.set_long_timeout_period(30.0)


def _configure_video_recording(args):
    """Configure video recording based on contents of ``args``.

    :raises RuntimeError: If the user asked for video recording, but the
        system does not support video recording.

    """
    if args.record_directory:
        args.record = True

    if args.record:
        if not args.record_directory:
            args.record_directory = '/tmp/autopilot'

        if not _have_video_recording_facilities():
            raise RuntimeError(
                "The application 'recordmydesktop' needs to be installed to "
                "record failing jobs."
            )
        autopilot.globals.configure_video_recording(
            True,
            args.record_directory,
            args.record_options
        )


def _have_video_recording_facilities():
    call_ret_code = subprocess.call(
        ['which', 'recordmydesktop'],
        stdout=subprocess.PIPE
    )
    return call_ret_code == 0


def _prepare_application_for_launch(application, interface):
    app_path, app_arguments = _get_application_path_and_arguments(application)
    return _prepare_launcher_environment(
        interface,
        app_path,
        app_arguments
    )


def _get_application_path_and_arguments(application):

    app_name, app_arguments = _get_app_name_and_args(application)

    try:
        app_path = _get_applications_full_path(app_name)
    except ValueError as e:
        raise RuntimeError(str(e))

    return app_path, app_arguments


def _get_app_name_and_args(argument_list):
    """Return a tuple of (app_name, [app_args])."""
    return argument_list[0], argument_list[1:]


def _get_applications_full_path(app_name):
    if not _application_name_is_full_path(app_name):
        try:
            app_name = subprocess.check_output(
                ["which", app_name],
                universal_newlines=True
            ).strip()
        except subprocess.CalledProcessError:
            raise ValueError(
                "Cannot find application '%s'" % (app_name)
            )
    return app_name


def _application_name_is_full_path(app_name):
    return os.path.isabs(app_name) or os.path.exists(app_name)


def _prepare_launcher_environment(interface, app_path, app_arguments):
    launcher_env = _get_application_launcher_env(interface, app_path)
    _raise_if_launcher_is_none(launcher_env, app_path)
    return launcher_env.prepare_environment(app_path, app_arguments)


def _raise_if_launcher_is_none(launcher_env, app_path):
    if launcher_env is None:
        raise RuntimeError(
            "Could not determine introspection type to use for "
            "application '{app_path}'.\n"
            "(Perhaps use the '-i' argument to specify an interface.)".format(
                app_path=app_path
            )
        )


def _get_application_launcher_env(interface, application_path):
    launcher_env = None
    if interface == 'Auto':
        launcher_env = _try_determine_launcher_env_or_raise(application_path)
    else:
        launcher_env = _get_app_env_from_string_hint(interface)

    return launcher_env


def _try_determine_launcher_env_or_raise(app_name):
    try:
        return get_application_launcher_wrapper(app_name)
    except RuntimeError as e:
        # Re-format the runtime error to be more user friendly.
        raise RuntimeError(
            "Error detecting launcher: {err}\n"
            "(Perhaps use the '-i' argument to specify an interface.)".format(
                err=str(e)
            )
        )


def _print_message_and_exit_error(msg):
    print(msg)
    exit(1)


def _run_with_profiling(callable, output_file):
    cProfile.runctx(
        'callable()',
        globals(),
        locals(),
        filename=output_file,
    )


class TestProgram(object):

    def __init__(self, defined_args=None):
        """Create a new TestProgram instance.

        :param defined_args: If specified, must be an object representing
            command line arguments, as returned by the ``parse_arguments``
            function. Passing in arguments prevents argparse from parsing
            sys.argv. Used in testing.

        """
        self.args = defined_args or parse_arguments()

    def run(self):
        setup_logging(getattr(self.args, 'verbose', False))

        if self.args.mode == 'list':
            self.list_tests()
        elif self.args.mode == 'run':
            self.run_tests()
        elif self.args.mode == 'vis':
            self.run_vis()
        elif self.args.mode == 'launch':
            self.launch_app()

    def run_vis(self):
        # importing this requires that DISPLAY is set. Since we don't always
        # want that requirement, do the import here:
        from autopilot.vis import vis_main

        # XXX - in quantal, overlay scrollbars make this process consume 100%
        # of the CPU. It's a known bug:
        #
        #https://bugs.launchpad.net/ubuntu/quantal/+source/qt4-x11/+bug/1005677
        #
        # Once that's been fixed we can remove the following line:
        #
        os.putenv('LIBOVERLAY_SCROLLBAR', '0')
        args = ['-testability'] if self.args.testability else []
        if self.args.enable_profile:
            _run_with_profiling(lambda: vis_main(args), 'vis_tool.profile')
        else:
            vis_main(args)

    def launch_app(self):
        """Launch an application, with introspection support."""

        try:
            app_path, app_arguments = _prepare_application_for_launch(
                self.args.application,
                self.args.interface
            )

            launch_process(
                app_path,
                app_arguments,
                capture_output=False
            )
        except RuntimeError as e:
            _print_message_and_exit_error("Error: " + str(e))

    def run_tests(self):
        """Run tests, using input from `args`."""
        test_suite, error_encountered = load_test_suite_from_name(
            self.args.suite
        )

        if not test_suite.countTestCases():
            raise RuntimeError('Did not find any tests')

        if self.args.random_order:
            shuffle(test_suite._tests)
            print("Running tests in random order")

        _configure_debug_profile(self.args)
        _configure_timeout_profile(self.args)
        try:
            _configure_video_recording(self.args)
        except RuntimeError as e:
            print("Error: %s" % str(e))
            exit(1)

        if self.args.verbose:
            autopilot.globals.set_log_verbose(True)

        result = construct_test_result(self.args)
        result.startTestRun()
        try:
            test_result = test_suite.run(result)
        finally:
            result.stopTestRun()

        if not test_result.wasSuccessful() or error_encountered:
            exit(1)

    def list_tests(self):
        """Print a list of tests we find inside autopilot.tests."""
        num_tests = 0
        total_title = "tests"
        test_suite, error_encountered = load_test_suite_from_name(
            self.args.suite
        )

        if self.args.run_order:
            test_list_fn = lambda: iterate_tests(test_suite)
        else:
            test_list_fn = lambda: sorted(iterate_tests(test_suite), key=id)

        # only show test suites, not test cases. TODO: Check if this is still
        # a requirement.
        if self.args.suites:
            suite_names = ["%s.%s" % (t.__module__, t.__class__.__name__)
                           for t in test_list_fn()]
            unique_suite_names = list(OrderedDict.fromkeys(suite_names).keys())
            num_tests = len(unique_suite_names)
            total_title = "suites"
            print("    %s" % ("\n    ".join(unique_suite_names)))
        else:
            for test in test_list_fn():
                has_scenarios = (hasattr(test, "scenarios")
                                 and type(test.scenarios) is list)
                if has_scenarios:
                    num_tests += len(test.scenarios)
                    print(" *%d %s" % (len(test.scenarios), test.id()))
                else:
                    num_tests += 1
                    print("    " + test.id())
        print("\n\n %d total %s." % (num_tests, total_title))

        if error_encountered:
            exit(1)


def main():
    test_app = TestProgram()
    try:
        test_app.run()
    except RuntimeError as e:
        print(e)
        exit(1)

if __name__ == "__main__":
    main()
