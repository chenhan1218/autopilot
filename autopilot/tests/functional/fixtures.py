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

from __future__ import absolute_import

import os
import stat
import tempfile

from fixtures import Fixture


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
