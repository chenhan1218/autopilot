# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2013 Canonical
# Author: Christopher Lee
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.

from collections import OrderedDict

from autopilot.utilities import _pick_variant, get_debug_logger


class ProcessManager(object):

    """A simple process manager class.

    The process manager is used to handle processes, windows and applications.
    This class should not be instantiated directly however. To get an instance
    of the keyboard class, call :py:meth:`create` instead.

    """

    @staticmethod
    def create(preferred_variant=""):
        """Get an instance of the :py:class:`ProcessManager` class.

        :param preferred_variant: A string containing a hint as to which variant you
            would like. However, this hint can be ignored - autopilot will prefer to
            return a keyboard variant other than the one requested, rather than fail
            to return anything at all.
        :raises: a RuntimeError will be raised if autopilot cannot instantate any of
            the possible backends.
        """
        def get_bamf_pm():
            from autopilot.emulators.processmanager._bamf import ProcessManager
            return ProcessManager()

        def get_upa_pm():
            from autopilot.emulators.processmanager._upa import ProcessManager
            return ProcessManager()

        variants = OrderedDict()
        variants['BAMF'] = get_bamf_pm
        variants['UPA'] = get_upa_pm
        return _pick_variant(variants, preferred_variant)

    def get_running_applications(self, user_visible_only=True):
        """Get a list of the currently running applications.

        If user_visible_only is True (the default), only applications
        visible to the user in the switcher will be returned.

        """
        raise NotImplementedError("You cannot use this class directly.")

    def get_running_applications_by_desktop_file(self, desktop_file):
        """Return a list of applications that have the desktop file *desktop_file*.

        This method will return an empty list if no applications
        are found with the specified desktop file.

        """
        raise NotImplementedError("You cannot use this class directly.")

    def get_open_windows(self, user_visible_only=True):
        """Get a list of currently open windows.

        If *user_visible_only* is True (the default), only applications visible
        to the user in the switcher will be returned.

        The result is sorted to be in stacking order.

        """
        raise NotImplementedError("You cannot use this class directly.")

    def wait_until_application_is_running(self, desktop_file, timeout):
        """Wait until a given application is running.

        :param string desktop_file: The name of the application desktop file.
        :param integer timeout: The maximum time to wait, in seconds. *If set to
         something less than 0, this method will wait forever.*

        :return: true once the application is found, or false if the application
         was not found until the timeout was reached.
        """
        raise NotImplementedError("You cannot use this class directly.")

    # Veebers: this will need to change a bit as it is expected to return a Gobject.
    def launch_application(self, desktop_file, files=[], wait=True):
        """Launch an application by specifying a desktop file.

        :param files: List of files to pass to the application. *Not all
         apps support this.*
        :type files: List of strings

        .. note:: If `wait` is True, this method will wait up to 10 seconds for
         the application to appear.

        :raises: **TypeError** on invalid *files* parameter.
        :return: The Gobject process object.
        """
        raise NotImplementedError("You cannot use this class directly.")


class Application(object):
    @property
    def desktop_file(self):
        """Get the application desktop file.

        This returns just the filename, not the full path.
        If the application no longer exists, this returns an empty string.
        """
        raise NotImplementedError("You cannot use this class directly.")

    @property
    def name(self):
        """Get the application name.

        .. note:: This may change according to the current locale. If you want a
         unique string to match applications against, use desktop_file instead.

        """
        raise NotImplementedError("You cannot use this class directly.")

    @property
    def icon(self):
        """Get the application icon.

        :return: The name of the icon.

        """
        raise NotImplementedError("You cannot use this class directly.")

    @property
    def is_active(self):
        """Is the application active (i.e. has keyboard focus)?"""
        raise NotImplementedError("You cannot use this class directly.")

    @property
    def is_urgent(self):
        """Is the application currently signalling urgency?"""
        raise NotImplementedError("You cannot use this class directly.")

    @property
    def user_visible(self):
        """Is this application visible to the user?

        .. note:: Some applications (such as the panel) are hidden to the user
         but may still be returned.

        """
        raise NotImplementedError("You cannot use this class directly.")

    def get_windows(self):
        """Get a list of the application windows."""
        raise NotImplementedError("You cannot use this class directly.")



class Window(object):
    # Veebers:
    #   The use of x_id and x_win.
    # x_id: Perhaps just a (unique) id that the bamf backend uses the x_id for
    # and the UPA uses (something)
    # x_win: Maybe wrap the immediate requirements in a property
    # (i.e. get_wm_state).
    @property
    def x_id(self):
        """Get the X11 Window Id."""
        raise NotImplementedError("You cannot use this class directly.")

    @property
    def x_win(self):
        """Get the X11 window object of the underlying window."""
        raise NotImplementedError("You cannot use this class directly.")

    # veebers: example from above comment.
    @property
    def get_wm_state(self):
        """Get the state of the underlying window."""
        raise NotImplementedError("You cannot use this class directly.")

    @property
    def name(self):
        """Get the window name.

        .. note:: This may change according to the current locale. If you want a
         unique string to match windows against, use the x_id instead.

        """
        raise NotImplementedError("You cannot use this class directly.")

    @property
    def title(self):
        """Get the window title.

        This may be different from the application name.

        .. note:: This may change depending on the current locale.

        """
        raise NotImplementedError("You cannot use this class directly.")

    @property
    def geometry(self):
        """Get the geometry for this window.

        :return: Tuple containing (x, y, width, height).

        """
        raise NotImplementedError("You cannot use this class directly.")

    @property
    def is_maximized(self):
        """Is the window maximized?

        Maximized in this case means both maximized vertically and
        horizontally. If a window is only maximized in one direction it is not
        considered maximized.

        """
        raise NotImplementedError("You cannot use this class directly.")

    @property
    def application(self):
        """Get the application that owns this window.

        This method may return None if the window does not have an associated
        application. The 'desktop' window is one such example.

        """
        raise NotImplementedError("You cannot use this class directly.")

    @property
    def user_visible(self):
        """Is this window visible to the user in the switcher?"""
        raise NotImplementedError("You cannot use this class directly.")

    @property
    def is_hidden(self):
        """Is this window hidden?

        Windows are hidden when the 'Show Desktop' mode is activated.

        """
        raise NotImplementedError("You cannot use this class directly.")

    @property
    def is_focused(self):
        """Is this window focused?"""
        raise NotImplementedError("You cannot use this class directly.")

    @property
    def is_valid(self):
        """Is this window object valid?

        Invalid windows are caused by windows closing during the construction of
        this object instance.

        """
        raise NotImplementedError("You cannot use this class directly.")

    @property
    def monitor(self):
        """Returns the monitor to which the windows belongs to"""
        raise NotImplementedError("You cannot use this class directly.")

    @property
    def closed(self):
        """Returns True if the window has been closed"""
        raise NotImplementedError("You cannot use this class directly.")

    def close(self):
        """Close the window."""
        raise NotImplementedError("You cannot use this class directly.")

    def set_focus(self):
        raise NotImplementedError("You cannot use this class directly.")
