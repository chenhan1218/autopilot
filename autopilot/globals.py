# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2012 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.

from __future__ import absolute_import

from compizconfig import Context

global_context = Context()

# this can be set to True, in which case tests will be recorded.
video_recording_enabled = False

# this is where videos will be put after being encoded.
video_record_directory = "/tmp/autopilot"
