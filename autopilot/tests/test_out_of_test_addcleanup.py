# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2013 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.

from testtools import TestCase
from testtools.matchers import Equals

from autopilot.testcase import AutopilotTestCase
from autopilot.utilities import addCleanup

log = ''

class AddCleanupTests(TestCase):

    def test_addCleanup_called_with_args_and_kwargs(self):
        """Test that out-of-test addClenaup works as expected, and is passed both
        args and kwargs.

        """
        class InnerTest(AutopilotTestCase):
            def write_to_log(self, *args, **kwargs):
                global log
                log = "Hello %r %r" % (args, kwargs)

            def test_foo(self):
                addCleanup(self.write_to_log, "arg1", 2, foo='bar')

        InnerTest('test_foo').run()
        self.assertThat(log, Equals("Hello ('arg1', 2) {'foo': 'bar'}"))

