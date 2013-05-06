# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2012-2013 Canonical
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


from __future__ import absolute_import

from codecs import open
import os
import os.path
import logging
from shutil import rmtree
import subprocess
from tempfile import mktemp, mkdtemp
from testtools.content import Content, text_content
from testtools.content_type import ContentType
from testtools.matchers import Contains, Equals, MatchesRegex, Not
from textwrap import dedent
import re


from autopilot.testcase import AutopilotTestCase


def remove_if_exists(path):
    if os.path.exists(path):
        if os.path.isdir(path):
            rmtree(path)
        else:
            os.remove(path)


logger = logging.getLogger(__name__)

class AutopilotFunctionalTestsBase(AutopilotTestCase):

    """The base class for the autopilot functional tests."""

    def setUp(self):
        super(AutopilotFunctionalTestsBase, self).setUp()
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

        logger.info("Starting autopilot command with:")
        logger.info("Autopilot command = %s", bin_path)
        logger.info("Arguments = %s", arguments)
        logger.info("CWD = %r", self.base_path)

        arg = [bin_path]
        arg.extend(arguments)
        process = subprocess.Popen(
            arg,
            cwd=self.base_path,
            env=environ,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            )

        stdout, stderr = process.communicate()
        retcode = process.poll()

        self.addDetail('retcode', text_content(str(retcode)))
        self.addDetail('stdout', Content(
            ContentType('text', 'plain', {'charset': 'iso-8859-1'}),
            lambda:[stdout]))
        self.addDetail('stderr', Content(
            ContentType('text', 'plain', {'charset': 'iso-8859-1'}),
            lambda:[stderr]))

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
            'w',
            encoding='utf8').write(contents)


class AutopilotFunctionalTests(AutopilotFunctionalTestsBase):

    """A collection of functional tests for autopilot."""

    def run_autopilot_list(self, list_spec='tests'):
        """Run 'autopilot list' in the specified base path.

        This patches the environment to ensure that it's *this* version of autopilot
        that's run.

        returns a tuple containing: (exit_code, stdout, stderr)

        """
        return self.run_autopilot(["list", list_spec])

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

''' % self.base_path
        self.assertThat(code, Equals(0))
        self.assertThat(error, Equals(''))
        self.assertTrue(re.search(expected_regex, output, re.MULTILINE))

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

''' % self.base_path
        self.assertThat(code, Equals(0))
        self.assertThat(error, Equals(''))
        self.assertTrue(re.search(expected_regex, output, re.MULTILINE))

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

    def test_record_flag_works(self):
        """Must be able to record videos when the -r flag is present."""
        self.create_test_file("test_simple.py", dedent("""\

            from autopilot.testcase import AutopilotTestCase


            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    self.fail()
            """
            ))

        self.addCleanup(remove_if_exists, "/tmp/autopilot")
        code, output, error = self.run_autopilot(["run", "-r", "tests"])

        self.assertThat(code, Equals(1))
        self.assertTrue(os.path.exists('/tmp/autopilot'))
        self.assertTrue(os.path.exists('/tmp/autopilot/tests.test_simple.SimpleTest.test_simple.ogv'))

    def test_record_dir_option_works(self):
        """Must be able to specify record directory flag."""
        self.create_test_file("test_simple.py", dedent("""\

            from autopilot.testcase import AutopilotTestCase


            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    self.fail()
            """
            ))
        video_dir = mktemp()
        self.addCleanup(remove_if_exists, video_dir)

        code, output, error = self.run_autopilot(["run", "-r", "-rd", video_dir, "tests"])

        self.assertThat(code, Equals(1))
        self.assertTrue(os.path.exists(video_dir))
        self.assertTrue(os.path.exists('%s/tests.test_simple.SimpleTest.test_simple.ogv' % (video_dir)))

    def test_no_videos_saved_when_record_option_is_not_present(self):
        """Videos must not be saved if the '-r' option is not specified."""
        self.create_test_file("test_simple.py", dedent("""\

            from autopilot.testcase import AutopilotTestCase


            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    self.fail()
            """
            ))
        video_dir = mktemp()
        self.addCleanup(remove_if_exists, video_dir)

        code, output, error = self.run_autopilot(["run", "-rd", video_dir, "tests"])

        self.assertThat(code, Equals(1))
        self.assertFalse(os.path.exists(video_dir))
        self.assertFalse(os.path.exists('%s/tests.test_simple.SimpleTest.test_simple.ogv' % (video_dir)))

    def test_runs_with_import_errors_fail(self):
        """Import errors inside a test must be considered a test failure."""
        self.create_test_file('test_simple.py', dedent("""\

            from autopilot.testcase import AutopilotTestCase
            # create an import error:
            import asdjkhdfjgsdhfjhsd

            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    pass
            """
            ))

        code, output, error = self.run_autopilot(["run", "tests"])

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

