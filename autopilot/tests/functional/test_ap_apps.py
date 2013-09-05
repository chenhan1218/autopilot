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


import datetime
import os
import stat
import subprocess
import logging
from mock import patch
from tempfile import mktemp
from testtools.matchers import raises, LessThan
from textwrap import dedent
from time import sleep

from autopilot.testcase import AutopilotTestCase
from autopilot.introspection import (
    get_proxy_object_for_existing_process,
    ProcessSearchError,
    _pid_is_running,
)


logger = logging.getLogger(__name__)


def _get_unused_pid():
    """Returns a Process ID number that isn't currently running.

    :raises: **RuntimeError** if unable to produce a number that doesn't
     correspond to a currently running process.
    """
    for i in xrange(10000, 20000):
        if not _pid_is_running(i):
            return i
    raise RuntimeError("Unable to find test PID.")


class ApplicationTests(AutopilotTestCase):
    """A base class for application mixin tests."""

    def write_script(self, content, extension=".py"):
        """Write a script to a temporary file, make it executable,
        and return the path to the script file.

        """
        path = mktemp(extension)
        open(path, 'w').write(content)
        self.addCleanup(os.unlink, path)

        os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)
        return path


class ApplicationLaunchTests(ApplicationTests):

    def test_unknown_app_exception(self):
        """launch_test_app must raise a RuntimeError when asked to launch an
        application that has an unknown introspection type.

        """
        path = self.write_script("")
        expected_error_message = "Autopilot could not determine the correct \
introspection type to use. You can specify one by overriding the \
AutopilotTestCase.pick_app_launcher method."

        self.assertThat(
            lambda: self.launch_test_application(path),
            raises(RuntimeError(expected_error_message)))

    def test_creating_app_proxy_for_running_app_not_on_dbus_fails(self):
        """Creating app proxy object for an application that isn't connected to
        the dbus session must raise a ProcessSearchError exception.

        """
        path = self.write_script(dedent("""\
            #!/usr/bin/python

            from time import sleep

            while True:
                print "Still running"
                sleep(1)
        """))

        expected_error = "Search criteria returned no results"
        self.assertThat(
            lambda: self.launch_test_application(path, app_type='qt'),
            raises(ProcessSearchError(expected_error))
        )

    def test_creating_app_for_non_running_app_fails(self):
        """Attempting to create an application proxy object for a process
        (using a PID) that isn't running must raise an exception.

        """
        pid = _get_unused_pid()

        self.assertThat(
            lambda: get_proxy_object_for_existing_process(pid=pid),
            raises(ProcessSearchError("PID %d could not be found" % pid))
        )

    def test_creating_proxy_for_segfaulted_app_failed(self):
        """Creating a proxy object for an application that has died since
        launching must throw ProcessSearchError exception.

        """
        path = self.write_script(dedent("""\
            #!/usr/bin/python

            from time import sleep
            import sys

            sleep(5)
            sys.exit(1)
        """))

        expected_error = "Process exited with exit code: 1"
        self.assertThat(
            lambda: self.launch_test_application(path, app_type='qt'),
            raises(ProcessSearchError(expected_error))
        )

    @patch(
        'autopilot.introspection._search_for_valid_connections',
        new=lambda *args: []
    )
    def test_creating_proxy_for_segfaulted_app_fails_quicker(self):
        """Searching for a process that has died since launching, the search
        must fail before the 10 second timeout.

        """
        path = self.write_script(dedent("""\
            #!/usr/bin/python

            from time import sleep
            import sys

            sleep(1)
            sys.exit(1)
        """))
        start = datetime.datetime.now()

        try:
            self.launch_test_application(path, app_type='qt')
        except ProcessSearchError:
            end = datetime.datetime.now()
        else:
            self.fail(
                "launch_test_application didn't raise expected exception"
            )

        difference = end - start
        self.assertThat(difference.total_seconds(), LessThan(5))

    def test_closing_app_produces_good_error_from_get_state_by_path(self):
        """Testing an application that closes before the test ends must
        produce a good error message when calling get_state_by_path on the
        application proxy object.

        """
        path = self.write_script(dedent("""\
            #!/usr/bin/python
            from PyQt4.QtGui import QMainWindow, QApplication
            from PyQt4.QtCore import QTimer

            from sys import argv

            app = QApplication(argv)
            win = QMainWindow()
            win.show()
            QTimer.singleShot(8000, app.exit)
            app.exec_()
            """))
        app_proxy = self.launch_test_application(path, app_type='qt')
        self.assertTrue(app_proxy is not None)

        def crashing_fn():
            for i in range(10):
                logger.debug("%d %r", i, app_proxy.get_state_by_path("/"))
                sleep(1)

        self.assertThat(
            crashing_fn,
            raises(
                RuntimeError(
                    "Application under test exited before the test finished!"
                )
            )
        )


