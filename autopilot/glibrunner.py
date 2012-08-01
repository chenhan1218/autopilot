# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2012 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.

from __future__ import absolute_import

import sys
import dbus
from dbus.mainloop.glib import DBusGMainLoop
import glib
import testtools
import threading

glib.threads_init()
dbus.mainloop.glib.threads_init()


# Turning run_in_glib_loop into a decorator is left as an exercise for the
# reader.
def run_in_glib_loop(function, *args, **kwargs):
    # log.info("Running: %r with args: %r and kwargs: %r", function, args, kwargs)
    loop = glib.MainLoop()
    # XXX: I think this has re-entrancy problems.  There is parallel code in
    # testtools somewhere (spinner.py or deferredruntest.py)
    result = []
    errors = []

    # This function is run in a worker thread. The GLib main loop is guaranteed to
    # be started before this function is run.
    class ThreadTest(threading.Thread):
        def __init__(self, loop):
            super(ThreadTest, self).__init__()
            self.loop = loop

        def run(self):
            DBusGMainLoop(set_as_default=True)
            try:
                # import pdb; pdb.set_trace()
                result.append(function(*args, **kwargs))
            except:
                errors.append(sys.exc_info())
                # XXX: Not sure if this is needed / desired
                raise
            finally:
                self.loop.quit()

    thread = ThreadTest(loop)
    # Calling thread.start directly here creates a possible race condition. We
    # need to be assured that the glib main loop has started by the time the test
    # is running, so we start the thread from the main loop itself. This waits
    # 10 mS - it could possibly be set to 0.
    glib.timeout_add(10, thread.start)
    loop.run()


    thread.join()
    if thread.is_alive():
        raise RuntimeError("Test %r did not exit after 120 seconds." % function)

    # assert loop.is_running() == False, "Loop should not be running after thread has quit!"

    if errors:
        raise errors[0]
    return True


class GlibRunner(testtools.RunTest):

    # This implementation runs setUp, the test and tearDown in one event
    # loop. Maybe not what's needed.

    def _run_core(self):
        run_in_glib_loop(super(GlibRunner, self)._run_core)
