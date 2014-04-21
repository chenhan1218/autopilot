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

from mock import patch
from testtools import TestCase
from testtools.matchers import Equals, Not, NotEquals

from autopilot.introspection import backends


class DBusAddressTests(TestCase):

    def test_can_construct(self):
        fake_bus = object()
        backends.DBusAddress(fake_bus, "conn", "path")

    def test_can_store_address_in_dictionary(self):
        fake_bus = object()
        backends.DBusAddress(fake_bus, "conn", "path")
        dict(addr=object())

    def test_equality_operator(self):
        fake_bus = object()
        addr1 = backends.DBusAddress(fake_bus, "conn", "path")

        self.assertThat(
            addr1,
            Equals(backends.DBusAddress(fake_bus, "conn", "path"))
        )
        self.assertThat(
            addr1,
            NotEquals(backends.DBusAddress(fake_bus, "conn", "new_path"))
        )
        self.assertThat(
            addr1,
            NotEquals(backends.DBusAddress(fake_bus, "conn2", "path"))
        )
        self.assertThat(
            addr1,
            NotEquals(backends.DBusAddress(object(), "conn", "path"))
        )

    def test_inequality_operator(self):
        fake_bus = object()
        addr1 = backends.DBusAddress(fake_bus, "conn", "path")

        self.assertThat(
            addr1,
            Not(NotEquals(backends.DBusAddress(fake_bus, "conn", "path")))
        )
        self.assertThat(
            addr1,
            NotEquals(backends.DBusAddress(fake_bus, "conn", "new_path"))
        )
        self.assertThat(
            addr1,
            NotEquals(backends.DBusAddress(fake_bus, "conn2", "path"))
        )
        self.assertThat(
            addr1,
            NotEquals(backends.DBusAddress(object(), "conn", "path"))
        )

    def test_session_bus_construction(self):
        connection = self.getUniqueString()
        object_path = self.getUniqueString()
        with patch.object(backends, 'get_session_bus') as patch_sb:
            addr = backends.DBusAddress.SessionBus(connection, object_path)
            self.assertThat(
                addr._addr_tuple,
                Equals(
                    backends.DBusAddress.AddrTuple(
                        patch_sb.return_value,
                        connection,
                        object_path
                    )
                )
            )

    def test_system_bus_construction(self):
        connection = self.getUniqueString()
        object_path = self.getUniqueString()
        with patch.object(backends, 'get_system_bus') as patch_sb:
            addr = backends.DBusAddress.SystemBus(connection, object_path)
            self.assertThat(
                addr._addr_tuple,
                Equals(
                    backends.DBusAddress.AddrTuple(
                        patch_sb.return_value,
                        connection,
                        object_path
                    )
                )
            )

    def test_custom_bus_construction(self):
        connection = self.getUniqueString()
        object_path = self.getUniqueString()
        bus_path = self.getUniqueString()
        with patch.object(backends, 'get_custom_bus') as patch_cb:
            addr = backends.DBusAddress.CustomBus(
                bus_path,
                connection,
                object_path
            )
            self.assertThat(
                addr._addr_tuple,
                Equals(
                    backends.DBusAddress.AddrTuple(
                        patch_cb.return_value,
                        connection,
                        object_path
                    )
                )
            )
            patch_cb.assert_called_once_with(bus_path)
