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

from testtools import TestCase
from testtools.matchers import raises

from autopilot.introspection import _xpathselect as xpathselect


class XPathSelectQueryTests(TestCase):

    def test_can_create_root_query(self):
        q = xpathselect.Query.root(b'Foo')
        self.assertEqual(b"/Foo", q.query_bytes())

    def test_can_create_app_name_from_ascii_string(self):
        q = xpathselect.Query.root(u'Foo')
        self.assertEqual(b"/Foo", q.query_bytes())

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
        path = b"/some/path"
        filters = dict(foo=123, bar=456)
        q = xpathselect.Query.root('some').select_child('path', filters)
        self.assertEqual("Query(%r %r)" % (path, filters), repr(q))

    def test_select_child(self):
        q = xpathselect.Query.root("Foo").select_child("Bar")
        self.assertEqual(q.query_bytes(), b"/Foo/Bar")

    def test_many_select_children(self):
        q = xpathselect.Query.root("Foo") \
            .select_child("Bar") \
            .select_child("Baz")

        self.assertEqual(b"/Foo/Bar/Baz", q.query_bytes())

    def test_select_ancestor(self):
        q = xpathselect.Query.root("Foo") \
            .select_descendant("Bar")

        self.assertEqual(b"/Foo//Bar", q.query_bytes())

    def test_many_select_descendant(self):
        q = xpathselect.Query.root("Foo") \
            .select_descendant("Bar") \
            .select_descendant("Baz")

        self.assertEqual(b"/Foo//Bar//Baz", q.query_bytes())
