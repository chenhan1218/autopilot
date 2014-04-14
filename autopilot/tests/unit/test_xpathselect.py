# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2014 Canonical
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

from testscenarios import TestWithScenarios
from testtools import TestCase
from testtools.matchers import raises

from autopilot.introspection import _xpathselect as xpathselect


class XPathSelectQueryTests(TestCase):

    def test_query_raises_TypeError_on_non_bytes_query(self):
        fn = lambda: xpathselect.Query(
            None,
            xpathselect.Query.Operation.CHILD,
            u'asd'
        )
        self.assertThat(
            fn,
            raises(
                TypeError(
                    "'query' parameter must be bytes, not %s"
                    % type(u'').__name__
                )
            )
        )

    def test_can_create_root_query(self):
        q = xpathselect.Query.root(b'Foo')
        self.assertEqual(b"/Foo", q.server_query_bytes())

    def test_can_create_app_name_from_ascii_string(self):
        q = xpathselect.Query.root(u'Foo')
        self.assertEqual(b"/Foo", q.server_query_bytes())

    def test_creating_root_query_with_unicode_app_name_raises(self):
        self.assertThat(
            lambda: xpathselect.Query.root(u"\u2026"),
            raises(
                ValueError("Type name '%s', must be ASCII encodable"
                           % (u'\u2026'))
                )
        )

    def test_repr_with_path(self):
        path = b"/some/path"
        q = xpathselect.Query.root('some').select_child('path')
        self.assertEqual("Query(%r)" % path, repr(q))

    def test_repr_with_path_and_filters(self):
        expected = b"/some/path[bar=456,foo=123]"
        filters = dict(foo=123, bar=456)
        q = xpathselect.Query.root('some').select_child('path', filters)
        self.assertEqual("Query(%r)" % expected, repr(q))

    def test_select_child(self):
        q = xpathselect.Query.root("Foo").select_child("Bar")
        self.assertEqual(q.server_query_bytes(), b"/Foo/Bar")

    def test_select_child_with_filters(self):
        q = xpathselect.Query.root("Foo")\
            .select_child("Bar", dict(visible=True))
        self.assertEqual(q.server_query_bytes(), b"/Foo/Bar[visible=True]")

    def test_many_select_children(self):
        q = xpathselect.Query.root("Foo") \
            .select_child("Bar") \
            .select_child("Baz")

        self.assertEqual(b"/Foo/Bar/Baz", q.server_query_bytes())

    def test_many_select_children_with_filters(self):
        q = xpathselect.Query.root("Foo") \
            .select_child("Bar", dict(visible=True)) \
            .select_child("Baz", dict(id=123))

        self.assertEqual(
            b"/Foo/Bar[visible=True]/Baz[id=123]",
            q.server_query_bytes()
        )

    def test_select_descendant(self):
        q = xpathselect.Query.root("Foo") \
            .select_descendant("Bar")

        self.assertEqual(b"/Foo//Bar", q.server_query_bytes())

    def test_select_descendant_with_filters(self):
        q = xpathselect.Query.root("Foo") \
            .select_descendant("Bar", dict(name="Hello"))

        self.assertEqual(b'/Foo//Bar[name="Hello"]', q.server_query_bytes())

    def test_many_select_descendants(self):
        q = xpathselect.Query.root("Foo") \
            .select_descendant("Bar") \
            .select_descendant("Baz")

        self.assertEqual(b"/Foo//Bar//Baz", q.server_query_bytes())

    def test_many_select_descendants_with_filters(self):
        q = xpathselect.Query.root("Foo") \
            .select_descendant("Bar", dict(visible=True)) \
            .select_descendant("Baz", dict(id=123))

        self.assertEqual(
            b"/Foo//Bar[visible=True]//Baz[id=123]",
            q.server_query_bytes()
        )

    def test_full_server_side_filter(self):
        q = xpathselect.Query.root("Foo") \
            .select_descendant("Bar", dict(visible=True)) \
            .select_descendant("Baz", dict(id=123))
        self.assertFalse(q.needs_client_side_filtering())

    def test_client_side_filter(self):
        q = xpathselect.Query.root("Foo") \
            .select_descendant("Bar", dict(visible=True)) \
            .select_descendant("Baz", dict(name=u"\u2026"))
        self.assertTrue(q.needs_client_side_filtering())

    def test_client_side_filter_all_query_bytes(self):
        q = xpathselect.Query.root("Foo") \
            .select_descendant("Bar", dict(visible=True)) \
            .select_descendant("Baz", dict(name=u"\u2026"))
        self.assertEqual(
            b'/Foo//Bar[visible=True]//Baz',
            q.server_query_bytes()
        )

    def test_deriving_from_client_side_filtered_query_raises_ValueError(self):
        q = xpathselect.Query.root("Foo") \
            .select_descendant("Baz", dict(name=u"\u2026"))
        fn = lambda: q.select_child("Foo")
        self.assertThat(
            fn,
            raises(ValueError(
                "Cannot create a new query from a parent that requires "
                "client-side filter processing."
            ))
        )

    def test_init_raises_TypeError_on_invalid_operation_type(self):
        fn = lambda: xpathselect.Query(None, u'/', b'sdf')
        self.assertThat(
            fn,
            raises(TypeError(
                "'operation' parameter must be bytes, not '%s'"
                % type(u'').__name__
            ))
        )

    def test_init_raises_ValueError_on_invalid_operation(self):
        fn = lambda: xpathselect.Query(None, b'foo', b'sdf')
        self.assertThat(
            fn,
            raises(ValueError("Invalid operation 'foo'."))
        )

    def test_init_raises_ValueError_on_invalid_descendant_search(self):
        fn = lambda: xpathselect.Query(None, b'//', b'*')
        self.assertThat(
            fn,
            raises(ValueError(
                "Must provide at least one server-side filter when searching "
                "for descendants and using a wildcard node."
            ))
        )


