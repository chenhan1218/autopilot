# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2013 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.

"""Gestural support for autopilot.

This module contains functions that can generate touch and multi-tuch gestures
for you. This is a convenience for the test author - there is nothing to prevent
you from generating your own gestures!

"""


def pinch(center, vector_start, vector_end):
    """Perform a two finger pinch (zoom) gesture.

    :param center: The coordinates (x,y) of the center of the pinch gesture.
    :param vector_start: The (x,y) values to move away from the center for the start.
    :param vector_end: The (x,y) values to move away from the center for the end.

    The fingers will move in 100 steps between the start and the end points.
    If start is smaller than end, the gesture will zoom in, otherwise it
    will zoom out. For example:

    """

    finger_1_start = [center[0] - vector_start[0], center[1] - vector_start[1]]
    finger_2_start = [center[0] + vector_start[0], center[1] + vector_start[1]]
    finger_1_end = [center[0] - vector_end[0], center[1] - vector_end[1]]
    finger_2_end = [center[0] + vector_end[0], center[1] + vector_end[1]]

    dx = 1.0 * (finger_1_end[0] - finger_1_start[0]) / 100
    dy = 1.0 * (finger_1_end[1] - finger_1_start[1]) / 100

    self._finger_down(0, finger_1_start[0], finger_1_start[1])
    self._finger_down(1, finger_2_start[0], finger_2_start[1])

    finger_1_cur = [finger_1_start[0] + dx, finger_1_start[1] + dy]
    finger_2_cur = [finger_2_start[0] - dx, finger_2_start[1] - dy]

    for i in range(0, 100):
        self._finger_move(0, finger_1_cur[0], finger_1_cur[1])
        self._finger_move(1, finger_2_cur[0], finger_2_cur[1])
        sleep(0.005)

        finger_1_cur = [finger_1_cur[0] + dx, finger_1_cur[1] + dy]
        finger_2_cur = [finger_2_cur[0] - dx, finger_2_cur[1] - dy]

    self._finger_move(0, finger_1_end[0], finger_1_end[1])
    self._finger_move(1, finger_2_end[0], finger_2_end[1])
    self._finger_up(0)
    self._finger_up(1)
