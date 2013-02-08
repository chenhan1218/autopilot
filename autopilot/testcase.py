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
import sys
from testscenarios import TestWithScenarios
from testtools import TestCase
from testtools.content import text_content
from testtools.matchers import Equals
import time

from autopilot.compizconfig import get_global_context
from autopilot.emulators.bamf import Bamf
from autopilot.emulators.zeitgeist import Zeitgeist
from autopilot.emulators.processmanager import ProcessManager
from autopilot.emulators.X11 import ScreenGeometry, Keyboard, Mouse, reset_display
from autopilot.glibrunner import AutopilotTestRunner
from autopilot.globals import (get_log_verbose,
    get_video_recording_enabled,
    get_video_record_directory,
    )
from autopilot.keybindings import KeybindingsHelper
from autopilot.matchers import Eventually
from autopilot.utilities import (get_compiz_setting,
    LogFormatter,
    )

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

    **Application Launch Support**

    This class contains the methods
    :meth:`~autopilot.testcase.AutopilotTestCase.start_app` and
    :meth:`~autopilot.testcase.AutopilotTestCase.start_app_window` which will
    launch one of the well-known applications and return a
    :class:`~autopilot.emulators.bamf.BamfApplication` or
    :class:`~autopilot.emulators.bamf.BamfWindow` instance to the launched
    process respectively. All applications launched in this way will be closed
    when the test ends.

    **Set Unity & Compiz Options**

    The :meth:`~autopilot.testcase.AutopilotTestCase.set_unity_option` and
    :meth:`~autopilot.testcase.AutopilotTestCase.set_compiz_option` methods set a
    unity or compiz setting to a particular value for the duration of the
    current test only. This is useful if you want the window manager to behave
    in a particular fashion for a particular test, while being assured that any
    chances are non-destructive.

    **Patch Process Environment**

    The :meth:`~autopilot.testcase.AutopilotTestCase.patch_environment` method
    patches the process environment, for the duration of the current test
    only. This allows you to set an environment variable for the duration of the
    current test only.

    """

    run_tests_with = AutopilotTestRunner

    KNOWN_APPS = {
        'Character Map' : {
            'desktop-file': 'gucharmap.desktop',
            'process-name': 'gucharmap',
            },
        'Calculator' : {
            'desktop-file': 'gcalctool.desktop',
            'process-name': 'gcalctool',
            },
        'Mahjongg' : {
            'desktop-file': 'gnome-mahjongg.desktop',
            'process-name': 'gnome-mahjongg',
            },
        'Remmina' : {
            'desktop-file': 'remmina.desktop',
            'process-name': 'remmina',
            },
        'System Settings' : {
            'desktop-file': 'gnome-control-center.desktop',
            'process-name': 'gnome-control-center',
            },
        'Text Editor' : {
            'desktop-file': 'gedit.desktop',
            'process-name': 'gedit',
            },
        'Terminal' : {
            'desktop-file': 'gnome-terminal.desktop',
            'process-name': 'gnome-terminal',
            },
        }


    def setUp(self):
        super(AutopilotTestCase, self).setUp()

        self._process_manager = ProcessManager()
        self._process_manager.snapshot_running_apps()
        self.addCleanup(self._process_manager.compare_system_with_snapshot)

        self.bamf = Bamf()
        self.keyboard = Keyboard()
        self.mouse = Mouse()
        self.zeitgeist = Zeitgeist()

        self.screen_geo = ScreenGeometry()
        self.addCleanup(Keyboard.cleanup)
        self.addCleanup(Mouse.cleanup)

    def call_gsettings_cmd(self, command, schema, *args):
        """Set a desktop wide gsettings option

        Using the gsettings command because there is a bug with importing
        from gobject introspection and pygtk2 simultaneously, and the Xlib
        keyboard layout bits are very unwieldy. This seems like the best
        solution, even a little bit brutish.
        """
        cmd = ['gsettings', command, schema] + list(args)
        # strip to remove the trailing \n.
        ret = check_output(cmd).strip()
        time.sleep(5)
        reset_display()
        return ret

    def set_unity_option(self, option_name, option_value):
        """Set an option in the unity compiz plugin options.

        .. note:: The value will be set for the current test only, and
         automatically undone when the test ends.

        :param option_name: The name of the unity option.
        :param option_value: The value you want to set.
        :raises: **KeyError** if the option named does not exist.

        """
        self.set_compiz_option("unityshell", option_name, option_value)

    def set_compiz_option(self, plugin_name, option_name, option_value):
        """Set a compiz option for the duration of this test only.

        .. note:: The value will be set for the current test only, and
         automatically undone when the test ends.

        :param plugin_name: The name of the compiz plugin where the option is
         registered. If the option is not in a plugin, the string "core" should
         be used as the plugin name.
        :param option_name: The name of the unity option.
        :param option_value: The value you want to set.
        :raises: **KeyError** if the option named does not exist.

        """
        old_value = self._set_compiz_option(plugin_name, option_name, option_value)
        # Cleanup is LIFO, during clean-up also allow unity to respond
        self.addCleanup(time.sleep, 0.5)
        self.addCleanup(self._set_compiz_option, plugin_name, option_name, old_value)
        # Allow unity time to respond to the new setting.
        time.sleep(0.5)

    def _set_compiz_option(self, plugin_name, option_name, option_value):
        logger.info("Setting compiz option '%s' in plugin '%s' to %r",
            option_name, plugin_name, option_value)
        setting = get_compiz_setting(plugin_name, option_name)
        old_value = setting.Value
        setting.Value = option_value
        get_global_context().Write()
        return old_value

    @classmethod
    def register_known_application(cls, name, desktop_file, process_name):
        """Register an application with autopilot.

        After calling this method, you may call :meth:`start_app` or
        :meth:`start_app_window` with the `name` parameter to start this
        application.
        You need only call this once within a test run - the application will
        remain registerred until the test run ends.

        :param name: The name to be used when launching the application.
        :param desktop_file: The filename (without path component) of the desktop file used to launch the application.
        :param process_name: The name of the executable process that gets run.
        :raises: **KeyError** if application has been registered already

        """
        if name in cls.KNOWN_APPS:
            raise KeyError("Application has been registered already")
        else:
            cls.KNOWN_APPS[name] = {
                                     "desktop-file" : desktop_file,
                                     "process-name" : process_name
                                   }

    @classmethod
    def unregister_known_application(cls, name):
        """Unregister an application with the known_apps dictionary.

        :param name: The name to be used when launching the application.
        :raises: **KeyError** if the application has not been registered.

        """
        if name in cls.KNOWN_APPS:
            del cls.KNOWN_APPS[name]
        else:
            raise KeyError("Application has not been registered")

    def start_app(self, app_name, files=[], locale=None):
        """Start one of the known applications, and kill it on tear down.

        .. warning:: This method will clear all instances of this application on
         tearDown, not just the one opened by this method! We recommend that
         you use the :meth:`start_app_window` method instead, as it is generally
         safer.

        :param app_name: The application name. *This name must either already
         be registered as one of the built-in applications that are supported
         by autopilot, or must have been registered using*
         :meth:`register_known_application` *beforehand.*
        :param files: (Optional) A list of paths to open with the
         given application. *Not all applications support opening files in this
         way.*
        :param locale: (Optional) The locale will to set when the application
         is launched. *If you want to launch an application without any
         localisation being applied, set this parameter to 'C'.*
        :returns: A :class:`~autopilot.emulators.bamf.BamfApplication` instance.

        """
        window = self._open_window(app_name, files, locale)
        if window:
            self.addCleanup(self.close_all_app, app_name)
            return window.application

        raise AssertionError("No new application window was opened.")

    def start_app_window(self, app_name, files=[], locale=None):
        """Open a single window for one of the known applications, and close it
        at the end of the test.

        :param app_name: The application name. *This name must either already
         be registered as one of the built-in applications that are supported
         by autopilot, or must have been registered with*
         :meth:`register_known_application` *beforehand.*
        :param files: (Optional) Should be a list of paths to open with the
         given application. *Not all applications support opening files in this
         way.*
        :param locale: (Optional) The locale will to set when the application
         is launched. *If you want to launch an application without any
         localisation being applied, set this parameter to 'C'.*
        :raises: **AssertionError** if no window was opened, or more than one
         window was opened.
        :returns: A :class:`~autopilot.emulators.bamf.BamfWindow` instance.

        """
        window = self._open_window(app_name, files, locale)
        if window:
            self.addCleanup(window.close)
            return window
        raise AssertionError("No window was opened.")

    def _open_window(self, app_name, files, locale):
        """Open a new 'app_name' window, returning the window instance or None.

        Raises an AssertionError if this creates more than one window.

        """
        existing_windows = self.get_open_windows_by_application(app_name)

        if locale:
            os.putenv("LC_ALL", locale)
            self.addCleanup(os.unsetenv, "LC_ALL")
            logger.info("Starting application '%s' with files %r in locale %s", app_name, files, locale)
        else:
            logger.info("Starting application '%s' with files %r", app_name, files)


        app = self.KNOWN_APPS[app_name]
        self.bamf.launch_application(app['desktop-file'], files)
        apps = self.bamf.get_running_applications_by_desktop_file(app['desktop-file'])

        for i in range(10):
            try:
                new_windows = []
                [new_windows.extend(a.get_windows()) for a in apps]
                filter_fn = lambda w: w.x_id not in [c.x_id for c in existing_windows]
                new_wins = filter(filter_fn, new_windows)
                if new_wins:
                    assert len(new_wins) == 1
                    return new_wins[0]
            except DBusException:
                pass
            time.sleep(1)
        return None

    def get_open_windows_by_application(self, app_name):
        """Get a list of BamfWindow instances for the given application name.

        :param app_name: The name of one of the well-known applications.
        :returns: A list of :class:`~autopilot.emulators.bamf.BamfWindow`
         instances.

        """
        existing_windows = []
        [existing_windows.extend(a.get_windows()) for a in self.get_app_instances(app_name)]
        return existing_windows

    def close_all_app(self, app_name):
        """Close all instances of the application 'app_name'."""
        app = self.KNOWN_APPS[app_name]
        try:
            pids = check_output(["pidof", app['process-name']]).split()
            if len(pids):
                call(["kill"] + pids)
        except CalledProcessError:
            logger.warning("Tried to close applicaton '%s' but it wasn't running.", app_name)

    def get_app_instances(self, app_name):
        """Get BamfApplication instances for app_name."""
        desktop_file = self.KNOWN_APPS[app_name]['desktop-file']
        return self.bamf.get_running_applications_by_desktop_file(desktop_file)

    def app_is_running(self, app_name):
        """Return true if an instance of the application is running."""
        apps = self.get_app_instances(app_name)
        return len(apps) > 0

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

    def assertVisibleWindowStack(self, stack_start):
        """Check that the visible window stack starts with the windows passed in.

        .. note:: Minimised windows are skipped.

        :param stack_start: An iterable of BamfWindow instances.
        :raises: **AssertionError** if the top of the window stack does not
         match the contents of the stack_start parameter.

        """
        stack = [win for win in self.bamf.get_open_windows() if not win.is_hidden]
        for pos, win in enumerate(stack_start):
            self.assertThat(stack[pos].x_id, Equals(win.x_id),
                            "%r at %d does not equal %r" % (stack[pos], pos, win))

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
