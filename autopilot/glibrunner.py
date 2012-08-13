# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2012 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.

from __future__ import absolute_import

import dbus.glib

import glib
import testtools
# import threading
try:
    import faulthandler
    faulthandler.enable()
except:
    pass

# Pokemon functions: gotta call 'em all!
# If you don't, random glib/gobject/gtk functions will hang...
glib.threads_init()
dbus.glib.threads_init()


# def run_in_glib_loop(function, *args, **kwargs):
#     try:
#         loop = glib.MainLoop()
#         # thread = WorkerThread(loop, lambda: )
#         # thread = threading.Thread(target=loop.run)
#         # thread.start()
#         result = function(*args, **kwargs)
#     except Exception as e:
#         return e
#     finally:
#         # glib.idle_add(loop.quit)
#         # thread.join(5)

#     # if thread.is_alive():
#     #     raise RuntimeError("Test %r did not exit after 5 seconds." % function)

#     return result


class GlibRunner(testtools.RunTest):
    pass

    # This implementation runs setUp, the test and tearDown in one event
    # loop. Maybe not what's needed.

    # def _run_core(self):
    #     run_in_glib_loop(super(GlibRunner, self)._run_core)
