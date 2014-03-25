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

import six


class Query(object):

    """Encapsulate an XPathSelect query."""

    def __init__(self, query):
        if not isinstance(query, six.binary_type):
            raise TypeError(
                "'query' parameter must be bytes, not %r" % type(bytes)
            )
        self._query = query

    @staticmethod
    def create_root_query(app_name):
        """Create a root query object."""
        return Query(b'/' + app_name)

