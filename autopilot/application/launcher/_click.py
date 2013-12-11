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

import logging
import os
import signal
import subprocess
from time import sleep
from testtools.content import content_from_file
import json

from autopilot.application.launcher import (
    _is_process_running,
    ApplicationLauncher,
)
from autopilot.application.environment._upstart import (
    UpstartApplicationEnvironment
)
from autopilot.introspection import get_proxy_object_for_existing_process


logger = logging.getLogger(__name__)


class ClickApplicationLauncher(ApplicationLauncher):
    def __init__(self, package_id, **kwargs):
        self.app_name = kwargs.pop('app_name', None)
        self.package_id = package_id
        self.app_id = _get_click_app_id(package_id, self.app_name)

        self._app_env = UpstartApplicationEnvironment()

        self.emulator_base = kwargs.pop('emulator_base', None)

    def launch(self, *arguments):
        # _set_upstart_env("QT_LOAD_TESTABILITY", 1)
        self._app_env._app_env.prepare_environment(
            self.app_path,
            arguments,
        )

        self._attach_logs()
        pid = _launch_click_app(self.app_id)
        self.addCleanup(self._kill_pid, pid)

        logger.info(
            "Click package %s has been launched with PID %d",
            self.app_id,
            pid
        )

        # reset the upstart env, and hope no one else launched,
        # or they'll have introspection enabled as well,
        # although this isn't the worth thing in the world.
        # _unset_upstart_env("QT_LOAD_TESTABILITY")

        proxy = get_proxy_object_for_existing_process(
            pid=pid,
            emulator_base=self.emulator_base
        )
        return proxy

    def _attach_logs(self):
        log_dir = os.path.expanduser('~/.cache/upstart/')
        log_name = 'application-click-{}.log'.format(self.app_id)
        log_path = os.path.join(log_dir, log_name)
        self.addCleanup(
            lambda: self.addDetail(
                "Application Log",
                content_from_file(log_path)
            )
        )


def _launch_click_app(app_id):
    subprocess.check_output([
        "/sbin/start",
        "application",
        "APP_ID={}".format(app_id),
    ])

    return _get_click_app_pid(app_id)


def _get_click_app_status(app_id):
    subprocess.check_output([
        "/sbin/initctl",
        "status",
        "application-click",
        "APP_ID={}".format(app_id)
    ])


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


def _get_click_manifest():
    """Return the click package manifest as a python list."""
    # get the whole click package manifest every time - it seems fast enough
    # but this is a potential optimisation point for the future:
    click_manifest_str = subprocess.check_output(
        ["click", "list", "--manifest"]
    )
    return json.loads(click_manifest_str)


def _get_click_app_pid(app_id):
    for i in range(10):
        try:
            list_output = _get_click_app_status(app_id)
        except subprocess.CalledProcessError:
            # application not started yet.
            pass
        else:
            for line in list_output.split('\n'):
                if app_id in line and "start/running" in line:
                    return int(line.split()[-1])
        # give the app time to launch - maybe this is not needed?:
        sleep(1)
    else:
        raise RuntimeError(
            "Could not find autopilot interface for click package"
            " '{}' after 10 seconds.".format(app_id)
        )


def _kill_pid(pid):
    """Kill the process with the specified pid."""
    logger.info("waiting for process to exit.")
    try:
        logger.info("Killing process %d", pid)
        os.killpg(pid, signal.SIGTERM)
    except OSError:
        logger.info("Appears process has already exited.")
    for i in range(10):
        if not _is_process_running(pid):
            break
        if i == 9:
            logger.info(
                "Killing process group, since it hasn't exited after "
                "10 seconds."
            )
            os.killpg(pid, signal.SIGKILL)
        sleep(1)
