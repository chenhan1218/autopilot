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
from StringIO import StringIO
from autopilot.utilities import LogFormatter, CleanupRegistered
from testtools.content import text_content
import subprocess
import os.path
import logging


logger = logging.getLogger(__name__)


def get_log_verbose():
    """Returns true if the user asked for verbose logging."""
    return _test_logger._log_verbose


class _TestLogger(CleanupRegistered):
    """A class that handles adding test logs as test result content."""

    def __init__(self):
        self._log_verbose = False

    def __call__(self, test_instance):
        self._setUpTestLogging(test_instance)
        if self._log_verbose:
            global logger
            logger.info("*" * 60)
            logger.info("Starting test %s", test_instance.shortDescription())

    @classmethod
    def on_test_start(cls, test_instance):
        if _test_logger._log_verbose:
            _test_logger(test_instance)

    def log_verbose(self, verbose):
        self._log_verbose = verbose

    def _setUpTestLogging(self, test_instance):
        self._log_buffer = StringIO()
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        formatter = LogFormatter()
        self._log_handler = logging.StreamHandler(stream=self._log_buffer)
        self._log_handler.setFormatter(formatter)
        root_logger.addHandler(self._log_handler)
        test_instance.addCleanup(self._tearDownLogging, test_instance)

    def _tearDownLogging(self, test_instance):
        root_logger = logging.getLogger()
        self._log_handler.flush()
        self._log_buffer.seek(0)
        test_instance.addDetail('test-log', text_content(self._log_buffer.getvalue()))
        root_logger.removeHandler(self._log_handler)
        # Calling del to remove the handler and flush the buffer.  We are
        # abusing the log handlers here a little.
        del self._log_buffer


_test_logger = _TestLogger()


def set_log_verbose(verbose):
    """Set whether or not we should log verbosely."""

    if type(verbose) is not bool:
        raise TypeError("Verbose flag must be a boolean.")
    _test_logger.log_verbose(verbose)


class _VideoLogger(CleanupRegistered):
    """Video capture autopilot tests, saving the results if the test failed."""

    _recording_app = '/usr/bin/recordmydesktop'
    _recording_opts = ['--no-sound', '--no-frame', '-o',]

    def __init__(self):
        self._enable_recording = False

    def __call__(self, test_instance):
        if not self._have_recording_app():
            logger.warning("Disabling video capture since '%s' is not present", self._recording_app)

        self._test_passed = True
        test_instance.addOnException(self._on_test_failed)
        test_instance.addCleanup(self._stop_video_capture, test_instance)
        self._start_video_capture(test_instance.shortDescription())

    @classmethod
    def on_test_start(cls, test_instance):
        if _video_logger._enable_recording:
            _video_logger(test_instance)

    def enable_recording(self, enable_recording):
        self._enable_recording = enable_recording

    def set_recording_dir(self, directory):
        self.recording_directory = directory

    def _have_recording_app(self):
        return os.path.exists(self._recording_app)

    def _start_video_capture(self, test_id):
        args = self._get_capture_command_line()
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
        """Stop the video capture. If the test failed, save the resulting file."""

        if self._test_passed:
            # We use kill here because we don't want the recording app to start
            # encoding the video file (since we're removing it anyway.)
            self._capture_process.kill()
            self._capture_process.wait()
        else:
            self._capture_process.terminate()
            self._capture_process.wait()
            if self._capture_process.returncode != 0:
                test_instance.addDetail('video capture log', text_content(self._capture_process.stdout.read()))
        self._capture_process = None

    def _get_capture_command_line(self):
        return [self._recording_app] + self._recording_opts

    def _ensure_directory_exists_but_not_file(self, file_path):
        dirpath = os.path.dirname(file_path)
        if not os.path.exists(dirpath):
            os.makedirs(dirpath)
        elif os.path.exists(file_path):
            logger.warning("Video capture file '%s' already exists, deleting.", file_path)
            os.remove(file_path)

    def _on_test_failed(self, ex_info):
        """Called when a test fails."""
        from unittest.case import SkipTest
        failure_class_type = ex_info[0]
        if failure_class_type is not SkipTest:
            self._test_passed = False


_video_logger = _VideoLogger()


def configure_video_recording(enable_recording, record_dir):
    """Configure video logging.

    enable_recording is a boolean, and enables or disables recording globally.
    record_dir is a string that specifies where videos will be stored.

    """
    if type(enable_recording) is not bool:
        raise TypeError("enable_recording must be a boolean.")
    if not isinstance(record_dir, basestring):
        raise TypeError("record_dir must be a string.")

    _video_logger.enable_recording(enable_recording)
    _video_logger.set_recording_dir(record_dir)

