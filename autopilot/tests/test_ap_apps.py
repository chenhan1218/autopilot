# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2012 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.

import subprocess

from autopilot.testcase import AutopilotTestCase
from autopilot.introspection.gtk import GtkIntrospectionTestMixin
from autopilot.introspection.qt import QtIntrospectionTestMixin

class QtTests(AutopilotTestCase, QtIntrospectionTestMixin):

    def setUp(self):
        super(QtTests, self).setUp()

        try:
            self.app_path = subprocess.check_output(['which','qmlviewer']).strip()
        except subprocess.CalledProcessError:
            self.skip("qmlviewer not found.")

    def test_can_launch_qt_app(self):
        app_proxy = self.launch_test_application(self.app_path)
        self.assertTrue(app_proxy is not None)


class GtkTests(AutopilotTestCase, GtkIntrospectionTestMixin):

    def setUp(self):
        super(GtkTests, self).setUp()

        try:
            self.app_path = subprocess.check_output(['which','gnome-mahjongg']).strip()
        except subprocess.CalledProcessError:
            self.skip("gnome-mahjongg not found.")

    def test_can_launch_qt_app(self):
        app_proxy = self.launch_test_application(self.app_path)
        self.assertTrue(app_proxy is not None)
