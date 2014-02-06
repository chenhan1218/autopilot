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
import re
from tempfile import mktemp
from testtools.matchers import Contains, Equals, MatchesRegex, Not
from textwrap import dedent

from autopilot.testcase import AutopilotTestCase
from autopilot.tests.functional import AutopilotRunTestBase, remove_if_exists


class AutopilotFunctionalTestsBase(AutopilotRunTestBase):

    """A collection of functional tests for autopilot."""

    def run_autopilot_list(self, list_spec='tests', extra_args=[]):
        """Run 'autopilot list' in the specified base path.

        This patches the environment to ensure that it's *this* version of
        autopilot that's run.

        returns a tuple containing: (exit_code, stdout, stderr)

        """
        args_list = ["list"] + extra_args + [list_spec]
        return self.run_autopilot(args_list)

    def assertTestsInOutput(self, tests, output, total_title='tests'):
        """Asserts that 'tests' are all present in 'output'."""

        if type(tests) is not list:
            raise TypeError("tests must be a list, not %r" % type(tests))
        if not isinstance(output, str):
            raise TypeError("output must be a string, not %r" % type(output))

        test_names = ''.join(['    %s\n' % t for t in sorted(tests)])
        expected = '''\
Loading tests from: %s

%s

 %d total %s.
''' % (self.base_path, test_names, len(tests), total_title)

        self.assertThat(output, Equals(expected))

    def test_can_list_empty_test_dir(self):
        """Autopilot list must report 0 tests found with an empty test
        module."""
        code, output, error = self.run_autopilot_list()

        self.assertThat(code, Equals(0))
        self.assertThat(error, Equals(''))
        self.assertTestsInOutput([], output)

    def test_can_list_tests(self):
        """Autopilot must find tests in a file."""
        self.create_test_file(
            'test_simple.py', dedent("""\

            from autopilot.testcase import AutopilotTestCase


            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    pass
            """)
        )

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
            self.assertTestsInOutput(
                ['tests.test_simple.SimpleTest.test_simple'], output)

    def test_list_tests_with_import_error(self):
        self.create_test_file(
            'test_simple.py', dedent("""\

            from autopilot.testcase import AutopilotTestCase
            # create an import error:
            import asdjkhdfjgsdhfjhsd

            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    pass
            """)
        )
        code, output, error = self.run_autopilot_list()
        self.assertThat(code, Equals(0))
        self.assertThat(error, Equals(''))
        self.assertThat(
            output,
            MatchesRegex(
                ".*ImportError: No module named [']?asdjkhdfjgsdhfjhsd[']?.*",
                re.DOTALL
            )
        )

    def test_list_tests_with_syntax_error(self):
        self.create_test_file(
            'test_simple.py', dedent("""\

            from autopilot.testcase import AutopilotTestCase
            # create a syntax error:
            ..

            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    pass
            """)
        )
        code, output, error = self.run_autopilot_list()
        expected_error = 'SyntaxError: invalid syntax'
        self.assertThat(code, Equals(0))
        self.assertThat(error, Equals(''))
        self.assertThat(output, Contains(expected_error))

    def test_list_nonexistent_test_returns_nonzero(self):
        code, output, error = self.run_autopilot_list(list_spec='1234')
        expected_msg = "could not import package 1234: No module"
        expected_result = "0 total tests"
        self.assertThat(code, Equals(1))
        self.assertThat(output, Contains(expected_msg))
        self.assertThat(output, Contains(expected_result))

    def test_can_list_scenariod_tests(self):
        """Autopilot must show scenario counts next to tests that have
        scenarios."""
        self.create_test_file(
            'test_simple.py', dedent("""\

            from autopilot.testcase import AutopilotTestCase


            class SimpleTest(AutopilotTestCase):

                scenarios = [
                    ('scenario one', {'key': 'value'}),
                    ]

                def test_simple(self):
                    pass
            """)
        )

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
        """Autopilot must show scenario counts next to tests that have
        scenarios.

        Tests multiple scenarios on a single test suite with multiple test
        cases.

        """
        self.create_test_file(
            'test_simple.py', dedent("""\

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
            """)
        )

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
        self.create_test_file(
            'test_simple.py', dedent("""\

            from autopilot.testcase import AutopilotTestCase


            class SimpleTest(AutopilotTestCase):

                scenarios = None

                def test_simple(self):
                    pass
            """)
        )

        code, output, error = self.run_autopilot_list()
        self.assertThat(code, Equals(0))
        self.assertThat(error, Equals(''))
        self.assertTestsInOutput(
            ['tests.test_simple.SimpleTest.test_simple'], output)

    def test_local_module_loaded_and_not_system_module(self):
        module_path1 = self.create_empty_test_module()
        module_path2 = self.create_empty_test_module()

        self.base_path = module_path2

        retcode, stdout, stderr = self.run_autopilot(
            ["run", "tests"],
            pythonpath=module_path1,
            use_script=True
        )

        self.assertThat(stdout, Contains(module_path2))

    def test_can_list_just_suites(self):
        """Must only list available suites, not the contained tests."""
        self.create_test_file(
            'test_simple_suites.py', dedent("""\

            from autopilot.testcase import AutopilotTestCase


            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    pass

            class AnotherSimpleTest(AutopilotTestCase):

                def test_another_simple(self):
                    pass

                def test_yet_another_simple(self):
                    pass
            """)
        )

        code, output, error = self.run_autopilot_list(extra_args=['--suites'])
        self.assertThat(code, Equals(0))
        self.assertThat(error, Equals(''))
        self.assertTestsInOutput(
            ['tests.test_simple_suites.SimpleTest',
             'tests.test_simple_suites.AnotherSimpleTest'],
            output, total_title='suites')

    def test_record_flag_works(self):
        """Must be able to record videos when the -r flag is present."""

        # The sleep is to avoid the case where recordmydesktop does not create
        # a file because it gets stopped before it's even started capturing
        # anything.
        self.create_test_file(
            "test_simple.py", dedent("""\

            from autopilot.testcase import AutopilotTestCase
            from time import sleep

            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    sleep(1)
                    self.fail()
            """)
        )

        should_delete = not os.path.exists('/tmp/autopilot')
        if should_delete:
            self.addCleanup(remove_if_exists, "/tmp/autopilot")
        else:
            self.addCleanup(
                remove_if_exists,
                '/tmp/autopilot/tests.test_simple.SimpleTest.test_simple.ogv')

        code, output, error = self.run_autopilot(["run", "-r", "tests"])

        self.assertThat(code, Equals(1))
        self.assertTrue(os.path.exists('/tmp/autopilot'))
        self.assertTrue(os.path.exists(
            '/tmp/autopilot/tests.test_simple.SimpleTest.test_simple.ogv'))
        if should_delete:
            self.addCleanup(remove_if_exists, "/tmp/autopilot")

    def test_record_dir_option_and_record_works(self):
        """Must be able to specify record directory flag and record."""

        # The sleep is to avoid the case where recordmydesktop does not create
        # a file because it gets stopped before it's even started capturing
        # anything.
        self.create_test_file(
            "test_simple.py", dedent("""\

            from autopilot.testcase import AutopilotTestCase
            from time import sleep


            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    sleep(1)
                    self.fail()
            """)
        )
        video_dir = mktemp()
        ap_dir = '/tmp/autopilot'
        self.addCleanup(remove_if_exists, video_dir)

        should_delete = not os.path.exists(ap_dir)
        if should_delete:
            self.addCleanup(remove_if_exists, ap_dir)
        else:
            self.addCleanup(
                remove_if_exists,
                '%s/tests.test_simple.SimpleTest.test_simple.ogv' % (ap_dir))

        code, output, error = self.run_autopilot(
            ["run", "-r", "-rd", video_dir, "tests"])

        self.assertThat(code, Equals(1))
        self.assertTrue(os.path.exists(video_dir))
        self.assertTrue(os.path.exists(
            '%s/tests.test_simple.SimpleTest.test_simple.ogv' % (video_dir)))
        self.assertFalse(
            os.path.exists(
                '%s/tests.test_simple.SimpleTest.test_simple.ogv' % (ap_dir)))

    def test_record_dir_option_works(self):
        """Must be able to specify record directory flag."""

        # The sleep is to avoid the case where recordmydesktop does not create
        # a file because it gets stopped before it's even started capturing
        # anything.
        self.create_test_file(
            "test_simple.py", dedent("""\

            from autopilot.testcase import AutopilotTestCase
            from time import sleep


            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    sleep(1)
                    self.fail()
            """)
        )
        video_dir = mktemp()
        self.addCleanup(remove_if_exists, video_dir)

        code, output, error = self.run_autopilot(
            ["run", "-rd", video_dir, "tests"])

        self.assertThat(code, Equals(1))
        self.assertTrue(os.path.exists(video_dir))
        self.assertTrue(
            os.path.exists(
                '%s/tests.test_simple.SimpleTest.test_simple.ogv' %
                (video_dir)))

    def test_no_videos_saved_when_record_option_is_not_present(self):
        """Videos must not be saved if the '-r' option is not specified."""
        self.create_test_file(
            "test_simple.py", dedent("""\

            from autopilot.testcase import AutopilotTestCase
            from time import sleep

            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    sleep(1)
                    self.fail()
            """)
        )
        self.addCleanup(
            remove_if_exists,
            '/tmp/autopilot/tests.test_simple.SimpleTest.test_simple.ogv')

        code, output, error = self.run_autopilot(["run", "tests"])

        self.assertThat(code, Equals(1))
        self.assertFalse(os.path.exists(
            '/tmp/autopilot/tests.test_simple.SimpleTest.test_simple.ogv'))

    def test_no_videos_saved_for_skipped_test(self):
        """Videos must not be saved if the test has been skipped (not
        failed).

        """
        self.create_test_file(
            "test_simple.py", dedent("""\

            from autopilot.testcase import AutopilotTestCase
            from time import sleep

            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    sleep(1)
                    self.skip("Skipping Test")
            """)
        )

        video_file_path = (
            '/tmp/autopilot/tests.test_simple.SimpleTest.test_simple.ogv')
        self.addCleanup(remove_if_exists, video_file_path)

        code, output, error = self.run_autopilot(["run", "-r", "tests"])

        self.assertThat(code, Equals(0))
        self.assertThat(os.path.exists(video_file_path), Equals(False))

    def test_no_video_for_nested_testcase_when_parent_and_child_fail(self):
        """Test recording must not create a new recording for nested testcases
        where both the parent and the child testcase fail.

        """
        self.create_test_file(
            "test_simple.py", dedent("""\

            from autopilot.testcase import AutopilotTestCase
            import os

            class OuterTestCase(AutopilotTestCase):

                def test_nested_classes(self):
                    class InnerTestCase(AutopilotTestCase):

                        def test_will_fail(self):
                            self.assertTrue(False)

                    InnerTestCase("test_will_fail").run()
                    self.assertTrue(False)
            """)
        )

        expected_video_file = (
            '/tmp/autopilot/tests.test_simple.OuterTestCase.'
            'test_nested_classes.ogv')
        erroneous_video_file = (
            '/tmp/autopilot/tests.test_simple.OuterTestCase.'
            'test_nested_classes.InnerTestCase.test_will_fail.ogv')

        self.addCleanup(remove_if_exists, expected_video_file)
        self.addCleanup(remove_if_exists, erroneous_video_file)

        code, output, error = self.run_autopilot(["run", "-v", "-r", "tests"])

        self.assertThat(code, Equals(1))
        self.assertThat(os.path.exists(expected_video_file), Equals(True))
        self.assertThat(os.path.exists(erroneous_video_file), Equals(False))

    def test_runs_with_import_errors_fail(self):
        """Import errors inside a test must be considered a test failure."""
        self.create_test_file(
            'test_simple.py', dedent("""\

            from autopilot.testcase import AutopilotTestCase
            # create an import error:
            import asdjkhdfjgsdhfjhsd

            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    pass
            """)
        )

        code, output, error = self.run_autopilot(["run", "tests"])

        self.assertThat(code, Equals(1))
        self.assertThat(error, Equals(''))
        self.assertThat(
            output,
            MatchesRegex(
                ".*ImportError: No module named [']?asdjkhdfjgsdhfjhsd[']?.*",
                re.DOTALL
            )
        )
        self.assertThat(output, Contains("FAILED (failures=1)"))

    def test_runs_with_syntax_errors_fail(self):
        """Import errors inside a test must be considered a test failure."""
        self.create_test_file(
            'test_simple.py', dedent("""\

            from autopilot.testcase import AutopilotTestCase
            # create a syntax error:
            ..

            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    pass
            """)
        )

        code, output, error = self.run_autopilot(["run", "tests"])

        expected_error = '''\
tests/test_simple.py", line 4
    ..
    ^
SyntaxError: invalid syntax

'''

        self.assertThat(code, Equals(1))
        self.assertThat(error, Equals(''))
        self.assertThat(output, Contains(expected_error))
        self.assertThat(output, Contains("FAILED (failures=1)"))

    def test_can_error_with_unicode_data(self):
        """Tests that assert with unicode errors must get saved to a log
        file."""
        self.create_test_file(
            "test_simple.py", dedent(u"""\
            # encoding: utf-8

            # from autopilot.testcase import AutopilotTestCase
            from testtools import TestCase

            class SimpleTest(TestCase):

                def test_simple(self):
                    self.fail(
                        u'\xa1pl\u0279oM \u01ddpo\u0254\u0131u\u2229 oll'
                        u'\u01ddH')

            """)
        )
        output_file_path = mktemp()
        self.addCleanup(remove_if_exists, output_file_path)

        code, output, error = self.run_autopilot(
            ["run", "-o", output_file_path, "tests"])

        self.assertThat(code, Equals(1))
        self.assertTrue(os.path.exists(output_file_path))
        log_contents = open(output_file_path, encoding='utf-8').read()
        self.assertThat(
            log_contents,
            Contains(u'\xa1pl\u0279oM \u01ddpo\u0254\u0131u\u2229 oll\u01ddH'))

    def test_can_write_xml_error_with_unicode_data(self):
        """Tests that assert with unicode errors must get saved to XML log
        file."""
        self.create_test_file(
            "test_simple.py", dedent(u"""\
            # encoding: utf-8

            # from autopilot.testcase import AutopilotTestCase
            from testtools import TestCase

            class SimpleTest(TestCase):

                def test_simple(self):
                    error = (u'\xa1pl\u0279oM \u01ddpo\u0254\u0131u'
                        u'\u2229 oll\u01ddH')
                    self.fail(error)

            """)
        )
        output_file_path = mktemp()
        self.addCleanup(remove_if_exists, output_file_path)

        code, output, error = self.run_autopilot([
            "run",
            "-o", output_file_path,
            "-f", "xml",
            "tests"])

        self.assertThat(code, Equals(1))
        self.assertTrue(os.path.exists(output_file_path))
        log_contents = open(output_file_path, encoding='utf-8').read()
        self.assertThat(
            log_contents,
            Contains(u'\xa1pl\u0279oM \u01ddpo\u0254\u0131u\u2229 oll\u01ddH'))

    def test_launch_needs_arguments(self):
        """Autopilot launch must complain if not given an application to
        launch."""
        rc, _, _ = self.run_autopilot(["launch"])
        self.assertThat(rc, Equals(2))

    def test_complains_on_unknown_introspection_type(self):
        """Launching a binary that does not support an introspection type we
        are familiar with must result in a nice error message.

        """
        rc, stdout, _ = self.run_autopilot(["launch", "yes"])

        self.assertThat(rc, Equals(1))
        self.assertThat(
            stdout,
            Contains(
                "Error: Could not determine introspection type to use for "
                "application '/usr/bin/yes'"))

    def test_complains_on_missing_file(self):
        """Must give a nice error message if we try and launch a binary that's
        missing."""
        rc, stdout, _ = self.run_autopilot(["launch", "DoEsNotExist"])

        self.assertThat(rc, Equals(1))
        self.assertThat(
            stdout, Contains("Error: cannot find application 'DoEsNotExist'"))

    def test_complains_on_non_dynamic_binary(self):
        """Must give a nice error message when passing in a non-dynamic
        binary."""
        # tzselect is a bash script, and is in the base system, so should
        # always exist.
        rc, stdout, _ = self.run_autopilot(["launch", "tzselect"])

        self.assertThat(rc, Equals(1))
        self.assertThat(
            stdout, Contains(
                "Error detecting launcher: Command '['ldd', "
                "'/usr/bin/tzselect']' returned non-zero exit status 1\n"
                "(Perhaps use the '-i' argument to specify an interface.)\n")
        )

    def test_run_random_order_flag_works(self):
        """Must run tests in random order when -ro is used"""
        self.create_test_file(
            "test_simple.py", dedent("""\

            from autopilot.testcase import AutopilotTestCase
            from time import sleep

            class SimpleTest(AutopilotTestCase):

                def test_simple_one(self):
                    pass
                def test_simple_two(self):
                    pass
            """)
        )

        code, output, error = self.run_autopilot(["run", "-ro", "tests"])

        self.assertThat(code, Equals(0))
        self.assertThat(output, Contains('Running tests in random order'))

    def test_run_random_flag_not_used(self):
        """Must not run tests in random order when -ro is not used"""
        self.create_test_file(
            "test_simple.py", dedent("""\

            from autopilot.testcase import AutopilotTestCase
            from time import sleep

            class SimpleTest(AutopilotTestCase):

                def test_simple_one(self):
                    pass
                def test_simple_two(self):
                    pass
            """)
        )

        code, output, error = self.run_autopilot(["run", "tests"])

        self.assertThat(code, Equals(0))
        self.assertThat(output, Not(Contains('Running tests in random order')))


