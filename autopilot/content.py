# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2013 Canonical
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

"""Content objects and helpers for autopilot tests."""

import io

from testtools.content import content_from_stream


def follow_file(path, test_case, content_name=None):
    """Start monitoring a file.

    Use this convenience function to attach the contents of a file to a test.

    :param path: The path to the file on disk you want to monitor.
    :param test_case: An object that supports attaching details and cleanup
        actions (i.e.- has the ``addDetail`` and ``addCleanup`` methods).
    :param content_name: A name to give this content. If not specified, the
        file path will be used instead.
    """
    test_case.addCleanup(
        test_case.addDetail,
        content_from_stream(
            stream=io.open(path),
            seek_offset=0,
            seek_whence=io.SEEK_END,
        )
    )
