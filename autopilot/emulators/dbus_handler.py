# Copyright 2012 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.

"""Initialise dbus once using glib mainloop."""

from __future__ import absolute_import

import dbus
from dbus.mainloop.glib import DBusGMainLoop

#
# DBus has an annoying bug where we need to initialise it with the gobject main
# loop *before* it's initialised anywhere else. This module exists so we can
# initialise the dbus module once, and once only.
DBusGMainLoop(set_as_default=True)

# create a global session bus object:
session_bus = dbus.SessionBus()
