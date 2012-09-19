# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2012 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.

from __future__ import absolute_import


# this can be set to True, in which case tests will be recorded.
video_recording_enabled = False

# this is where videos will be put after being encoded.
video_record_directory = "/tmp/autopilot"

# if set to true, autopilot will output all pythong logging to stderr
__log_verbose = False

def get_log_verbose():
    """Returns true if the user asked for verbose logging."""
    global __log_verbose
    return __log_verbose


def set_log_verbose(verbose):
    """Set whether or not we should log verbosely."""
    if type(verbose) is not bool:
        raise TypeError("Verbose flag must be a boolean.")
    global __log_verbose
    __log_verbose = verbose
