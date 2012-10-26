# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2012 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.

"""Autopilot-specific testtools matchers."""

from __future__ import absolute_import

from functools import partial
from testtools.matchers import Matcher, Mismatch
from time import sleep


class Eventually(Matcher):
    """Asserts that a value will eventually equal a given Matcher object.

    This works on objects that *either* have a :meth:`wait_for(expected)`
    function, *or* objects that are callable and return the most current value
    (i.e.- they refresh the objects value).

    """

    def __init__(self, matcher):
        super(Eventually, self).__init__()
        match_fun = getattr(matcher, 'match', None)
        if match_fun is None or not callable(match_fun):
            raise TypeError("Eventually must be called with a testtools matcher argument.")
        self.matcher = matcher

    def match(self, value):
        if callable(value):
            wait_fun = partial(_callable_wait_for, value)
        else:
            wait_fun = getattr(value, 'wait_for', None)
            if wait_fun is None or not callable(wait_fun):
                raise TypeError("Eventually is only usable with attributes that have a wait_for function or callable objects.")

        try:
            wait_fun(self.matcher)
        except AssertionError as e:
            return Mismatch(str(e))
        return None

    def __str__(self):
        return "Eventually " + str(self.matcher)


def _callable_wait_for(refresh_fn, matcher):
    """Like the patched :meth:`wait_for method`, but for callable objects instead
    of patched variables.

    """

    for i in range(10):
        new_value = refresh_fn()
        mismatch = matcher.match(new_value)
        if mismatch:
            failure_msg = mismatch.describe()
        else:
            return

        sleep(1)

    # can't give a very descriptive message here, especially as refresh_fn
    # is likely to be a lambda.
    raise AssertionError("After 10 seconds test failed: %s", failure_msg)