class AutopilotPatchEnvironmentTests(AutopilotTestCase):

    def test_patch_environment_new_patch_is_unset_to_none(self):
        """patch_environment must unset the environment variable if previously
        was unset.

        """

        class PatchEnvironmentSubTests(AutopilotTestCase):

            def test_patch_env_sets_var(self):
                """Setting the environment variable must make it available."""
                self.patch_environment("APABC321", "Foo")
                self.assertThat(os.getenv("APABC321"), Equals("Foo"))

        self.assertThat(os.getenv('APABC321'), Equals(None))

        result = PatchEnvironmentSubTests("test_patch_env_sets_var").run()

        self.assertThat(result.wasSuccessful(), Equals(True))
        self.assertThat(os.getenv('APABC321'), Equals(None))

    def test_patch_environment_existing_patch_is_reset(self):
        """patch_environment must reset the environment back to it's previous
        value.

        """

        class PatchEnvironmentSubTests(AutopilotTestCase):

            def test_patch_env_sets_var(self):
                """Setting the environment variable must make it available."""
                self.patch_environment("APABC987", "InnerTest")
                self.assertThat(os.getenv("APABC987"), Equals("InnerTest"))

        self.patch_environment('APABC987', "OuterTest")
        self.assertThat(os.getenv('APABC987'), Equals("OuterTest"))

        result = PatchEnvironmentSubTests("test_patch_env_sets_var").run()

        self.assertThat(result.wasSuccessful(), Equals(True))
        self.assertThat(os.getenv('APABC987'), Equals("OuterTest"))


