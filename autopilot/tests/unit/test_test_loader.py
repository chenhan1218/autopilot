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

import os
import os.path
from testtools import TestCase
from testtools.matchers import Not, Raises
from contextlib import contextmanager
from mock import patch
import shutil
import tempfile

from autopilot.run import get_package_location, load_test_suite_from_name


@contextmanager
def working_dir(directory):
    original_directory = os.getcwd()
    os.chdir(directory)
    try:
        yield
    finally:
        os.chdir(original_directory)


class TestLoaderTests(TestCase):

    def setUp(self):
        super(TestLoaderTests, self).setUp()
        self.sandbox_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.sandbox_dir)

    @contextmanager
    def open_sandbox_file(self, relative_path):
        full_path = os.path.join(self.sandbox_dir, relative_path)
        dirname = os.path.dirname(full_path)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        with open(full_path, 'w') as f:
            yield f

    @contextmanager
    def simple_file_setup(self):
        with self.open_sandbox_file('test_foo.py') as f:
            f.write('')
        with working_dir(self.sandbox_dir):
            yield

    def test_get_package_location_can_import_file(self):
        with self.simple_file_setup():
            self.assertThat(
                lambda: get_package_location('test_foo'),
                Not(Raises())
            )

    def test_get_package_location_returns_correct_directory(self):
        with self.simple_file_setup():
            actual = get_package_location('test_foo')

        self.assertEqual(self.sandbox_dir, actual)

    def test_get_package_location_can_import_package(self):
        with self.open_sandbox_file('tests/__init__.py') as f:
            f.write('')

        with working_dir(self.sandbox_dir):
            self.assertThat(
                lambda: get_package_location('tests'),
                Not(Raises()),
                verbose=True
            )

    def test_get_package_location_returns_correct_directory_for_package(self):
        with self.open_sandbox_file('tests/__init__.py') as f:
            f.write('')

        with working_dir(self.sandbox_dir):
            actual = get_package_location('tests')

        self.assertEqual(self.sandbox_dir, actual)

    def test_get_package_location_can_import_nested_module(self):
        with self.open_sandbox_file('tests/__init__.py') as f:
            f.write('')
        with self.open_sandbox_file('tests/foo.py') as f:
            f.write('')

        with working_dir(self.sandbox_dir):
            self.assertThat(
                lambda: get_package_location('tests.foo'),
                Not(Raises()),
                verbose=True
            )

    def test_get_package_location_returns_correct_directory_for_nested_module(self):  # noqa
        with self.open_sandbox_file('tests/__init__.py') as f:
            f.write('')
        with self.open_sandbox_file('tests/foo.py') as f:
            f.write('')

        with working_dir(self.sandbox_dir):
            actual = get_package_location('tests.foo')

        self.assertEqual(self.sandbox_dir, actual)

    def test_load_test_suite_from_name_can_load_file(self):
        with self.open_sandbox_file('test_foo.py') as f:
            f.write(SIMPLE_TESTCASE)
        with working_dir(self.sandbox_dir):
            suite = load_test_suite_from_name('test_foo')

        self.assertEqual(1, len(suite._tests))

    def test_load_test_suite_from_name_can_load_nested_module(self):
        with self.open_sandbox_file('tests/__init__.py') as f:
            f.write('')
        with self.open_sandbox_file('tests/test_foo.py') as f:
            f.write(SIMPLE_TESTCASE)
        with working_dir(self.sandbox_dir):
            suite = load_test_suite_from_name('tests.test_foo')

        self.assertEqual(1, len(suite._tests))

    @patch('autopilot.run._reexecute_autopilot_using_module')
    @patch('autopilot.run._is_testing_autopilot_module', new=lambda *a: True)
    def test_testing_autopilot_is_redirected(self, patched_executor):
        patched_executor.return_value = 0
        load_test_suite_from_name('autopilot')
        self.assertTrue(patched_executor.called)


SIMPLE_TESTCASE = """\

from unittest import TestCase


class SimpleTests(TestCase):

    def test_passes(self):
        self.assertEqual(1, 1)
"""
