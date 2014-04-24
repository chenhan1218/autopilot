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


import argparse
from docutils import nodes
from sphinx.util.compat import Directive

from autopilot.run import _get_parser

# Let's just instantiate this once for all the directives
PARSER = _get_parser()


def setup(app):
    app.add_directive('argparse_description', ArgparseDescription)
    app.add_directive('argparse_epilog', ArgparseEpilog)
    app.add_directive('argparse_options', ArgparseOptions)
    app.add_directive('argparse_usage', ArgparseUsage)


class _ArgparseSection(Directive):

    has_content = True

    def __init__(self, *args, **kw):
        super(_ArgparseSection, self).__init__(*args, **kw)
        self.parser = PARSER

    def format_text(self, text):
        """Format arbitrary text."""
        formatter = self.parser._get_formatter()
        formatter.add_text(text)
        return formatter.format_help()


class ArgparseDescription(_ArgparseSection):
    def run(self):
        description = self.format_text(self.parser.description)
        return [nodes.Text(description)]


class ArgparseEpilog(_ArgparseSection):
    def run(self):
        epilog = self.format_text(self.parser.epilog)
        return [nodes.Text(epilog)]


class ArgparseOptions(_ArgparseSection):
    def run(self):
        formatter = self.parser._get_formatter()

        for action_group in self.parser._action_groups:
            formatter.start_section(action_group.title)
            formatter.add_text(action_group.description)
            formatter.add_arguments(action_group._group_actions)
            formatter.end_section()

        options = formatter.format_help()

        return [nodes.Text(options)]


class ArgparseUsage(_ArgparseSection):
    def run(self):
        usage_nodes = []
        for action in self.parser._subparsers._actions:
            if type(action) == argparse._SubParsersAction:
                choices = action.choices
                break
        for choice in choices.values():
            parser_usage = choice.format_usage()
            usage_words = parser_usage.split()
            del usage_words[0]
            usage_words[0] = 'autopilot'
            usage = ' '.join(usage_words) + '\n.br\n'
            usage_nodes.append(nodes.Text(usage))
        return usage_nodes
