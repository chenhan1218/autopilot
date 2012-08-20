# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2012 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.

from __future__ import absolute_import

from testtools.matchers import Equals, raises, Not

from autopilot.testcase import AutopilotTestCase
import logging
logger = logging.getLogger(__name__)



class CompizConfigOptionTests(AutopilotTestCase):

    def test_set_option_raises_KeyError_on_bad_plugin_name(self):
        """set_compiz_option must raise KeyError when given a bad plugin name."""
        fn = lambda: self.set_compiz_option('rubbishpluginname', 'rubbishsettingname', 'settingvalue')
        self.assertThat(fn, raises(KeyError("Compiz plugin 'rubbishpluginname' does not exist.")))

    def test_set_option_raises_KeyError_on_bad_setting_name(self):
        """set_compiz_option must raise KeyError when called with a bad setting name."""
        fn = lambda: self.set_compiz_option('core', 'rubbishsettingname', 'settingvalue')
        self.assertThat(fn, raises(KeyError("Compiz setting 'rubbishsettingname' does not exist in plugin 'core'.")))


