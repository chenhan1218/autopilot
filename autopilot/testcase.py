# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2012-2013 Canonical
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


"""
Quick Start
===========

The :class:`AutopilotTestCase` is the main class test authors will be
interacting with. Every autopilot test case should derive from this class.
:class:`AutopilotTestCase` derives from :class:`testtools.TestCase`, so test
authors can use all the methods defined in that class as well.

**Writing tests**

Tests must be named: ``test_<testname>``, where *<testname>* is the name of the
test. Test runners (including autopilot itself) look for methods with this
naming convention. It is recommended that you make your test names descriptive
of what each test is testing. For example, possible test names include::

    test_ctrl_p_opens_print_dialog
    test_dash_remembers_maximized_state

**Launching the Application Under Test**

If you are writing a test for an application, you need to use the
:meth:`~AutopilotTestCase.launch_test_application` method. This will launch the
application, enable introspection, and return a proxy object representing the
root of the application introspection tree.

"""

from __future__ import absolute_import

import logging
import os
import signal
import subprocess

from testscenarios import TestWithScenarios
from testtools import TestCase
from testtools.content import text_content
from testtools.matchers import Equals
from time import sleep

from autopilot.process import ProcessManager
from autopilot.input import Keyboard, Mouse
from autopilot.introspection import (
    get_application_launcher,
    get_application_launcher_from_string_hint,
    get_autopilot_proxy_object_for_process,
    launch_application,
    ProcessSearchError,
)
from autopilot.display import Display
from autopilot.utilities import on_test_started
from autopilot.keybindings import KeybindingsHelper
from autopilot.matchers import Eventually
try:
    from autopilot import tracepoint as tp
    HAVE_TRACEPOINT = True
except ImportError:
    HAVE_TRACEPOINT = False


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


def _lttng_trace_test_started(test_id):
    if HAVE_TRACEPOINT:
        tp.emit_test_started(test_id)
    else:
        logger.warning(
            "No tracing available - install the python-autopilot-trace "
            "package!")


def _lttng_trace_test_ended(test_id):
    if HAVE_TRACEPOINT:
        tp.emit_test_ended(test_id)


