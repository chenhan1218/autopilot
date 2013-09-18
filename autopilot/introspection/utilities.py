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
from dbus import Interface
import os.path
import subprocess
import json


def _pid_is_running(pid):
    """Check for the existence of a currently running PID.

    :returns: **True** if PID is running **False** otherwise.
    """
    return os.path.exists("/proc/%d" % pid)


def _get_bus_connections_pid(bus, connection_name):
    """Returns the pid for the connection **connection_name** on **bus**

    :raises: **DBusException** if connection_name is invalid etc.

    """
    bus_obj = bus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus')
    bus_iface = Interface(bus_obj, 'org.freedesktop.DBus')
    return bus_iface.GetConnectionUnixProcessID(connection_name)


def translate_state_keys(state_dict):
    """Translates the *state_dict* passed in so the keys are usable as python
    attributes."""
    return {k.replace('-', '_'): v for k, v in state_dict.items()}


def _get_click_manifest():
    """Return the click package manifest as a python list."""
    # get the whole click package manifest every time - it seems fast enough
    # but this is a potential optimisation point for the future:
    click_manifest_str = subprocess.check_output(
        ["click", "list", "--manifest"]
    )
    return json.loads(click_manifest_str)


def _get_click_app_id(package_id, app_name=None):
    for pkg in _get_click_manifest():
        if pkg['name'] == package_id:
            if app_name is None:
                app_name = pkg['hooks'].keys()[0]
            elif app_name not in pkg['hooks']:
                raise RuntimeError(
                    "Application '{}' is not present within the click "
                    "package '{}'.".format(app_name, package_id))

            return "{0}_{1}_{2}".format(package_id, app_name, pkg['version'])
    raise RuntimeError(
        "Unable to find package '{}' in the click manifest."
        .format(package_id)
    )
