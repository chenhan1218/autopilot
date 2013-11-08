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

from __future__ import absolute_import

import logging

import testtools

from autopilot.logging import log_action


class LogHandlerTestCase(testtools.TestCase):
    """A mixin that adds a memento loghandler for testing logging.

    Originally written by:
     - Guillermo Gonzalez
     - Facundo Batista
     - Natalia Bidart

    """

    class MementoHandler(logging.Handler):
        """A handler class which stores logging records in a list."""
        def __init__(self, *args, **kwargs):
            """Create the instance, and add a records attribute."""
            logging.Handler.__init__(self, *args, **kwargs)
            self.records = []

        def emit(self, record):
            """Just add the record to self.records."""
            self.records.append(record)

        def check(self, level, msg, check_traceback=False):
            """Check that something is logged."""
            result = False
            for rec in self.records:
                if rec.levelname == level:
                    result = str(msg) in rec.getMessage()
                    if not result and check_traceback:
                        result = str(msg) in rec.exc_text
                    if result:
                        break

            return result

    def setUp(self):
        """Add the memento handler to the root logger."""
        super(LogHandlerTestCase, self).setUp()
        self.memento_handler = self.MementoHandler()
        self.root_logger = logging.getLogger()
        self.root_logger.addHandler(self.memento_handler)

    def tearDown(self):
        """Remove the memento handler from the root logger."""
        self.root_logger.removeHandler(self.memento_handler)
        super(LogHandlerTestCase, self).tearDown()

    def assertLogLevelContains(self, level, message, check_traceback=False):
        check = self.memento_handler.check(
            level, message, check_traceback=check_traceback)

        msg = ('Expected logging message/s could not be found:\n%s\n'
               'Current logging records are:\n%s')
        expected = '\t%s: %s' % (level, message)
        records = ['\t%s: %s' % (r.levelname, r.getMessage())
                   for r in self.memento_handler.records]
        self.assertTrue(check, msg % (expected, '\n'.join(records)))


class ObjectWithLogDecorator(object):

    @log_action(logging.info)
    def do_something_without_docstring(self, *args, **kwargs):
        pass

    @log_action(logging.info)
    def do_something_with_docstring(self, *args, **kwargs):
        """Do something with docstring."""
        pass

    @log_action(logging.info)
    def do_something_with_multiline_docstring(self, *args, **kwargs):
        """Do something with a multiline docstring.

        This should not be logged.
        """
        pass


class LoggingTestCase(LogHandlerTestCase):

    def setUp(self):
        super(LoggingTestCase, self).setUp()
        self.root_logger.setLevel(logging.INFO)
        self.logged_object = ObjectWithLogDecorator()

    def test_logged_action_without_docstring(self):
        self.logged_object.do_something_without_docstring(
            'arg1', 'arg2', arg3='arg3', arg4='arg4')
        self.assertLogLevelContains(
            'INFO',
            "ObjectWithLogDecorator: do_something_without_docstring. "
            "Arguments ('arg1', 'arg2'). "
            "Keyword arguments: {'arg3': 'arg3', 'arg4': 'arg4'}.")

    def test_logged_action_with_docstring(self):
        self.logged_object.do_something_with_docstring(
            'arg1', 'arg2', arg3='arg3', arg4='arg4')
        self.assertLogLevelContains(
            'INFO',
            "ObjectWithLogDecorator: Do something with docstring. "
            "Arguments ('arg1', 'arg2'). "
            "Keyword arguments: {'arg3': 'arg3', 'arg4': 'arg4'}.")

    def test_logged_action_with_multiline_docstring(self):
        self.logged_object.do_something_with_multiline_docstring(
            'arg1', 'arg2', arg3='arg3', arg4='arg4')
        self.assertLogLevelContains(
            'INFO',
            "ObjectWithLogDecorator: "
            "Do something with a multiline docstring. "
            "Arguments ('arg1', 'arg2'). "
            "Keyword arguments: {'arg3': 'arg3', 'arg4': 'arg4'}.")
