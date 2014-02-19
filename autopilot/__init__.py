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

from argparse import ArgumentParser, REMAINDER, Action
import subprocess

from autopilot._debug import (
    get_all_debug_profiles,
    get_default_debug_profile,
)
from autopilot.testresult import get_output_formats, get_default_format
from autopilot.exceptions import BackendException

version = '1.4.0'


def parse_arguments(argv=None):
    """Parse command-line arguments, and return an argparse arguments
    object.
    """
    parser = ArgumentParser(
        description="Autopilot test tool.",
        epilog="Each command (run, list, launch etc.) has additional help that"
        " can be viewed by passing the '-h' flag to the command. For "
        "example: 'autopilot run -h' displays further help for the "
        "'run' command."
    )
    parser.add_argument('-v', '--version', action='version',
                        version=get_version_string(),
                        help="Display autopilot version and exit.")
    subparsers = parser.add_subparsers(help='Run modes', dest="mode")

    parser_run = subparsers.add_parser('run', help="Run autopilot tests")
    parser_run.add_argument('-o', "--output", required=False,
                            help='Write test result report to file.\
                            Defaults to stdout.\
                            If given a directory instead of a file will \
                            write to a file in that directory named: \
                            <hostname>_<dd.mm.yyy_HHMMSS>.log')
    available_formats = get_output_formats().keys()
    parser_run.add_argument('-f', "--format", choices=available_formats,
                            default=get_default_format(),
                            required=False,
                            help='Specify desired output format. \
                            Default is "text".')
    parser_run.add_argument("-ff", "--failfast", action='store_true',
                            required=False, default=False,
                            help="Stop the test run on the first error \
                            or failure.")
    parser_run.add_argument('-r', '--record', action='store_true',
                            default=False, required=False,
                            help="Record failing tests. Required \
                            'recordmydesktop' app to be installed.\
                            Videos are stored in /tmp/autopilot.")
    parser_run.add_argument("-rd", "--record-directory", required=False,
                            type=str, help="Directory to put recorded tests")
    parser_run.add_argument("--record-options", required=False,
                            type=str, help="Comma separated list of options \
                            to pass to recordmydesktop")
    parser_run.add_argument("-ro", "--random-order", action='store_true',
                            required=False, default=False,
                            help="Run the tests in random order")
    parser_run.add_argument(
        '-v', '--verbose', default=False, required=False, action='count',
        help="If set, autopilot will output test log data to stderr during a "
        "test run. Set twice to also log data useful for debugging autopilot "
        "itself.")
    parser_run.add_argument(
        "--debug-profile",
        choices=[p.name for p in get_all_debug_profiles()],
        default=get_default_debug_profile().name,
        help="Select a profile for what additional debugging information "
        "should be attached to failed test results."
    )
    parser_run.add_argument(
        "--timeout-profile",
        choices=['normal', 'long'],
        default='normal',
        help="Alter the timeout values Autopilot uses. Selecting 'long' will "
        "make autopilot use longer timeouts for various polling loops. This "
        "useful if autopilot is running on very slow hardware"
    )
    parser_run.add_argument("suite", nargs="+",
                            help="Specify test suite(s) to run.")

    parser_list = subparsers.add_parser('list', help="List autopilot tests")
    parser_list.add_argument(
        "-ro", "--run-order", required=False, default=False,
        action="store_true",
        help="List tests in run order, rather than alphabetical order (the "
        "default).")
    parser_list.add_argument(
        "--suites", required=False, action='store_true',
        help="Lists only available suites, not tests contained within the "
        "suite.")
    parser_list.add_argument("suite", nargs="+",
                             help="Specify test suite(s) to run.")

    if have_vis():
        parser_vis = subparsers.add_parser(
            'vis', help="Open the Autopilot visualiser tool")
        parser_vis.add_argument(
            '-v', '--verbose', required=False, default=False, action='count',
            help="Show autopilot log messages. Set twice to also log data "
            "useful for debugging autopilot itself.")

    parser_launch = subparsers.add_parser(
        'launch', help="Launch an application with introspection enabled")
    parser_launch.add_argument(
        '-i', '--interface', choices=('Gtk', 'Qt', 'Auto'), default='Auto',
        help="Specify which introspection interface to load. The default"
        "('Auto') uses ldd to try and detect which interface to load.")
    parser_launch.add_argument(
        '-v', '--verbose', required=False, default=False, action='count',
        help="Show autopilot log messages. Set twice to also log data useful "
        "for debugging autopilot itself.")
    parser_launch.add_argument(
        'application', action=_OneOrMoreArgumentStoreAction, type=str,
        nargs=REMAINDER,
        help="The application to launch. Can be a full path, or just an "
        "application name (in which case Autopilot will search for it in "
        "$PATH).")
    args = parser.parse_args(args=argv)

    # TR - 2013-11-27 - a bug in python3.3 means argparse doesn't fail
    # correctly when no commands are specified.
    # http://bugs.python.org/issue16308
    if args.mode is None:
        parser.error("too few arguments")

    if 'suite' in args:
        args.suite = [suite.rstrip('/') for suite in args.suite]

    return args


class _OneOrMoreArgumentStoreAction(Action):

    def __call__(self,  parser, namespace, values, option_string=None):
        if len(values) == 0:
            parser.error(
                "Must specify at least one argument to the 'launch' command")
        setattr(namespace, self.dest, values)


def have_vis():
    """Return true if the vis package is installed."""
    try:
        from autopilot.vis import vis_main  # flake8: noqa
        return True
    except ImportError:
        return False


def get_version_string():
    version_string = "Autopilot Source Version: " + _get_source_version()
    pkg_version = _get_package_version()
    if pkg_version:
        version_string += "\nAutopilot Package Version: " + pkg_version
    return version_string


def _get_source_version():
    return version


def _get_package_version():
    """Get the version of the currently installed package version, or None.

    Only returns the package version if the package is installed, *and* we seem
    to be running the system-wide installed code.
    """
    if _running_in_system():
        return _get_package_installed_version()
    return None


def _running_in_system():
    """Return True if we're running autopilot from the system installation
    dir."""
    return __file__.startswith('/usr/')


def _get_package_installed_version():
    """Get the version string of the system-wide installed package, or None if
    it is not installed.

    """
    try:
        return subprocess.check_output(
            [
                "dpkg-query",
                "--showformat",
                "${Version}",
                "--show",
                "python-autopilot",
            ],
            universal_newlines=True
        ).strip()
    except subprocess.CalledProcessError:
        return None
