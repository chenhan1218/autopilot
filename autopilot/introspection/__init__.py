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


"""Package for introspection object support and search.

This package contains the methods and classes that are of use for accessing
dbus proxy objects and creating Custom Proxy Object classes.

For retrieving proxy objects for already existing processes there are two
methods:

- :meth:`~autopilot.introspection.get_proxy_object_for_existing_process`
- :meth:`~autopilot.introspection.get_autopilot_proxy_object_for_process`

Both take search criteria and return a proxy object that can be queried.

For creating your own Custom Proxy Classes thers is:
- :class:`autopilot.introspection.CustomEmulatorBase`

.. seealso::
    The tutorial section :ref:`custom_proxy_classes` for further details on
    using 'CustomEmulatorBase' to write custom proxy classes.

"""

from autopilot.introspection.dbus import CustomEmulatorBase
from autopilot.introspection._search import (
    get_autopilot_proxy_object_for_process,
    get_proxy_object_for_existing_process
)

__all__ = [
    'CustomEmulatorBase',
    'get_autopilot_proxy_object_for_process',
    'get_proxy_object_for_existing_process'
]
