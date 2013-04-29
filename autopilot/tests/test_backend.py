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


from testtools import TestCase
from testtools.matchers import Equals, Not, NotEquals
from autopilot.introspection.backends import DBusAddress

class DBusAddressTests(TestCase):

    def test_can_construct(self):
        fake_bus = object()
        addr = DBusAddress(fake_bus, "conn", "path")

    def test_can_store_address_in_dictionary(self):
        fake_bus = object()
        addr = DBusAddress(fake_bus, "conn", "path")
        dict(addr=object())

    def test_equality_operator(self):
        fake_bus = object()
        addr1 = DBusAddress(fake_bus, "conn", "path")

        self.assertThat(addr1, Equals(DBusAddress(fake_bus, "conn", "path")))
        self.assertThat(addr1, Not(Equals(DBusAddress(fake_bus, "conn", "new_path"))))
        self.assertThat(addr1, Not(Equals(DBusAddress(fake_bus, "conn2", "path"))))
        self.assertThat(addr1, Not(Equals(DBusAddress(object(), "conn", "path"))))


    def test_inequality_operator(self):
        fake_bus = object()
        addr1 = DBusAddress(fake_bus, "conn", "path")

        self.assertThat(addr1, Not(NotEquals(DBusAddress(fake_bus, "conn", "path"))))
        self.assertThat(addr1, NotEquals(DBusAddress(fake_bus, "conn", "new_path")))
        self.assertThat(addr1, NotEquals(DBusAddress(fake_bus, "conn2", "path")))
        self.assertThat(addr1, NotEquals(DBusAddress(object(), "conn", "path")))


