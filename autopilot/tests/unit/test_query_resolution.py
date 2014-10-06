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
from testscenarios import WithScenarios
from textwrap import dedent
from unittest.mock import patch

from autopilot.display import _upa as upa


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
        with patch.object(upa, '_get_fbset_output') as patched_gfo:
            patched_gfo.return_value = patched_fbset_resolution
            observed = upa._get_fbset_resolution()
        self.assertEqual((768, 1280), observed)

    def test_get_fbset_resolution_raises_runtimeError(self):
        patched_fbset_resolution = 'something went wrong!'
        with patch.object(upa, '_get_fbset_output') as patched_gfo:
            patched_gfo.return_value = patched_fbset_resolution
            self.assertThat(
                upa._get_fbset_resolution,
                raises(RuntimeError),
            )

    def test_hardcoded_raises_error_on_unknown_model(self):
        with patch.object(upa, 'image_codename', return_value="unknown"):
            self.assertThat(
                upa._get_hardcoded_resolution,
                raises(
                    NotImplementedError(
                        'Device "unknown" is not supported by Autopilot.'
                    )
                )
            )

    def test_query_resolution_uses_fbset_first(self):
        with patch.object(upa, '_get_fbset_resolution', return_value=(1, 2)):
            self.assertEqual((1, 2), upa.query_resolution())

    def test_query_resolution_uses_hardcoded_second(self):
        with patch.object(upa, '_get_fbset_resolution', side_effect=Exception):
            with patch.object(
                upa, '_get_hardcoded_resolution', return_value=(2, 3)
            ):
                self.assertEqual((2, 3), upa.query_resolution())


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
