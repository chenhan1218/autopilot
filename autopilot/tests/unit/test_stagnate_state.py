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
from testtools.matchers import Equals, raises
from autopilot.input import StagnantStateDetector


class StagnantCheckTests(TestCase):

    def test_state_change_resets_counter(self):
        state_check = StagnantStateDetector(threshold=5)
        x, y = (1, 1)
        for i in xrange(1, 5):
            state_check.check_state(x, y)
        self.assertThat(state_check._stagnant_count, Equals(3))

        state_check.check_state(10, 10)
        self.assertThat(state_check._stagnant_count, Equals(0))

    def test_raises_exception_when_threshold_hit(self):
        state_check = StagnantStateDetector(threshold=1)

        x, y = (1, 1)
        state_check.check_state(x, y)

        fn = lambda: state_check.check_state(x, y)
        self.assertThat(
            fn,
            raises(
                StagnantStateDetector.StagnantState(
                    "State has been the same for 1 iterations"
                )
            )
        )

    def test_raises_exception_when_thresold_is_zero(self):
        fn = lambda: StagnantStateDetector(threshold=0)
        self.assertThat(
            fn,
            raises(ValueError("Threshold must be greater than 0"))
        )
