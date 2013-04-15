# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2012 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.

from __future__ import absolute_import

from autopilot.testcase import AutopilotTestCase
from testtools.matchers import Is, Not, raises

def dummy_addCleanup(*args, **kwargs):
    pass


class ApplicationSupportTests(AutopilotTestCase):

    def test_launch_with_bad_types_raises_typeerror(self):
        """Calling launch_test_application with something other than a string must
        raise a TypeError"""

        self.assertThat(lambda: self.launch_test_application(1), raises(TypeError))
        self.assertThat(lambda: self.launch_test_application(True), raises(TypeError))
        self.assertThat(lambda: self.launch_test_application(1.0), raises(TypeError))
        self.assertThat(lambda: self.launch_test_application(object()), raises(TypeError))
        self.assertThat(lambda: self.launch_test_application(None), raises(TypeError))
        self.assertThat(lambda: self.launch_test_application([]), raises(TypeError))
        self.assertThat(lambda: self.launch_test_application((None,)), raises(TypeError))

    def test_launch_raises_ValueError_on_unknown_kwargs(self):
        """launch_test_application must raise ValueError when given unknown
        keyword arguments.

        """
        fn = lambda: self.launch_test_application('gedit', arg1=123, arg2='asd')
        self.assertThat(fn, raises(ValueError("Unknown keyword arguments: 'arg1', 'arg2'.")))

    def test_launch_raises_ValueError_on_unknown_kwargs_with_known(self):
        """launch_test_application must raise ValueError when given unknown
        keyword arguments.

        """
        fn = lambda: self.launch_test_application('gedit', arg1=123, arg2='asd', launch_dir='/')
        self.assertThat(fn, raises(ValueError("Unknown keyword arguments: 'arg1', 'arg2'.")))
