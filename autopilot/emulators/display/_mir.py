import logging

from autopilot.emulators.input import Display as DisplayBase

logger = logging.getLogger(__name__)

class Display(DisplayBase):
    """The base class/inteface for the display devices"""

    class BlacklistedDriverError(RuntimeError):
        """Cannot set primary monitor when running drivers listed in the driver blacklist."""

    def get_num_screens(self):
        """Get the number of screens attached to the PC."""
        return 1

    def get_primary_screen(self):
        """Returns an integer of which screen is considered the primary"""
        return 0

    def get_screen_width(self):
        return 1

    def get_screen_height(self):
        return 1

    def get_screen_geometry(self, screen_number):
        """Get the geometry for a particular screen.

        :return: Tuple containing (x, y, width, height).

        """
        return(1, 1, 1, 1)

    def is_rect_on_screen(self, screen_number, rect):
        """Returns True if *rect* is **entirely** on the specified screen, with no overlap."""
        return True

    def is_point_on_screen(self, screen_number, point):
        """Returns True if *point* is on the specified screen.

        *point* must be an iterable type with two elements: (x, y)

        """
        return True

    def is_point_on_any_screen(self, point):
        """Returns true if *point* is on any currently configured screen."""
        return True

    #should this be here or else where?
    def move_mouse_to_screen(self, screen_number):
        """Move the mouse to the center of the specified screen."""
        pass

    # This should be moved elsewhere.
    def drag_window_to_screen(self, window, screen):
        """Drags *window* to *screen*

        :param BamfWindow window: The window to drag
        :param integer screen: The monitor to drag the *window* to
        :raises: **TypeError** if *window* is not a BamfWindow

        """
        pass
