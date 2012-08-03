# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2012 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.

from __future__ import absolute_import

from testtools import TestCase
from testtools.matchers import Is, Not

from autopilot.introspection.qt import QtIntrospectionTestMixin


class ApplicationSupportTests(TestCase):

    def test_can_create(self):
        mixin = QtIntrospectionTestMixin()
        self.assertThat(mixin, Not(Is(None)))
