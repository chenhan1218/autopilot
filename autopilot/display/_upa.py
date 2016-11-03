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
from autopilot.platform import get_display_server

DISPLAY_SERVER_X11 = 'X11'
DISPLAY_SERVER_MIR = 'MIR'
ENV_MIR_SOCKET = 'MIR_SERVER_HOST_SOCKET'


def query_resolution():
    display_server = get_display_server()
    if display_server == DISPLAY_SERVER_X11:
        return _get_resolution_from_xrandr()
    elif display_server == DISPLAY_SERVER_MIR:
        return _get_resolution_from_mirout()
    else:
        raise RuntimeError(
            'Unknown display server. Only {} and {} are supported.'.format(
                DISPLAY_SERVER_MIR,
                DISPLAY_SERVER_X11
            )
        )


def _get_stdout_for_command(command, *args):
    full_command = [command]
    full_command.extend(args)
    return subprocess.check_output(
        full_command,
        universal_newlines=True,
        stderr=subprocess.DEVNULL,
    ).split('\n')


def _get_resolution_from_xrandr():
    xrandr_output = _get_stdout_for_command('xrandr', '--current')
    for line in xrandr_output:
        if '*' in line:
            return _grab_resolution_from_line(line)
    raise ValueError('Something for now')


def _get_resolution_from_mirout():
    mirout_output = _get_stdout_for_command('mirout', _get_unity8_mir_socket())
    grab_resolution = False
    for line in mirout_output:
        if grab_resolution:
            return _grab_resolution_from_line(line)
        if 'connected' in line:
            grab_resolution = True
    raise ValueError('Something for now')


def _get_unity8_mir_socket():
    return os.environ.get(ENV_MIR_SOCKET)


def _grab_resolution_from_line(line):
    return tuple([int(i) for i in line.strip().split()[0].split('x')])


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
