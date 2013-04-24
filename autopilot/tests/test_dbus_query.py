# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2013 Canonical
# Author: Christopher Lee
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.

import windowmocker
import json
import os
from tempfile import mktemp

from autopilot.testcase import AutopilotTestCase
from testtools.matchers import Equals, NotEquals

class DbusQueryTests(AutopilotTestCase):
    """A collection of dbus query tests for autopilot."""

    def start_fully_featured_app(self):
        """Create an application that includes menus and other nested
        elements."""
        window_spec = {
            "Menu": [
                {
                    "Title": "File",
                    "Menu": [
                        "Open",
                        "Save",
                        "Save As",
                        "Quit"
                    ]
                },
                {
                    "Title": "Help",
                    "Menu": [
                        "Help 1",
                        "Help 2",
                        "Help 3",
                        "Help 4"
                    ]
                }
            ],
            "Contents": "TextEdit"
        }

        file_path = mktemp()
        json.dump(window_spec, open(file_path, 'w'))
        self.addCleanup(os.remove, file_path)

        return self.launch_test_application('window-mocker', file_path)

    def pick_app_launcher(self, app_path):
        # force Qt app introspection:
        from autopilot.introspection.qt import QtApplicationLauncher
        return QtApplicationLauncher()

    def test_select_single_selects_only_available_object(self):
        """Must be able to select a single unique object."""
        app = self.start_fully_featured_app()
        main_window = app.select_single('QMainWindow')
        self.assertThat(main_window, NotEquals(None))

    def test_single_select_on_object(self):
        """Must be able to select a single unique child of an object."""
        app = self.start_fully_featured_app()
        main_win = app.select_single('QMainWindow')
        menu_bar = main_win.select_single('QMenuBar')
        self.assertThat(menu_bar, NotEquals(None))

    def test_select_multiple_on_object_returns_all(self):
        """Must be able to select all child objects."""
        app = self.start_fully_featured_app()
        main_win = app.select_single('QMainWindow')
        menu_bar = main_win.select_single('QMenuBar')
        menus = menu_bar.select_many('QMenu')
        self.assertThat(len(menus), Equals(2))

    def test_select_multiple_on_object_with_parameter(self):
        """Must be able to select a specific object determined by a parameter."""
        app = self.start_fully_featured_app()
        main_win = app.select_single('QMainWindow')
        menu_bar = main_win.select_single('QMenuBar')
        help_menu = menu_bar.select_many('QMenu', title='Help')
        self.assertThat(len(help_menu), Equals(1))
        self.assertThat(help_menu[0].title, Equals('Help'))

    def test_select_single_on_object_with_param(self):
        """Must only select a single unique object using a parameter."""
        app = self.start_fully_featured_app()
        main_win = app.select_single('QMainWindow')
        menu_bar = main_win.select_single('QMenuBar')
        help_menu = menu_bar.select_single('QMenu', title='Help')
        self.assertThat(help_menu, NotEquals(None))
        self.assertThat(help_menu.title, Equals('Help'))
