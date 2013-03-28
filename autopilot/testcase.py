# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2012 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.

"""Autopilot test case classes."""

from __future__ import absolute_import

from dbus import DBusException
import logging
import os
from StringIO import StringIO
from subprocess import (
    call,
    CalledProcessError,
    check_output,
    Popen,
    PIPE,
    STDOUT,
    )

from testscenarios import TestWithScenarios
from testtools import TestCase
from testtools.content import text_content
from testtools.matchers import Equals
import time

from autopilot.emulators.bamf import Bamf
from autopilot.emulators.zeitgeist import Zeitgeist
from autopilot.emulators.processmanager import ProcessManager
from autopilot.emulators.X11 import ScreenGeometry, reset_display
from autopilot.emulators.input import get_keyboard, get_mouse
from autopilot.emulators.display import get_display
from autopilot.globals import (get_log_verbose,
    get_video_recording_enabled,
    get_video_record_directory,
    )
from autopilot.keybindings import KeybindingsHelper
from autopilot.matchers import Eventually
from autopilot.utilities import LogFormatter

logger = logging.getLogger(__name__)


try:
    from testscenarios.scenarios import multiply_scenarios
except ImportError:
    from itertools import product
    def multiply_scenarios(*scenarios):
        """Multiply two or more iterables of scenarios.

        It is safe to pass scenario generators or iterators.

        :returns: A list of compound scenarios: the cross-product of all
            scenarios, with the names concatenated and the parameters
            merged together.
        """
        result = []
        scenario_lists = map(list, scenarios)
        for combination in product(*scenario_lists):
            names, parameters = zip(*combination)
            scenario_name = ','.join(names)
            scenario_parameters = {}
            for parameter in parameters:
                scenario_parameters.update(parameter)
            result.append((scenario_name, scenario_parameters))
        return result


class LoggedTestCase(TestWithScenarios, TestCase):
    """Initialize the logging for the test case."""

    def setUp(self):
        self._setUpTestLogging()
        # The reason that the super setup is done here is due to making sure
        # that the logging is properly set up prior to calling it.
        super(LoggedTestCase, self).setUp()
        if get_log_verbose():
            logger.info("*" * 60)
            logger.info("Starting test %s", self.shortDescription())

    def _setUpTestLogging(self):
        self._log_buffer = StringIO()
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        formatter = LogFormatter()
        self._log_handler = logging.StreamHandler(stream=self._log_buffer)
        self._log_handler.setFormatter(formatter)
        root_logger.addHandler(self._log_handler)

        #Tear down logging in a cleanUp handler, so it's done after all other
        # tearDown() calls and cleanup handlers.
        self.addCleanup(self._tearDownLogging)

    def _tearDownLogging(self):
        root_logger = logging.getLogger()
        self._log_handler.flush()
        self._log_buffer.seek(0)
        self.addDetail('test-log', text_content(self._log_buffer.getvalue()))
        root_logger.removeHandler(self._log_handler)
        # Calling del to remove the handler and flush the buffer.  We are
        # abusing the log handlers here a little.
        del self._log_buffer



class VideoCapturedTestCase(LoggedTestCase):
    """Video capture autopilot tests, saving the results if the test failed."""

    _recording_app = '/usr/bin/recordmydesktop'
    _recording_opts = ['--no-sound', '--no-frame', '-o',]

    def setUp(self):
        super(VideoCapturedTestCase, self).setUp()
        global video_recording_enabled
        if get_video_recording_enabled() and not self._have_recording_app():
            video_recording_enabled = False
            logger.warning("Disabling video capture since '%s' is not present", self._recording_app)

        if get_video_recording_enabled():
            self._test_passed = True
            self.addOnException(self._on_test_failed)
            self.addCleanup(self._stop_video_capture)
            self._start_video_capture()

    def _have_recording_app(self):
        return os.path.exists(self._recording_app)

    def _start_video_capture(self):
        args = self._get_capture_command_line()
        self._capture_file = self._get_capture_output_file()
        self._ensure_directory_exists_but_not_file(self._capture_file)
        args.append(self._capture_file)
        logger.debug("Starting: %r", args)
        self._capture_process = Popen(args, stdout=PIPE, stderr=STDOUT)

    def _stop_video_capture(self):
        """Stop the video capture. If the test failed, save the resulting file."""

        if self._test_passed:
            # We use kill here because we don't want the recording app to start
            # encoding the video file (since we're removing it anyway.)
            self._capture_process.kill()
            self._capture_process.wait()
        else:
            self._capture_process.terminate()
            self._capture_process.wait()
            if self._capture_process.returncode != 0:
                self.addDetail('video capture log', text_content(self._capture_process.stdout.read()))
        self._capture_process = None

    def _get_capture_command_line(self):
        return [self._recording_app] + self._recording_opts

    def _get_capture_output_file(self):
        return os.path.join(get_video_record_directory(), '%s.ogv' % (self.shortDescription()))

    def _ensure_directory_exists_but_not_file(self, file_path):
        dirpath = os.path.dirname(file_path)
        if not os.path.exists(dirpath):
            os.makedirs(dirpath)
        elif os.path.exists(file_path):
            logger.warning("Video capture file '%s' already exists, deleting.", file_path)
            os.remove(file_path)

    def _on_test_failed(self, ex_info):
        """Called when a test fails."""
        self._test_passed = False


