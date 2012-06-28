# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2012 Canonical
# Author: Brandon Schaefer
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.

"""Class to add text files to the file lens."""

from __future__ import absolute_import

import logging
import os.path
from zeitgeist.client import ZeitgeistClient
from zeitgeist.datamodel import Event, Interpretation, Manifestation, ResultType


class Zeitgeist(object):
    """Class to access zeitgeist."""

    def __init__(self):
        self.zg = ZeitgeistClient()
        self.temp_file = None
        self.logger = logging.getLogger(__name__)

    def add_existing_file(self, path):
        """Takes a complete path to an existing text file then adds it to the file lens."""
        if os.path.exists(path):
            self.__add_text_file(path)
        else:
          self.logger.info("File not found on path: %s." %(path))

    def __add_text_file(self, path):
        """Takes a path to a file and creates an event for it then querys it."""
        file_lens = "file://"
        dir_path = os.path.dirname(path)
        name = os.path.basename(path)

        event = Event.new_for_values (interpretation=Interpretation.ACCESS_EVENT,
                                      manifestation=Manifestation.USER_ACTIVITY,
                                      subject_uri=file_lens + path,
                                      subject_interpretation=Interpretation.TEXT_DOCUMENT,
                                      subject_manifestation=Manifestation.FILE_DATA_OBJECT,
                                      subject_origin=file_lens + dir_path,
                                      subject_text=name)
        self.zg.insert_event(event)

        template = Event.new_for_values (interpretation=Interpretation.ACCESS_EVENT,
                                         manifestation=Manifestation.USER_ACTIVITY)

        self.zg.find_events_for_template (template,
                                     self.__log_events_cb,
                                     num_events=1,
                                     result_type=ResultType.MostRecentSubjects)

    def __log_events_cb(self, events):
        """Callback to recive events, we are just using it to log each event."""
        self.logger.info("Found Events")
        for event in events:
            for subject in event.subjects:
                self.logger.info(" * %s" % (subject.uri))
