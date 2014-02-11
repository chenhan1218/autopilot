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
from mock import patch

from autopilot.display._upa import query_resolution


class QueryResolutionFunctionTests(TestCase):

    @patch('subprocess.check_output', return_value=b'"768x1280"')
    def test_fbset_lookup(self, mock_check_output):
        self.assertEqual((768, 1280), query_resolution())

    @patch('subprocess.check_output', side_effect=[OSError(), b'mako'])
    def test_dict_lookup(self, mock_check_output):
        self.assertEqual((768, 1280), query_resolution())

    @patch('subprocess.check_output', side_effect=[OSError(), b'warhog'])
    def test_dict_lookup_name_fail(self, mock_check_output):
        self.assertRaises(NotImplementedError, query_resolution)

    @patch('subprocess.check_output', side_effect=[OSError(), OSError()])
    def test_dict_lookup_noname_fail(self, mock_check_output):
        self.assertRaises(NotImplementedError, query_resolution)
