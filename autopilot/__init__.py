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

version = '1.3'


class BackendException(RuntimeError):

    """An error occured while trying to initialise an autopilot backend."""

    def __init__(self, original_exception):
        super(BackendException, self).__init__(
            "Error while initialising backend. Original exception was: " \
            + original_exception.message
            )
        self.original_exception = original_exception


def parse_arguments(argv=None):
    """Parse command-line arguments, and return an argparse arguments
    object.
    """
    parser = ArgumentParser(description="Autopilot test tool.")
    subparsers = parser.add_subparsers(help='Run modes', dest="mode")

    parser_run = subparsers.add_parser('run', help="Run autopilot tests")
    parser_run.add_argument('-o', "--output", required=False,
                            help='Write test result report to file.\
                            Defaults to stdout.\
                            If given a directory instead of a file will \
                            write to a file in that directory named: \
                            <hostname>_<dd.mm.yyy_HHMMSS>.log')
    parser_run.add_argument('-f', "--format", choices=['text', 'xml'],
                            default='text',
                            required=False,
                            help='Specify desired output format. \
                            Default is "text".')
    parser_run.add_argument('-r', '--record', action='store_true',
                            default=False, required=False,
                            help="Record failing tests. Required \
                            'recordmydesktop' app to be installed.\
                            Videos are stored in /tmp/autopilot.")
    parser_run.add_argument("-rd", "--record-directory", required=False,
                            default="/tmp/autopilot", type=str,
                            help="Directory to put recorded tests \
                            (only if -r) specified.")
    parser_run.add_argument('-v', '--verbose', default=False, required=False,
                            action='count',
                            help="If set, autopilot will output test log data \
                            to stderr during a test run. Set twice to also log \
                            data useful for debugging autopilot itself.")
    parser_run.add_argument("suite", nargs="+",
                            help="Specify test suite(s) to run.")

    parser_list = subparsers.add_parser('list', help="List autopilot tests")
    parser_list.add_argument("-ro", "--run-order", required=False, default=False,
                            action="store_true",
                            help="List tests in run order, rather than alphabetical \
                            order (the default).")
    parser_list.add_argument("--suites", required=False, action='store_true',
                             help="Lists only available suites, not tests contained \
                             within the suite.")
    parser_list.add_argument("suite", nargs="+",
                             help="Specify test suite(s) to run.")

    if have_vis():
        parser_vis = subparsers.add_parser('vis',
                                          help="Open the Autopilot visualiser tool")
        parser_vis.add_argument('-v', '--verbose', required=False, default=False,
                                action='count', help="Show autopilot log messages. \
                                Set twice to also log data useful for debugging \
                                autopilot itself.")

    parser_launch = subparsers.add_parser('launch',
                            help="Launch an application with introspection enabled")
    parser_launch.add_argument('-i', '--interface',
                            choices=('Gtk', 'Qt', 'Auto'), default='Auto',
                            help="Specify which introspection interface to load. \
                            The default ('Auto') uses ldd to try and detect which \
                            interface to load.")
    parser_launch.add_argument('-v', '--verbose', required=False, default=False,
                            action='count', help="Show autopilot log messages. \
                            Set twice to also log data useful for debugging \
                            autopilot itself.")
    parser_launch.add_argument('application', action=_OneOrMoreArgumentStoreAction,
                            type=str, nargs=REMAINDER,
                            help="The application to launch. Can be a full path, \
                            or just an application name (in which case Autopilot \
                                will search for it in $PATH).")
    args = parser.parse_args(args=argv)

    return args


class _OneOrMoreArgumentStoreAction(Action):

    def __call__(self,  parser, namespace, values, option_string=None):
        if len(values) == 0:
            parser.error("Must specify at least one argument to the 'launch' command")
        setattr(namespace, self.dest, values)


def have_vis():
    """Return true if the vis package is installed."""
    try:
        from autopilot.vis import vis_main
        return True
    except ImportError:
        return False
