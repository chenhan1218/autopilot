# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2012 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.

"""Functions to deal with ibus service."""

from __future__ import absolute_import

from gi.repository import IBus, GLib
import os
import logging
import subprocess
from gi.repository import GConf
from time import sleep


logger = logging.getLogger(__name__)
_cached_bus = None


def get_ibus_bus():
    """Get the ibus bus object, possibly starting the ibus daemon if it's
    not already running.

    :raises: **RuntimeError** in the case of ibus-daemon being unavailable.

    """
    max_tries = 5
    for i in range(max_tries):
        if IBus.get_address() is None:
            pid = os.spawnlp(os.P_NOWAIT, "ibus-daemon", "ibus-daemon", "-d", "--xim")
            logger.info("Started ibus-daemon with pid %i." % (pid))
            sleep(2)
        else:
            global _cached_bus
            if _cached_bus is not None and _cached_bus.is_connected():
                return _cached_bus

            bus = IBus.Bus.new()
            for i in range(5):
                for i in range(10):
                    if bus.is_connected():
                        _cached_bus = bus
                        return bus
                    sleep(1)
                if not bus.is_connected():
                    logger.warning("IBus bus failed to connect after 10 seconds, killing daemon.")
                subprocess.check_call(["killall", "ibus-daemon"])

    raise RuntimeError("Could not start ibus-daemon after %d tries." % (max_tries))


def reset_ibus_bus():
    global _cached_bus
    if _cached_bus is not None:
        _cached_bus.exit(restart=True)
        _cached_bus = None


def get_available_input_engines():
    """Get a list of available input engines."""
    bus = get_ibus_bus()
    return [e.get_name() for e in bus.list_engines()]


def get_active_input_engines():
    """Get the list of input engines that have been activated."""
    bus = get_ibus_bus()
    return [e.get_name() for e in bus.list_active_engines()]


def set_active_engines(engine_list):
    """Installs the engines in *engine_list* into the list of active iBus
    engines.

    The specified engines must appear in the return list from
    get_available_input_engines().

    .. note:: This function removes all other engines.

    This function returns the list of engines installed before this function was
    called. The caller should pass this list to set_active_engines to restore
    ibus to it's old state once the test has finished.

    :param engine_list: List of engine names
    :type engine_list: List of strings
    :raises: **TypeError** on invalid *engine_list* parameter.
    :raises: **ValueError** when engine_list contains invalid engine name.

    """
    if type(engine_list) is not list:
        raise TypeError("engine_list must be a list of valid engine names.")
    available_engines = get_available_input_engines()
    for engine in engine_list:
        if not isinstance(engine, basestring):
            raise TypeError("Engines in engine_list must all be strings.")
        if engine not in available_engines:
            raise ValueError("engine_list contains invalid engine name: '%s'", engine)

    bus = get_ibus_bus()
    config = bus.get_config()

    config.set_value("general",
                     "preload_engine_mode",
                     GLib.Variant.new_int32(IBus.PreloadEngineMode.USER))

    old_engines = get_active_input_engines()
    config.set_value("general",
                    "preload_engines",
                    GLib.Variant("as", engine_list)
                    )
    # need to restart the ibus bus before it'll pick up the new engine.
    # see bug report here:
    # http://code.google.com/p/ibus/issues/detail?id=1418&thanks=1418&ts=1329885137
    reset_ibus_bus()

    return old_engines


def set_gconf_option(path, value):
    """Set the gconf setting on `path` to the defined `value`"""
    _set_gconf_list (path, value)


def get_gconf_option(path):
    """Get the gconf setting on `path`"""
    client = GConf.Client.get_default()
    value = client.get(path)
    return _get_native_gconf_value(value)


def _set_gconf_list(path, values):
    gconf_value = '[%s]' % ','.join(values)
    subprocess.check_output(["gconftool-2", "--set", "--type=list", "--list-type=string", path, gconf_value])


def _get_native_gconf_value(value):
    """Translates a GConfValue to a native one"""
    if value.type is GConf.ValueType.STRING:
        return value.get_string()
    elif value.type is GConf.ValueType.INT:
        return value.get_int()
    elif value.type is GConf.ValueType.FLOAT:
        return value.get_float()
    elif value.type is GConf.ValueType.BOOL:
        return value.get_bool()
    elif value.type is GConf.ValueType.LIST:
        return [_get_native_gconf_value(val) for val in value.get_list()]
    else:
        raise TypeError("Invalid gconf value type")
