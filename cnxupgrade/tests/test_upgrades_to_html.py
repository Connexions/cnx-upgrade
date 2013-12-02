# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###

"""Tests for to_html command-line interface.
"""

import sys
import unittest

from . import DB_CONNECTION_STRING

class ToHtmlTestCase(unittest.TestCase):

    def call_target(self, **kwargs):
        from ..upgrades import to_html
        return to_html.cli_command(**kwargs)

    def test(self):
        # Mock produce_html_for_modules
        from ..upgrades import to_html
        original_func = to_html.produce_html_for_modules
        self.addCleanup(setattr, to_html, 'produce_html_for_modules',
                        original_func)
        self.call_count = 0
        def f(*args, **kwargs):
            self.call_count += 1
            self.args = args
            self.kwargs = kwargs
            return []
        setattr(to_html, 'produce_html_for_modules', f)

        self.call_target(db_conn_str=DB_CONNECTION_STRING,
                         id_select_query='SELECT 2',
                         overwrite_html=False,
                         filename='index.cnxml')

        # Assert produce_html_for_modules is called
        self.assertEqual(self.call_count, 1)
        self.assertEqual(str(type(self.args[0])),
                         "<type 'psycopg2._psycopg.connection'>")
        self.assertEqual(self.args[1], 'SELECT 2')
        self.assertEqual(self.kwargs, {
            'source_filename': 'index.cnxml', 'overwrite_html': False})
