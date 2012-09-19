# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2012 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.

import os

from autopilot.introspection import ApplicationIntrospectionTestMixin


class GtkIntrospectionTestMixin(ApplicationIntrospectionTestMixin):
    """A mix-in class to make Gtk application introspection easier."""

    def prepare_environment(self, app_path, arguments):
        """Prepare the application, or environment to launch with autopilot-support.

        """
        modules = os.getenv('GTK_MODULES', '').split(':')
        if 'autopilot-gtk' not in modules:
            modules.append('autopilot-gtk')
            os.putenv('GTK_MODULES', ':'.join(modules))


        return app_path, arguments


