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


try:
    # Python 2
    from StringIO import StringIO
except ImportError:
    # Python 3
    from io import StringIO

import logging
import os.path
import signal
import subprocess

from autopilot._debug import DebugProfile
from autopilot.utilities import LogFormatter, CleanupRegistered

from testtools.content import text_content

logger = logging.getLogger(__name__)


def get_log_verbose():
    """Return true if the user asked for verbose logging."""
    return _test_logger._log_verbose


class _TestLogger(CleanupRegistered):

    """A class that handles adding test logs as test result content."""

    def __init__(self):
        self._log_verbose = False
        self._log_buffer = None

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
        if self._log_buffer is None:
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
        test_instance.addDetail(
            'test-log', text_content(self._log_buffer.getvalue()))
        root_logger.removeHandler(self._log_handler)
        self._log_buffer = None


_test_logger = _TestLogger()


def set_log_verbose(verbose):
    """Set whether or not we should log verbosely."""

    if type(verbose) is not bool:
        raise TypeError("Verbose flag must be a boolean.")
    _test_logger.log_verbose(verbose)


_debug_profile_fixture = DebugProfile


def set_debug_profile_fixture(fixture_class):
    global _debug_profile_fixture
    _debug_profile_fixture = fixture_class


def get_debug_profile_fixture():
    global _debug_profile_fixture
    return _debug_profile_fixture


_default_timeout_value = 10


def set_default_timeout_period(new_timeout):
    global _default_timeout_value
    _default_timeout_value = new_timeout


def get_default_timeout_period():
    global _default_timeout_value
    return _default_timeout_value


_long_timeout_value = 30


def set_long_timeout_period(new_timeout):
    global _long_timeout_value
    _long_timeout_value = new_timeout


def get_long_timeout_period():
    global _long_timeout_value
    return _long_timeout_value
