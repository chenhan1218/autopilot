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


class FilterDecision(object):
    """Makes the decision if this connection matches the criteria given the
    parameters.

    If the connection passes the criteria the 'success' callable is called
    passed the provided details and it's result is returned (which may be
    the return of a filter called by that filter and so on.)

    By default a non-applicable result returns false.


    !!! Is this getting too complicated? Should there just be a
        'add_next_filter' method that gets called if required?

    """
    def _pass(dbus_connection, params):
        return True, params

    def _fail(dbs_connection, params):
        return False, params

    def __init__(
            self,
            on_success=_pass,
            on_failure=_fail,
            on_not_applicable=_fail
    ):
        # self._on_success = lambda params: (True, params)
        # self._on_not_applicable = lambda params: (False, params)
        # self._on_failure = lambda params: (False, params)
        self._on_success = on_success
        self._on_failure = on_failure
        self._on_not_applicable = on_not_applicable

    def __call__(self, dbus_connection, parameters):
        """This is where the decision is actually made.

        Returns a tuple containing the filter result and the passed parameters
        that may have beeb modified in the process of the filter.
        (for instance some cached values may have been added or flags set.)

        for instance:

        if passes_test(dbus_conn, parameters):
            return self._on_success(dbus_conn, parameters)
        else if not applicable(dbus_conn, parameters):
            return self._on_not_applicable(dbus_conn, parameters)
        else:
            return self._on_failure(dbus_conn, parameters)
        """
        raise NotImplementedError("You cannot use this class directly.")

    def add_on_success(self, filter):
        self._raise_if_not_callable(filter)
        self._on_success = filter

    def add_on_not_applicable(self, filter):
        self._raise_if_not_callable(filter)
        self._on_not_applicable = filter

    def add_on_failure(self, filter):
        self._raise_if_not_callable(filter)
        self._on_failure = filter

    def _raise_if_not_callable(self, filter):
        if not isinstance(filter, FilterDecision) and not callable(filter):
            raise RuntimeError("Filter must be a callable method or object.")


# class DbusConnection(object):
#     """Encapsulates the connection details."""
#     pass


class SearchParamters(object):
    """Encapsulates the search criteria details."""

    def __init__(self, **kwargs):
        self._parameters = dict(kwargs)

    def get(self, arg):
        try:
            return self._parameters[arg]
        except KeyError:
            # raise SomeCustomExceptionPerhaps
            pass

    def __str__(self):
        # duplicate _get_search_criteria_string_representation
        pass


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