''' % self.base_path

        self.assertThat(code, Equals(1))
        self.assertThat(error, Equals(''))
        self.assertTrue(re.search(expected_regex, output, re.MULTILINE))
        self.assertThat(output, Contains("FAILED (failures=1)"))

    def test_runs_with_syntax_errors_fail(self):
        """Import errors inside a test must be considered a test failure."""
        self.create_test_file('test_simple.py', dedent("""\

            from autopilot.testcase import AutopilotTestCase
            # create a syntax error:
            ..

            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    pass
            """
            ))

        code, output, error = self.run_autopilot(["run", "tests"])

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

''' % self.base_path

        self.assertThat(code, Equals(1))
        self.assertThat(error, Equals(''))
        self.assertTrue(re.search(expected_regex, output, re.MULTILINE))
        self.assertThat(output, Contains("FAILED (failures=1)"))

    def test_can_error_with_unicode_data(self):
        """Tests that assert with unicode errors must get saved to a log file."""
        self.create_test_file("test_simple.py", dedent(u"""\
            # encoding: utf-8

            # from autopilot.testcase import AutopilotTestCase
            from testtools import TestCase

            class SimpleTest(TestCase):

                def test_simple(self):
                    self.fail(u'\xa1pl\u0279oM \u01ddpo\u0254\u0131u\u2229 oll\u01ddH')

            """
            ))
        output_file_path = mktemp()
        self.addCleanup(remove_if_exists, output_file_path)

        code, output, error = self.run_autopilot(["run", "-o", output_file_path, "tests"])

        self.assertThat(code, Equals(1))
        self.assertTrue(os.path.exists(output_file_path))
        log_contents = unicode(open(output_file_path, encoding='utf-8').read())
        self.assertThat(log_contents,
            Contains(u'\xa1pl\u0279oM \u01ddpo\u0254\u0131u\u2229 oll\u01ddH'))

    def test_can_write_xml_error_with_unicode_data(self):
        """Tests that assert with unicode errors must get saved to XML log file."""
        self.create_test_file("test_simple.py", dedent(u"""\
            # encoding: utf-8

            # from autopilot.testcase import AutopilotTestCase
            from testtools import TestCase

            class SimpleTest(TestCase):

                def test_simple(self):
                    self.fail(u'\xa1pl\u0279oM \u01ddpo\u0254\u0131u\u2229 oll\u01ddH')

            """
            ))
        output_file_path = mktemp()
        self.addCleanup(remove_if_exists, output_file_path)

        code, output, error = self.run_autopilot([
            "run",
            "-o", output_file_path,
            "-f", "xml",
            "tests"])

        self.assertThat(code, Equals(1))
        self.assertTrue(os.path.exists(output_file_path))
        log_contents = unicode(open(output_file_path, encoding='utf-8').read())
        self.assertThat(log_contents,
            Contains(u'\xa1pl\u0279oM \u01ddpo\u0254\u0131u\u2229 oll\u01ddH'))

    def test_launch_needs_arguments(self):
        """Autopilot launch must complain if not given an application to launch."""
        rc, _, _ = self.run_autopilot(["launch"])
        self.assertThat(rc, Equals(2))

    def test_complains_on_unknown_introspection_type(self):
        """Launching a binary that does not support an introspection type we are
        familiar with must result in a nice error message.

        """
        rc, stdout, _ = self.run_autopilot(["launch", "yes"])

        self.assertThat(rc, Equals(1))
        self.assertThat(stdout,
            Contains("Error: Could not determine introspection type to use for application '/usr/bin/yes'"))

    def test_complains_on_missing_file(self):
        """Must give a nice error message if we try and launch a binary that's missing."""
        rc, stdout, _ = self.run_autopilot(["launch", "DoEsNotExist"])

        self.assertThat(rc, Equals(1))
        self.assertThat(stdout,
            Contains("Error: cannot find application 'DoEsNotExist'"))

    def test_complains_on_non_dynamic_binary(self):
        """Must give a nice error message when passing in a non-dynamic binary."""
        #tzselect is a bash script, and is in the base system, so should always exist.
        rc, stdout, _ = self.run_autopilot(["launch", "tzselect"])

        self.assertThat(rc, Equals(1))
        self.assertThat(stdout,
            Contains("Error detecting launcher: Command '['ldd', '/usr/bin/tzselect']' returned non-zero exit status 1\n(Perhaps use the '-i' argument to specify an interface.)\n"))