class ServerSideParameterFilterStringTests(TestWithScenarios, TestCase):

    scenarios = [
        ('bool true', dict(k='visible', v=True, r=b"visible=True")),
        ('bool false', dict(k='visible', v=False, r=b"visible=False")),
        ('int +ve', dict(k='size', v=123, r=b"size=123")),
        ('int -ve', dict(k='prio', v=-12, r=b"prio=-12")),
        ('simple string', dict(k='Name', v=u"btn1", r=b"Name=\"btn1\"")),
        ('simple bytes', dict(k='Name', v=b"btn1", r=b"Name=\"btn1\"")),
        ('string space', dict(k='Name', v=u"a b  c ", r=b"Name=\"a b  c \"")),
        ('bytes space', dict(k='Name', v=b"a b  c ", r=b"Name=\"a b  c \"")),
        ('string escapes', dict(
            k='a',
            v=u"\a\b\f\n\r\t\v\\",
            r=br'a="\x07\x08\x0c\n\r\t\x0b\\"')),
        ('byte escapes', dict(
            k='a',
            v=b"\a\b\f\n\r\t\v\\",
            r=br'a="\x07\x08\x0c\n\r\t\x0b\\"')),
        ('escape quotes (str)', dict(k='b', v="'", r=b'b="\\' + b"'" + b'"')),
        (
            'escape quotes (bytes)',
            dict(k='b', v=b"'", r=b'b="\\' + b"'" + b'"')
        ),
    ]

    def test_query_string(self):
        s = xpathselect._get_filter_string_for_key_value_pair(self.k, self.v)
        self.assertEqual(s, self.r)


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
        ('int overflow 1', dict(key='key', value=-2147483648, result=True)),
        ('int overflow 2', dict(key='key', value=-2147483649, result=False)),
        ('int overflow 3', dict(key='key', value=2147483647, result=True)),
        ('int overflow 4', dict(key='key', value=2147483648, result=False)),
        ('unicode string', dict(key='key', value=u'H\u2026i', result=False)),
    ]

    def test_valid_server_side_param(self):
        self.assertEqual(
            xpathselect._is_valid_server_side_filter_param(
                self.key,
                self.value
            ),
            self.result
        )
