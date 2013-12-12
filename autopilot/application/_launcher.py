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

"""Base package for application launchers."""

import signal
from time import sleep
from testtools.content import content_from_file, text_content
import json
import fixtures
import logging
import os
import subprocess
import psutil

from autopilot.application.environment import ApplicationEnvironment
from autopilot.application.environment._upstart import (
    UpstartApplicationEnvironment
)

from autopilot.introspection import get_proxy_object_for_existing_process


logger = logging.getLogger(__name__)


class ApplicationLauncher(fixtures.Fixture):
    """A class that knows how to launch an application with a certain type of
    introspection enabled.

    """

    @staticmethod
    def create(case_addDetail, **kwargs):
        """
        kwargs must contain one of either:
          *application* - The application that you want to launch
          *package_id* - The Upstart/Click package you want to launch

        All other kwargs will be passed on to the ApplicationLauncher.
        """
        application = kwargs.pop('application', None)
        package_id = kwargs.pop('package_id', None)
        if application is not None:
            return NormalApplicationLauncher(
                case_addDetail,
                application,
                **kwargs
            )
        elif package_id is not None:
            return ClickApplicationLauncher(
                case_addDetail,
                package_id,
                **kwargs
            )
        else:
            raise ValueError("Unsure what application type to launch")

    def launch(self, *arguments):
        raise NotImplementedError("Sub-classes must implement this method.")


def _is_process_running(pid):
    return psutil.pid_exists(pid)


def launch_process(application, args, capture_output, **kwargs):
    """Launch an autopilot-enabled process and return the process object."""
    commandline = [application]
    commandline.extend(args)
    logger.info("Launching process: %r", commandline)
    cap_mode = None
    if capture_output:
        cap_mode = subprocess.PIPE
    process = subprocess.Popen(
        commandline,
        stdin=subprocess.PIPE,
        stdout=cap_mode,
        stderr=cap_mode,
        close_fds=True,
        preexec_fn=os.setsid,
        universal_newlines=True,
        **kwargs
    )
    return process


def _set_upstart_env(key, value):
    subprocess.call([
        "/sbin/initctl",
        "set-env",
        "{key}={value}".format(key=key, value=value),
    ])


def _unset_upstart_env(key):
    subprocess.call([
        "/sbin/initctl",
        "unset-env",
        "QT_LOAD_TESTABILITY",
    ])


class ClickApplicationLauncher(ApplicationLauncher):
    def __init__(self, case_addDetail, package_id, **kwargs):
        self.case_addDetail = case_addDetail
        self.app_name = kwargs.pop('app_name', None)
        self.package_id = package_id
        self.app_id = _get_click_app_id(package_id, self.app_name)

        self._app_env = self.useFixture(UpstartApplicationEnvironment())

        self.emulator_base = kwargs.pop('emulator_base', None)

    def launch(self, *arguments):
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
            lambda: self.case_addDetail(
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


class NormalApplicationLauncher(ApplicationLauncher):
    def __init__(self, case_addDetail, application, **kwargs):
        super(NormalApplicationLauncher, self).__init__()
        self.case_addDetail = case_addDetail

        # self.app_path = app_path
        # kwargs['app_path'] = app_path
        kwargs['application'] = application
        self.app_path = application       # Need to sort this out, application or application path. . .

        self.kwargs = kwargs

        self.cwd = kwargs.pop('launch_dir', None)
        self.capture_output = kwargs.pop('capture_output', True)

    def setUp(self):
        super(NormalApplicationLauncher, self).setUp()
        self._app_env = self.useFixture(
            ApplicationEnvironment.create(**self.kwargs)
        )

    def launch(self, arguments):
        app_path, arguments = self._app_env.prepare_environment(
            self.app_path,
            arguments,
        )
        self._process = launch_process(
            self.app_path,
            arguments,
            self.capture_output,
            cwd=self.cwd,
        )

        self.addCleanup(self._kill_process_and_attach_logs, self._process)
        # return get_autopilot_proxy_object_for_process({})

    def _kill_process_and_attach_logs(self, process):
        stdout, stderr, return_code = _kill_process(process)
        self.case_addDetail(
            'process-return-code',
            text_content(str(return_code))
        )
        self.case_addDetail('process-stdout', text_content(stdout))
        self.case_addDetail('process-stderr', text_content(stderr))


def _kill_process(process):
    """Kill the process, and return the stdout, stderr and return code."""
    stdout = ""
    stderr = ""
    logger.info("waiting for process to exit.")
    try:
        logger.info("Killing process %d", process.pid)
        os.killpg(process.pid, signal.SIGTERM)
    except OSError:
        logger.info("Appears process has already exited.")
    for i in range(10):
        tmp_out, tmp_err = process.communicate()
        stdout += tmp_out
        stderr += tmp_err
        if not _is_process_running(process.pid):
            break
        if i == 9:
            logger.info(
                "Killing process group, since it hasn't exited after "
                "10 seconds."
            )
            os.killpg(process.pid, signal.SIGKILL)
        sleep(1)
    return stdout, stderr, process.returncode
