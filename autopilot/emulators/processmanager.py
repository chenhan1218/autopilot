# Copyright 2012 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.

"""The processmanager module contains utilities for starting, stopping, and
generally managing processes during a test."""

from __future__ import absolute_import
import logging
from time import sleep

from autopilot.emulators.bamf import Bamf


logger = logging.getLogger(__name__)

class ProcessManager(object):
    """Manage Processes during a test cycle."""

    def __init__(self):
        self._bamf = Bamf()
        self.snapshot = None

    def snapshot_running_apps(self):
        """Make a list of all the running applications, and store it.

        The stored list can later be used to detect any applications that have
        been launched during a test and not shut down.

        You may only call this method once before calling
        compare_system_with_snapshot. Calling this method multiple times will
        cause a RuntimeError to be raised.
        """

        if self.snapshot:
            raise RuntimeError("You may only call snapshot_running_apps once \
before calling compare_system_with_snapshot.")

        self.snapshot = self._bamf.get_running_applications()

    def compare_system_with_snapshot(self):
        """Compare the currently running application with the last snapshot.

        This method will raise an AssertionError if there are any new applications
        currently running that were not running when the snapshot was taken.

        This method should typically be called at the every end of a test.
        """
        if self.snapshot is None:
            raise RuntimeError("No snapshot to match against.")

        new_apps = []
        for i in range(10):
            current_apps = self._bamf.get_running_applications()
            new_apps = filter(lambda i: i not in self.snapshot, current_apps)
            if not new_apps:
                self.snapshot = None
                return
            sleep(1)
        self.snapshot = None
        raise AssertionError("The following apps were started during the test and not closed: %r", new_apps)


