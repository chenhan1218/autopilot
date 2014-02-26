# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2014 Canonical
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

import autopilot.tests.functional as test_init
from autopilot.tests.functional import TempDesktopFile
from autopilot.tests.functional import TempDesktopFile as TDF


import os.path
from mock import patch
from testtools import TestCase
from testtools.matchers import Equals


class TempDesktopFileTests(TestCase):
    def test_desktop_file_dir_created_if_doesnt_exist(self):
        test_desktop_file_dir = self.getUniqueString()
        with patch.object(test_init.os.path, 'exists', return_value=False):
            with patch.object(TDF, '_create_desktop_file_dir') as p_create_dir:
                temp_desktop_file = TempDesktopFile()
                temp_desktop_file._ensure_desktop_dir_exists(
                    test_desktop_file_dir
                )

                p_create_dir.assert_called_once_with(test_desktop_file_dir)

    def test_correct_desktop_file_path_used(self):
        test_user_home_path = self.getUniqueString()
        with patch.object(
            test_init.os, 'getenv', return_value=test_user_home_path
        ):
            temp_desktop_file = TempDesktopFile()
            self.assertThat(
                temp_desktop_file._get_local_desktop_file_directory(),
                Equals(
                    os.path.join(
                        test_user_home_path, '.local', 'share', 'applications'
                    )
                )
            )

    def test_desktop_file_removed_at_cleanup(self):
        with patch.object(
            test_init.os, 'getenv', return_value="/tmp"
        ):
            desktop_file_fixture = self.useFixture(TempDesktopFile())
            tmp_file_name = desktop_file_fixture.get_desktop_file_path()
            self.addCleanup(self.remove_if_exists, tmp_file_name)

            self.assertTrue(os.path.exists(tmp_file_name))
            desktop_file_fixture.cleanUp()
            self.assertFalse(os.path.exists(tmp_file_name))

    def remove_if_exists(self, path):
        if os.path.exists(path):
            os.remove(path)
