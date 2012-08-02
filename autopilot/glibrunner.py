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
# import dbus
# from dbus.mainloop.glib import DBusGMainLoop
import glib
# import gtk
# import gtk.gdk
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
# dbus.mainloop.glib.threads_init()
# gtk.gdk.threads_init()

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
                # _print("Thread '%i': mainloop not yet running, backing off" % (self.ident, ))
                time.sleep(0.5)
                continue
            # from autopilot.emulators.bamf import Bamf
            # print Bamf().get_running_applications()
            self.result = self.worker()
        except:
            self.errors.append(sys.exc_info())
            # XXX: Not sure if this is needed / desired
            raise
        finally:
            # print "Quitting main loop now."
            glib.idle_add(self.loop.quit)
            # gtk.mainquit()
            print "Done"


def run_in_glib_loop(function, *args, **kwargs):
    # set_main_loop()
    loop = glib.MainLoop()
    # dbus.set_default_main_loop(dbus_loop)

    thread = WorkerThread(loop, lambda: function(*args, **kwargs))
    thread.start()
    loop.run()
    print "Loop finished."
    thread.join()
    # print "Thread joined"
    if thread.is_alive():
        raise RuntimeError("Test %r did not exit after 120 seconds." % function)

    if thread.errors:
        raise thread.errors[0]
    return thread.result


class GlibRunner(testtools.RunTest):

    # This implementation runs setUp, the test and tearDown in one event
    # loop. Maybe not what's needed.

    def _run_core(self):
        run_in_glib_loop(super(GlibRunner, self)._run_core)
