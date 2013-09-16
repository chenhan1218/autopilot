# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2013 Canonical
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

"""Logging helpers for Autopilot tests."""

from functools import wraps


def log_action(log_func):
    """Decorator to log the call of an action method."""

    def middle(f):

        @wraps(f)
        def inner(instance, *args, **kwargs):
            class_name = str(instance.__class__.__name__)
            docstring = f.__doc__
            if docstring:
                docstring = docstring.split('\n')[0].strip()
            else:
                docstring = f.__name__
            log_line = '%s: %s. Arguments %r. Keyword arguments: %r.'
            log_func(log_line, class_name, docstring, args, kwargs)
            return f(instance, *args, **kwargs)

        return inner

    return middle
