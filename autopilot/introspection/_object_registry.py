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

from autopilot.utilities import get_debug_logger

_object_registry = {}


class IntrospectableObjectMetaclass(type):
    """Metaclass to insert appropriate classes into the object registry."""

    def __new__(cls, classname, bases, classdict):
        """Add class name to type registry."""
        class_object = type.__new__(cls, classname, bases, classdict)
        if classname in (
            'ApplicationProxyObject',
            'CustomEmulatorBase',
            'DBusIntrospectionObject',
        ):
            return class_object

        if getattr(class_object, '_id', None) is not None:
            if class_object._id in _object_registry:
                _object_registry[class_object._id][classname] = class_object
            else:
                _object_registry[class_object._id] = {classname: class_object}
        return class_object


DBusIntrospectionObjectBase = IntrospectableObjectMetaclass(
    'DBusIntrospectionObjectBase',
    (object,),
    {}
)


class _CustomEmulatorMeta(IntrospectableObjectMetaclass):

    def __new__(cls, name, bases, d):
        # only consider classes derived from CustomEmulatorBase
        if name != 'CustomEmulatorBase':
            # and only if they don't already have an Id set.
            have_id = False
            for base in bases:
                if hasattr(base, '_id'):
                    have_id = True
                    break
            if not have_id:
                d['_id'] = uuid4()
        return super(_CustomEmulatorMeta, cls).__new__(cls, name, bases, d)


# TODO: de-duplicate this!
def get_classname_from_path(object_path):
    return object_path.split("/")[-1]


def _get_proxy_object_class(object_id, default_class, path, state):
    """Return a custom proxy class, either from the list or the default.

    Use helper functions to check the class list or return the default.
    :param proxy_class_dict: dict of proxy classes to try
    :param default_class: default class to use if nothing in dict matches
    :param path: dbus path
    :param state: dbus state
    :returns: appropriate custom proxy class
    :raises ValueError: if more than one class in the dict matches

    """
    proxy_class_dict = _object_registry[object_id]
    class_type = _try_custom_proxy_classes(proxy_class_dict, path, state)
    if class_type:
        return class_type
    return _get_default_proxy_class(default_class,
                                    get_classname_from_path(path))


def _try_custom_proxy_classes(proxy_class_dict, path, state):
    """Identify which custom proxy class matches the dbus path and state.

    If more than one class in proxy_class_dict matches, raise an exception.
    :param proxy_class_dict: dict of proxy classes to try
    :param path: dbus path
    :param state: dbus state dict
    :returns: matching custom proxy class
    :raises ValueError: if more than one class matches

    """
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

    We want the object to inherit from CustomEmulatorBase, not the object
    class that is doing the selecting.
    :param default_class: default class to use if no bases match
    :param name: name of new class
    :returns: custom proxy object class

    """
    get_debug_logger().warning(
        "Generating introspection instance for type '%s' based on generic "
        "class.", name)
    for base in default_class.__bases__:
        if issubclass(base, CustomEmulatorBase):
            base_class = base
            break
    else:
        base_class = default_class
    return type(str(name), (base_class,), {})


def _create_custom_proxy_object_base(proxy_base_class):
    class_object = _CustomEmulatorMeta(
        'CustomEmulatorBase',
        (proxy_base_class, ),
        {}
    )
    class_object.__doc__ = \
        """This class must be used as a base class for any custom emulators
        defined within a test case.

        .. seealso::
            Tutorial Section :ref:`custom_proxy_classes`
                Information on how to write custom emulators.
        """
    return class_object


# This doesn't work at the moment, simply because DBusIntrospectionObject isn't
# availabel right now. However, once the DBusIntrospectionObject has been
# cleaned up we should be able to reduce it to a pure interface that allows us
# to import it (as it shouldn't depend on the object registry.)
class DBusIntrospectionObject(object):  # make it build
    pass
CustomEmulatorBase = _create_custom_proxy_object_base(DBusIntrospectionObject)
