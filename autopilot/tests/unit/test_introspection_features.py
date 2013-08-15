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


from testtools import TestCase
from testtools.matchers import Equals, NotEquals
from testscenarios import TestWithScenarios


from autopilot.introspection.dbus import (
    _get_filter_string_for_key_value_pair,
    _is_valid_server_side_filter_param,
    CustomEmulatorBase,
)


class IntrospectionFeatureTests(TestCase):

    def test_custom_emulator_base_does_not_have_id(self):
        self.assertThat(hasattr(CustomEmulatorBase, '_id'), Equals(False))

    def test_derived_emulator_bases_do_have_id(self):
        class MyEmulatorBase(CustomEmulatorBase):
            pass
        self.assertThat(hasattr(MyEmulatorBase, '_id'), Equals(True))

    def test_derived_children_have_same_id(self):
        class MyEmulatorBase(CustomEmulatorBase):
            pass

        class MyEmulator(MyEmulatorBase):
            pass

        class MyEmulator2(MyEmulatorBase):
            pass

        self.assertThat(MyEmulatorBase._id, Equals(MyEmulator._id))
        self.assertThat(MyEmulatorBase._id, Equals(MyEmulator2._id))

    def test_children_have_different_ids(self):
        class MyEmulatorBase(CustomEmulatorBase):
            pass

        class MyEmulatorBase2(CustomEmulatorBase):
            pass

        self.assertThat(MyEmulatorBase._id, NotEquals(MyEmulatorBase2._id))


class ServerSideParamMatchingTests(TestWithScenarios, TestCase):

    """Tests for the server side matching decision function."""

    scenarios = [
        ('should work', dict(key='keyname', value='value', result=True)),
        ('invalid key', dict(key='k  e', value='value', result=False)),
        ('string value', dict(key='key', value='v  e', result=True)),
        ('string value2', dict(key='key', value='v?e', result=True)),
        ('string value3', dict(key='key', value='1/2."!@#*&^%', result=True)),
        ('bool value', dict(key='key', value=False, result=True)),
        ('int value', dict(key='key', value=123, result=True)),
        ('int value2', dict(key='key', value=-123, result=True)),
        ('float value', dict(key='key', value=1.0, result=False)),
        ('dict value', dict(key='key', value={}, result=False)),
        ('obj value', dict(key='key', value=TestCase, result=False)),
    ]

    def test_valid_server_side_param(self):
        self.assertThat(
            _is_valid_server_side_filter_param(self.key, self.value),
            Equals(self.result)
        )


class ServerSideParameterFilterStringTests(TestWithScenarios, TestCase):

    scenarios = [
        ('bool true', dict(k='visible', v=True, r="visible=True")),
        ('bool false', dict(k='visible', v=False, r="visible=False")),
        ('int +ve', dict(k='size', v=123, r="size=123")),
        ('int -ve', dict(k='prio', v=-12, r="prio=-12")),
        ('simple string', dict(k='Name', v="btn1", r="Name=\"btn1\"")),
        ('string space', dict(k='Name', v="a b  c ", r="Name=\"a b  c \"")),
        ('str escapes', dict(
            k='a',
            v="\a\b\f\n\r\t\v\\",
            r=r'a="\x07\x08\x0c\n\r\t\x0b\\"')),
        ('escape quotes', dict(k='b', v="'", r='b="\\' + "'" + '"')),
    ]

    def test_query_string(self):
        s = _get_filter_string_for_key_value_pair(self.k, self.v)
        self.assertThat(s, Equals(self.r))
