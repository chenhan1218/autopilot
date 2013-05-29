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

from autopilot.utilities import BaseClassForCleanup, _cleanup_objects
from autopilot.testcase import AutopilotTestCase


calling_test = None


class StartFinalExecutionTests(TestCase):

    def test_nonconformant_class_isnt_added(self):
        class MyNonconformant(BaseClassForCleanup):
            """This class doesn't define the required classmethods"""
            pass

        self.assertFalse(type(MyNonconformant()) in _cleanup_objects)

    def test_half_conformant_class_not_added(self):
        class HalfConformantStart(BaseClassForCleanup):
            """This class only on_test_start required classmethod"""
            @classmethod
            def on_test_start(cls, test_instance):
                pass

        class HalfConformantEnd(BaseClassForCleanup):
            """This class only on_test_end required classmethod"""
            @classmethod
            def on_test_End(cls, test_instance):
                pass

        self.assertFalse(type(HalfConformantStart()) in _cleanup_objects)
        self.assertFalse(type(HalfConformantEnd()) in _cleanup_objects)

    def test_conformant_class_is_added(self):
        class Conformant(BaseClassForCleanup):
            """This class does define the required classmethods"""
            @classmethod
            def on_test_start(cls, test_instance):
                pass

            @classmethod
            def on_test_end(cls, test_instance):
                pass

        self.assertTrue(type(Conformant()) in _cleanup_objects)

    def test_on_test_start_and_end_methods_called(self):
        class Conformant(BaseClassForCleanup):
            """This class defines the required classmethods"""
            @classmethod
            def on_test_start(cls, test_instance):
                pass

            @classmethod
            def on_test_end(cls, test_instance):
                pass

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


