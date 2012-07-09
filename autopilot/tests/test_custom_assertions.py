# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2012 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.

from __future__ import absolute_import

from testtools.matchers import Equals, raises, Not

from autopilot.testcase import AutopilotTestCase
import logging
logger = logging.getLogger(__name__)


class TestObject(object):

    test_property = 123

    another_property = "foobar"

    def test_method(self):
        return 456


class AssertionTests(AutopilotTestCase):

    test_object = TestObject()

    def test_assert_property_raises_valueerror_on_empty_test(self):
        """assert_property must raise ValueError if called without any kwargs."""

        self.assertThat(lambda: self.assert_property(self.test_object), raises(ValueError))

    def test_assert_property_raises_valueerror_on_callable(self):
        """assert_property must raise ValueError when called with a callable
        property name.

        """

        self.assertThat(lambda: self.assert_property(self.test_object, test_method=456),
            raises(ValueError))

    def test_assert_property_raises_assert_with_single_property(self):
        """assert_property must raise an AssertionError when called with a single
        property.

        """
        self.assertThat(lambda: self.assert_property(self.test_object, test_property=234),
            raises(AssertionError))

    def test_assert_property_doesnt_raise(self):
        """assert_property must not raise an exception if called with correct
        parameters.

        """

        self.assertThat(lambda: self.assert_property(self.test_object, test_property=123),
            Not(raises(AssertionError)))

    def test_assert_property_doesnt_raise_multiples(self):
        """assert_property must not raise an exception if called with correct
        parameters.

        """

        self.assertThat(lambda: self.assert_property(self.test_object, test_property=123, another_property="foobar"),
            Not(raises(AssertionError)))

    def test_assert_property_raises_assert_with_double_property(self):
        """assert_property must raise an AssertionError when called with a single
        property.

        """
        self.assertThat(lambda: self.assert_property(self.test_object, test_property=234, another_property=123),
            raises(AssertionError))

    def test_assert_properties_works(self):
        """Asserts that the assert_properties method is a synonym for assert_property."""
        self.assertThat(callable(self.assert_properties), Equals(True))
        self.assertThat(lambda: self.assert_properties(self.test_object, test_property=123, another_property="foobar"),
            Not(raises(AssertionError)))
