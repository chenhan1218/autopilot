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
from testtools.content import text_content
from testtools.matchers import Equals
from textwrap import dedent

logger = logging.getLogger(__name__)

class AutopilotFunctionalTests(TestCase):

    """A collection of functional tests for autopilot."""

    def setUp(self):
        super(AutopilotFunctionalTests, self).setUp()
        self.base_path = self.create_empty_test_module()

    def create_empty_test_module(self):
        """Create an empty temp directory, with an empty test directory inside it.

        This method handles cleaning up the directory once the test completes.

        Returns the full path to the temp directory.

        """

        # create the base directory:
        base_path = mkdtemp()
        self.addDetail('base path', text_content(base_path))
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

    def run_autopilot_list(self, list_spec='tests'):
        """Run 'autopilot list' in the specified base path.

        This patches the environment to ensure that it's *this* version of autopilot
        that's run.

        returns a tuple containing: (exit_code, stdout, stderr)

        """
        ap_base_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                '..',
                '..'
                )
            )
        bin_path = os.path.join(ap_base_path, 'bin', 'autopilot')

        environ = os.environ
        environ.update(dict(
                PYTHONPATH='%s:%s' % (self.base_path, ap_base_path),
                DISPLAY=':0'))

        process = subprocess.Popen(
            "%s list %s" % (bin_path, list_spec),
            cwd=self.base_path,
            env=environ,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True
            )

        stdout, stderr = process.communicate()
        retcode = process.poll()

        self.addDetail('retcode', text_content(str(retcode)))
        self.addDetail('stdout', text_content(stdout))
        self.addDetail('stderr', text_content(stderr))

        return (retcode, stdout, stderr)

    def create_test_file(self, name, contents):
        """Create a test file with the given name and contents.

        'name' must end in '.py' if it is to be importable.
        'contents' must be valid python code.

        """
        open(
            os.path.join(
                self.base_path,
                'tests',
                name),
            'w').write(contents)

    def test_can_list_empty_test_dir(self):
        """Autopilot list must report 0 tests found with an empty test module."""
        code, output, error = self.run_autopilot_list()

        expected_output = '\n\n 0 total tests.\n'

        self.assertThat(code, Equals(0))
        self.assertThat(error, Equals(''))
        self.assertThat(output, Equals(expected_output))

    def test_can_list_tests(self):
        """Autopilot must find tests in a file."""
        self.create_test_file('test_simple.py', dedent("""\

            from autopilot.testcase import AutopilotTestCase


            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    pass
            """
            ))

        code, output, error = self.run_autopilot_list('tests.test_simple')

        expected_output = '''\
    tests.test_simple.SimpleTest.test_simple


 1 total tests.
'''


        self.assertThat(code, Equals(0))
        self.assertThat(error, Equals(''))
        self.assertThat(output, Equals(expected_output))


