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


from functools import partial
from os.path import join
from xml.etree import ElementTree



def _start_trawl(bus, connection_name, on_success_cb):
    # introspect_fn is now a function that takes two params:
    # conn_name, obj_name (optional)
    introspect_fn = partial(_introspect_dbus_object, bus)
    # process_obj_fn is now a function that takes three params:
    # conn_name, obj_name, xml
    process_obj_fn = partial(_process_object, on_success_cb, introspect_fn)
    introspect_fn = partial(introspect_fn, reply_handler=process_obj_fn)

    introspect_fn(connection_name)


def _introspect_dbus_object(bus, conn_name, obj_name='/', reply_handler):
    """Return a list of objects and their interfaces."""
    obj = bus.get_object(conn_name, obj_name)
    obj.Introspect(
        dbus_interface='org.freedesktop.DBus.Introspectable',
        reply_handler=lambda xml: reply_handler(
            conn_name, obj_name, xml)
    )


def _process_object(on_success_cb, get_xml_cb, conn_name, obj_name, xml):
    root = ElementTree.fromstring(xml)

    for child in root.getchildren():
        child_name = join(obj_name, child.attrib['name'])
        # If we found another node, make sure we get called again with a new
        # XML block.
        if child.tag == 'node':
            get_xml_cb(conn_name, child_name)
        # If we found an interface, call our success function with the
        # interface name
        elif child.tag == 'interface':
            iface_name = child_name.split('/')[-1]
            on_success_cb(conn_name, obj_name, iface_name)