class AutopilotVerboseFunctionalTests(AutopilotFunctionalTestsBase):

    """Scenarioed functional tests for autopilot's verbose logging."""

    scenarios = [
        ('text_format', dict(output_format='text')),
        ('xml_format', dict(output_format='xml'))
    ]

    def test_verbose_flag_works(self):
        """Verbose flag must log to stderr."""
        self.create_test_file(
            "test_simple.py", dedent("""\

            from autopilot.testcase import AutopilotTestCase


            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    pass
            """)
        )

        code, output, error = self.run_autopilot(["run",
                                                  "-f", self.output_format,
                                                  "-v", "tests"])

        self.assertThat(code, Equals(0))
        self.assertThat(
            error, Contains(
                "Starting test tests.test_simple.SimpleTest.test_simple"))

    def test_verbose_flag_shows_timestamps(self):
        """Verbose log must include timestamps."""
        self.create_test_file(
            "test_simple.py", dedent("""\

            from autopilot.testcase import AutopilotTestCase


            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    pass
            """)
        )

        code, output, error = self.run_autopilot(["run",
                                                  "-f", self.output_format,
                                                  "-v", "tests"])

        self.assertThat(error, MatchesRegex("^\d\d:\d\d:\d\d\.\d\d\d"))

    def test_verbose_flag_shows_success(self):
        """Verbose log must indicate successful tests (text format)."""
        self.create_test_file(
            "test_simple.py", dedent("""\

            from autopilot.testcase import AutopilotTestCase


            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    pass
            """)
        )

        code, output, error = self.run_autopilot(["run",
                                                  "-f", self.output_format,
                                                  "-v", "tests"])

        self.assertThat(
            error, Contains("OK: tests.test_simple.SimpleTest.test_simple"))

    def test_verbose_flag_shows_error(self):
        """Verbose log must indicate test error with a traceback."""
        self.create_test_file(
            "test_simple.py", dedent("""\

            from autopilot.testcase import AutopilotTestCase


            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    raise RuntimeError("Intentionally fail test.")
            """)
        )

        code, output, error = self.run_autopilot(["run",
                                                  "-f", self.output_format,
                                                  "-v", "tests"])

        self.assertThat(
            error, Contains("ERROR: tests.test_simple.SimpleTest.test_simple"))
        self.assertThat(error, Contains("traceback:"))
        self.assertThat(
            error,
            Contains("RuntimeError: Intentionally fail test.")
        )

    def test_verbose_flag_shows_failure(self):
        """Verbose log must indicate a test failure with a traceback (xml
        format)."""
        self.create_test_file(
            "test_simple.py", dedent("""\

            from autopilot.testcase import AutopilotTestCase


            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    self.assertTrue(False)
            """)
        )

        code, output, error = self.run_autopilot(["run",
                                                  "-f", self.output_format,
                                                  "-v", "tests"])

        self.assertIn("FAIL: tests.test_simple.SimpleTest.test_simple", error)
        self.assertIn("traceback:", error)
        self.assertIn("AssertionError: False is not true", error)

    def test_verbose_flag_captures_nested_autopilottestcase_classes(self):
        """Verbose log must contain the log details of both the nested and
        parent testcase."""
        self.create_test_file(
            "test_simple.py", dedent("""\

            from autopilot.testcase import AutopilotTestCase
            import os

            class OuterTestCase(AutopilotTestCase):

                def test_nested_classes(self):
                    class InnerTestCase(AutopilotTestCase):

                        def test_produce_log_output(self):
                            self.assertTrue(True)

                    InnerTestCase("test_produce_log_output").run()
                    self.assertTrue(True)
            """)
        )

        code, output, error = self.run_autopilot(["run",
                                                  "-f", self.output_format,
                                                  "-v", "tests"])

        self.assertThat(code, Equals(0))
        self.assertThat(
            error, Contains(
                "Starting test tests.test_simple.OuterTestCase."
                "test_nested_classes"))
        self.assertThat(
            error, Contains(
                "Starting test tests.test_simple.InnerTestCase."
                "test_produce_log_output"))

    def test_can_enable_debug_output(self):
        """Verbose log must show debug messages if we specify '-vv'."""
        self.create_test_file(
            "test_simple.py", dedent("""\

            from autopilot.testcase import AutopilotTestCase
            from autopilot.utilities import get_debug_logger


            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    get_debug_logger().debug("Hello World")
            """)
        )

        code, output, error = self.run_autopilot(["run",
                                                  "-f", self.output_format,
                                                  "-vv", "tests"])

        self.assertThat(error, Contains("Hello World"))

    def test_debug_output_not_shown_by_default(self):
        """Verbose log must not show debug messages unless we specify '-vv'."""
        self.create_test_file(
            "test_simple.py", dedent("""\

            from autopilot.testcase import AutopilotTestCase
            from autopilot.utilities import get_debug_logger


            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    get_debug_logger().debug("Hello World")
            """)
        )

        code, output, error = self.run_autopilot(["run",
                                                  "-f", self.output_format,
                                                  "-v", "tests"])

        self.assertThat(error, Not(Contains("Hello World")))

    def test_verbose_flag_shows_autopilot_version(self):
        from autopilot import get_version_string
        """Verbose log must indicate successful tests (text format)."""
        self.create_test_file(
            "test_simple.py", dedent("""\

            from autopilot.testcase import AutopilotTestCase


            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    pass
            """)
        )

        code, output, error = self.run_autopilot(["run",
                                                  "-f", self.output_format,
                                                  "-v", "tests"])
        self.assertThat(
            error, Contains(get_version_string()))

    def test_failfast(self):
        """Run stops after first error encountered."""
        self.create_test_file(
            'test_failfast.py', dedent("""\

            from autopilot.testcase import AutopilotTestCase


            class SimpleTest(AutopilotTestCase):

                def test_one(self):
                    raise Exception

                def test_two(self):
                    raise Exception
            """)
        )
        code, output, error = self.run_autopilot(["run",
                                                  "--failfast",
                                                  "tests"])
        self.assertThat(code, Equals(1))
        self.assertIn("Ran 1 test", output)
        self.assertIn("FAILED (failures=1)", output)
