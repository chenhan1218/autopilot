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

from autopilot.introspection import _search as _s

from mock import Mock
from testtools import TestCase
from testtools.matchers import (
    Equals,
    raises,
)


class FilterTests(TestCase):

    def test_can_provide_list_of_filters_to_FilterRunner(self):
        _s.FilterRunner([_s.PassingFilter])

    def test_passing_empty_filter_list_raises(self):
        self.assertThat(
            lambda: _s.FilterRunner([]),
            raises(ValueError("Filter list must not be empty"))
        )

    def test_can_run_can_be_called(self):
        runner = _s.FilterRunner([_s.PassingFilter])

        runner.run()
