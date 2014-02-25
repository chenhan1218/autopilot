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

from mock import Mock
import tempfile
from testtools import TestCase, PlaceHolder
from testtools.content import text_content
from testtools.matchers import Contains, raises
from testscenarios import WithScenarios

from autopilot import testresult
from autopilot import run


class LoggedTestResultDecoratorTests(TestCase):

    def construct_simple_content_object(self):
        return text_content(self.getUniqueString)

    def test_can_construct(self):
        testresult.LoggedTestResultDecorator(Mock())

    def test_addSuccess_calls_decorated_test(self):
        wrapped = Mock()
        result = testresult.LoggedTestResultDecorator(wrapped)
        fake_test = PlaceHolder('fake_test')
        fake_details = self.construct_simple_content_object()

        result.addSuccess(fake_test, fake_details)

        wrapped.addSuccess.assert_called_once_with(
            fake_test,
            details=fake_details
        )

    def test_addError_calls_decorated_test(self):
        wrapped = Mock()
        result = testresult.LoggedTestResultDecorator(wrapped)
        fake_test = PlaceHolder('fake_test')
        fake_error = object()
        fake_details = self.construct_simple_content_object()

        result.addError(fake_test, fake_error, fake_details)

        wrapped.addError.assert_called_once_with(
            fake_test,
            fake_error,
            details=fake_details
        )

    def test_addFailure_calls_decorated_test(self):
        wrapped = Mock()
        result = testresult.LoggedTestResultDecorator(wrapped)
        fake_test = PlaceHolder('fake_test')
        fake_error = object()
        fake_details = self.construct_simple_content_object()

        result.addFailure(fake_test, fake_error, fake_details)

        wrapped.addFailure.assert_called_once_with(
            fake_test,
            fake_error,
            details=fake_details
        )


class OutputFormatFactoryTests(TestCase):

    def test_has_text_format(self):
        self.assertTrue('text' in testresult.get_output_formats())

    def test_has_xml_format(self):
        self.assertTrue('xml' in testresult.get_output_formats())

    def test_has_subunit_format(self):
        self.assertTrue('subunit' in testresult.get_output_formats())

    def test_default_format_is_available(self):
        self.assertThat(
            testresult.get_output_formats(),
            Contains(testresult.get_default_format())
        )


class TestResultOutputStreamTests(WithScenarios, TestCase):

    scenarios = [
        (f, dict(format=f)) for f in testresult.get_output_formats().keys()
    ]

    def get_supported_options(self):
        output_path = tempfile.mktemp()
        options = {
            'stream': run.get_output_stream(self.format, output_path)
        }
        if self.format == 'text':
            options['failfast'] = False
        return options

    def test_factory_function_is_a_callable(self):
        self.assertTrue(
            callable(testresult.get_output_formats()[self.format])
        )

    def test_factory_callable_raises_on_unknown_kwargs(self):
        factory_fn = testresult.get_output_formats()[self.format]
        options = self.get_supported_options()
        options['unknown_kwarg'] = True

        self.assertThat(
            lambda: factory_fn(**options),
            raises(ValueError)
        )
