``emulators`` - Backwards compatibility for autopilot v1.2
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++


.. module autopilot.emulators
   :synopsis: Backwards compatibility module to provide the 'emulators' namespace.


The emulators module exists for backwards compatibility only.

This module exists to make it easier to upgrade from autopilot v1.2 to v1.3 by
providing the old 'emulators' namespace. However, it's a bad idea to rely on this
module continuing to exist. It contains several sub-modules:

 * :mod:`autopilot.display`
 * :mod:`autopilot.clipboard`
 * :mod:`autopilot.dbus_handler`
 * :mod:`autopilot.ibus`
 * :mod:`autopilot.input`

