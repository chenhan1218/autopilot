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


import os
import stat
import subprocess
from tempfile import mktemp
from testtools.matchers import raises
from textwrap import dedent

from autopilot.testcase import AutopilotTestCase


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
