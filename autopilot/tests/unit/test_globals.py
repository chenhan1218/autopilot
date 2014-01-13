# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2014 Canonical
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
from testtools.matchers import Equals

import autopilot.globals as _g


class DebugProfileFunctionTests(TestCase):

    def setUp(self):
        super(DebugProfileFunctionTests, self).setUp()
        # since we're modifying a global in our tests, make sure we restore
        # the original value after each test has run:
        original_value = _g._debug_profile_fixture
        self.addCleanup(
            lambda: setattr(_g, '_debug_profile_fixture', original_value)
        )

    def test_can_set_and_get_fixture(self):
        fake_fixture = object()
        _g.set_debug_profile_fixture(fake_fixture)
        self.assertThat(_g.get_debug_profile_fixture(), Equals(fake_fixture))
