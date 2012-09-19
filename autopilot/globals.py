# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2012 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.

from __future__ import absolute_import

# this can be set to True, in which case tests will be recorded.
__video_recording_enabled = False

# this is where videos will be put after being encoded.
__video_record_directory = "/tmp/autopilot"

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


def configure_video_recording(enable_recording, record_dir):
    """Configure video logging.

    enable_recording is a boolean, and enables or disables recording globally.
    record_dir is a string that specifies where videos will be stored.

    """
    if type(enable_recording) is not bool:
        raise TypeError("enable_recording must be a boolean.")
    if not isinstance(record_dir, basestring):
        raise TypeError("record_dir must be a string.")

    global __video_recording_enabled
    global __video_record_directory

    __video_recording_enabled = enable_recording
    __video_record_directory = record_dir


def get_video_recording_enabled():
    global __video_recording_enabled
    return __video_recording_enabled


def get_video_record_directory():
    global __video_record_directory
    return __video_record_directory
