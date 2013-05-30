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


from testtools import TestCase
from testtools.matchers import Equals, NotEquals
from mock import patch

from autopilot.utilities import CleanupRegistered, _cleanup_objects
from autopilot.testcase import AutopilotTestCase


calling_test = None
_on_start_test = False
_on_end_test = False

_should_throw_exception = False

class StartFinalExecutionTests(TestCase):

    def test_conformant_class_is_added(self):
        class Conformant(CleanupRegistered):
            pass

        self.assertTrue(Conformant in _cleanup_objects)

    def test_not_defining_class_methods_doesnt_except(self):
        class Conformant(CleanupRegistered):
            """This class defines the required classmethods"""

        class InnerTest(AutopilotTestCase):
            def test_foo(self):
                global calling_test
                calling_test = self

        test_run = InnerTest('test_foo').run()

        with patch.object(Conformant, 'on_test_start') as on_test_start:
            with patch.object(Conformant, 'on_test_end') as on_test_end:
                InnerTest('test_foo').run()
                self.assertTrue(test_run.wasSuccessful())
                on_test_start.assert_called_once_with(calling_test)
                on_test_end.assert_called_once_with(calling_test)

    def test_on_test_start_and_end_methods_called(self):
        class Conformant(CleanupRegistered):
            """This class defines the required classmethods"""
            @classmethod
            def on_test_start(cls, test_instance):
                global _on_start_test
                _on_start_test = True

            @classmethod
            def on_test_end(cls, test_instance):
                global _on_end_test
                _on_end_test = True

        class InnerTest(AutopilotTestCase):
            def test_foo(self):
                global calling_test
                calling_test = self

        test_run = InnerTest('test_foo').run()

        InnerTest('test_foo').run()
        self.assertTrue(test_run.wasSuccessful())
        self.assertTrue(_on_start_test)
        self.assertTrue(_on_end_test)

    def test_on_test_start_raises_exception_handled_nicely(self):
        class Conformant(CleanupRegistered):
            """This class defines the required classmethods"""
            @classmethod
            def on_test_end(cls, test_instance):
                if _should_throw_exception:
                    print "@@@@THROWING!!!!"
                    raise IndexError

        class InnerTest(AutopilotTestCase):
            def test_foo(self):
                global calling_test
                calling_test = self

        def _set_throw_exception_false():
            global _should_throw_exception
            _should_throw_exception = False

        global _should_throw_exception
        _should_throw_exception = True

        self.addCleanup(_set_throw_exception_false)

        test_run = InnerTest('test_foo').run()

        InnerTest('test_foo').run()
        self.assertTrue(test_run.wasSuccessful())