class AutopilotTestCase(TestWithScenarios, TestCase, KeybindingsHelper):
    """Wrapper around testtools.TestCase that adds significant functionality.

    This class should be the base class for all autopilot test case classes.
    Not using this class as the base class disables several important
    convenience methods, and also prevents the use of the failed-test
    recording tools.

    """

    def setUp(self):
        super(AutopilotTestCase, self).setUp()
        on_test_started(self)

        _lttng_trace_test_started(self.id())
        self.addCleanup(_lttng_trace_test_ended, self.id())

        self._process_manager = None
        self._mouse = None
        self._kb = None
        self._display = None

        try:
            self._app_snapshot = \
                self.process_manager.get_running_applications()
            self.addCleanup(self._compare_system_with_app_snapshot)
        except RuntimeError:
            logger.warning(
                "Process manager backend unavailable, application snapshot "
                "support disabled.")

    @property
    def process_manager(self):
        if self._process_manager is None:
            self._process_manager = ProcessManager.create()
        return self._process_manager

    @property
    def keyboard(self):
        if self._kb is None:
            self._kb = Keyboard.create()
        return self._kb

    @property
    def mouse(self):
        if self._mouse is None:
            self._mouse = Mouse.create()
        return self._mouse

    @property
    def display(self):
        if self._display is None:
            self._display = Display.create()
        return self._display

    def launch_test_application(self, application, *arguments, **kwargs):
        """Launch ``application`` and return a proxy object for the
        application.

        Use this method to launch an application and start testing it. The
        positional arguments are used as arguments to the application to lanch.
        Keyword arguments are used to control the manner in which the
        application is launched.

        This method is designed to be flexible enough to launch all supported
        types of applications. Autopilot can automatically determine how to
        enable introspection support for dynamically linked binary
        applications. For example, to launch a binary Gtk application, a test
        might start with::

            app_proxy = self.launch_test_application('gedit')

        Applications can be given command line arguments by supplying
        positional arguments to this method. For example, if we want to launch
        ``gedit`` with a certain document loaded, we might do this::

            app_proxy = self.launch_test_application(
                'gedit', '/tmp/test-document.txt')

        ... a Qt5 Qml application is launched in a similar fashion::

            app_proxy = self.launch_test_application(
                'qmlscene', 'my_scene.qml')

        If you wish to launch an application that is not a dynamically linked
        binary, you must specify the application type. For example, a Qt4
        python application might be launched like this::

            app_proxy = self.launch_test_application(
                'my_qt_app.py', app_type='qt')

        Similarly, a python/Gtk application is launched like so::

            app_proxy = self.launch_test_application(
                'my_gtk_app.py', app_type='gtk')

        .. seealso::

            Method :py:meth:`AutopilotTestCase.pick_app_launcher`
                Specify application introspection type globally.

        :param application: The application to launch. The application can be
            specified as:

             * A full, absolute path to an executable file.
               (``/usr/bin/gedit``)
             * A relative path to an executable file.
               (``./build/my_app``)
             * An app name, which will be searched for in $PATH (``my_app``)

        :keyword app_type: If set, provides a hint to autopilot as to which
            kind of introspection to enable. This is needed when the
            application you wish to launch is *not* a dynamically linked
            binary. Valid values are 'gtk' or 'qt'. These strings are case
            insensitive.

        :keyword launch_dir: If set to a directory that exists the process
            will be launched from that directory.

        :keyword capture_output: If set to True (the default), the process
            output will be captured and attached to the test as test detail.

        :keyword emulator_base: If set, specifies the base class to be used for
            all emulators for this loaded application.

        :raises: **ValueError** if unknown keyword arguments are passed.
        :return: A proxy object that represents the application. Introspection
         data is retrievable via this object.

        """
        app_path = subprocess.check_output(['which', application]).strip()
        # Get a launcher, tests can override this if they need:
        launcher_hint = kwargs.pop('app_type', '')
        launcher = None
        if launcher_hint != '':
            launcher = get_application_launcher_from_string_hint(launcher_hint)
        if launcher is None:
            try:
                launcher = self.pick_app_launcher(app_path)
            except RuntimeError:
                pass
        if launcher is None:
            raise RuntimeError(
                "Autopilot could not determine the correct introspection type "
                "to use. You can specify one by overriding the "
                "AutopilotTestCase.pick_app_launcher method.")
        emulator_base = kwargs.pop('emulator_base', None)
        process = launch_application(launcher, app_path, *arguments, **kwargs)
        self.addCleanup(self._kill_process_and_attach_logs, process)
        return get_autopilot_proxy_object_for_process(process, emulator_base)

    def _compare_system_with_app_snapshot(self):
        """Compare the currently running application with the last snapshot.

        This method will raise an AssertionError if there are any new
        applications currently running that were not running when the snapshot
        was taken.
        """
        if self._app_snapshot is None:
            raise RuntimeError("No snapshot to match against.")

        new_apps = []
        for i in range(10):
            current_apps = self.process_manager.get_running_applications()
            new_apps = filter(
                lambda i: i not in self._app_snapshot, current_apps)
            if not new_apps:
                self._app_snapshot = None
                return
            sleep(1)
        self._app_snapshot = None
        raise AssertionError(
            "The following apps were started during the test and not closed: "
            "%r", new_apps)

    def patch_environment(self, key, value):
        """Patch the process environment, setting *key* with value *value*.

        This patches os.environ for the duration of the test only. After
        calling this method, the following should be True::

            os.environ[key] == value

        After the test, the patch will be undone (including deleting the key if
        if didn't exist before this method was called).

        .. note:: Be aware that patching the environment in this way only
         affects the current autopilot process, and any processes spawned by
         autopilot. If you are planing on starting an application from within
         autopilot and you want this new application to read the patched
         environment variable, you must patch the environment *before*
         launching the new process.

        :param string key: The name of the key you wish to set. If the key
         does not already exist in the process environment it will be created
         (and then deleted when the test ends).
        :param string value: The value you wish to set.

        """
        if key in os.environ:
            def _undo_patch(key, old_value):
                logger.info(
                    "Resetting environment variable '%s' to '%s'",
                    key,
                    old_value
                )
                os.environ[key] = old_value
            old_value = os.environ[key]
            self.addCleanup(_undo_patch, key, old_value)
        else:
            def _remove_patch(key):
                try:
                    del os.environ[key]
                except KeyError:
                    logger.warning(
                        "Attempted to delete environment key '%s' that doesn't"
                        "exist in the environment",
                        key
                    )
            self.addCleanup(_remove_patch, key)
        os.environ[key] = value

    def assertVisibleWindowStack(self, stack_start):
        """Check that the visible window stack starts with the windows passed
        in.

        .. note:: Minimised windows are skipped.

        :param stack_start: An iterable of
         :class:`~autopilot.process.Window` instances.
        :raises: **AssertionError** if the top of the window stack does not
         match the contents of the stack_start parameter.

        """
        stack = [
            win for win in
            self.process_manager.get_open_windows() if not win.is_hidden]
        for pos, win in enumerate(stack_start):
            self.assertThat(
                stack[pos].x_id, Equals(win.x_id),
                "%r at %d does not equal %r" % (stack[pos], pos, win))

    def assertProperty(self, obj, **kwargs):
        """Assert that *obj* has properties equal to the key/value pairs in
        kwargs.

        This method is intended to be used on objects whose attributes do not
        have the :meth:`wait_for` method (i.e.- objects that do not come from
        the autopilot DBus interface).

        For example, from within a test, to assert certain properties on a
        `~autopilot.process.Window` instance::

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
                raise AssertionError(
                    "Object %r does not have an attribute named '%s'"
                    % (obj, prop_name))
            if callable(attr):
                raise ValueError(
                    "Object %r's '%s' attribute is a callable. It must be a "
                    "property." % (obj, prop_name))
            self.assertThat(
                lambda: getattr(obj, prop_name),
                Eventually(Equals(desired_value)))

    assertProperties = assertProperty

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

    def _attach_process_logs(self, process):
        stdout, stderr = process.communicate()
        return_code = process.returncode
        self.addDetail('process-return-code', text_content(str(return_code)))
        self.addDetail('process-stdout', text_content(stdout))
        self.addDetail('process-stderr', text_content(stderr))

    def _kill_process(self, process):
        logger.info("waiting for process to exit.")
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except OSError:
            logger.info("Appears process has already exited.")
        for i in range(10):
            process.poll()
            if process.returncode is not None:
                break
            if i == 9:
                logger.info("Killing process group, since it hasn't exited after 10 seconds.")
                os.killpg(process.pid, signal.SIGKILL)
            sleep(1)

    def _kill_process_and_attach_logs(self, process):
        self._kill_process(process)
        self._attach_process_logs(process)
