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
from tempfile import  mkdtemp
from testtools.content import Content, text_content
from testtools.content_type import ContentType

from autopilot.testcase import AutopilotTestCase


def remove_if_exists(path):
    if os.path.exists(path):
        if os.path.isdir(path):
            rmtree(path)
        else:
            os.remove(path)


logger = logging.getLogger(__name__)


class AutopilotRunTestBase(AutopilotTestCase):

    """The base class for the autopilot functional tests."""

    def setUp(self):
        super(AutopilotRunTestBase, self).setUp()
        self.base_path = self.create_empty_test_module()

    def create_empty_test_module(self):
        """Create an empty temp directory, with an empty test directory inside
        it.

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
                '..',
                '..'
            )
        )

        environment_patch = dict(DISPLAY=':0')
        if not os.getcwd().startswith('/usr/'):
            environment_patch['PYTHONPATH'] = ap_base_path
        bin_path = os.path.join(ap_base_path, 'bin', 'autopilot')
        if not os.path.exists(bin_path):
            bin_path = subprocess.check_output(['which', 'autopilot']).strip()
            logger.info(
                "Not running from source, setting bin_path to %s", bin_path)

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
        self.addDetail(
            'stdout',
            Content(
                ContentType('text', 'plain', {'charset': 'iso-8859-1'}),
                lambda: [stdout]
            )
        )
        self.addDetail(
            'stderr',
            Content(
                ContentType('text', 'plain', {'charset': 'iso-8859-1'}),
                lambda: [stderr]
            )
        )

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
