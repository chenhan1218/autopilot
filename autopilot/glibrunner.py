# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2012 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.

from __future__ import absolute_import

import dbus.glib

import sys
import glib
import testtools
import time
import threading
try:
    import faulthandler
    faulthandler.enable()
except:
    pass

# Pokemon functions: gotta call 'em all!
# If you don't, random glib/gobject/gtk functions will hang...
glib.threads_init()
dbus.glib.threads_init()

class WorkerThread(threading.Thread):
    def __init__(self, loop, worker):
        super(WorkerThread, self).__init__()
        self.loop = loop
        self.worker = worker
        self.errors = []
        self.result = None

    def run(self):
        try:
            while self.loop.is_running() is False:
                time.sleep(0.5)

            self.result = self.worker()
        except:
            self.errors.append(sys.exc_info())
        finally:
            glib.idle_add(self.loop.quit)


def run_in_glib_loop(function, *args, **kwargs):
    try:
        loop = glib.MainLoop()
        thread = WorkerThread(loop, lambda: function(*args, **kwargs))
        thread.start()
        loop.run()
        thread.join(5 * 60)
    except Exception as e:
        return e

    if thread.is_alive():
        raise RuntimeError("Test %r did not exit after 5 minutes." % function)

    if thread.errors:
        raise thread.errors[0]
    return thread.result


class GlibRunner(testtools.RunTest):

    # This implementation runs setUp, the test and tearDown in one event
    # loop. Maybe not what's needed.

    def _run_core(self):
        run_in_glib_loop(super(GlibRunner, self)._run_core)
