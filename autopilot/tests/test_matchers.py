# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2012 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.

from __future__ import absolute_import

from autopilot.introspection.dbus import DBusIntrospectionObject
from autopilot.matchers import Eventually
from autopilot.testcase import AutopilotTestCase

import dbus
from testtools.matchers import Equals, IsInstance, LessThan, Mismatch, raises
from time import time

class EventuallyMatcherTests(AutopilotTestCase):

    scenarios = [
        ('callable', dict(attribute_type='callable')),
        ('wait_for', dict(attribute_type='wait_for')),
    ]

    def make_fake_attribute_with_result(self, result):
        """Make a fake attribute with the given result.

        This will either return a callable, or an attribute patched with a
        wait_for method, according to the current test scenario.

        """
        class FakeObject(DBusIntrospectionObject):

            def __init__(self, props):
                super(FakeObject, self).__init__(props)
                FakeObject._fake_props = props

            @classmethod
            def get_state_by_path(cls, piece):
                return [('FakeObject', cls._fake_props)]

        if self.attribute_type == 'callable':
            return lambda: result
        elif self.attribute_type == 'wait_for':
            obj = FakeObject(dict(id=123,attr=dbus.Boolean(result)))
            return obj.attr

    def test_eventually_matcher_returns_Mismatch(self):
        """Eventually matcher must return a Mismatch."""
        attr = self.make_fake_attribute_with_result(False)
        e = Eventually(Equals(True)).match(lambda: attr)

        self.assertThat(e, IsInstance(Mismatch))

    def test_eventually_default_timeout(self):
        """Eventually matcher must default to 10 second timeout."""
        attr = self.make_fake_attribute_with_result(False)
        start = time()
        Eventually(Equals(True)).match(attr)
        # max error of 1 second seems reasonable:
        self.assertThat(abs(time() - start - 10.0), LessThan(1))

    def test_eventually_passes_immeadiately(self):
        """Eventually matcher must not wait if the assertion passes initially."""
        start = time()
        attr = self.make_fake_attribute_with_result(True)
        Eventually(Equals(True)).match(attr)
        # max error of 1 second seems reasonable:
        self.assertThat(abs(time() - start), LessThan(1))

    def test_eventually_matcher_allows_non_default_timeout(self):
        """Eventually matcher must allow a non-default timeout value."""
        start = time()
        attr = self.make_fake_attribute_with_result(False)
        Eventually(Equals(True), timeout=5).match(attr)
        # max error of 1 second seems reasonable:
        self.assertThat(abs(time() - start - 5.0), LessThan(1))


class EventuallyNonScenariodTests(AutopilotTestCase):

    def test_eventually_matcher_raises_ValueError_on_unknown_kwargs(self):
        self.assertThat(lambda: Eventually(Equals(True), foo=123), raises(ValueError))
