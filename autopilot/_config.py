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

import collections.abc


_test_config_string = ""


def set_configuration_string(config_string):
    """Set the test configuration string.

    This must be a text string that specifies the test configuration. The
    string is a comma separated list of 'key=value' or 'key' tokens.

    """
    global _test_config_string
    _test_config_string = config_string


def get_test_configuration():
    return ConfigDict(_test_config_string)


class ConfigDict(collections.abc.Mapping):

    def __init__(self, config_string):
        self._data = {}
        for item in config_string.split(','):
            if not item:
                continue
            parts = item.split('=')
            if len(parts) == 1:
                self._data[parts[0]] = '1'
            elif len(parts) == 2:
                self._data[parts[0]] = parts[1]
            else:
                raise ValueError(
                    "Invalid configuration string '{}'".format(config_string)
                )

    def __getitem__(self, key):
        return self._data.__getitem__(key)

    def __iter__(self):
        return self._data.__iter__()

    def __len__(self):
        return self._data.__len__()
