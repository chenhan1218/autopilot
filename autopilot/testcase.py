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
from gi.repository import Gio
import logging
import os
import signal
from subprocess import (
    call,
    CalledProcessError,
    check_output,
    )

from testscenarios import TestWithScenarios
from testtools import TestCase
from testtools.content import text_content
from testtools.matchers import Equals
from time import sleep

from autopilot.processmanager import ProcessManager
from autopilot.input import Keyboard, Mouse
from autopilot.introspection import (
    get_application_launcher,
    get_autopilot_proxy_object_for_process,
    launch_application,
    launch_process,
    )
from autopilot.display import Display
from autopilot.globals import on_test_started
from autopilot.keybindings import KeybindingsHelper
from autopilot.matchers import Eventually


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


class AutopilotTestCase(TestWithScenarios, TestCase, KeybindingsHelper):
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
    :class:`~autopilot.processmanager.Application` or
    :class:`~autopilot.processmanager.Window` instance to the launched
    process respectively. All applications launched in this way will be closed
    when the test ends.


    **Patch Process Environment**

    The :meth:`~autopilot.testcase.AutopilotTestCase.patch_environment` method
    patches the process environment, for the duration of the current test
    only. This allows you to set an environment variable for the duration of the
    current test only.

    """

    KNOWN_APPS = {
        'Character Map' : {
            'desktop-file': 'gucharmap.desktop',
            'process-name': 'gucharmap',
            },
        'Calculator' : {
            'desktop-file': 'gcalctool.desktop',
            'process-name': 'gnome-calculator',
            },
        'Mahjongg' : {
            'desktop-file': 'mahjongg.desktop',
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
        on_test_started(self)

        self._process_manager = ProcessManager.create()
        self._app_snapshot = self._process_manager.get_running_applications()
        self.addCleanup(self._compare_system_with_app_snapshot)

        self.keyboard = Keyboard.create()
        self.mouse = Mouse.create()

        self.screen_geo = Display.create()
        self.addCleanup(self.keyboard.cleanup)
        self.addCleanup(self.mouse.cleanup)

    def _compare_system_with_app_snapshot(self):
        """Compare the currently running application with the last snapshot.

        This method will raise an AssertionError if there are any new applications
        currently running that were not running when the snapshot was taken.
        """
        if self._app_snapshot is None:
            raise RuntimeError("No snapshot to match against.")

        new_apps = []
        for i in range(10):
            current_apps = self._process_manager.get_running_applications()
            new_apps = filter(lambda i: i not in self._app_snapshot, current_apps)
            if not new_apps:
                self._app_snapshot = None
                return
            sleep(1)
        self._app_snapshot = None
        raise AssertionError("The following apps were started during the test and not closed: %r", new_apps)

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
        :returns: A :class:`~autopilot.processmanager.Application` instance.

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
        :returns: A :class:`~autopilot.processmanger.Window` instance.

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
        self._process_manager.launch_application(app['desktop-file'], files)
        apps = self._process_manager.get_running_applications_by_desktop_file(app['desktop-file'])

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
            sleep(1)
        return None

    def get_open_windows_by_application(self, app_name):
        """Get a list of ~autopilot.processmanager.Window` instances
        for the given application name.

        :param app_name: The name of one of the well-known applications.
        :returns: A list of :class:`~autopilot.processmanager.Window`
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
        """Get `~autopilot.processmanager.Application` instances for app_name."""
        desktop_file = self.KNOWN_APPS[app_name]['desktop-file']
        return self._process_manager.get_running_applications_by_desktop_file(desktop_file)

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

        :param stack_start: An iterable of
         `~autopilot.processmanager.Window` instances.
        :raises: **AssertionError** if the top of the window stack does not
         match the contents of the stack_start parameter.

        """
        stack = [win for win in self._process_manager.get_open_windows() if not win.is_hidden]
        for pos, win in enumerate(stack_start):
            self.assertThat(stack[pos].x_id, Equals(win.x_id),
                            "%r at %d does not equal %r" % (stack[pos], pos, win))

    def assertProperty(self, obj, **kwargs):
        """Assert that *obj* has properties equal to the key/value pairs in kwargs.

        This method is intended to be used on objects whose attributes do not
        have the :meth:`wait_for` method (i.e.- objects that do not come from
        the autopilot DBus interface).

        For example, from within a test, to assert certain properties on a
        `~autopilot.processmanager.Window` instance::

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

    def launch_test_application(self, application, *arguments, **kwargs):
        """Launch ``application`` and return a proxy object for the application.

        Use this method to launch an application and start testing it. The
        positional arguments are used as arguments to the application to lanch.
        Keyword arguments are used to control the manner in which the application
        is launched.

        This method is designed to be flexible enough to launch all supported
        types of applications. For example, to launch a traditional Gtk application,
        a test might start with::

            app_proxy = self.launch_test_application('gedit')

        ... a Qt4 Qml application might be launched like this::

            app_proxy = self.launch_test_application('qmlviewer', 'my_scene.qml')

        ... a Qt5 Qml application is launched in a similar fashion::

            app_proxy = self.launch_test_application('qmlscene', 'my_scene.qml')

        :param application: The application to launch. The application can be
            specified as:

             * A full, absolute path to an executable file. (``/usr/bin/gedit``)
             * A relative path to an executable file. (``./build/my_app``)
             * An app name, which will be searched for in $PATH (``my_app``)

        :keyword launch_dir:  If set to a directory that exists the process will be
            launched from that directory.

        :keyword capture_output: If set to True (the default), the process output
            will be captured and attached to the test as test detail.

        :raises: **ValueError** if unknown keyword arguments are passed.
        :return: A proxy object that represents the application. Introspection
         data is retrievable via this object.

        """
        # first, we get a launcher. Tests can override this if they need:
        launcher = self.pick_app_launcher(application)
        if launcher is None:
            raise RuntimeError("Autopilot could not determine the correct \
                introspection type to use. You can specify one by overriding \
                the AutopilotTestCase.pick_app_launcher method.")
        process = launch_application(launcher, application, *arguments, **kwargs)
        self.addCleanup(self._kill_process_and_attach_logs, process)
        return get_autopilot_proxy_object_for_process(process)

    def pick_app_launcher(self, app_path):
        """Given an application path, return an object suitable for launching
        the application.

        This function attempts to guess what kind of application you are
        launching. If, for some reason the default implementation returns the
        wrong launcher, test authors may override this method to provide their
        own implemetnation.

        The default implementation calls
        :py:func:`autopilot.introspection.get_application_launcher`

        """
        # default implementation is in autopilot.introspection:
        return get_application_launcher(app_path)

    def _kill_process_and_attach_logs(self, process):
        process.kill()
        logger.info("waiting for process to exit.")
        for i in range(10):
            if process.returncode is not None:
                break
            if i == 9:
                logger.info("Terminating process group, since it hasn't exited after 10 seconds.")
                os.killpg(process.pid, signal.SIGTERM)
            sleep(1)
        stdout, stderr = process.communicate()
        self.addDetail('process-stdout', text_content(stdout))
        self.addDetail('process-stderr', text_content(stderr))
