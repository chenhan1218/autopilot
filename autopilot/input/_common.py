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


"""Common, private utility code for input emulators."""

import logging

logger = logging.getLogger(__name__)


def get_center_point(object_proxy):
    """Get the center point of an object, searching for several different ways
    of determining exactly where the center is.

    """
    try:
        x, y, w, h = object_proxy.globalRect
        logger.debug("Moving to object's globalRect coordinates.")
        return x+w/2, y+h/2
    except AttributeError:
        pass
    except (TypeError, ValueError):
        raise ValueError(
            "Object '%r' has globalRect attribute, but it is not of the "
            "correct type" % object_proxy)

    try:
        x, y = object_proxy.center_x, object_proxy.center_y
        logger.debug("Moving to object's center_x, center_y coordinates.")
        return x, y
    except AttributeError:
        pass
    except (TypeError, ValueError):
        raise ValueError(
            "Object '%r' has center_x, center_y attributes, but they are not "
            "of the correct type" % object_proxy)

    try:
        x, y, w, h = (
            object_proxy.x, object_proxy.y, object_proxy.w, object_proxy.h)
        logger.debug(
            "Moving to object's center point calculated from x,y,w,h "
            "attributes.")
        return x+w/2, y+h/2
    except AttributeError:
        raise ValueError(
            "Object '%r' does not have any recognised position attributes" %
            object_proxy)
    except (TypeError, ValueError):
        raise ValueError(
            "Object '%r' has x,y attribute, but they are not of the correct "
            "type" % object_proxy)
