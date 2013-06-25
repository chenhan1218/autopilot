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


from autopilot import BackendException
from autopilot.testcase import AutopilotTestCase
from autopilot.process import ProcessManager
from autopilot.utilities import on_test_started

from subprocess import Popen, call
from testtools import TestCase
from testtools.matchers import Equals, NotEquals, LessThan
from threading import Thread
from time import sleep, time


class ProcessEmulatorTests(AutopilotTestCase):

    def ensure_gedit_not_running(self):
        """Close any open gedit applications."""
        apps = self.process_manager.get_running_applications_by_desktop_file('gedit.desktop')
        if apps:
            # this is a bit brutal, but easier in this context than the alternative.
            call(['killall', 'gedit'])

    def test_wait_for_app_running_works(self):
        """Make sure we can wait for an application to start."""
        def start_gedit():
            sleep(5)
            Popen(['gedit'])

        self.addCleanup(self.ensure_gedit_not_running)
        start = time()
        t = Thread(target=start_gedit())
        t.start()
        ret = self.process_manager.wait_until_application_is_running('gedit.desktop', 10)
        end = time()
        t.join()

        self.assertThat(ret, Equals(True))
        self.assertThat(abs(end - start - 5.0), LessThan(1))

    def test_wait_for_app_running_times_out_correctly(self):
        """Make sure the bamf emulator times out correctly if no app is started."""
        self.ensure_gedit_not_running()

        start = time()
        ret = self.process_manager.wait_until_application_is_running('gedit.desktop', 5)
        end = time()

        self.assertThat(abs(end - start - 5.0), LessThan(1))
        self.assertThat(ret, Equals(False))

    def test_start_app(self):
        """Ensure we can start an Application."""
        app = self.process_manager.start_app('Calculator')

        self.assertThat(app, NotEquals(None))
        self.assertThat(app.name, Equals('Calculator'))

    def test_start_app_window(self):
        """Ensure we can start an Application Window."""
        app = self.process_manager.start_app_window('Calculator')

        self.assertThat(app, NotEquals(None))
        self.assertThat(app.name, Equals('Calculator'))


class ProcessManagerApplicationNoCleanupTests(TestCase):
    """Testing the process manager without the automated cleanup that running
    within as an AutopilotTestCase provides.

    """
    def setUp(self):
        # Need to disable the automated cleanup that AutopilotTestCase provides.
        class FakeTestCase(object):
            def addCleanup(self, *args, **kwargs):
                pass
            def addOnException(self, handler):
                pass
            def shortDescription(self):
                pass
            def _report_traceback(self, arg):
                pass
        super(ProcessManagerApplicationNoCleanupTests, self).setUp()
        on_test_started(FakeTestCase())

    def test_can_close_all_app(self):
        """Ensure that closing an app actually closes all app instances."""
        try:
            process_manager = ProcessManager.create(preferred_backend="BAMF")
        except BackendException as e:
            self.skip("Test is only for BAMF backend ({}).".format(e.message))

        process_manager.start_app('Calculator')

        process_manager.close_all_app('Calculator')

        # ps/pgrep lists gnome-calculator as gnome-calculato (see lp
        # bug:1174911)
        ret_code = call(["pgrep", "-c", "gnome-calculato"])
        self.assertThat(ret_code, Equals(1), "Application is still running")

