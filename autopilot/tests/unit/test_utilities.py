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

from mock import patch
import re
import six
from testtools import skipIf, TestCase
from testtools.matchers import (
    Equals,
    IsInstance,
    LessThan,
    MatchesRegex,
    Not,
    raises,
    Raises,
)
import time

from autopilot.utilities import (
    _raise_on_unknown_kwargs,
    compatible_repr,
    deprecated,
    sleep,
)


class ElapsedTimeCounter(object):

    """A simple utility to count the amount of real time that passes."""

    def __enter__(self):
        self._start_time = time.time()
        return self

    def __exit__(self, *args):
        pass

    @property
    def elapsed_time(self):
        return time.time() - self._start_time


class MockableSleepTests(TestCase):

    def test_mocked_sleep_contextmanager(self):
        with ElapsedTimeCounter() as time_counter:
            with sleep.mocked():
                sleep(10)
            self.assertThat(time_counter.elapsed_time, LessThan(2))

    def test_mocked_sleep_methods(self):
        with ElapsedTimeCounter() as time_counter:
            sleep.enable_mock()
            self.addCleanup(sleep.disable_mock)

            sleep(10)
            self.assertThat(time_counter.elapsed_time, LessThan(2))

    def test_total_time_slept_starts_at_zero(self):
        with sleep.mocked() as sleep_counter:
            self.assertThat(sleep_counter.total_time_slept(), Equals(0.0))

    def test_total_time_slept_accumulates(self):
        with sleep.mocked() as sleep_counter:
            sleep(1)
            self.assertThat(sleep_counter.total_time_slept(), Equals(1.0))
            sleep(0.5)
            self.assertThat(sleep_counter.total_time_slept(), Equals(1.5))
            sleep(0.5)
            self.assertThat(sleep_counter.total_time_slept(), Equals(2.0))

    def test_unmocked_sleep_calls_real_time_sleep_function(self):
        with patch('autopilot.utilities.time') as patched_time:
            sleep(1.0)

            patched_time.sleep.assert_called_once_with(1.0)


class CompatibleReprTests(TestCase):

    @skipIf(six.PY3, "Applicable to python 2 only")
    def test_py2_unicode_is_returned_as_bytes(self):
        repr_fn = compatible_repr(lambda: u"unicode")
        result = repr_fn()
        self.assertThat(result, IsInstance(six.binary_type))
        self.assertThat(result, Equals(b'unicode'))

    @skipIf(six.PY3, "Applicable to python 2 only")
    def test_py2_bytes_are_untouched(self):
        repr_fn = compatible_repr(lambda: b"bytes")
        result = repr_fn()
        self.assertThat(result, IsInstance(six.binary_type))
        self.assertThat(result, Equals(b'bytes'))

    @skipIf(six.PY2, "Applicable to python 3 only")
    def test_py3_unicode_is_untouched(self):
        repr_fn = compatible_repr(lambda: u"unicode")
        result = repr_fn()
        self.assertThat(result, IsInstance(six.text_type))
        self.assertThat(result, Equals(u'unicode'))

    @skipIf(six.PY2, "Applicable to python 3 only.")
    def test_py3_bytes_are_returned_as_unicode(self):
        repr_fn = compatible_repr(lambda: b"bytes")
        result = repr_fn()
        self.assertThat(result, IsInstance(six.text_type))
        self.assertThat(result, Equals(u'bytes'))


class UnknownKWArgsTests(TestCase):

    def test_raise_if_not_empty_raises_on_nonempty_dict(self):
        populated_dict = dict(testing=True)
        self.assertThat(
            lambda: _raise_on_unknown_kwargs(populated_dict),
            raises(ValueError("Unknown keyword arguments: 'testing'."))
        )

    def test_raise_if_not_empty_does_not_raise_on_empty(self):
        empty_dict = dict()
        self.assertThat(
            lambda: _raise_on_unknown_kwargs(empty_dict),
            Not(Raises())
        )


class DeprecatedDecoratorTests(TestCase):

    def test_deprecated_logs_warning(self):

        @deprecated('Testing')
        def not_testing():
            pass

        with patch('autopilot.utilities.logger') as patched_log:
            not_testing()

            self.assertThat(
                patched_log.warning.call_args[0][0],
                MatchesRegex(
                    "WARNING: in file \".*.py\", line \d+ in "
                    "test_deprecated_logs_warning\nThis "
                    "function is deprecated. Please use 'Testing' instead.\n",
                    re.DOTALL
                )
            )