class AutopilotVerboseFunctionalTests(AutopilotFunctionalTestsBase):

    """Scenarioed functional tests for autopilot's verbose logging."""

    scenarios = [
        ('text_format', dict(output_format='text')),
        ('xml_format', dict(output_format='xml'))
    ]

    def test_verbose_flag_works(self):
        """Verbose flag must log to stderr."""
        self.create_test_file("test_simple.py", dedent("""\

            from autopilot.testcase import AutopilotTestCase


            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    pass
            """
            ))

        code, output, error = self.run_autopilot(["run",
                                                  "-f", self.output_format,
                                                  "-v", "tests"])

        self.assertThat(code, Equals(0))
        self.assertThat(error, Contains("Starting test tests.test_simple.SimpleTest.test_simple"))

    def test_verbose_flag_shows_timestamps(self):
        """Verbose log must include timestamps."""
        self.create_test_file("test_simple.py", dedent("""\

            from autopilot.testcase import AutopilotTestCase


            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    pass
            """
            ))

        code, output, error = self.run_autopilot(["run",
                                                  "-f", self.output_format,
                                                  "-v", "tests"])

        self.assertThat(error, MatchesRegex("^\d\d:\d\d:\d\d\.\d\d\d"))

    def test_verbose_flag_shows_success(self):
        """Verbose log must indicate successful tests (text format)."""
        self.create_test_file("test_simple.py", dedent("""\

            from autopilot.testcase import AutopilotTestCase


            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    pass
            """
            ))

        code, output, error = self.run_autopilot(["run",
                                                  "-f", self.output_format,
                                                  "-v", "tests"])

        self.assertThat(error, Contains("OK: tests.test_simple.SimpleTest.test_simple"))

    def test_verbose_flag_shows_error(self):
        """Verbose log must indicate test error with a traceback."""
        self.create_test_file("test_simple.py", dedent("""\

            from autopilot.testcase import AutopilotTestCase


            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    self.assertTrue()
            """
            ))

        code, output, error = self.run_autopilot(["run",
                                                  "-f", self.output_format,
                                                  "-v", "tests"])

        self.assertThat(error, Contains("ERROR: tests.test_simple.SimpleTest.test_simple"))
        self.assertThat(error, Contains("traceback:"))
        self.assertThat(error, Contains("TypeError: assertTrue() takes at least 2 arguments (1 given)"))

    def test_verbose_flag_shows_failure(self):
        """Verbose log must indicate a test failure with a traceback (xml format)."""
        self.create_test_file("test_simple.py", dedent("""\

            from autopilot.testcase import AutopilotTestCase


            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    self.assertTrue(False)
            """
            ))

        code, output, error = self.run_autopilot(["run",
                                                  "-f", self.output_format,
                                                  "-v", "tests"])

        self.assertIn("FAIL: tests.test_simple.SimpleTest.test_simple", error)
        self.assertIn("traceback:", error)
        self.assertIn("AssertionError: False is not true", error)

    def test_can_enable_debug_output(self):
        """Verbose log must show debug messages if we specify '-vv'."""
        self.create_test_file("test_simple.py", dedent("""\

            from autopilot.testcase import AutopilotTestCase
            from autopilot.utilities import get_debug_logger


            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    get_debug_logger().debug("Hello World")
            """
            ))

        code, output, error = self.run_autopilot(["run",
                                                  "-f", self.output_format,
                                                  "-vv", "tests"])

        self.assertThat(error, Contains("Hello World"))

    def test_debug_output_not_shown_by_default(self):
        """Verbose log must not show debug messages unless we specify '-vv'."""
        self.create_test_file("test_simple.py", dedent("""\

            from autopilot.testcase import AutopilotTestCase
            from autopilot.utilities import get_debug_logger


            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    get_debug_logger().debug("Hello World")
            """
            ))

        code, output, error = self.run_autopilot(["run",
                                                  "-f", self.output_format,
                                                  "-v", "tests"])

        self.assertThat(error, Not(Contains("Hello World")))