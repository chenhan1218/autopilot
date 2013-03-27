# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2013 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.

"Platform identification utilities for Autopilot."


class Platform(object):
    """The Platform class encapsulates details relevant to the current platform.

    Test authors should not instantiate this class directly. Instead, use the
    create method to create an instance of the Platform class.

    """

    @property
    def model(self):
        """Get the model name of the current platform.

        For desktop / laptop installations, this will return "Desktop".
        Otherwise, the current hardware model will be returned. For example:

        >>> Platform.create().model
        ... "Galaxy Nexus"

        """

    @property
    def image_codename(self):
        """Get the image codename.

        For desktop / laptop installations this will return "Desktop".
        Otherwise, the codename of the image that was installed will be
        returned. FOr example:

        >>> Platform.create().image_codename
        ... "maguro"

        """
