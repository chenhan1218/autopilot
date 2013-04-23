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


"""Autopilot test result classes"""

import logging
import sys

from autopilot.globals import get_log_verbose


class AutopilotVerboseResult(object):
    """A result class that logs failures, errors and success via the python logging framework."""

    def _log(self, level, message):
        """Performs the actual message logging"""
        if get_log_verbose():
            logging.getLogger().log(level, message)

    def _log_details(self, level, details):
        """Logs the relavent test details"""
        for detail in details:
            # Skip the test-log as it was logged while the test executed
            if detail == "test-log":
                continue
            text = "%s: {{{\n%s}}}" % (detail, details[detail].as_text())
            self._log(level, text)

    def addSuccess(self, test, details=None):
        """Called for a successful test"""
        # Allow for different calling syntax used by the base class.
        if details is None:
            super(type(self), self).addSuccess(test)
        else:
            super(type(self), self).addSuccess(test, details)
        self._log(logging.INFO, "OK: %s" % (test.id()))

    def addError(self, test, err=None, details=None):
        """Called for a test which failed with an error"""
        # Allow for different calling syntax used by the base class.
        # The xml path only uses 'err'. Use of 'err' can be
        # forced by raising TypeError when it is not specified.
        if err is None:
            raise TypeError
        if details is None:
            super(type(self), self).addError(test, err)
        else:
            super(type(self), self).addError(test, err, details)
        self._log(logging.ERROR, "ERROR: %s" % (test.id()))
        if hasattr(test, "getDetails"):
            self._log_details(logging.ERROR, test.getDetails())

    def addFailure(self, test, err=None, details=None):
        """Called for a test which failed an assert"""
        # Allow for different calling syntax used by the base class.
        # The xml path only uses 'err' or 'details'. Use of 'err' can be
        # forced by raising TypeError when it is not specified.
        if err is None:
            raise TypeError
        if details is None:
            super(type(self), self).addFailure(test, err)
        else:
            super(type(self), self).addFailure(test, err, details)
        self._log(logging.ERROR, "FAIL: %s" % (test.id()))
        if hasattr(test, "getDetails"):
            self._log_details(logging.ERROR, test.getDetails())
