# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2012 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.


from autopilot.testcase import AutopilotTestCase

from subprocess import Popen, call
from time import sleep
from threading import Thread

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


