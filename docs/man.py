# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2012-2013 Canonical
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


class ArgparseDescription(_ArgparseSection):
    def run(self):
        return [nodes.Text(self.parser.format_description())]


class ArgparseEpilog(_ArgparseSection):
    def run(self):
        return [nodes.Text(self.parser.format_epilog())]


class ArgparseOptions(_ArgparseSection):
    def run(self):
        return [nodes.Text(self.parser.format_options())]


class ArgparseUsage(_ArgparseSection):
    def run(self):
        parser_usage = self.parser.format_usage()
        usage_words = parser_usage.split()
        del usage_words[0]
        usage_words[0] = 'autopilot'
        usage = ' '.join(usage_words) + '\n'
        return [nodes.Text(usage)]
