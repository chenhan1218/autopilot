# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2012-2013 Canonical
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


from __future__ import absolute_import

from autopilot.introspection.dbus import DBusIntrospectionObject
from autopilot.matchers import Eventually

import dbus
from testscenarios import TestWithScenarios
from testtools import TestCase
from testtools.matchers import (
    Contains,
    Equals,
    IsInstance,
    LessThan,
    MatchesException,
    Mismatch,
    Raises,
)
from time import time


def make_fake_attribute_with_result(result, attribute_type='wait_for'):
    """Make a fake attribute with the given result.

    This will either return a callable, or an attribute patched with a
    wait_for method, according to the current test scenario.

    """
    class FakeObject(DBusIntrospectionObject):
        def __init__(self, props):
            super(FakeObject, self).__init__(props, "/FakeObject")
            FakeObject._fake_props = props

        @classmethod
        def get_state_by_path(cls, piece):
            return [('/FakeObject', cls._fake_props)]

    if attribute_type == 'callable':
        return lambda: result
    elif attribute_type == 'wait_for':
        if isinstance(result, bool):
            obj = FakeObject(dict(id=123, attr=dbus.Boolean(result)))
            return obj.attr
        else:
            obj = FakeObject(dict(id=123, attr=result))
            return obj.attr


class ObjectPatchingMatcherTests(TestCase):
    """Ensure the core functionality the matchers use is correct."""

    def test_default_wait_for_args(self):
        """Ensure we can call wait_for with the correct arg."""
        intro_obj = make_fake_attribute_with_result(False)
        intro_obj.wait_for(False)


class EventuallyMatcherTests(TestWithScenarios, TestCase):

    scenarios = [
        ('callable', dict(attribute_type='callable')),
        ('wait_for', dict(attribute_type='wait_for')),
    ]

    def test_eventually_matcher_returns_Mismatch(self):
        """Eventually matcher must return a Mismatch."""
        attr = make_fake_attribute_with_result(False, self.attribute_type)
        e = Eventually(Equals(True)).match(lambda: attr)

        self.assertThat(e, IsInstance(Mismatch))

    def test_eventually_default_timeout(self):
        """Eventually matcher must default to 10 second timeout."""
        attr = make_fake_attribute_with_result(False, self.attribute_type)
        start = time()
        Eventually(Equals(True)).match(attr)
        # max error of 1 second seems reasonable:
        self.assertThat(abs(time() - start - 10.0), LessThan(1))

    def test_eventually_passes_immeadiately(self):
        """Eventually matcher must not wait if the assertion passes
        initially."""
        start = time()
        attr = make_fake_attribute_with_result(True, self.attribute_type)
        Eventually(Equals(True)).match(attr)
        # max error of 1 second seems reasonable:
        self.assertThat(abs(time() - start), LessThan(1))

    def test_eventually_matcher_allows_non_default_timeout(self):
        """Eventually matcher must allow a non-default timeout value."""
        start = time()
        attr = make_fake_attribute_with_result(False, self.attribute_type)
        Eventually(Equals(True), timeout=5).match(attr)
        # max error of 1 second seems reasonable:
        self.assertThat(abs(time() - start - 5.0), LessThan(1))

    def test_mismatch_message_has_correct_timeout_value(self):
        """The mismatch value must have the correct timeout value in it."""
        attr = make_fake_attribute_with_result(False, self.attribute_type)
        mismatch = Eventually(Equals(True), timeout=1).match(attr)
        self.assertThat(
            mismatch.describe(), Contains("After 1.0 seconds test"))


class EventuallyNonScenariodTests(TestCase):

    def test_eventually_matcher_raises_ValueError_on_unknown_kwargs(self):
        self.assertThat(
            lambda: Eventually(Equals(True), foo=123),
            Raises(MatchesException(
                ValueError, "Unknown keyword arguments: foo")))

    def test_match_with_expected_value_unicode(self):
        """The mismatch value must have the correct timeout value in it."""
        start = time()
        attr = make_fake_attribute_with_result(
            unicode(str("阿布从").decode('utf8')), 'wait_for')
        print attr
        Eventually(
            Equals(unicode(u'\u963f\u5e03\u4ece').encode('utf8'))).match(attr)
        #this should not take more than 1 second
        self.assertThat(abs(time() - start), LessThan(1))

    def test_match_with_new_value_unicode(self):
        """The mismatch value must have the correct timeout value in it."""
        start = time()
        attr = make_fake_attribute_with_result(
            str("阿布从"), 'wait_for')
        print attr
        Eventually(Equals(unicode(u'\u963f\u5e03\u4ece'))).match(attr)
        # this should not take more than 1 second
        self.assertThat(abs(time() - start), LessThan(1))

    def test_mismatch_with_bool(self):
        """The mismatch value must have the correct timeout value in it."""
        attr = make_fake_attribute_with_result(False, 'wait_for')
        mismatch = Eventually(Equals(True), timeout=1).match(attr)
        self.assertThat(
            mismatch.describe(), Contains("failed"))

    def test_mismatch_with_unicode(self):
        """The mismatch value must have the correct timeout value in it."""
        attr = make_fake_attribute_with_result(str("阿布从1"), 'wait_for')
        mismatch = Eventually(Equals(
            unicode(u'\u963f\u5e03\u4ece')), timeout=.5).match(attr)
        self.assertThat(
            mismatch.describe(), Contains('failed'))

    def test_output_utf8(self):
        """The mismatch value must have the correct timeout value in it."""
        self.skip("output is in utf8")
        attr = make_fake_attribute_with_result(str("阿布从1"), 'wait_for')
        mismatch = Eventually(Equals(
            unicode(u'\u963f\u5e03\u4ece')), timeout=.5).match(attr)
        self.assertThat(
            mismatch.describe(), Contains("阿布从11"))
