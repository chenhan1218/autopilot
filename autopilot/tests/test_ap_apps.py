# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2012 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.

import os
import stat
import subprocess
from tempfile import mktemp
from textwrap import dedent

from autopilot.testcase import AutopilotTestCase
from autopilot.introspection.gtk import GtkIntrospectionTestMixin
from autopilot.introspection.qt import QtIntrospectionTestMixin


class ApplicationTests(AutopilotTestCase):
    """A base class for application mixin tests."""

    def write_script(self, content, extension=".py"):
        """Writes a python script to a temporary file, makes it executable,
        and returns the path to the script file.

        """
        path = mktemp(extension)
        open(path, 'w').write(content)
        self.addCleanup(os.unlink, path)

        os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)
        return path


class QtTests(ApplicationTests, QtIntrospectionTestMixin):

    def setUp(self):
        super(QtTests, self).setUp()

        try:
            self.app_path = subprocess.check_output(['which','qmlviewer']).strip()
        except subprocess.CalledProcessError:
            self.skip("qmlviewer not found.")

    def test_can_launch_qt_app(self):
        app_proxy = self.launch_test_application(self.app_path)
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
        app_proxy = self.launch_test_application(path)
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
        app_proxy = self.launch_test_application(wrapper_path)
        self.assertTrue(app_proxy is not None)


class GtkTests(ApplicationTests, GtkIntrospectionTestMixin):

    def setUp(self):
        super(GtkTests, self).setUp()

        try:
            self.app_path = subprocess.check_output(['which','gnome-mahjongg']).strip()
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
        app_proxy = self.launch_test_application(path)
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
        app_proxy = self.launch_test_application(wrapper_path)
        self.assertTrue(app_proxy is not None)
