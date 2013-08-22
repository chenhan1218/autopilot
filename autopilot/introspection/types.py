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


"""
Autopilot proxy type support.
=============================

This module defines the classes that are used for all attributes on proxy
objects. All proxy objects contain attributes that transparently mirror the
values present in the application under test. Autopilot takes care of keeping
these values up to date.

Object attributes fall into two categories. Attributes that are a single
string, boolean, or integer property are sent directly across DBus. These are
called "plain" types, and are stored in autopilot as instnaces of the
:class:`PlainType` class. Attributes that are more complex (a rectangle, for
example) are called "complex" types, and are split into several component
values, sent across dbus, and are then reconstituted in autopilot into useful
objects.

"""

from __future__ import absolute_import
from functools import partial
import dbus


class ValueType(object):

    """Store constants for different special types that autopilot understands.

    DO NOT add items here unless you have documented them correctly in
    docs/appendix/protocol.rst.

    """
    PLAIN = 0
    RECTANGLE = 1
    POINT = 2
    SIZE = 3
    COLOR = 4
    DATETIME = 5
    TIME = 6


def create_value_instance(value, parent, name):
    """Create an object that exposes the interesing part of the value
    specified, given the value_type_id.

    :param parent: The object this attribute belongs to.
    :param name: The name of this attribute.
    :param value: The value array from DBus.

    """
    type_dict = {
        ValueType.PLAIN: PlainType,
        ValueType.RECTANGLE: Rectangle,
        ValueType.POINT: Point,
        ValueType.SIZE: Size,
        ValueType.DATETIME: DateTime,
        ValueType.TIME: Time,
    }
    type_id = value[0]
    value = value[1:]
    # TODO: deal with type Ids that are not in the dictionary more cleanly.
    return type_dict[type_id](*value, parent=parent, name=name)


class TypeBase(object):

    def wait_for(self, expected_value, timeout=10):
        """Wait up to 10 seconds for our value to change to
        *expected_value*.

        *expected_value* can be a testtools.matcher. Matcher subclass (like
        LessThan, for example), or an ordinary value.

        This works by refreshing the value using repeated dbus calls.

        :raises AssertionError: if the attribute was not equal to the
         expected value after 10 seconds.

        :raises RuntimeError: if the attribute you called this on was not
         constructed as part of an object.

        """
        # It's guaranteed that our value is up to date, since __getattr__
        # calls refresh_state. This if statement stops us waiting if the
        # value is already what we expect:
        if self == expected_value:
            return

        if self.name is None or self.parent is None:
            raise RuntimeError(
                "This variable was not constructed as part of "
                "an object. The wait_for method cannot be used."
            )

        def make_unicode(value):
            if isinstance(value, str):
                return unicode(value.decode('utf8'))
            return value

        if hasattr(expected_value, 'expected'):
            expected_value.expected = make_unicode(expected_value.expected)

        # unfortunately not all testtools matchers derive from the Matcher
        # class, so we can't use issubclass, isinstance for this:
        match_fun = getattr(expected_value, 'match', None)
        is_matcher = match_fun and callable(match_fun)
        if not is_matcher:
            expected_value = Equals(expected_value)

        time_left = timeout
        while True:
            _, new_state = self.parent.get_new_state()
            new_state = translate_state_keys(new_state)
            new_value = make_unicode(new_state[self.name])
            # Support for testtools.matcher classes:
            mismatch = expected_value.match(new_value)
            if mismatch:
                failure_msg = mismatch.describe()
            else:
                self.parent._set_properties(new_state)
                return

            if time_left >= 1:
                sleep(1)
                time_left -= 1
            else:
                sleep(time_left)
                break

        raise AssertionError(
            "After %.1f seconds test on %s.%s failed: %s" % (
                timeout, self.parent.__class__.__name__, self.name,
                failure_msg))


class PlainType(TypeBase):

    """Plain type support in autopilot proxy objects.

    Instances of this class will be used for all plain attrubites. The word
    "plain" in this context means anything that's marshalled as a string,
    boolean or integer type across dbus.

    Instances of these classes can be used just like the underlying type. For
    example, given an object property called 'length' that is marshalled over
    dbus as an integer value, the following will be true::

        >>> isinstance(object.length, PlainType)
        True
        >>> isinstance(object.length, int)
        True
        >>> print object.length
        123
        >>> print object.length + 32
        155

    However, a special case exists for boolean values: because you cannot
    subclass from the 'bool' type, the following check will fail (
    ``object.visible`` is a boolean property)::

        >>> isinstance(object.visible, bool)
        False

    However boolean values will behave exactly as you expect them to.

    """

    def __new__(cls, value, parent=None, name=None):
        # PlainType is used for strings, ints, bools, and anything else that
        # does not have a more specialised representation. We want to return
        # an instance of PlainType that derives from the actual value.
        new_type_name = type(value).__name__
        new_type_bases = (type(value), cls)
        new_type_dict = {
            "name": name,
            "parent": parent
        }
        return type(new_type_name, new_type_bases, new_type_dict)(value)


