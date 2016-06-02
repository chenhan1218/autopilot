# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2016 Canonical
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

from unittest.mock import Mock
from collections import namedtuple


X_DEFAULT = 0
Y_DEFAULT = 0
W_DEFAULT = 0
H_DEFAULT = 0


def get_mock_object(x=X_DEFAULT, y=Y_DEFAULT, w=W_DEFAULT, h=H_DEFAULT):
    mock_object = Mock()
    mock_object.globalRect = _get_global_rect_as_named_tuple(x, y, w, h)
    return mock_object


def _get_global_rect_as_named_tuple(x, y, w, h):
    global_rect = namedtuple('globalRect', ['x', 'y', 'w', 'h'])
    global_rect.x = x
    global_rect.y = y
    global_rect.w = w
    global_rect.h = h
    return global_rect
