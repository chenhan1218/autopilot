# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2013 Canonical
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

from gi.repository import GLib
from mock import Mock, patch
from testtools import TestCase
from testtools.matchers import (
    Not,
    Raises,
)

import autopilot.process._bamf as _b
from autopilot.process._bamf import _launch_application


class ProcessBamfTests(TestCase):
    def test_launch_application_attempts_launch_uris_as_manager_first(self):
        """_launch_application must attempt to use launch_uris_as_manager
        before trying to use launch_uris.

        """
        test_desktop_file = self.getUniqueString()
        process = Mock()

        with patch.object(
            _b.Gio.DesktopAppInfo,
            'new',
            new=process
        ):
            self.assertThat(
                lambda: _launch_application(test_desktop_file, []),
                Not(Raises())
            )
            self.assertFalse(process.launch_uris.called)
            process.launch_uris_as_manager.called_once_with(
                [],
                None,
                GLib.SpawnFlags.SEARCH_PATH
                | GLib.SpawnFlags.STDOUT_TO_DEV_NULL,
                None,
                None,
                None,
                None
            )

    def test_launch_application_falls_back_to_earlier_ver_uri_call(self):
        """_launch_application must fallback to using launch_uris if the call
        to launch_uris_as_manager fails due to being an older version.

        """
        test_desktop_file = self.getUniqueString()
        process = Mock()
        process.launch_uris_as_manager.side_effect = TypeError(
            "Argument 2 does not allow None as a value"
        )

        with patch.object(
            _b.Gio.DesktopAppInfo,
            'new',
            return_value=process
        ):
            _launch_application(test_desktop_file, [])
            self.assertThat(
                lambda: _launch_application(test_desktop_file, []),
                Not(Raises())
            )
            process.launch_uris.called_once_with([], None)
