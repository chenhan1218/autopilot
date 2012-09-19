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
from testtools.matchers import Contains, Equals, MatchesRegex
from textwrap import dedent
import re


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
        return self.run_autopilot("list " + list_spec)

    def run_autopilot(self, arguments):
        ap_base_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                '..',
                '..'
                )
            )

        environment_patch = dict(DISPLAY=':0')
        # Set PYTHONPATH always, since we can't tell what sys.path will be in the
        # child process.
        environment_patch['PYTHONPATH'] = ap_base_path

        bin_path = os.path.join(ap_base_path, 'bin', 'autopilot')
        if not os.path.exists(bin_path):
            bin_path = subprocess.check_output(['which', 'autopilot']).strip()
            logger.info("Not running from source, setting bin_path to %s", bin_path)

        environ = os.environ
        environ.update(environment_patch)

        process = subprocess.Popen(
            "%s %s" % (bin_path, arguments),
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

    def assertTestsInOutput(self, tests, output):
        """Asserts that 'tests' are all present in 'output'."""

        if type(tests) is not list:
            raise TypeError("tests must be a list, not %r" % type(tests))
        if not isinstance(output, basestring):
            raise TypeError("output must be a string, not %r" % type(output))

        expected = '''\
Loading tests from: %s

%s

 %d total tests.
''' % (self.base_path,
    ''.join(['    %s\n' % t for t in sorted(tests)]),
    len(tests))

        self.assertThat(output, Equals(expected))


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

        self.assertThat(code, Equals(0))
        self.assertThat(error, Equals(''))
        self.assertTestsInOutput([], output)

    def test_can_list_tests(self):
        """Autopilot must find tests in a file."""
        self.create_test_file('test_simple.py', dedent("""\

            from autopilot.testcase import AutopilotTestCase


            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    pass
            """
            ))

        # ideally these would be different tests, but I'm lazy:
        valid_test_specs = [
            'tests',
            'tests.test_simple',
            'tests.test_simple.SimpleTest',
            'tests.test_simple.SimpleTest.test_simple',
            ]
        for test_spec in valid_test_specs:
            code, output, error = self.run_autopilot_list(test_spec)
            self.assertThat(code, Equals(0))
            self.assertThat(error, Equals(''))
            self.assertTestsInOutput(['tests.test_simple.SimpleTest.test_simple'], output)

    def test_list_tests_with_import_error(self):
        self.create_test_file('test_simple.py', dedent("""\

            from autopilot.testcase import AutopilotTestCase
            # create an import error:
            import asdjkhdfjgsdhfjhsd

            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    pass
            """
            ))
        code, output, error = self.run_autopilot_list()
        expected_regex = '''\
Loading tests from: %s

Failed to import test module: tests.test_simple
Traceback \(most recent call last\):
  File "/usr/lib/python2.7/unittest/loader.py", line 252, in _find_tests
    module = self._get_module_from_name\(name\)
  File "/usr/lib/python2.7/unittest/loader.py", line 230, in _get_module_from_name
    __import__\(name\)
  File "/tmp/\w*/tests/test_simple.py", line 4, in <module>
    import asdjkhdfjgsdhfjhsd
ImportError: No module named asdjkhdfjgsdhfjhsd



 0 total tests.
''' % self.base_path
        self.assertThat(code, Equals(0))
        self.assertThat(error, Equals(''))
        self.assertThat(output, MatchesRegex(expected_regex, re.MULTILINE))

    def test_list_tests_with_syntax_error(self):
        self.create_test_file('test_simple.py', dedent("""\

            from autopilot.testcase import AutopilotTestCase
            # create a syntax error:
            ..

            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    pass
            """
            ))
        code, output, error = self.run_autopilot_list()
        expected_regex = '''\
Loading tests from: %s

Failed to import test module: tests.test_simple
Traceback \(most recent call last\):
  File "/usr/lib/python2.7/unittest/loader.py", line 252, in _find_tests
    module = self._get_module_from_name\(name\)
  File "/usr/lib/python2.7/unittest/loader.py", line 230, in _get_module_from_name
    __import__\(name\)
  File "/tmp/\w*/tests/test_simple.py", line 4
    \.\.
    \^
SyntaxError: invalid syntax



 0 total tests.
''' % self.base_path
        self.assertThat(code, Equals(0))
        self.assertThat(error, Equals(''))
        self.assertThat(output, MatchesRegex(expected_regex, re.MULTILINE))

    def test_can_list_scenariod_tests(self):
        """Autopilot must show scenario counts next to tests that have scenarios."""
        self.create_test_file('test_simple.py', dedent("""\

            from autopilot.testcase import AutopilotTestCase


            class SimpleTest(AutopilotTestCase):

                scenarios = [
                    ('scenario one', {'key': 'value'}),
                    ]

                def test_simple(self):
                    pass
            """
            ))

        expected_output = '''\
Loading tests from: %s

 *1 tests.test_simple.SimpleTest.test_simple


 1 total tests.
''' % self.base_path

        code, output, error = self.run_autopilot_list()
        self.assertThat(code, Equals(0))
        self.assertThat(error, Equals(''))
        self.assertThat(output, Equals(expected_output))

    def test_can_list_scenariod_tests_with_multiple_scenarios(self):
        """Autopilot must show scenario counts next to tests that have scenarios.

        Tests multiple scenarios on a single test suite with multiple test cases.

        """
        self.create_test_file('test_simple.py', dedent("""\

            from autopilot.testcase import AutopilotTestCase


            class SimpleTest(AutopilotTestCase):

                scenarios = [
                    ('scenario one', {'key': 'value'}),
                    ('scenario two', {'key': 'value2'}),
                    ]

                def test_simple(self):
                    pass

                def test_simple_two(self):
                    pass
            """
            ))

        expected_output = '''\
Loading tests from: %s

 *2 tests.test_simple.SimpleTest.test_simple
 *2 tests.test_simple.SimpleTest.test_simple_two


 4 total tests.
''' % self.base_path

        code, output, error = self.run_autopilot_list()
        self.assertThat(code, Equals(0))
        self.assertThat(error, Equals(''))
        self.assertThat(output, Equals(expected_output))

    def test_can_list_invalid_scenarios(self):
        """Autopilot must ignore scenarios that are not lists."""
        self.create_test_file('test_simple.py', dedent("""\

            from autopilot.testcase import AutopilotTestCase


            class SimpleTest(AutopilotTestCase):

                scenarios = None

                def test_simple(self):
                    pass
            """
            ))

        code, output, error = self.run_autopilot_list()
        self.assertThat(code, Equals(0))
        self.assertThat(error, Equals(''))
        self.assertTestsInOutput(['tests.test_simple.SimpleTest.test_simple'], output)

    def test_verbose_flag_works(self):
        """Verbose flag must log to stderr."""
        self.create_test_file("test_simple.py", dedent("""\

            from autopilot.testcase import AutopilotTestCase


            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    '''This is the test description.'''
                    pass
            """
            ))

        code, output, error = self.run_autopilot("run -v tests")

        self.assertThat(code, Equals(0))
        self.assertThat(error, Contains("Starting test tests.test_simple.SimpleTest.test_simple"))
