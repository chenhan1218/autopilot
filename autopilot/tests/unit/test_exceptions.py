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
from testtools.matchers import raises, Equals

from autopilot.introspection.dbus import StateNotFoundError


class StateNotFoundTests(TestCase):

    def test_requires_class_name_to_construct(self):
        """You must pass a class name in to the StateNotFoundError exception
        class initialiser in order to construct it.

        """
        self.assertThat(
            lambda: StateNotFoundError(),
            raises(TypeError('__init__() takes exactly 2 arguments (1 given)'))
        )

    def test_can_be_constructed_with_class_name_only(self):
        """Must be able to construct error class with a class name only."""
        err = StateNotFoundError("MyClass")
        self.assertThat(
            err.message,
            Equals("State not found for class 'MyClass'.")
        )
