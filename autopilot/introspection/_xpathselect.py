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

"""Classes and functions that encode knowledge of the xpathselect query
language.

This module is internal, and should not be used directly.

The main class is 'Query', which represents an xpathselect query. Query is a
read-only object - once it has been constructed, it cannot be changed. This is
partially to ease testing, but also to provide guarantees in the proxy object
classes.

To create a query, you must either have a reference to an existing query, or
you must know the name of the root note. To create a query from an existing
query::

    >>> new_query = existing_query.select_child("NodeName")

To create a query given the root node name::

    >>> new_root_query = Query.root("AppName")

Since the XPathSelect language is not perfect, and since we'd like to support
a rich set of selection criteria, not all queries can be executed totally on
the server side. Query instnaces are intelligent enough to know when they must
invoke some client-side processing - in this case the
'needs_client_side_filtering' method will return True.

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

        ALL = (ROOT, CHILD, DESCENDANT)

    def __init__(self, parent, operation, query, filters={}):
        """Create a new query object.

        You shouldn't need to call this directly.

        :param parent: The parent query object. Pass in None to make the root
            query object.
        :param operation: The operation object to perform on the result from
            the parent node.
        :param query: The query expression for this node.
        :param filters: A dictionary of filters to apply.

        :raises TypeError: If the 'query' parameter is not 'bytes'.
        :raises ValueError: If parent is specified, and the parent query needs
            client side filter processing. Only the last query in the query
            chain can have filters that need to be executed on the client-side.
        :raises TypeError: If the operation parameter is not 'bytes'.
        :raises ValueError: if operation is not one of the members of the
            Query.Operation class.

        """
        if not isinstance(query, six.binary_type):
            raise TypeError(
                "'query' parameter must be bytes, not %s"
                % type(query).__name__
            )
        if (
            parent
            and parent.needs_client_side_filtering()
        ):
            raise ValueError(
                "Cannot create a new query from a parent that requires "
                "client-side filter processing."
            )
        if not isinstance(operation, six.binary_type):
            raise TypeError(
                "'operation' parameter must be bytes, not '%s'"
                % type(operation).__name__)
        if operation not in Query.Operation.ALL:
            raise ValueError("Invalid operation '%s'." % operation.decode())
        self._parent = parent
        self._operation = operation
        self._query = query
        self._server_filters = {
            k: v for k, v in filters.items()
            if _is_valid_server_side_filter_param(k, v)
        }
        self._client_filters = {
            k: v for k, v in filters.items() if k not in self._server_filters
        }

    @staticmethod
    def root(app_name):
        """Create a root query object.

        :param app_name: The name of the root node in the introspection tree.
            This is also typically the application name.

        :returns: A new Query instance, representing the root of the tree.
        """
        app_name = _try_encode_type_name(app_name)
        return Query(
            None,
            Query.Operation.ROOT,
            app_name
        )

    def needs_client_side_filtering(self):
        """Return true if this query requires some filtering on the client-side
        """
        return self._client_filters or (
            self._parent.needs_client_side_filtering()
            if self._parent else False
        )

    def server_query_bytes(self):
        """Get a bytestring representing the entire query.

        This method returns a bytestring suitable for sending to the server.
        """
        parent_query = self._parent.server_query_bytes() \
            if self._parent is not None else b''

        return parent_query + \
            self._operation + \
            self._query + \
            self._get_server_filter_bytes()

    def _get_server_filter_bytes(self):
        if self._server_filters:
            keys = sorted(self._server_filters.keys())
            return b'[' + \
                b",".join(
                    [
                        _get_filter_string_for_key_value_pair(
                            k,
                            self._server_filters[k]
                        ) for k in keys
                        if _is_valid_server_side_filter_param(
                            k,
                            self._server_filters[k]
                        )
                    ]
                ) + \
                b']'
        return b''

    @compatible_repr
    def __repr__(self):
        return "Query(%r)" % self.server_query_bytes()

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

    def select_descendant(self, ancestor_name, filters={}):
        """Return a query matching an ancestor of the current node.

        :param ancestor_name: The name of the ancestor node to match.

        :returns: A Query instance that will match the ancestor.

        """
        ancestor_name = _try_encode_type_name(ancestor_name)
        return Query(
            self,
            Query.Operation.DESCENDANT,
            ancestor_name,
            filters
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


def _filters_contains_client_side_filters(filters):
    """Return True if 'filters' contains at least one filter pair that must
    be executed on the client-side.

    """
    return not all(
        (_is_valid_server_side_filter_param(k, v) for k, v in filters.items())
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
    """Return bytes representing the filter query for this key/value pair.

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
        return '{}="{}"'.format(key, escaped_value).encode('utf-8')
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
        return '{}="{}"'.format(key, escaped_value).encode('utf-8')
    elif isinstance(value, int) or isinstance(value, bool):
        return "{}={}".format(key, repr(value)).encode('utf-8')
    else:
        raise ValueError("Unsupported value type: {}".format(type(value)))
