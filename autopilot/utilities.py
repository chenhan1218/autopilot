# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2012 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.
#
# This script is designed to run unity in a test drive manner. It will drive
# X and test the GL calls that Unity makes, so that we can easily find out if
# we are triggering graphics driver/X bugs.

"""Various utility classes and functions that are useful when running tests."""

from __future__ import absolute_import

import logging
import os
import time
from Xlib import X, display, protocol

_display = None

def get_display():
    """Get a Xlib display object. Creating the display prints garbage to stdout."""
    global _display
    if _display is None:
        with Silence():
            _display = display.Display()
    return _display



def make_window_skip_taskbar(window, set_flag=True):
    """Set the skip-taskbar kint on an X11 window.

    'window' should be an Xlib window object.
    set_flag should be 'True' to set the flag, 'False' to clear it.

    """
    state = get_display().get_atom('_NET_WM_STATE_SKIP_TASKBAR', 1)
    action = int(set_flag)
    if action == 0:
        print "Clearing flag"
    elif action == 1:
        print "Setting flag"
    _setProperty('_NET_WM_STATE', [action, state, 0, 1], window)
    get_display().sync()


def get_desktop_viewport():
    """Get the x,y coordinates for the current desktop viewport top-left corner."""
    return _getProperty('_NET_DESKTOP_VIEWPORT')


def get_desktop_geometry():
    """Get the full width and height of the desktop, including all the viewports."""
    return _getProperty('_NET_DESKTOP_GEOMETRY')


def _setProperty(_type, data, win=None, mask=None):
    """ Send a ClientMessage event to a window"""
    if not win:
        win = get_display().screen().root
    if type(data) is str:
        dataSize = 8
    else:
        # data length must be 5 - pad with 0's if it's short, truncate otherwise.
        data = (data + [0] * (5 - len(data)))[:5]
        dataSize = 32

    ev = protocol.event.ClientMessage(window=win,
        client_type=get_display().get_atom(_type),
        data=(dataSize, data))

    if not mask:
        mask = (X.SubstructureRedirectMask | X.SubstructureNotifyMask)
    get_display().screen().root.send_event(ev, event_mask=mask)


def _getProperty(_type, win=None):
    if not win:
        win = get_display().screen().root
    atom = win.get_full_property(get_display().get_atom(_type), X.AnyPropertyType)
    if atom: return atom.value


def get_compiz_setting(plugin_name, setting_name):
    """Get a compiz setting object.

    'plugin_name' is the name of the plugin (e.g. 'core' or 'unityshell')
    'setting_name' is the name of the setting (e.g. 'alt_tab_timeout')

    This function will raise KeyError if the plugin or setting named does not
    exist.

    """
    # circular dependancy:
    from autopilot.compizconfig import get_setting
    return get_setting(plugin_name, setting_name)


def get_compiz_option(plugin_name, setting_name):
    """Get a compiz setting value.

    This is the same as calling:

    >>> get_compiz_setting(plugin_name, setting_name).Value

    """
    return get_compiz_setting(plugin_name, setting_name).Value


# Taken from http://code.activestate.com/recipes/577564-context-manager-for-low-level-redirection-of-stdou/
# licensed under the MIT license.
class Silence(object):
    """Context manager which uses low-level file descriptors to suppress
    output to stdout/stderr, optionally redirecting to the named file(s).

    >>> with Silence():
    ...     # do something that prints to stdout or stderr:
    ...

    """
    def __init__(self, stdout=os.devnull, stderr=os.devnull, mode='w'):
        self.outfiles = stdout, stderr
        self.combine = (stdout == stderr)
        self.mode = mode

    def __enter__(self):
        import sys
        self.sys = sys
        # save previous stdout/stderr
        self.saved_streams = saved_streams = sys.__stdout__, sys.__stderr__
        self.fds = fds = [s.fileno() for s in saved_streams]
        self.saved_fds = map(os.dup, fds)
        # flush any pending output
        for s in saved_streams: s.flush()

        # open surrogate files
        if self.combine:
            null_streams = [open(self.outfiles[0], self.mode, 0)] * 2
            if self.outfiles[0] != os.devnull:
                # disable buffering so output is merged immediately
                sys.stdout, sys.stderr = map(os.fdopen, fds, ['w']*2, [0]*2)
        else: null_streams = [open(f, self.mode, 0) for f in self.outfiles]
        self.null_fds = null_fds = [s.fileno() for s in null_streams]
        self.null_streams = null_streams

        # overwrite file objects and low-level file descriptors
        map(os.dup2, null_fds, fds)

    def __exit__(self, *args):
        sys = self.sys
        # flush any pending output
        for s in self.saved_streams: s.flush()
        # restore original streams and file descriptors
        map(os.dup2, self.saved_fds, self.fds)
        sys.stdout, sys.stderr = self.saved_streams
        # clean up
        for s in self.null_streams: s.close()
        for fd in self.saved_fds: os.close(fd)
        return False


class LogFormatter(logging.Formatter):

    # this is the default format to use for logging
    log_format = "%(asctime)s %(levelname)s %(module)s:%(lineno)d - %(message)s"

    def __init__(self):
        super(LogFormatter, self).__init__(self.log_format)

    def formatTime(self, record, datefmt=None):
        ct = self.converter(record.created)
        if datefmt:
            s = time.strftime(datefmt, ct)
        else:
            t = time.strftime("%H:%M:%S", ct)
            s = "%s.%03d" % (t, record.msecs)
        return s
