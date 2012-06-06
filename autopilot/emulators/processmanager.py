# Copyright 2011 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.

"""The processmanager module contains utilities for starting, stopping, and
generally managing processes during a test."""

from __future__ import absolute_import

import os
import logging
from subprocess import check_output, call, CalledProcessError

from autopilot.emulators.bamf import Bamf


logger = logging.getLogger(__name__)

class ProcessManager(object):
    """Manage Processes during a test cycle."""

    KNOWN_APPS = {
        'Character Map' : {
            'desktop-file': 'gucharmap.desktop',
            'process-name': 'gucharmap',
            },
        'Calculator' : {
            'desktop-file': 'gcalctool.desktop',
            'process-name': 'gcalctool',
            },
        'Mahjongg' : {
            'desktop-file': 'mahjongg.desktop',
            'process-name': 'mahjongg',
            },
        'Remmina' : {
            'desktop-file': 'remmina.desktop',
            'process-name': 'remmina',
            },
        'System Settings' : {
            'desktop-file': 'gnome-control-center.desktop',
            'process-name': 'gnome-control-center',
            },
        'Text Editor' : {
            'desktop-file': 'gedit.desktop',
            'process-name': 'gedit',
            },
        }

    def __init__(self):
        self._bamf = Bamf()

    def start_test(self):
        """Call this before your test starts."""

    def end_test(self):
        """Call this after your test ends."""

    def start_app(self, app_name, files=[], locale=None):
        """Start one of the known apps, and kill it on tear down.

        If files is specified, start the application with the specified files.
        If locale is specified, the locale will be set when the application is launched.

        The method returns the BamfApplication instance.

        """
        if locale:
            os.putenv("LC_ALL", locale)
            self.addCleanup(os.unsetenv, "LC_ALL")
            logger.info("Starting application '%s' with files %r in locale %s", app_name, files, locale)
        else:
            logger.info("Starting application '%s' with files %r", app_name, files)

        app = self.KNOWN_APPS[app_name]
        self.bamf.launch_application(app['desktop-file'], files)
        apps = self.bamf.get_running_applications_by_desktop_file(app['desktop-file'])
        self.addCleanup(self.close_all_app, app_name)
        self.assertThat(len(apps), Equals(1))
        return apps[0]

    def close_all_app(self, app_name):
        """Close all instances of the app_name."""
        app = self.KNOWN_APPS[app_name]
        try:
            pids = check_output(["pidof", app['process-name']]).split()
            if len(pids):
                call(["kill"] + pids)
        except CalledProcessError:
            logger.warning("Tried to close applicaton '%s' but it wasn't running.", app_name)

    def get_app_instances(self, app_name):
        """Get BamfApplication instances for app_name."""
        desktop_file = self.KNOWN_APPS[app_name]['desktop-file']
        return self.bamf.get_running_applications_by_desktop_file(desktop_file)

    def app_is_running(self, app_name):
        """Returns true if an instance of the application is running."""
        apps = self.get_app_instances(app_name)
        return len(apps) > 0
