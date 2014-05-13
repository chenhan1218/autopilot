# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2012-2014 Canonical
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

import fixtures
import logging
import os


logger = logging.getLogger(__name__)


class RMDVideoLogFixture(fixtures.Fixture):

    """Video capture autopilot tests, saving the results if the test failed."""

    _recording_app = '/usr/bin/recordmydesktop'
    _recording_opts = ['--no-sound', '--no-frame', '-o']
    _record_directory = '/tmp/autopilot'

    def __init__(self, recording_directory):
        self.recording_directory = recording_directory

    def setUp(self):
        super(RMDVideoLogFixture, self).setUp()

        if not self._have_recording_app():
            logger.warning(
                "Disabling video capture since '%s' is not present",
                self._recording_app)

    def __call__(self, test_instance):
        self._test_passed = True
        self.addOnException(self._on_test_failed)
        self.addCleanup(self._stop_video_capture, test_instance)
        self._start_video_capture(test_instance.shortDescription())

    def _have_recording_app(self):
        return os.path.exists(self._recording_app)

    def _start_video_capture(self, test_id):
        args = self.get_capture_command_line()
        self._capture_file = os.path.join(
            self.recording_directory,
            '%s.ogv' % (test_id)
        )
        self._ensure_directory_exists_but_not_file(self._capture_file)
        args.append(self._capture_file)
        logger.debug("Starting: %r", args)
        self._capture_process = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )

    def _stop_video_capture(self, test_instance):
        """Stop the video capture. If the test failed, save the resulting
        file."""

        if self._test_passed:
            # SIGABRT terminates the program and removes
            # the specified output file.
            self._capture_process.send_signal(signal.SIGABRT)
            self._capture_process.wait()
        else:
            self._capture_process.terminate()
            self._capture_process.wait()
            if self._capture_process.returncode != 0:
                test_instance.addDetail(
                    'video capture log',
                    text_content(self._capture_process.stdout.read()))
        self._capture_process = None
        self._currently_recording_description = None

    def _ensure_directory_exists_but_not_file(self, file_path):
        dirpath = os.path.dirname(file_path)
        if not os.path.exists(dirpath):
            os.makedirs(dirpath)
        elif os.path.exists(file_path):
            logger.warning(
                "Video capture file '%s' already exists, deleting.", file_path)
            os.remove(file_path)

    def _on_test_failed(self, ex_info):
        """Called when a test fails."""
        from unittest.case import SkipTest
        failure_class_type = ex_info[0]
        if failure_class_type is not SkipTest:
            self._test_passed = False

    def get_capture_command_line(self):
        return [self._recording_app] + self._recording_opts
