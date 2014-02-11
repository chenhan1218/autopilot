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
from testscenarios import WithScenarios
from textwrap import dedent
from mock import patch

from autopilot.display import _upa  as upa


class QueryResolutionFunctionTests(TestCase):

    @patch('subprocess.check_output', return_value=b'')
    def test_fbset_output_calls_subprocess(self, patched_check_output):
        upa._get_fbset_output()
        patched_check_output.assert_called_once_with(
            ["fbset", "-s", "-x"]
        )

    def test_get_fbset_resolution(self):
        patched_fbset_resolution = dedent(
            '''
            Mode "768x1280"
                # D: 0.002 MHz, H: 0.002 kHz, V: 0.002 Hz
                DotClock 0.003
                HTimings 768 776 780 960
                VTimings 1280 1288 1290 1312
                Flags    "-HSync" "-VSync"
            EndMode
            '''
        )
        with patch.object(upa, '_get_fbset_output', return_value=patched_fbset_resolution):
            observed = upa._get_fbset_resolution()
        self.assertEqual((768, 1280), observed)


class HardCodedResolutionTests(WithScenarios, TestCase):

    scenarios = [
        ("generic", dict(name="generic", expected=(480, 800))),
        ("mako", dict(name="mako", expected=(768, 1280))),
        ("maguro", dict(name="maguro", expected=(720, 1280))),
        ("manta", dict(name="manta", expected=(2560, 1600))),
        ("grouper", dict(name="grouper", expected=(800, 1280))),
    ]

    def test_hardcoded_resolutions_works_for_known_codenames(self):
        with patch.object(upa, 'image_codename', return_value=self.name):
            observed = upa._get_hardcoded_resolution()
        self.assertEqual(self.expected, observed)


    # @patch('subprocess.check_output', return_value=b'"768x1280"')
    # def test_fbset_lookup(self, mock_check_output):
    #     self.assertEqual((768, 1280), query_resolution())

    # @patch('subprocess.check_output', side_effect=[OSError(), b'mako'])
    # def test_dict_lookup(self, mock_check_output):
    #     self.assertEqual((768, 1280), query_resolution())

    # @patch('subprocess.check_output', side_effect=[OSError(), b'warhog'])
    # def test_dict_lookup_name_fail(self, mock_check_output):
    #     self.assertRaises(NotImplementedError, query_resolution)

    # @patch('subprocess.check_output', side_effect=[OSError(), OSError()])
    # def test_dict_lookup_noname_fail(self, mock_check_output):
    #     self.assertRaises(NotImplementedError, query_resolution)
