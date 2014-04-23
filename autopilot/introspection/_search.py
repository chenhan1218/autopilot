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
import logging
from operator import methodcaller


logger = logging.getLogger(__name__)


DbusConnection = namedtuple('DbusConnection', ['bus', 'connection_name'])


class FilterResult(object):
    PASS = object()
    FAIL = object()


class FilterRunner(object):

    def __init__(self, filter_list):
        if not filter_list:
            raise ValueError("Filter list must not be empty")
        self._filters = filter_list

    def matches(self, dbus_connection, search_parameters):
        for f in self._filters:
            result = f.matches(dbus_connection, search_parameters)
            if result == FilterResult.FAIL:
                return False
        return True


def FilterPrioritySorter(filter_list, runner_class):
    return runner_class(
        sorted(filter_list, key=methodcaller('priority'), reverse=True)
    )


def FilterListGenerator(search_parameters, parameter_filter_lookup):
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

    return filter_list



# create filter list based on arguments
# create runner based on filter list

# def find_matching_connections():
#     connections = []

#     # Timer loop here
#     # populate connections based on the previous lot of connections
#     for c in connections:
#         if filter_runner(c, kwargs):
#            blah.append(c)
#     # valid_connections = [c for c in connections if filter_runner(c, kwargs)]
#     # if len(valid_connections) >= 1:
#     #     return valid_connections


# def _raise_if_process_exited(process):
#     """Raises ProcessSearchError if the non-None process is no longer running.

#     """
#     _get_child_pids.reset_cache()
#     if process is not None and not _process_is_running(process):
#         return_code = process.poll()
#         raise ProcessSearchError(
#             "Process exited with exit code: %d"
#             % return_code
#         )
