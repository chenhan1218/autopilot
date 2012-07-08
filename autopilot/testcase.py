# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2012 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.

"""
Autopilot test case class.
"""

from __future__ import absolute_import

from compizconfig import Setting, Plugin
import gconf
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
from autopilot.emulators.processmanager import ProcessManager
from autopilot.emulators.X11 import ScreenGeometry, Keyboard, Mouse, reset_display
from autopilot.glibrunner import GlibRunner
from autopilot.globals import (global_context,
    video_recording_enabled,
    video_record_directory,
    )
from autopilot.keybindings import KeybindingsHelper


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

    def _setUpTestLogging(self):
        class MyFormatter(logging.Formatter):

            def formatTime(self, record, datefmt=None):
                ct = self.converter(record.created)
                if datefmt:
                    s = time.strftime(datefmt, ct)
                else:
                    t = time.strftime("%H:%M:%S", ct)
                    s = "%s.%03d" % (t, record.msecs)
                return s

        self._log_buffer = StringIO()
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(stream=self._log_buffer)
        log_format = "%(asctime)s %(levelname)s %(module)s:%(lineno)d - %(message)s"
        handler.setFormatter(MyFormatter(log_format))
        root_logger.addHandler(handler)
        #Tear down logging in a cleanUp handler, so it's done after all other
        # tearDown() calls and cleanup handlers.
        self.addCleanup(self._tearDownLogging)

    def _tearDownLogging(self):
        logger = logging.getLogger()
        for handler in logger.handlers:
            handler.flush()
            self._log_buffer.seek(0)
            self.addDetail('test-log', text_content(self._log_buffer.getvalue()))
            logger.removeHandler(handler)
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
        if video_recording_enabled and not self._have_recording_app():
            video_recording_enabled = False
            logger.warning("Disabling video capture since '%s' is not present", self._recording_app)

        if video_recording_enabled:
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
        return os.path.join(video_record_directory, '%s.ogv' % (self.shortDescription()))

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
    """Wrapper around testtools.TestCase that takes care of some cleaning."""

    run_test_with = GlibRunner

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
            'desktop-file': 'mahjongg.desktop',
            'process-name': 'mahjongg',
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
        }

    def setUp(self):
        super(AutopilotTestCase, self).setUp()

        self._process_manager = ProcessManager()
        self._process_manager.snapshot_running_apps()
        self.addCleanup(self._process_manager.compare_system_with_snapshot)

        self.bamf = Bamf()
        self.keyboard = Keyboard()
        self.mouse = Mouse()

        self.screen_geo = ScreenGeometry()
        self.addCleanup(Keyboard.cleanup)
        self.addCleanup(Mouse.cleanup)

    def call_gsettings_cmd(self, command, schema, *args):
        """Set a desktop wide gsettings option

        Using the gsettings command because there's a bug with importing
        from gobject introspection and pygtk2 simultaneously, and the Xlib
        keyboard layout bits are very unweildy. This seems like the best
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

        The value will be set for the current test only.

        """
        self.set_compiz_option("unityshell", option_name, option_value)

    def set_compiz_option(self, plugin_name, setting_name, setting_value):
        """Set setting `setting_name` in compiz plugin `plugin_name` to value `setting_value`
        for one test only.
        """
        old_value = self._set_compiz_option(plugin_name, setting_name, setting_value)
        self.addCleanup(self._set_compiz_option, plugin_name, setting_name, old_value)
        # Allow unity time to respond to the new setting.
        time.sleep(0.5)

    def _set_compiz_option(self, plugin_name, option_name, option_value):
        logger.info("Setting compiz option '%s' in plugin '%s' to %r",
            option_name, plugin_name, option_value)
        plugin = Plugin(global_context, plugin_name)
        setting = Setting(plugin, option_name)
        old_value = setting.Value
        setting.Value = option_value
        global_context.Write()
        return old_value

    def set_gconf_option(self, path, value):
        """Set the gconf setting on `path` to the defined `value`"""
        client = gconf.client_get_default()
        gconfval = self._get_gconf_from_native_value(value, path)
        client.set(path, gconfval)

    def get_gconf_option(self, path):
        """Get the gconf setting on `path`"""
        client = gconf.client_get_default()
        value = client.get(path)
        return self._get_native_gconf_value(value)

    def _get_gconf_from_native_value(self, value, path):
        """Translates a python type to a GConfValue"""
        if type(value) is str:
            gconfvalue = gconf.Value(gconf.VALUE_STRING)
            gconfvalue.set_string(value)
        elif type(value) is int:
            gconfvalue = gconf.Value(gconf.VALUE_INT)
            gconfvalue.set_int(value)
        elif type(value) is float:
            gconfvalue = gconf.Value(gconf.VALUE_FLOAT)
            gconfvalue.set_float(value)
        elif type(value) is bool:
            gconfvalue = gconf.Value(gconf.VALUE_BOOL)
            gconfvalue.set_bool(value)
        elif type(value) is list:
            gconfvalue = gconf.Value(gconf.VALUE_LIST)
            values = [self._get_gconf_from_native_value(val, path) for val in value]

            if len(values) == 0:
                client = gconf.client_get_default()
                path_value = client.get(path)
                assert(path_value.type == gconf.VALUE_LIST)
                gconfvalue.set_list_type(path_value.get_list_type())
                gconfvalue.set_list([])
            else:
                gconfvalue.set_list_type(values[0].type)
                gconfvalue.set_list(values)
        else:
            raise TypeError("Invalid gconf value type")

        return gconfvalue

    def _get_native_gconf_value(self, value):
        """Translates a GConfValue to a native one"""
        if value.type is gconf.VALUE_STRING:
            return value.get_string()
        elif value.type is gconf.VALUE_INT:
            return value.get_int()
        elif value.type is gconf.VALUE_FLOAT:
            return value.get_float()
        elif value.type is gconf.VALUE_BOOL:
            return value.get_bool()
        elif value.type is gconf.VALUE_LIST:
            return [self._get_native_gconf_value(val) for val in value.get_list()]
        else:
            raise TypeError("Invalid gconf value type")

    def assertVisibleWindowStack(self, stack_start):
        """Check that the visible window stack starts with the windows passed in.

        The start_stack is an iterable of BamfWindow objects.
        Minimised windows are skipped.

        """
        stack = [win for win in self.bamf.get_open_windows() if not win.is_hidden]
        for pos, win in enumerate(stack_start):
            self.assertThat(stack[pos].x_id, Equals(win.x_id),
                            "%r at %d does not equal %r" % (stack[pos], pos, win))

    def start_app(self, app_name, files=[], locale=None):
        """Start one of the known apps, and kill it on tear down.

        Note: This method will clear all instances of this application on tearDown,
        not just the one opened by this method!

        If files is specified, start the application with the specified files.
        If locale is specified, the locale will be set when the application is launched.

        The method returns the BamfApplication instance.

        """
        window = self._open_window(app_name, files, locale)
        if window:
            self.addCleanup(self.close_all_app, app_name)
            return window.application

        raise AssertionError("No new application window was opened.")

    def start_app_window(self, app_name, files=[], locale=None):
        """Start one of the known apps, and kill it on tear down.

        If files is specified, start the application with the specified files.
        If locale is specified, the locale will be set when the application is launched.

        The method returns the BamfWindow instance.

        If no window was opened, or more than one window was opened, this method
        raises AssertionError.

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
            new_windows = []
            [new_windows.extend(a.get_windows()) for a in apps]
            filter_fn = lambda w: w.x_id not in [c.x_id for c in existing_windows]
            new_wins = filter(filter_fn, new_windows)
            if new_wins:
                assert len(new_wins) == 1
                return new_wins[0]
            time.sleep(1)
        return None



    def get_open_windows_by_application(self, app_name):
        """Get a list of BamfWindow instances for the given application name."""
        existing_windows = []
        [existing_windows.extend(a.get_windows()) for a in self.get_app_instances(app_name)]
        return existing_windows

    def close_all_app(self, app_name):
        """Close all instances of the app_name."""
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
        """Returns true if an instance of the application is running."""
        apps = self.get_app_instances(app_name)
        return len(apps) > 0

    def patch_environment(self, key, value):
        """Patch the system environment 'key' with value 'value'.

        This patches os.environ for the duration of the test only:

        os.environ[key] == value

        After the test, the patch will be undone (including deleting the key if
        if didn't exist before this method was called).

        """
        if key in os.environ:
            old_value = os.environ[key]
            self.addCleanup(os.putenv, key, old_value)
        else:
            self.addCleanup(os.unsetenv, key)
        os.environ[key] = value
