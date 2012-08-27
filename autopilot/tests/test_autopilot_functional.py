# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2012 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.

from __future__ import absolute_import

import os
import os.path
import logging
from shutil import rmtree
import subprocess
from tempfile import mkdtemp
from testtools import TestCase
from testtools.matchers import Equals
from textwrap import dedent

logger = logging.getLogger(__name__)

class AutopilotFunctionalTests(TestCase):

    """A collection of functional tests for autopilot."""

    def create_empty_test_module(self):
        """Create an empty temp directory, with an empty test directory inside it.

        This method handles cleaning up the directory once the test completes.

        Returns the full path to the temp directory.

        """

        # create the base directory:
        base_path = mkdtemp()
        self.addCleanup(rmtree, base_path)

        # create the tests directory:
        os.mkdir(
            os.path.join(base_path, 'tests')
            )

        # make tests importable:
        open(
            os.path.join(
                base_path,
                'tests',
                '__init__.py'),
            'w').write('# Auto-generated file.')
        return base_path

    def run_autopilot_list(self, base_path):
        """Run 'autopilot list' in the specified base path.

        This patches the environment to ensure that it's *this* version of autopilot
        that's run.

        """
        ap_base_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                '..',
                '..'
                )
            )
        bin_path = os.path.join(ap_base_path, 'bin', 'autopilot')

        return subprocess.check_output(
            [bin_path, 'list', 'tests'],
            cwd=base_path,
            env=dict(PYTHONPATH='%s:%s' % (base_path, ap_base_path))
            )

    def test_can_list_empty_test_dir(self):
        base_path = self.create_empty_test_module()
        output = self.run_autopilot_list(base_path)

        expected_output = '\n\n 0 total tests.\n'
        self.assertThat(output, Equals(expected_output))


