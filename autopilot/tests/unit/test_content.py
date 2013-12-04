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

from tempfile import NamedTemporaryFile

from mock import Mock
from testtools import TestCase

from autopilot.content import follow_file


class FileFollowerTests(TestCase):

    def test_follow_file_adds_addDetail_cleanup(self):
        fake_test = Mock()
        with NamedTemporaryFile() as f:
            follow_file(f.name, fake_test)

        self.assertTrue(fake_test.addCleanup.called)
        self.assertTrue(
            fake_test.addCleanup.call_args[0][0] == fake_test.addDetail
        )

    def test_follow_file_content_object_contains_new_file_data(self):
        fake_test = Mock()
        with NamedTemporaryFile() as f:
            follow_file(f.name, fake_test)
            f.write(u"Hello")
            f.flush()

        actual = fake_test.addCleanup.call_args[0][1].as_text()
        self.assertEqual(u"Hello", actual)

    def test_follow_file_does_not_contain_old_file_data(self):
        fake_test = Mock()
        with NamedTemporaryFile() as f:
            f.write(u"Hello")
            f.flush()
            follow_file(f.name, fake_test)
            f.write(u"World")
            f.flush()

        actual = fake_test.addCleanup.call_args[0][1].as_text()
        self.assertEqual(u"World", actual)
