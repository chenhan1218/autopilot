# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2012-2013 Canonical
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


"""Package for introspection support.

This package contains the internal implementation of the autopilot
introspection mechanism, and probably isn't useful to most test authors.

"""

from __future__ import absolute_import

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