class QtTests(ApplicationTests):

    def _find_qt_binary_chooser(self, version, name):
        # Check for existence of the binary when qtchooser is installed
        # We cannot use 'which', as qtchooser installs wrappers - we need to
        # check in the actual library paths
        env = subprocess.check_output(
            ['qtchooser', '-qt=' + version, '-print-env']).split('\n')
        for i in env:
            if i.find('QTTOOLDIR') >= 0:
                path = i.lstrip("QTTOOLDIR=").strip('"') + "/" + name
                if os.path.exists(path):
                    return path
                return None
        return None

    def _find_qt_binary_old(self, version, name):
        # Check for the existence of the binary the old way
        try:
            path = subprocess.check_output(['which', 'qmlviewer']).strip()
        except subprocess.CalledProcessError:
            path = None
        return path

    def setUp(self):
        super(QtTests, self).setUp()

        try:
            qtversions = subprocess.check_output(
                ['qtchooser', '-list-versions']).split('\n')
            check_func = self._find_qt_binary_chooser
        except OSError:
            # This means no qtchooser is installed, so let's check for
            # qmlviewer and qmlscene manually, the old way
            qtversions = ['qt4', 'qt5']
            check_func = self._find_qt_binary_old

        not_found = True
        if 'qt4' in qtversions:
            path = check_func('qt4', 'qmlviewer')
            if path:
                not_found = False
                self.app_path = path
                self.patch_environment("QT_SELECT", "qt4")

        if 'qt5' in qtversions:
            path = check_func('qt5', 'qmlscene')
            if path:
                not_found = False
                self.app_path = path
                self.patch_environment("QT_SELECT", "qt5")

        if not_found:
            self.skip("Neither qmlviewer nor qmlscene is installed")

    def test_can_launch_qt_app(self):
        app_proxy = self.launch_test_application(self.app_path, app_type='qt')
        self.assertTrue(app_proxy is not None)

    def test_can_launch_qt_script(self):
        path = self.write_script(dedent("""\
            #!/usr/bin/python
            from PyQt4.QtGui import QMainWindow, QApplication
            from sys import argv

            app = QApplication(argv)
            win = QMainWindow()
            win.show()
            app.exec_()
            """))
        app_proxy = self.launch_test_application(path, app_type='qt')
        self.assertTrue(app_proxy is not None)

    def test_can_launch_wrapper_script(self):
        path = self.write_script(dedent("""\
            #!/usr/bin/python
            from PyQt4.QtGui import QMainWindow, QApplication
            from sys import argv

            app = QApplication(argv)
            win = QMainWindow()
            win.show()
            app.exec_()
            """))
        wrapper_path = self.write_script(dedent("""\
            #!/bin/sh

            echo "Launching %s"
            %s $*
            """ % (path, path)),
            extension=".sh")
        app_proxy = self.launch_test_application(wrapper_path, app_type='qt')
        self.assertTrue(app_proxy is not None)


class GtkTests(ApplicationTests):

    def setUp(self):
        super(GtkTests, self).setUp()

        try:
            self.app_path = subprocess.check_output(
                ['which', 'gnome-mahjongg']).strip()
        except subprocess.CalledProcessError:
            self.skip("gnome-mahjongg not found.")

    def test_can_launch_gtk_app(self):
        app_proxy = self.launch_test_application(self.app_path)
        self.assertTrue(app_proxy is not None)

    def test_can_launch_gtk_script(self):
        path = self.write_script(dedent("""\
            #!/usr/bin/python
            from gi.repository import Gtk

            win = Gtk.Window()
            win.connect("delete-event", Gtk.main_quit)
            win.show_all()
            Gtk.main()
            """))
        app_proxy = self.launch_test_application(path, app_type='gtk')
        self.assertTrue(app_proxy is not None)

    def test_can_launch_wrapper_script(self):
        path = self.write_script(dedent("""\
            #!/usr/bin/python
            from gi.repository import Gtk

            win = Gtk.Window()
            win.connect("delete-event", Gtk.main_quit)
            win.show_all()
            Gtk.main()
            """))
        wrapper_path = self.write_script(dedent("""\
            #!/bin/sh

            echo "Launching %s"
            %s
            """ % (path, path)),
            extension=".sh")
        app_proxy = self.launch_test_application(wrapper_path, app_type='gtk')
        self.assertTrue(app_proxy is not None)
