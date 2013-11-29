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

from __future__ import absolute_import

import logging

from autopilot.globals import get_log_verbose
from testtools import (
    ExtendedToOriginalDecorator,
    TestResultDecorator,
    TextTestResult,
)


class LoggedTestResultDecorator(TestResultDecorator):
    """A decorator that logs messages to python's logging system."""

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
        self._log(logging.INFO, "OK: %s" % (test.id()))
        return super(LoggedTestResultDecorator, self).addSuccess(test, details)

    def addError(self, test, err=None, details=None):
        self._log(logging.ERROR, "ERROR: %s" % (test.id()))
        if hasattr(test, "getDetails"):
            self._log_details(logging.ERROR, test.getDetails())
        return super(type(self), self).addError(test, err, details)

    def addFailure(self, test, err=None, details=None):
        """Called for a test which failed an assert"""
        self._log(logging.ERROR, "FAIL: %s" % (test.id()))
        if hasattr(test, "getDetails"):
            self._log_details(logging.ERROR, test.getDetails())
        return super(type(self), self).addFailure(test, err, details)


def get_output_formats():
    """Get information regarding the different output formats supported."""
    supported_formats = {}

    supported_formats['text'] = (
        "Text output",
        lambda *args, **kwargs: LoggedTestResultDecorator(
            TextTestResult(*args, **kwargs)
        ),
    )

    try:
        from junitxml import JUnitXmlResult
        supported_formats['xml'] = (
            "JUnitXml output",
            lambda *args, **kwargs: LoggedTestResultDecorator(
                ExtendedToOriginalDecorator(
                    JUnitXmlResult(*args, **kwargs)
                )
            ),
        )
    except ImportError:
        pass
    return supported_formats


def get_default_format():
    return 'text'


def get_output_format(format):
    """Return a Result object for each format we support."""

    if format == "text":
        return type('VerboseTextTestResult', (TextTestResult,),
                    dict(AutopilotVerboseResult.__dict__))

    elif format == "xml":
        from junitxml import JUnitXmlResult
        return type('VerboseXmlResult', (JUnitXmlResult,),
                    dict(AutopilotVerboseResult.__dict__))

    raise KeyError("Unknown format name '%s'" % format)
