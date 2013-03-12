import logging

logger = logging.getLogger(__name__)

class Display:
    """The base class/inteface for the display devices"""

    class BlacklistedDriverError(RuntimeError):
        """Cannot set primary monitor when running drivers listed in the driver blacklist."""

    def get_num_monitors(self):
        """Get the number of monitors attached to the PC."""
        return 1

    def get_primary_monitor(self):
        """Returns an integer of which monitor is considered the primary"""
        return 0

    def get_screen_width(self):
        return 1

    def get_screen_height(self):
        return 1

    def get_monitor_geometry(self, monitor_number):
        """Get the geometry for a particular monitor.

        :return: Tuple containing (x, y, width, height).

        """
        return(1, 1, 1, 1)

    def is_rect_on_monitor(self, monitor_number, rect):
        """Returns True if *rect* is **entirely** on the specified monitor, with no overlap."""
        return True

    def is_point_on_monitor(self, monitor_number, point):
        """Returns True if *point* is on the specified monitor.

        *point* must be an iterable type with two elements: (x, y)

        """
        return True

    def is_point_on_any_monitor(self, point):
        """Returns true if *point* is on any currently configured monitor."""
        return True

    #should this be here or else where?
    def move_mouse_to_monitor(self, monitor_number):
        """Move the mouse to the center of the specified monitor."""
        pass

    # This should be moved elsewhere.
    def drag_window_to_monitor(self, window, monitor):
        """Drags *window* to *monitor*

        :param BamfWindow window: The window to drag
        :param integer monitor: The monitor to drag the *window* to
        :raises: **TypeError** if *window* is not a BamfWindow

        """
        pass
