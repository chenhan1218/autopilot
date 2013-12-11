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

from autopilot.application.launcher import _set_upstart_env, _unset_upstart_env
from autopilot.application.environment import ApplicationEnvironment


class UpstartApplicationEnvironment(ApplicationEnvironment):

    def prepare_environment(self, app_path, arguments):
        """Prepare the application, or environment to launch with
        autopilot-support.

        """
        _set_upstart_env("QT_LOAD_TESTABILITY", 1)
        self.addCleanup(_unset_upstart_env, "QT_LOAD_TESTABILITY")

        return app_path, arguments
