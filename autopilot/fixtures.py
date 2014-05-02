# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2012-2014 Canonical
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

"""Provide test fixtures for public use."""

import logging

from fixtures import Fixture
from os import environ

_logger = logging.getLogger(__name__)


class EnvironmentPatch(Fixture):

    """Patch the process environment, setting *key* with value *value*.

    This patches os.environ for the duration of the test only. After
    calling this method, the following should be True::

        os.environ[key] == value

    After the test, the patch will be undone (including deleting the key if
    if didn't exist before this method was called).

    .. note:: Be aware that patching the environment in this way only
     affects the current autopilot process, and any processes spawned by
     autopilot. If you are planing on starting an application from within
     autopilot and you want this new application to read the patched
     environment variable, you must patch the environment *before*
     launching the new process.

    :param string key: The name of the key you wish to set. If the key
     does not already exist in the process environment it will be created
     (and then deleted when the test ends).
    :param string value: The value you wish to set.

    """

    def __init__(self, key, value):
        self.key = key
        self.value = value

    def setUp(self):
        super(EnvironmentPatch, self).setUp()
        if self.key in environ:
            def _undo_patch(key, old_value):
                _logger.info(
                    "Resetting environment variable '%s' to '%s'",
                    self.key,
                    old_value
                )
                environ[self.key] = old_value
            old_value = environ[self.key]
            self.addCleanup(_undo_patch, self.key, old_value)
        else:
            def _remove_patch(key):
                try:
                    _logger.info(
                        "Deleting previously-created environment "
                        "variable '%s'",
                        self.key
                    )
                    del environ[self.key]
                except KeyError:
                    _logger.warning(
                        "Attempted to delete environment key '%s' that doesn't"
                        "exist in the environment",
                        self.key
                    )
            self.addCleanup(_remove_patch, self.key)
        _logger.info(
            "Setting environment variable '%s' to '%s'",
            self.key,
            self.value
        )
        environ[self.key] = self.value
