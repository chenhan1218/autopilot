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

"""Fixtures for the autopilot functional test suite."""

from __future__ import absolute_import

import logging
import os
import stat
from shutil import rmtree
import tempfile
from textwrap import dedent

from fixtures import Fixture


logger = logging.getLogger(__name__)


class ExecutableScript(Fixture):
    """Write some text to a file on disk and make it executable."""

    def __init__(self, script, extension=".py"):
        """Initialise the fixture.

        :param script: The contents of the script file.
        :param extension: The desired extension on the script file.

        """
        super(ExecutableScript, self).__init__()
        self._script = script
        self._extension = extension

    def setUp(self):
        super(ExecutableScript, self).setUp()
        with tempfile.NamedTemporaryFile(
            suffix=self._extension,
            mode='w',
            delete=False
        ) as f:
            f.write(self._script)
            self.path = f.name
        self.addCleanup(os.unlink, self.path)

        os.chmod(self.path, os.stat(self.path).st_mode | stat.S_IXUSR)


class TempDesktopFile(Fixture):
    def setUp(self):
        super(TempDesktopFile, self).setUp()
        path_created = TempDesktopFile._ensure_desktop_dir_exists()
        self._desktop_file_path = self._create_desktop_file()

        self.addCleanup(
            TempDesktopFile._remove_desktop_file_components,
            path_created,
            self._desktop_file_path,
        )

    def get_desktop_file_path(self):
        return self._desktop_file_path

    @staticmethod
    def _ensure_desktop_dir_exists():
        desktop_file_dir = TempDesktopFile._desktop_file_dir()
        if not os.path.exists(desktop_file_dir):
            return TempDesktopFile._create_desktop_file_dir(desktop_file_dir)
        return ''

    @staticmethod
    def _desktop_file_dir():
        return os.path.join(
            os.getenv('HOME'),
            '.local',
            'share',
            'applications'
        )

    @staticmethod
    def _create_desktop_file_dir(desktop_file_dir):
        """Create the directory specified.

        Returns the component of the path that did not exist, or the empty
        string if the entire path already existed.

        """
        # We might be creating more than just the leaf directory, so we need to
        # keep track of what doesn't already exist and remove it when we're
        # done. Defaults to removing the full path
        path_to_delete = ""
        if not os.path.exists(desktop_file_dir):
            path_to_delete = desktop_file_dir
        full_path, leaf = os.path.split(desktop_file_dir)
        while leaf != "":
            if not os.path.exists(full_path):
                path_to_delete = full_path
            full_path, leaf = os.path.split(full_path)

        try:
            os.makedirs(desktop_file_dir)
        except OSError:
            logger.warning("Directory already exists: %s" % desktop_file_dir)
        return path_to_delete

    @staticmethod
    def _remove_desktop_file_components(created_path, created_file):
        if created_path != "":
            rmtree(created_path)
        else:
            os.remove(created_file)

    @staticmethod
    def _create_desktop_file():
        _, tmp_file_path = tempfile.mkstemp(
            suffix='.desktop',
            dir=TempDesktopFile._desktop_file_dir()
        )
        with open(tmp_file_path, 'w') as desktop_file:
            desktop_file.write(
                dedent("""\
                [Desktop Entry]
                Type=Application
                Exec=Not important
                Path=Not important
                Name=Test app
                Icon=Not important""")
            )
        return tmp_file_path
