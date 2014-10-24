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

from unittest.mock import Mock, patch
import re
from testtools import TestCase
from testtools.matchers import (
    Equals,
    GreaterThan,
    IsInstance,
    LessThan,
    MatchesRegex,
    Not,
    raises,
    Raises,
)
import timeit

from autopilot.utilities import (
    _raise_if_time_oddity_since_last_event,
    _raise_on_unknown_kwargs,
    _sleep_for_calculated_delta,
    cached_result,
    compatible_repr,
    deprecated,
    EventDelay,
    sleep,
)


class ElapsedTimeCounter(object):

    """A simple utility to count the amount of real time that passes."""

    def __enter__(self):
        self._start_time = timeit.default_timer()
        return self

    def __exit__(self, *args):
        pass

    @property
    def elapsed_time(self):
        return timeit.default_timer() - self._start_time


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


class EventDelayTests(TestCase):

    def setUp(self):
        super(EventDelayTests, self).setUp()
        self.event_delayer = EventDelay()

    def test_mocked_event_interval_adder_contextmanager(self):
        with ElapsedTimeCounter() as time_counter:
            with self.event_delayer.mocked():
                # The first call of delay() only stores the last time
                # stamp, it is only the second call where the delay
                # actually happens. So we call delay() twice here to
                # ensure mocking is working as expected.
                self.event_delayer.delay(10)
                self.event_delayer.delay(3)
                self.assertThat(time_counter.elapsed_time, LessThan(2))

    def test_last_event_start_at_zero(self):
        with self.event_delayer.mocked() as mocked_delayer:
            self.assertThat(
                mocked_delayer.last_event_time(), Equals(0.0))

    def test_last_event_delay_counter_updates_on_first_call(self):
        self.event_delayer.delay(1.0)

        self.assertThat(self.event_delayer._last_event, GreaterThan(0.0))

    def test_unmocked_first_call_no_delay(self):
        with patch('autopilot.utilities.time') as patched_time:
            self.event_delayer.delay()
            self.assertThat(patched_time.sleep.call_count, Equals(0))

    def test_unmocked_second_call_delay(self):
        with patch('autopilot.utilities.time') as patched_time:
            self.event_delayer.delay()
            self.event_delayer.delay()
            self.assertThat(patched_time.sleep.call_count, Equals(1))

    def test_no_sleep_if_time_jumps_since_last_event(self):
        with patch('autopilot.utilities.time') as patched_time:
            self.event_delayer.delay(2, current_time=lambda: 100)
            self.event_delayer.delay(2, current_time=lambda: 110)
            self.assertThat(patched_time.sleep.call_count, Equals(0))

    def test_sleep_delta_calculator_returns_zero_if_time_delta_negative(self):
        result = _sleep_for_calculated_delta(100, 2, 97)
        self.assertThat(result, Equals(0.0))

    def test_sleep_delta_calculator_returns_zero_if_time_delta_zero(self):
        result = _sleep_for_calculated_delta(100, 2, 98)
        self.assertThat(result, Equals(0.0))

    def test_sleep_delta_calculator_returns_non_zero_if_delta_not_zero(self):
        result = _sleep_for_calculated_delta(100, 1, 100)
        self.assertThat(result, Equals(1.0))

    def test_time_sanity_checker_raises_if_time_smaller_than_last_event(self):
        self.assertRaises(
            ValueError,
            _raise_if_time_oddity_since_last_event,
            current_time=90,
            last_event_time=100
        )

    def test_time_sanity_checker_raises_if_time_equal_last_event_time(self):
        self.assertRaises(
            ValueError,
            _raise_if_time_oddity_since_last_event,
            current_time=100,
            last_event_time=100
        )

    def test_time_sanity_checker_return_if_time_greater_than_last_event(self):
        result = _raise_if_time_oddity_since_last_event(
            current_time=400, last_event_time=100)

        self.assertIsNone(result)


class CompatibleReprTests(TestCase):

    def test_py3_unicode_is_untouched(self):
        repr_fn = compatible_repr(lambda: "unicode")
        result = repr_fn()
        self.assertThat(result, IsInstance(str))
        self.assertThat(result, Equals('unicode'))

    def test_py3_bytes_are_returned_as_unicode(self):
        repr_fn = compatible_repr(lambda: b"bytes")
        result = repr_fn()
        self.assertThat(result, IsInstance(str))
        self.assertThat(result, Equals('bytes'))


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


class CachedResultTests(TestCase):

    def get_wrapped_mock_pair(self):
        inner = Mock()
        # Mock() under python 2 does not support __name__. When we drop py2
        # support we can obviously delete this hack:
        return inner, cached_result(inner)

    def test_can_be_used_as_decorator(self):
        @cached_result
        def foo():
            pass

    def test_adds_reset_cache_callable_to_function(self):
        @cached_result
        def foo():
            pass

        self.assertTrue(hasattr(foo, 'reset_cache'))

    def test_retains_docstring(self):
        @cached_result
        def foo():
            """xxXX super docstring XXxx"""
            pass

        self.assertThat(foo.__doc__, Equals("xxXX super docstring XXxx"))

    def test_call_passes_through_once(self):
        inner, wrapped = self.get_wrapped_mock_pair()
        wrapped()
        inner.assert_called_once_with()

    def test_call_passes_through_only_once(self):
        inner, wrapped = self.get_wrapped_mock_pair()
        wrapped()
        wrapped()
        inner.assert_called_once_with()

    def test_first_call_returns_actual_result(self):
        inner, wrapped = self.get_wrapped_mock_pair()
        self.assertThat(
            wrapped(),
            Equals(inner.return_value)
        )

    def test_subsequent_calls_return_actual_results(self):
        inner, wrapped = self.get_wrapped_mock_pair()
        wrapped()
        self.assertThat(
            wrapped(),
            Equals(inner.return_value)
        )

    def test_can_pass_hashable_arguments(self):
        inner, wrapped = self.get_wrapped_mock_pair()
        wrapped(1, True, 2.0, "Hello", tuple(), )
        inner.assert_called_once_with(1, True, 2.0, "Hello", tuple())

    def test_passing_kwargs_raises_TypeError(self):
        inner, wrapped = self.get_wrapped_mock_pair()
        self.assertThat(
            lambda: wrapped(foo='bar'),
            raises(TypeError)
        )

    def test_passing_unhashable_args_raises_TypeError(self):
        inner, wrapped = self.get_wrapped_mock_pair()
        self.assertThat(
            lambda: wrapped([]),
            raises(TypeError)
        )

    def test_resetting_cache_works(self):
        inner, wrapped = self.get_wrapped_mock_pair()
        wrapped()
        wrapped.reset_cache()
        wrapped()
        self.assertThat(inner.call_count, Equals(2))
