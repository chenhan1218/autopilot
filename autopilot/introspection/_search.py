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

"""Private Package for searching dbus for useful connections."""

from __future__ import absolute_import

from collections import namedtuple
from functools import partial
import logging
from operator import methodcaller


logger = logging.getLogger(__name__)


DbusConnection = namedtuple('DbusConnection', ['bus', 'connection_name'])


class FilterResult(object):
    PASS = object()
    FAIL = object()


def matches(filter_list, dbus_connection, search_parameters):
    if not filter_list:
        raise ValueError("Filter list must not be empty")
    for f in filter_list:
        result = f.matches(dbus_connection, search_parameters)
        if result == FilterResult.FAIL:
            return False
    return True


def _filter_function_from_search_params(search_parameters, filter_lookup=None):
    """Returns a callable filter function that will use a prioritised filter
    list based on the search_parameters.

    """

    parameter_filter_lookup = filter_lookup or _param_to_filter_map
    filter_list = []
    try:
        for search_key in search_parameters.keys():
            required_filter = parameter_filter_lookup[search_key]
            if required_filter not in filter_list:
                filter_list.append(required_filter)
    except KeyError:
        raise KeyError(
            "Search parameter %s doesn't have a corresponding filter in %r"
            % (search_key, parameter_filter_lookup),
        )

    sorted_filter_list = sorted(
        filter_list,
        key=methodcaller('priority'),
        reverse=True
    )
    return partial(matches, sorted_filter_list)
