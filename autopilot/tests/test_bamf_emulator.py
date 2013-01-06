# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2012 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.


from autopilot.testcase import AutopilotTestCase

from subprocess import Popen, call
from testtools.matchers import Equals, LessThan
from threading import Thread
from time import sleep, time

class BamfEmulatorTests(AutopilotTestCase):

    def test_wait_for_app_running_works(self):
        def start_gedit():
            sleep(2)
            Popen(['gedit'])

        t = Thread(target=start_gedit())
        t.start()
        ret = self.bamf.wait_until_application_is_running('gedit.desktop', 10)
        t.join()
        self.assertTrue(ret)
        call(['killall', 'gedit'])

    def test_wait_for_app_running_times_out_correctly(self):
        call(['killall', 'gedit'])
        start = time()
        ret = self.bamf.wait_until_application_is_running('gedit.desktop', 5)
        end = time()
        self.assertThat(abs(end - start - 5.0), LessThan(1))
        self.assertThat(ret, Equals(False))


