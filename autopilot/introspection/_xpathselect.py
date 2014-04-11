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

"""Classes and functions that encopde knowledge of the xpathselect query
language.

This module is internal, and should not be used directly.

"""
import re
import six

from autopilot.utilities import compatible_repr


class Query(object):

    """Encapsulate an XPathSelect query."""

    class Operation(object):
        ROOT = b'/'
        CHILD = b'/'
        DESCENDANT = b'//'

    def __init__(self, parent, operation, query, filters={}):
        """Create a new query object.

        You shouldn't need to call this directly.

        :param parent: The parent query object. Pass in None to make the root
            query object.
        :param operation: The operation object to perform on the result from
            the parent node.
        :param query: The query expression for this node.
        :param filters: A dictionary of filters to apply.

        """
        if not isinstance(query, six.binary_type):
            raise TypeError(
                "'query' parameter must be bytes, not %r" % type(bytes)
            )
        self._parent = parent
        self._operation = operation
        self._query = query
        self._filters = filters

    @staticmethod
    def root(app_name):
        """Create a root query object."""
        app_name = _try_encode_type_name(app_name)
        return Query(
            None,
            Query.Operation.ROOT,
            app_name
        )

    def query_bytes(self):
        """Get the query bytes."""
        parent_query = self._parent.query_bytes() \
            if self._parent is not None else b''
        return parent_query + self._operation + self._query

    @compatible_repr
    def __repr__(self):
        return "Query(%r%s)" % (
            self.query_bytes(),
            " " + repr(self._filters) if self._filters else ""
        )

    def select_child(self, child_name, filters={}):
        """Return a query matching an immediate child.

        Keyword arguments may be used to restrict which nodes to match.

        :param child_name: The name of the child node to match.

        :returns: A Query instance that will match the child.

        """
        child_name = _try_encode_type_name(child_name)
        return Query(
            self,
            Query.Operation.CHILD,
            child_name,
            filters
        )

    def select_descendant(self, ancestor_name):
        """Return a query matching an ancestor of the current node.

        :param ancestor_name: The name of the ancestor node to match.

        :returns: A Query instance that will match the ancestor.

        """
        ancestor_name = _try_encode_type_name(ancestor_name)
        return Query(
            self,
            Query.Operation.DESCENDANT,
            ancestor_name
        )


def _try_encode_type_name(name):
    if isinstance(name, six.string_types):
        try:
            name = name.encode('ascii')
        except UnicodeEncodeError:
            raise ValueError(
                "Type name '%s', must be ASCII encodable" % (name)
            )
    return name


def _validate_filters(filter_dict):
    for k, v in filter_dict.items():
        if not _is_valid_server_side_filter_param(k, v):
            raise ValueError(
                "Filter %s = %r is not a valid server-side query." % (
                    k, v)
            )


# TODO: Remove this function from autopilot.introspection.dbus.
def _is_valid_server_side_filter_param(key, value):
    """Return True if the key and value parameters are valid for server-side
    processing.

    """
    key_is_valid = re.match(
        r'^[a-zA-Z0-9_\-]+( [a-zA-Z0-9_\-])*$',
        key
    ) is not None

    if type(value) == int:
        return key_is_valid and (-2**31 <= value <= 2**31 - 1)

    elif type(value) == bool:
        return key_is_valid

    elif type(value) == six.binary_type:
        return key_is_valid

    elif type(value) == six.text_type:
        try:
            value.encode('ascii')
            return key_is_valid
        except UnicodeEncodeError:
            pass
    return False


# TODO: Remove this function from autopilot.introspection.dbus.
def _get_filter_string_for_key_value_pair(key, value):
    """Return a string representing the filter query for this key/value pair.

    The value must be suitable for server-side filtering. Raises ValueError if
    this is not the case.

    """
    if isinstance(value, six.text_type):
        if six.PY3:
            escaped_value = value.encode("unicode_escape")\
                .decode('ASCII')\
                .replace("'", "\\'")
        else:
            escaped_value = value.encode('utf-8').encode("string_escape")
            # note: string_escape codec escapes "'" but not '"'...
            escaped_value = escaped_value.replace('"', r'\"')
        return '{}="{}"'.format(key, escaped_value)
    elif isinstance(value, six.binary_type):
        if six.PY3:
            escaped_value = value.decode('utf-8')\
                .encode("unicode_escape")\
                .decode('ASCII')\
                .replace("'", "\\'")
        else:
            escaped_value = value.encode("string_escape")
            # note: string_escape codec escapes "'" but not '"'...
            escaped_value = escaped_value.replace('"', r'\"')
        return '{}="{}"'.format(key, escaped_value)
    elif isinstance(value, int) or isinstance(value, bool):
        return "{}={}".format(key, repr(value))
    else:
        raise ValueError("Unsupported value type: {}".format(type(value)))
