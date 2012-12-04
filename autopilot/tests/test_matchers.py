# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2012 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.

from __future__ import absolute_import

from autopilot.testcase import AutopilotTestCase
from autopilot.matchers import Eventually

from testtools import ExpectedException
from testtools.matchers import Equals, LessThan, MismatchError
from time import time

class EventuallyMatcherTests(AutopilotTestCase):

    def test_matcher_raises_MismatchError(self):
        """Eventually matcher must raise an MismatchError."""
        with ExpectedException(MismatchError):
            Eventually(Equals(True)).match(lambda: False)

    def test_eventually_default_timeout(self):
        """Eventually matcher must default to 10 second timeout."""
        start = time()
        with ExpectedException(MismatchError):
            Eventually(Equals(True)).match(lambda: False)
        # max error of 1 second seems reasonable:
        self.assertThat(abs(time() - start - 10.0), LessThan(1))

    def test_eventually_passes_immeadiately(self):
        """Eventually matcher must not wait if the assertion passes initially."""
        start = time()

        Eventually(Equals(True)).match(lambda: True)
        # max error of 1 second seems reasonable:
        self.assertThat(abs(time() - start), LessThan(1))

    def test_eventually_matcher_allows_non_default_timeout(self):
        """Eventually matcher must allow a non-default timeout value."""
        start = time()
        with ExpectedException(MismatchError):
            Eventually(Equals(True), timeout=5).match(lambda: False)
        # max error of 1 second seems reasonable:
        self.assertThat(abs(time() - start - 5.0), LessThan(1))
