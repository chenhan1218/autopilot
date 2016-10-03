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

import os
import subprocess

from autopilot.display import Display as DisplayBase
from autopilot.introspection.utilities import process_util

DISPLAY_SERVER_X = 'XOrg'
DISPLAY_SERVER_MIR = 'Mir'
ENV_XDG_RUNTIME_DIR = 'XDG_RUNTIME_DIR'
PROCESS_NAME_X_SERVER = 'Xorg'
SOCKET_MIR = 'mir_socket'


def query_resolution():
    display_server = query_current_display_server()
    if display_server == DISPLAY_SERVER_X:
        return _get_resolution_from_xrandr()
    elif display_server == DISPLAY_SERVER_MIR:
        return _get_resolution_from_mirout()
    else:
        raise RuntimeError(
            'Unknown display server. Only {} and {} are supported.'.format(
                DISPLAY_SERVER_MIR,
                DISPLAY_SERVER_X
            )
        )


def _get_resolution_from_xrandr():
    xrandr_stdout = subprocess.check_output(
        ['xrandr', '--current'],
        universal_newlines=True
    ).split('\n')
    for line in xrandr_stdout:
        if '*' in line:
            return _grab_resolution_from_line(line)
    raise ValueError('Something for now')


def _get_process_environ_path(process_name):
    return '/proc/{}/environ'.format(
        process_util.get_pid_for_process(process_name)
    )


def _get_process_environ(process_name):
    with open(_get_process_environ_path(process_name), 'r') as file:
        output = file.read()
    return output.split('\0')


def _get_environ_variable_for_process(variable, process_name):
    all_variables = _get_process_environ(process_name)
    for var in all_variables:
        if var and var.startswith(variable) and \
                var.index('=') == len(variable):
            return var.split('=')[1]


def _get_unity8_mir_socket():
    return _get_environ_variable_for_process('UNITY_MIR_SOCKET', 'unity8')


def _grab_resolution_from_line(line):
    return tuple([int(i) for i in line.strip().split()[0].split('x')])


def _get_resolution_from_mirout():
    mirout_stdout = subprocess.check_output(
        ['mirout', _get_unity8_mir_socket()],
        universal_newlines=True
    ).split('\n')
    grab_resolution = False
    for line in mirout_stdout:
        if grab_resolution:
            return _grab_resolution_from_line(line)
        if 'connected' in line:
            grab_resolution = True
    raise ValueError('Something for now')


def _is_x_server_running():
    if not os.environ.get('DISPLAY'):
        return False
    try:
        return bool(process_util.get_pids_for_process(PROCESS_NAME_X_SERVER))
    except ValueError:
        return False


def _is_mir_based_server_running():
    xdg_dir = os.environ.get(ENV_XDG_RUNTIME_DIR)
    return xdg_dir is not None and os.path.exists(
        os.path.join(xdg_dir, SOCKET_MIR)
    )


def query_current_display_server():
    if _is_x_server_running():
        return DISPLAY_SERVER_X
    elif _is_mir_based_server_running():
        return DISPLAY_SERVER_MIR
    else:
        raise RuntimeError('No or unknown display server running.')


class Display(DisplayBase):
    """The base class/inteface for the display devices"""

    def __init__(self):
        super(Display, self).__init__()
        self._X, self._Y = query_resolution()

    def get_num_screens(self):
        """Get the number of screens attached to the PC."""
        return 1

    def get_primary_screen(self):
        """Returns an integer of which screen is considered the primary"""
        return 0

    def get_screen_width(self):
        return self._X

    def get_screen_height(self):
        return self._Y

    def get_screen_geometry(self, screen_number):
        """Get the geometry for a particular screen.

        :return: Tuple containing (x, y, width, height).

        """
        return 0, 0, self._X, self._Y
