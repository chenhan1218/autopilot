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
from testtools.matchers import Contains

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
            f.write(b"Hello")
            f.flush()

        actual = fake_test.addCleanup.call_args[0][2].as_text()
        self.assertEqual(u"Hello", actual)

    def test_follow_file_does_not_contain_old_file_data(self):
        fake_test = Mock()
        with NamedTemporaryFile() as f:
            f.write(b"Hello")
            f.flush()
            follow_file(f.name, fake_test)
            f.write(b"World")
            f.flush()

        actual = fake_test.addCleanup.call_args[0][2].as_text()
        self.assertEqual(u"World", actual)

    def test_follow_file_uses_filename_by_default(self):
        fake_test = Mock()
        with NamedTemporaryFile() as f:
            follow_file(f.name, fake_test)

            actual = fake_test.addCleanup.call_args[0][1]
            self.assertEqual(f.name, actual)

    def test_follow_file_uses_cotent_name(self):
        fake_test = Mock()
        content_name = self.getUniqueString()
        with NamedTemporaryFile() as f:
            follow_file(f.name, fake_test, content_name)

            actual = fake_test.addCleanup.call_args[0][1]
            self.assertEqual(content_name, actual)

    def test_real_test_has_detail_added(self):
        with NamedTemporaryFile() as f:
            class FakeTest(TestCase):
                def test_foo(self):
                        follow_file(f.name, self)
                        f.write(b"Hello")
                        f.flush()
            test = FakeTest('test_foo')
            result = test.run()
        self.assertTrue(result.wasSuccessful)
        self.assertThat(test.getDetails(), Contains(f.name))