def _array_packed_type(num_args):
    """Return a base class that accepts 'num_args' and is packed into a dbus
    Array type.

    """
    class _ArrayPackedType(dbus.Array, TypeBase):

        def __init__(self, *args, **kwargs):
            if len(args) != self._required_arg_count:
                raise ValueError(
                    "%s must be constructed with %d arguments, not %d"
                    % (
                        self.__class__.__name__,
                        self._required_arg_count,
                        len(args)
                    )
                )
            super(_ArrayPackedType, self).__init__(args)
            # TODO: pop instead of get, and raise on unknown kwarg
            self.parent = kwargs.get("parent", None)
            self.name = kwargs.get("name", None)
    return type(
        "_ArrayPackedType_{}".format(num_args),
        (_ArrayPackedType,),
        dict(_required_arg_count=num_args)
    )


class Rectangle(_array_packed_type(4)):

    """The RectangleType class represents a rectangle in cartesian space.

    To construct a rectangle, pass the x, y, width and height parameters in to
    the class constructor::

        my_rect = Rectangle(12,13,100,150)

    These attributes can be accessed either using named attributes, or via
    sequence indexes::

        >>> my_rect.x == my_rect[0] == 12
        True
        >>> my_rect.y == my_rect[1] == 13
        True
        >>> my_rect.w == my_rect[2] == 100
        True
        >>> my_rect.h == my_rect[3] == 150
        True

    You may also access the width and height values using the ``width`` and
    ``height`` properties::

        >>> my_rect.width == my_rect.w
        True
        >>> my_rect.height == my_rect.h
        True

    Rectangles can be compared using ``==`` and ``!=``, either to another
    Rectangle instance, or to any mutable sequence type::

        >>> my_rect == [12, 13, 100, 150]
        True
        >>> my_rect != Rectangle(1,2,3,4)
        True

    """

    @property
    def x(self):
        return self[0]

    @property
    def y(self):
        return self[1]

    @property
    def w(self):
        return self[2]

    @property
    def width(self):
        return self[2]

    @property
    def h(self):
        return self[3]

    @property
    def height(self):
        return self[3]


class Point(_array_packed_type(2)):

    """The Point class represents a 2D point in cartesian space.

    To construct a Point, pass in the x, y parameters to the class
    constructor::

        >>> my_point = Point(50,100)

    These attributes can be accessed either using named attributes, or via
    sequence indexes::

        >>> my_point.x == my_point[0] == 50
        True
        >>> my_point.y == my_point[1] == 100
        True

    Point instances can be compared using ``==`` and ``!=``, either to another
    Point instance, or to any mutable sequence type with the correct number of
    items::

        >>> my_point == [50, 100]
        True
        >>> my_point != Point(5, 10)
        True

    """

    @property
    def x(self):
        return self[0]

    @property
    def y(self):
        return self[1]


class Size(_array_packed_type(2)):

    """The Size class represents a 2D size in cartesian space.

    To construct a Size, pass in the width, height parameters to the class
    constructor::

        >>> my_size = Size(50,100)

    These attributes can be accessed either using named attributes, or via
    sequence indexes::

        >>> my_size.width == my_size.w == my_size[0] == 50
        True
        >>> my_size.height == my_size.h == my_size[1] == 100
        True

    Size instances can be compared using ``==`` and ``!=``, either to another
    Size instance, or to any mutable sequence type with the correct number of
    items::

        >>> my_size == [50, 100]
        True
        >>> my_size != Size(5, 10)
        True

    """

    @property
    def w(self):
        return self[0]

    @property
    def width(self):
        return self[0]

    @property
    def h(self):
        return self[1]

    @property
    def height(self):
        return self[1]


class Color(_array_packed_type(4)):

    """The Color class represents an RGBA Color.

    To construct a Color, pass in the red, green, blue and alpha parameters to
    the class constructor::

        >>> my_color = Color(50, 100, 200, 255)

    These attributes can be accessed either using named attributes, or via
    sequence indexes::

        >>> my_color.red == my_color[0] == 50
        True
        >>> my_color.green == my_color[1] == 100
        True
        >>> my_color.blue == my_color[2] == 200
        True
        >>> my_color.alpha == my_color[3] == 255
        True

    Color instances can be compared using ``==`` and ``!=``, either to another
    Color instance, or to any mutable sequence type with the correct number of
    items::

        >>> my_color == [50, 100, 200, 255]
        True
        >>> my_color != Color(5, 10, 0, 0)
        True

    """

    @property
    def red(self):
        return self[0]

    @property
    def green(self):
        return self[1]

    @property
    def blue(self):
        return self[2]

    @property
    def alpha(self):
        return self[3]


class DateTime(_array_packed_type(1)):
    pass


class Time(_array_packed_type(3)):
    pass
