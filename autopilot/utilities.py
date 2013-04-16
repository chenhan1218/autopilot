# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2012 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.
#
# This script is designed to run unity in a test drive manner. It will drive
# X and test the GL calls that Unity makes, so that we can easily find out if
# we are triggering graphics driver/X bugs.

"""Various utility classes and functions that are useful when running tests."""

from __future__ import absolute_import

import inspect
import logging
import os
import time
from functools import wraps

from autopilot import BackendException


def _pick_backend(variants, preferred_backend):
    """Pick a backend and return an instance of it."""
    possible_backends = variants.keys()
    get_debug_logger().debug("Possible backends: %s", ','.join(possible_backends))
    if preferred_backend:
        if preferred_backend in possible_backends:
            possible_backends.sort(lambda a,b: -1 if a == preferred_backend else 0)
        else:
            raise RuntimeError("Unknown backend '%s'" % (preferred_backend))
    failure_reasons = []
    for be in possible_backends:
        try:
            return variants[be]()
        except Exception as e:
            get_debug_logger().warning("Can't create backend %s: %r", be, e)
            failure_reasons.append('%s: %r' % (be, e))
            if preferred_backend != '':
                raise BackendException(e)
    raise RuntimeError("Unable to instantiate any backends\n%s" % '\n'.join(failure_reasons))


# Taken from http://code.activestate.com/recipes/577564-context-manager-for-low-level-redirection-of-stdou/
# licensed under the MIT license.
class Silence(object):
    """Context manager which uses low-level file descriptors to suppress
    output to stdout/stderr, optionally redirecting to the named file(s).

    >>> with Silence():
    ...     # do something that prints to stdout or stderr:
    ...

    """
    def __init__(self, stdout=os.devnull, stderr=os.devnull, mode='w'):
        self.outfiles = stdout, stderr
        self.combine = (stdout == stderr)
        self.mode = mode

    def __enter__(self):
        import sys
        self.sys = sys
        # save previous stdout/stderr
        self.saved_streams = saved_streams = sys.__stdout__, sys.__stderr__
        self.fds = fds = [s.fileno() for s in saved_streams]
        self.saved_fds = map(os.dup, fds)
        # flush any pending output
        for s in saved_streams: s.flush()

        # open surrogate files
        if self.combine:
            null_streams = [open(self.outfiles[0], self.mode, 0)] * 2
            if self.outfiles[0] != os.devnull:
                # disable buffering so output is merged immediately
                sys.stdout, sys.stderr = map(os.fdopen, fds, ['w']*2, [0]*2)
        else: null_streams = [open(f, self.mode, 0) for f in self.outfiles]
        self.null_fds = null_fds = [s.fileno() for s in null_streams]
        self.null_streams = null_streams

        # overwrite file objects and low-level file descriptors
        map(os.dup2, null_fds, fds)

    def __exit__(self, *args):
        sys = self.sys
        # flush any pending output
        for s in self.saved_streams: s.flush()
        # restore original streams and file descriptors
        map(os.dup2, self.saved_fds, self.fds)
        sys.stdout, sys.stderr = self.saved_streams
        # clean up
        for s in self.null_streams: s.close()
        for fd in self.saved_fds: os.close(fd)
        return False


class LogFormatter(logging.Formatter):

    # this is the default format to use for logging
    log_format = "%(asctime)s %(levelname)s %(module)s:%(lineno)d - %(message)s"

    def __init__(self):
        super(LogFormatter, self).__init__(self.log_format)

    def formatTime(self, record, datefmt=None):
        ct = self.converter(record.created)
        if datefmt:
            s = time.strftime(datefmt, ct)
        else:
            t = time.strftime("%H:%M:%S", ct)
            s = "%s.%03d" % (t, record.msecs)
        return s


class Timer(object):

    """A context-manager that times a block of code, writing the results to the log."""

    def __init__(self, code_name, log_level=logging.DEBUG):
        self.code_name = code_name
        self.log_level = log_level
        self.start = 0
        self.logger = get_debug_logger()

    def __enter__(self):
        self.start = time.time()

    def __exit__(self, *args):
        self.end = time.time()
        self.logger.log(self.log_level, "'%s' took %.3fS", self.code_name, self.end - self.start)


def get_debug_logger():
    """Get a logging object to be used as a debug logger only."""
    logger = logging.getLogger("autopilot.debug")
    logger.addFilter(DebugLogFilter())
    return logger


class DebugLogFilter(object):

    """A filter class for the logging framework that allows us to turn off the
    debug log.

    """

    debug_log_enabled = False

    def filter(self, record):
        return int(self.debug_log_enabled)


def deprecated(alternative):
    """Write a deprecation warning directly to stderr."""
    def fdec(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            import sys
            outerframe_details = inspect.getouterframes(inspect.currentframe())[1]
            filename, line_number, function_name = outerframe_details[1:4]
            sys.stderr.write("WARNING: in file \"{0}\", line {1} in {2}\n".format(filename, line_number, function_name))
            sys.stderr.write("This function is deprecated. Please use '%s' instead.\n" % alternative)
            return fn(*args, **kwargs)
        return wrapped
    return fdec


class _CleanupWrapper(object):
    """Support for calling 'addCleanup' outside the test case."""

    def __init__(self):
        self._test_instance = None

    def __call__(self, callable, *args, **kwargs):
        if self._test_instance is None:
            raise RuntimeError("Out-of-test addCleanup can only be called while an autopilot test case is running!")
        self._test_instance.addCleanup(callable, *args, **kwargs)

    def set_test_instance(self, test_instance):
        self._test_instance = test_instance
        test_instance.addCleanup(self._on_test_ended)

    def _on_test_ended(self):
        self._test_instance = None


addCleanup = _CleanupWrapper()
