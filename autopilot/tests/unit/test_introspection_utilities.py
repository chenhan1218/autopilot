# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2016 Canonical
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

from contextlib import contextmanager
import subprocess
import os
import signal
import uuid

from testtools import TestCase

from autopilot.introspection.utilities import (
    _query_pids_for_process,
    get_pid_for_process,
    get_pids_for_process
)


RUNNING_PROCESS = 'compiz'
NON_RUNNING_PROCESS = uuid.uuid1().__str__()


def not_raises(predicate, *args, **kwargs):
    try:
        return bool(predicate(*args, **kwargs))
    except ValueError:
        return False


class ProcessUtilitiesTestCase(TestCase):

    def test_passing_non_running_process_raises(self):
        self.assertRaises(
            ValueError,
            _query_pids_for_process,
            NON_RUNNING_PROCESS
        )

    def test_passing_running_process_not_raises(self):
        self.assertTrue(
            not_raises(
                _query_pids_for_process,
                RUNNING_PROCESS
            )
        )

    def test_passing_integer_raises(self):
        self.assertRaises(ValueError, _query_pids_for_process, 911)

    def test_pid_for_process_is_int(self):
        self.assertIsInstance(get_pid_for_process(RUNNING_PROCESS), int)

    # def test_pids_for_process_is_list(self):
    #     self.assertIsInstance(get_pids_for_process(PYTHON_PROCESS_NAME), list)
    #
    # def test_passing_process_with_multiple_pids_raises(self):
    #     self.assertRaises(ValueError, get_pid_for_process, PYTHON_PROCESS_NAME)
