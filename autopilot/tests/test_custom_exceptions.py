# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2013 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.


from testtools import TestCase
from testtools.matchers import Equals, IsInstance

from autopilot import BackendException

class BackendExceptionTests(TestCase):

    def test_must_wrap_exception(self):
        """BackendException must be able to wrap another exception instance."""
        err = BackendException(RuntimeError("Hello World"))
        self.assertThat(err.original_exception, IsInstance(RuntimeError))
        self.assertThat(err.original_exception.message, Equals("Hello World"))

    def test_dunder_str(self):
        err = BackendException(RuntimeError("Hello World"))
        self.assertThat(str(err),
            Equals("Error while initialising backend. Original exception was: Hello World"))

    def test_dunder_repr(self):
        err = BackendException(RuntimeError("Hello World"))
        self.assertThat(repr(err),
            Equals("BackendException('Error while initialising backend. Original exception was: Hello World',)"))
