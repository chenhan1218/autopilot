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


import json
import os
from tempfile import mktemp

from autopilot.testcase import AutopilotTestCase
from testtools.matchers import Equals, NotEquals, raises


class DbusQueryTests(AutopilotTestCase):
    """A collection of dbus query tests for autopilot."""

    def start_fully_featured_app(self):
        """Create an application that includes menus and other nested
        elements.

        """
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

        return self.launch_test_application(
            'window-mocker', file_path, app_type="qt")

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
        """Must be able to select a specific object determined by a
        parameter.

        """
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

    def test_select_many_uses_unique_object(self):
        """Given 2 objects of the same type with childen, selection on one will
        only get its children.

        """
        app = self.start_fully_featured_app()
        main_win = app.select_single('QMainWindow')
        menu_bar = main_win.select_single('QMenuBar')
        help_menu = menu_bar.select_single('QMenu', title='Help')
        actions = help_menu.select_many('QAction')
        self.assertThat(len(actions), Equals(5))

    def test_select_single_no_name_no_parameter_raises_exception(self):
        app = self.start_fully_featured_app()
        fn = lambda: app.select_single()
        self.assertThat(fn, raises(TypeError))

    def test_select_single_no_match_returns_none(self):
        app = self.start_fully_featured_app()
        failed_match = app.select_single("QMadeupType")
        self.assertThat(failed_match, Equals(None))

    def test_select_single_parameters_only(self):
        app = self.start_fully_featured_app()
        main_win = app.select_single('QMainWindow')
        titled_help = main_win.select_single(title='Help')
        self.assertThat(titled_help, NotEquals(None))
        self.assertThat(titled_help.title, Equals('Help'))

    def test_select_single_parameters_no_match_returns_none(self):
        app = self.start_fully_featured_app()
        failed_match = app.select_single(title="Non-existant object")
        self.assertThat(failed_match, Equals(None))

    def test_select_single_returning_multiple_raises(self):
        app = self.start_fully_featured_app()
        fn = lambda: app.select_single('QMenu')
        self.assertThat(fn, raises(ValueError))

    def test_select_many_no_name_no_parameter_raises_exception(self):
        app = self.start_fully_featured_app()
        fn = lambda: app.select_single()
        self.assertThat(fn, raises(TypeError))

    def test_select_many_only_using_parameters(self):
        app = self.start_fully_featured_app()
        many_help_menus = app.select_many(title='Help')
        self.assertThat(len(many_help_menus), Equals(2))

    def test_select_many_with_no_parameter_matches_returns_empty_list(self):
        app = self.start_fully_featured_app()
        failed_match = app.select_many('QMenu', title='qwerty')
        self.assertThat(failed_match, Equals([]))
