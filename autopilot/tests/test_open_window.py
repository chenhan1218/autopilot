# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2012 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.

from __future__ import absolute_import

from testtools.matchers import Equals

from autopilot.testcase import AutopilotTestCase
from autopilot.process import ProcessManager
import logging
logger = logging.getLogger(__name__)


class OpenWindowTests(AutopilotTestCase):

    scenarios = [(k, {'app_name': k}) for k in ProcessManager.KNOWN_APPS.iterkeys()]

    def test_open_window(self):
        """self.start_app_window must open a new window of the given app."""
        existing_apps = self.process_manager.get_app_instances(self.app_name)
        old_wins = []
        for app in existing_apps:
            old_wins.extend(app.get_windows())
        logger.debug("Old windows: %r", old_wins)

        win = self.process_manager.start_app_window(self.app_name)
        logger.debug("New window: %r", win)
        is_new = win.x_id not in [w.x_id for w in old_wins]
        self.assertThat(is_new, Equals(True))
