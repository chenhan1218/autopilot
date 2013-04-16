# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2013 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.

from collections import OrderedDict
from testtools import TestCase
from testtools.matchers import raises, Equals, IsInstance
from textwrap import dedent

from autopilot import BackendException
from autopilot.utilities import _pick_backend


class PickBackendTests(TestCase):

    def test_raises_runtime_error_on_empty_backends(self):
        """Must raise a RuntimeError when we pass no backends."""
        fn = lambda: _pick_backend({}, '')
        self.assertThat(fn, raises(RuntimeError("Unable to instantiate any backends\n")))

    def test_single_backend(self):
        """Must return a backend when called with a single backend."""
        class Backend(object):
            pass
        _create_backend = lambda:Backend()
        backend = _pick_backend(dict(foo=_create_backend), '')
        self.assertThat(backend, IsInstance(Backend))

    def test_first_backend(self):
        """Must return the first backend when called with a two backends."""
        class Backend1(object):
            pass
        class Backend2(object):
            pass
        backend_dict = OrderedDict()
        backend_dict['be1'] = lambda:Backend1()
        backend_dict['be2'] = lambda:Backend2()

        backend = _pick_backend(backend_dict, '')
        self.assertThat(backend, IsInstance(Backend1))

    def test_preferred_backend(self):
        """Must return the preferred backend when called with a two backends."""
        class Backend1(object):
            pass
        class Backend2(object):
            pass
        backend_dict = OrderedDict()
        backend_dict['be1'] = lambda:Backend1()
        backend_dict['be2'] = lambda:Backend2()

        backend = _pick_backend(backend_dict, 'be2')
        self.assertThat(backend, IsInstance(Backend2))

    def test_raises_backend_exception_on_preferred_backend(self):
        """Must raise a BackendException when the preferred backendcannot be created."""
        class Backend1(object):
            pass
        class Backend2(object):
            def __init__(self):
                raise ValueError("Foo")
        backend_dict = OrderedDict()
        backend_dict['be1'] = lambda:Backend1()
        backend_dict['be2'] = lambda:Backend2()

        fn = lambda:_pick_backend(backend_dict, 'be2')
        self.assertThat(fn, raises(BackendException))

    def test_backend_exception_wraps_original_exception(self):
        """Raised backend Exception must wrap exception from backend."""
        class Backend1(object):
            pass
        class Backend2(object):
            def __init__(self):
                raise ValueError("Foo")
        backend_dict = OrderedDict()
        backend_dict['be1'] = lambda:Backend1()
        backend_dict['be2'] = lambda:Backend2()

        raised = False
        try:
            _pick_backend(backend_dict, 'be2')
        except BackendException as e:
            raised = True
            self.assertTrue(hasattr(e, 'original_exception'))
            self.assertThat(e.original_exception, IsInstance(ValueError))
            self.assertThat(e.original_exception.message, Equals("Foo"))
        self.assertTrue(raised)

    def test_failure_of_all_backends(self):
        """When we cannot create any backends, must raise RuntimeError."""
        class BadBackend(object):
            def __init__(self):
                raise ValueError("Foo")
        backend_dict = OrderedDict()
        backend_dict['be1'] = lambda:BadBackend()
        backend_dict['be2'] = lambda:BadBackend()

        fn = lambda: _pick_backend(backend_dict, '')
        expected_exception = RuntimeError(dedent("""\
            Unable to instantiate any backends
            be1: ValueError('Foo',)
            be2: ValueError('Foo',)"""))

        self.assertThat(fn, raises(expected_exception))
