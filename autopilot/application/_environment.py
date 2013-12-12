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

"""Base package or application environment setup."""

import fixtures
import os
import subprocess

from autopilot.application._launcher import _set_upstart_env, _unset_upstart_env

class ApplicationEnvironment(fixtures.Fixture):

    @staticmethod
    def create(**kwargs):
        app_hint = kwargs.pop('app_type', None)
        application = kwargs.pop('application', None)
        package_id = kwargs.pop('package_id', None)
        if app_hint is not None:
            return _get_app_env_from_string_hint(app_hint)
        elif application is not None:
            return _get_app_env(application)
        elif package_id is not None:
            import autopilot.application.environment._upstart as _upstart
            return _upstart.UpstartApplicationEnvironment()
        else:
            return None  # or raise exception?

    def prepare_environment(self, app_path, arguments):
        """Prepare the application, or environment to launch with
        autopilot-support.

        The method *must* return a tuple of (*app_path*, *arguments*). Either
        of these can be altered by this method.

        """
        raise NotImplementedError("Sub-classes must implement this method.")


def _get_app_env(application):
    """Return an instance of :class:`ApplicationLauncher` that knows how to
    launch the application at 'app_path'.
    """
    # TODO: this is a teeny bit hacky - we call ldd to check whether this
    # application links to certain library. We're assuming that linking to
    # libQt* or libGtk* means the application is introspectable. This excludes
    # any non-dynamically linked executables, which we may need to fix further
    # down the line.
    import autopilot.application.environment._gtk as _gtk
    import autopilot.application.environment._qt as _qt

    app_path = _get_application_path(application)

    try:
        ldd_output = subprocess.check_output(
            ["ldd", app_path],
            universal_newlines=True
        ).strip().lower()
    except subprocess.CalledProcessError as e:
        raise RuntimeError(e)
    if 'libqtcore' in ldd_output or 'libqt5core' in ldd_output:
        return _qt.QtApplicationEnvironment()
    elif 'libgtk' in ldd_output:
        return _gtk.GtkApplicationEnvironment()
    return None


def _get_application_path(application):
    try:
        return subprocess.check_output(
            ['which', application],
            universal_newlines=True
        ).strip()
    except subprocess.CalledProcessError:
        return ""


def _get_app_env_from_string_hint(hint):
    from autopilot.application.environment import QtApplicationEnvironment
    from autopilot.application.environment import GtkApplicationEnvironment

    hint = hint.lower()
    if hint == 'qt':
        return QtApplicationEnvironment()
    elif hint == 'gtk':
        return GtkApplicationEnvironment()
    return None


class GtkApplicationEnvironment(ApplicationEnvironment):

    def prepare_environment(self, app_path, arguments):
        """Prepare the application, or environment to launch with
        autopilot-support.

        """
        modules = os.getenv('GTK_MODULES', '').split(':')
        if 'autopilot' not in modules:
            modules.append('autopilot')
            os.putenv('GTK_MODULES', ':'.join(modules))

        return app_path, arguments


class QtApplicationEnvironment(ApplicationEnvironment):

    def prepare_environment(self, app_path, arguments):
        """Prepare the application, or environment to launch with
        autopilot-support.

        """
        if '-testability' not in arguments:
            insert_pos = 0
            for pos, argument in enumerate(arguments):
                if argument.startswith("-qt="):
                    insert_pos = pos + 1
                    break
            arguments.insert(insert_pos, '-testability')

        return app_path, arguments


class UpstartApplicationEnvironment(ApplicationEnvironment):

    def prepare_environment(self, app_path, arguments):
        """Prepare the application, or environment to launch with
        autopilot-support.

        """
        _set_upstart_env("QT_LOAD_TESTABILITY", 1)
        self.addCleanup(_unset_upstart_env, "QT_LOAD_TESTABILITY")

        return app_path, arguments
