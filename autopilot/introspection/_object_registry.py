# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2014 Canonical
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

"""Object registry.

This is an internal module, and is not supposed to be used directly.

This module contains the object registry, which keeps track to the various
classes we use when creating proxy classes. The object registry allows test
authors to write their own classes to be used instead of the generic one that
autopilot creates.

"""

from uuid import uuid4

from autopilot.introspection._xpathselect import get_classname_from_path
from autopilot.utilities import get_debug_logger
from contextlib import contextmanager

_object_registry = {}


class IntrospectableObjectMetaclass(type):
    """Metaclass to insert appropriate classes into the object registry."""

    def __new__(cls, classname, bases, classdict):
        """Create a new proxy class, possibly adding it to the object registry.

        Test authors may derive a class from DBusIntrospectionObject or the
        CustomEmulatorBase alias and use this as their 'emulator base'. This
        class will be given a unique '_id' attribute. That attribute is the
        first level index into the object registry. It's used so we can have
        custom proxy classes for more than one process at the same time and
        avoid clashes in the dictionary.
        """

        # ignore the classes at the top of the inheritance heirarchy (i.e.- the
        # ones that we control.)
        if classname not in (
            'ApplicationProxyObject',
            'CustomEmulatorBase',
            'DBusIntrospectionObject',
            'DBusIntrospectionObjectBase',
        ):
            # also ignore classes that derive from a class that already has the
            # _id attribute set.
            have_id = any([hasattr(b, '_id') for b in bases])
            if not have_id:
                # Add the '_id' attribute as a class attr:
                classdict['_id'] = uuid4()

        # make the object. Nothing special here.
        class_object = type.__new__(cls, classname, bases, classdict)

        # If the newly made object has an id, add it to the object registry.
        if getattr(class_object, '_id', None) is not None:
            if class_object._id in _object_registry:
                _object_registry[class_object._id][classname] = class_object
            else:
                _object_registry[class_object._id] = {classname: class_object}
        # in all cases, return the class unchanged.
        return class_object


DBusIntrospectionObjectBase = IntrospectableObjectMetaclass(
    'DBusIntrospectionObjectBase',
    (object,),
    {}
)


def _get_proxy_object_class(object_id, default_class, path, state):
    """Return a custom proxy class, from the object registry or the default.

    This function first inspects the object registry using the object_id passed
    in. The object_id will be unique to all custom proxy classes for the same
    application.

    If that fails, we create a class on the fly based on the default class.

    :param object_id: The _id attribute of the class doing the lookup. This is
        used to index into the object registry to retrieve the dict of proxy
        classes to try.
    :param default_class: default class to use if nothing in dict matches
    :param path: dbus path
    :param state: dbus state
    :returns: appropriate custom proxy class
    :raises ValueError: if more than one class in the dict matches

    """
    class_type = _try_custom_proxy_classes(object_id, path, state)
    if class_type:
        return class_type
    return _get_default_proxy_class(default_class,
                                    get_classname_from_path(path))


def _try_custom_proxy_classes(object_id, path, state):
    """Identify which custom proxy class matches the dbus path and state.

    If more than one class in proxy_class_dict matches, raise an exception.
    :param proxy_class_dict: dict of proxy classes to try
    :param path: dbus path
    :param state: dbus state dict
    :returns: matching custom proxy class
    :raises ValueError: if more than one class matches

    """
    proxy_class_dict = _object_registry[object_id]
    possible_classes = [c for c in proxy_class_dict.values() if
                        c.validate_dbus_object(path, state)]
    if len(possible_classes) > 1:
        raise ValueError(
            'More than one custom proxy class matches this object: '
            'Matching classes are: %s. State is %s.  Path is %s.'
            ','.join([repr(c) for c in possible_classes]),
            repr(state),
            path)
    if len(possible_classes) == 1:
        return possible_classes[0]
    return None


def _get_default_proxy_class(default_class, name):
    """Return a custom proxy object class of the default or a base class.

    We want the object to inherit from the class that is set as the emulator
    base class, not the class that is doing the selecting (which will be the
    'default_class' parameter).

    :param default_class: default class to use if no bases match
    :param name: name of new class
    :returns: custom proxy object class

    """
    get_debug_logger().warning(
        "Generating introspection instance for type '%s' based on generic "
        "class.", name)
    for base in default_class.__bases__:
        if hasattr(base, '_id'):
            base_class = base
            break
    else:
        base_class = default_class
    return type(str(name), (base_class,), {})


@contextmanager
def patch_registry(new_registry):
    """A utility context manager that allows us to patch the object registry.

    Within the scope of the context manager, the object registry will be set
    to the 'new_registry' value passed in. When the scope exits, the old object
    registry will be restored.

    """
    global _object_registry
    old_registry = _object_registry
    _object_registry = new_registry
    try:
        yield
    except Exception:
        _object_registry = old_registry
        raise
