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

from testtools.content import Content, ContentType
import logging
import os
import signal
from time import sleep

from autopilot.application.launcher import (
    _is_process_running,
    ApplicationLauncher,
    launch_process,
)
from autopilot.application.environment import ApplicationEnvironment
from autopilot.introspection import get_autopilot_proxy_object_for_process

logger = logging.getLogger(__name__)


class NormalApplicationLauncher(ApplicationLauncher):
    def __init__(self, application, **kwargs):
        # self.app_path = app_path
        # kwargs['app_path'] = app_path
        super(NormalApplicationLauncher, self).__init__()
        kwargs['application'] = application
        self.app_path = application       # Need to sort this out, application or application path. . .
        self._app_env = self.useFixture(
            ApplicationEnvironment.create(**kwargs)
        )

        self.cwd = kwargs.pop('launch_dir', None)
        self.capture_output = kwargs.pop('capture_output', True)

        self._return_code = None
        self._stdout = ""
        self._stderr = ""

    def setUp(self):
        super(NormalApplicationLauncher, self).setUp()

        content_type = ContentType('text', 'plain')
        self.addDetail('process-return-code', Content(content_type, lambda: str(self._return_code)))
        self.addDetail('process-stdout', Content(content_type, lambda: self._stdout))
        self.addDetail('process-stderr', Content(content_type, lambda: self._stderr))

    def launch(self, arguments):
        app_path, arguments = self._app_env.prepare_environment(
            self.app_path,
            arguments,
        )
        self._process = launch_process(
            self.app_path,
            arguments,
            self.capture_output,
            cwd = self.cwd,
        )

        # self.addCleanup(self._kill_process_and_attach_logs, self._process)
        # return get_autopilot_proxy_object_for_process({})

    def cleanUp(self):
        print ">> Cleanup happening"
        import ipdb; ipdb.set_trace()
        super(NormalApplicationLauncher, self).cleanUp()
        self._stdout, self._stderr, self._return_code = _kill_process(self._process)

    def _kill_process_and_attach_logs(self, process):
        self._stdout, self._stderr, self._return_code = _kill_process(process)
        # self.addDetail('process-return-code', text_content(str(return_code)))
        # self.addDetail('process-stdout', text_content(stdout))
        # self.addDetail('process-stderr', text_content(stderr))


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
