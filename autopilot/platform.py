# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2013 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.

"""
Platform identification utilities for Autopilot.
================================================

This module provides functions that give test authors hints as to which platform
their tests are currently running on. This is useful when tests should only run
on certain platforms.

"""

from os.path import exists


def model():
    """Get the model name of the current platform.

    For desktop / laptop installations, this will return "Desktop".
    Otherwise, the current hardware model will be returned. For example:

    >>> autopilot.platform.model()
    ... "Galaxy Nexus"

    """
    return _PlatformDetector.create().model


def image_codename():
    """Get the image codename.

    For desktop / laptop installations this will return "Desktop".
    Otherwise, the codename of the image that was installed will be
    returned. For example:

    >>> autopilot.platform.image_codename()
    ... "maguro"

    """
    return _PlatformDetector.create().image_codename


class _PlatformDetector(object):

    _cached_detector = None

    @staticmethod
    def create():
        """Create a platform detector object, or return one we baked earlier."""
        if _PlatformDetector._cached_detector is None:
            _PlatformDetector._cached_detector = _PlatformDetector()
        return _PlatformDetector._cached_detector

    def __init__(self):
        self.model = "Desktop"
        self.image_codename = "Desktop"

        property_file = _get_property_file()
        if property_file is not None:
            self.update_values_from_build_file(property_file)

    def update_values_from_build_file(self, property_file):
        """Read build.prop file and parse it."""
        properties = _parse_build_properties_file(property_file)
        self.model = properties.get('ro.product.model', "Desktop")
        self.image_codename = properties.get('ro.product.name', "Desktop")


def _get_property_file():
    """Return a file-like object that contains the contents of the build properties
    file, if it exists, or None.

    """
    if exists('/system/build.prop'):
        return open('/system/build.prop')
    return None


def _parse_build_properties_file(property_file):
    """Parse 'property_file', which must be a file-like object containing the
    system build properties.

    Returns a dictionary of key,value pairs.

    """
    properties = {}
    for line in property_file:
        line = line.strip()
        if not line or line.startswith('#') or line.isspace():
            continue
        split_location = line.find('=')
        if split_location == -1:
            continue
        key = line[:split_location]
        value = line[split_location + 1:]

        properties[key] = value
    return properties

