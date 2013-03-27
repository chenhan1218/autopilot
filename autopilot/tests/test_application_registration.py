# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2012 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.

from __future__ import absolute_import

from testtools import TestCase
from testtools.matchers import Equals, Not, raises, Contains


from autopilot.testcase import AutopilotTestCase


def safe_unregister_application(test_case_class, app_name):
    if app_name in test_case_class.KNOWN_APPS:
        test_case_class.unregister_known_application(app_name)

class ApplicationRegistrationTests(TestCase):

    def test_can_register_new_application(self):
        AutopilotTestCase.register_known_application(
            "NewApplicationName",
            "newapp.desktop",
            "newapp")
        self.addCleanup(safe_unregister_application,
            AutopilotTestCase,
            "NewApplicationName")

        app_details = AutopilotTestCase.KNOWN_APPS['NewApplicationName']

        self.assertThat(AutopilotTestCase.KNOWN_APPS, Contains("NewApplicationName"))
        self.assertTrue(type(app_details) is dict)
        self.assertThat(app_details, Contains('desktop-file'))
        self.assertThat(app_details, Contains('process-name'))
        self.assertThat(app_details['desktop-file'], Equals('newapp.desktop'))
        self.assertThat(app_details['process-name'], Equals('newapp'))

    def test_registering_app_twice_raises_KeyError(self):
        """Registering an application with the same app name as one that's
        already in the dictionary must raise KeyError and not change the
        dictionary.

        """
        AutopilotTestCase.register_known_application(
            "NewApplicationName",
            "newapp.desktop",
            "newapp")
        self.addCleanup(safe_unregister_application,
            AutopilotTestCase,
            "NewApplicationName")

        app_details = AutopilotTestCase.KNOWN_APPS['NewApplicationName']
        register_fn = lambda: AutopilotTestCase.register_known_application(
            "NewApplicationName",
            "newapp2.desktop",
            "newapp2")

        self.assertThat(register_fn, raises(
            KeyError("Application has been registered already")))
        self.assertThat(AutopilotTestCase.KNOWN_APPS, Contains("NewApplicationName"))
        self.assertTrue(type(app_details) is dict)
        self.assertThat(app_details, Contains('desktop-file'))
        self.assertThat(app_details, Contains('process-name'))
        self.assertThat(app_details['desktop-file'], Equals('newapp.desktop'))
        self.assertThat(app_details['process-name'], Equals('newapp'))

    def test_can_unregister_application(self):
        AutopilotTestCase.register_known_application(
            "NewApplicationName",
            "newapp.desktop",
            "newapp")
        self.addCleanup(safe_unregister_application,
            AutopilotTestCase,
            "NewApplicationName")

        AutopilotTestCase.unregister_known_application("NewApplicationName")

        self.assertThat(AutopilotTestCase.KNOWN_APPS,
            Not(Contains("NewApplicationName")))

    def test_unregistering_unknown_application_raises_KeyError(self):
        """Trying to unregister an application that is not already registered
        must raise a KeyError.

        """

        unregister_fn = lambda: AutopilotTestCase.unregister_known_application("FooBarBaz")

        self.assertThat(unregister_fn, raises(KeyError("Application has not been registered")))