class AutopilotTestCase(VideoCapturedTestCase, KeybindingsHelper):
    """Wrapper around testtools.TestCase that adds significant functionality.

    This class should be the base class for all autopilot test case classes. Not
    using this class as the base class disables several important convenience
    methods, and also prevents the use of the failed-test recording tools.

    Some of the more notable features of this class include:

    **Patch Process Environment**

    The :meth:`~autopilot.testcase.AutopilotTestCase.patch_environment` method
    patches the process environment, for the duration of the current test
    only. This allows you to set an environment variable for the duration of the
    current test only.

    """

    def setUp(self):
        super(AutopilotTestCase, self).setUp()

        self._process_manager = ProcessManager()
        self._process_manager.snapshot_running_apps()
        self.addCleanup(self._process_manager.compare_system_with_snapshot)

        self.bamf = Bamf()
        self.keyboard = get_keyboard()
        self.mouse = get_mouse()
        self.zeitgeist = Zeitgeist()

        self.screen_geo = get_display()
        self.addCleanup(self.keyboard.cleanup)
        self.addCleanup(self.mouse.cleanup)

    def patch_environment(self, key, value):
        """Patch the process environment, setting *key* with value *value*.

        This patches os.environ for the duration of the test only. After calling
        this method, the following should be True::

            os.environ[key] == value

        After the test, the patch will be undone (including deleting the key if
        if didn't exist before this method was called).

        .. note:: Be aware that patching the environment in this way only
         affects the current autopilot process, and any processes spawned by
         autopilot. If you are planing on starting an application from within
         autopilot and you want this new application to read the patched
         environment variable, you must patch the environment *before* launching
         the new process.

        :param string key: The name of the key you wish to set. If the key does not
         already exist in the process environment it will be created (and then
         deleted when the test ends).
        :param string value: The value you wish to set.

        """
        if key in os.environ:
            old_value = os.environ[key]
            self.addCleanup(os.putenv, key, old_value)
        else:
            self.addCleanup(os.unsetenv, key)
        os.environ[key] = value

    def assertProperty(self, obj, **kwargs):
        """Assert that *obj* has properties equal to the key/value pairs in kwargs.

        This method is intended to be used on objects whose attributes do not
        have the :meth:`wait_for` method (i.e.- objects that do not come from
        the autopilot DBus interface).

        For example, from within a test, to assert certain properties on a
        BamfWindow instance::

            self.assertProperty(my_window, is_maximized=True)

        .. note:: assertProperties is a synonym for this method.

        :param obj: The object to test.
        :param kwargs: One or more keyword arguments to match against the
         attributes of the *obj* parameter.
        :raises: **ValueError** if no keyword arguments were given.
        :raises: **ValueError** if a named attribute is a callable object.
        :raises: **AssertionError** if any of the attribute/value pairs in
         kwargs do not match the attributes on the object passed in.

        """
        if not kwargs:
            raise ValueError("At least one keyword argument must be present.")

        for prop_name, desired_value in kwargs.iteritems():
            none_val = object()
            attr = getattr(obj, prop_name, none_val)
            if attr == none_val:
                raise AssertionError("Object %r does not have an attribute named '%s'"
                    % (obj, prop_name))
            if callable(attr):
                raise ValueError("Object %r's '%s' attribute is a callable. It must be a property."
                    % (obj, prop_name))
            self.assertThat(lambda: getattr(obj, prop_name), Eventually(Equals(desired_value)))

    assertProperties = assertProperty
