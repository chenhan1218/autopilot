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

from autopilot.introspection import ApplicationLauncher


class GtkApplicationLauncher(ApplicationLauncher):
    """A mix-in class to make Gtk application introspection easier."""

    def prepare_environment(self, app_path, arguments):
        """Prepare the application, or environment to launch with
        autopilot-support.

        """
        modules = os.getenv('GTK_MODULES', '').split(':')
        if 'autopilot' not in modules:
            modules.append('autopilot')
            os.putenv('GTK_MODULES', ':'.join(modules))

        return app_path, arguments
