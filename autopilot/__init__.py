# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2012 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.


class BackendException(RuntimeError):

    """An error occured while trying to initialise an autopilot backend."""

    def __init__(self, original_exception):
        super(BackendException, self).__init__(
            "Error while initialising backend. Original exception was: " \
            + original_exception.message
            )
        self.original_exception = original_exception
