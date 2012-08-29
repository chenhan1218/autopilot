# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2012 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.
#
# This script is designed to run unity in a test drive manner. It will drive
# X and test the GL calls that Unity makes, so that we can easily find out if
# we are triggering graphics driver/X bugs.

"""Functions that wrap compizconfig to avoid some unpleasantness in that module."""

from __future__ import absolute_import


from autopilot.utilities import Silence

_global_context = None

def get_global_context():
    """Get the compizconfig global context object."""
    global _global_context
    if _global_context is None:
        with Silence():
            from compizconfig import Context
            _global_context = Context()
    return _global_context


def get_plugin(plugin_name):
    """Get a compizconfig plugin with the specified name.

    Raises KeyError of the plugin named does not exist.

    """
    ctx = get_global_context()
    with Silence():
        try:
            return ctx.Plugins[plugin_name]
        except KeyError:
            raise KeyError("Compiz plugin '%s' does not exist." % (plugin_name))


def get_setting(plugin_name, setting_name):
    """Get a compizconfig setting object, given a plugin name and setting name.

    Raises KeyError if the plugin or setting is not found.

    """
    plugin = get_plugin(plugin_name)
    with Silence():
        try:
            return plugin.Screen[setting_name]
        except KeyError:
            raise KeyError("Compiz setting '%s' does not exist in plugin '%s'." % (setting_name, plugin_name))
