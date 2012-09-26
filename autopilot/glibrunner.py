# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2012 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.

from __future__ import absolute_import

import testtools

try:
    import faulthandler
    faulthandler.enable()
except:
    pass


__all__ = [
    'AutopilotTestRunner',
    ]

class AutopilotTestRunner(testtools.RunTest):
    pass

