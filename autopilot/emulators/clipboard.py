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

"""A collection of functions relating to the X11clipboards."""


import glib
from Queue import Queue
import gtk


def get_clipboard_contents():
    """Get the contents of the clipboard.

    This function returns the text copied to the 'CLIPBOARD' clipboard. Text can
    be added to this clipbaord using Ctrl+C.

    You *must* use this function rather than using the Gtk Clipboard class, since
    the Clipboard class cannot be used from a separate thread.

    """

    def get_cb_text(q):
        cb = gtk.Clipboard(selection="CLIPBOARD")
        q.put(cb.wait_for_text())
        return False

    queue = Queue()
    id = glib.idle_add(get_cb_text, queue)
    data = queue.get()
    glib.source_remove(id)
    return data
