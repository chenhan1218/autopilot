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

import fixtures
import logging
import os
import subprocess
import psutil

logger = logging.getLogger(__name__)


class ApplicationLauncher(fixtures.Fixture):
    """A class that knows how to launch an application with a certain type of
    introspection enabled.

    """

    @staticmethod
    def create(**kwargs):
        """
        kwargs must contain one of either:
          *application* - The application that you want to launch
          *package_id* - The Upstart/Click package you want to launch

        All other kwargs will be passed on to the ApplicationLauncher.
        """

        from autopilot.application.launcher._traditional import NormalApplicationLauncher
        from autopilot.application.launcher._click import ClickApplicationLauncher
        application = kwargs.pop('application', None)
        package_id = kwargs.pop('package_id', None)
        if application is not None:
            return NormalApplicationLauncher(application, **kwargs)
        elif package_id is not None:
            return ClickApplicationLauncher(package_id, **kwargs)
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

