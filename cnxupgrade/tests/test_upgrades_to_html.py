# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###

"""Tests for to_html command-line interface.
"""

from io import BytesIO
import sys
import unittest

from . import DB_CONNECTION_STRING

class ToHtmlTestCase(unittest.TestCase):

    def setUp(self):
        # Capture stdout
        original_stdout = sys.stdout
        self.addCleanup(setattr, sys, 'stdout', original_stdout)
        sys.stdout = BytesIO()

        # Mock produce_html_for_modules
        from ..upgrades import to_html
        original_func = to_html.produce_html_for_modules
        self.addCleanup(setattr, to_html, 'produce_html_for_modules',
                        original_func)
        self.call_modules_count = 0
        def f(*args, **kwargs):
            self.call_modules_count += 1
            self.modules_args = args
            self.modules_kwargs = kwargs
            return []
        to_html.produce_html_for_modules = f

        # Mock produce_html_for_abstracts
        original_abstracts = to_html.produce_html_for_abstracts
        self.addCleanup(setattr, to_html, 'produce_html_for_abstracts',
                        original_abstracts)
        self.call_abstracts_count = 0
        def g(*args, **kwargs):
            self.call_abstracts_count += 1
            self.abstracts_args = args
            self.abstracts_kwargs = kwargs
            return []
        to_html.produce_html_for_abstracts = g

    def call_target(self, **kwargs):
        from ..upgrades import to_html
        return to_html.cli_command(**kwargs)

    def test_transform_abstracts(self):
        self.call_target(db_conn_str=DB_CONNECTION_STRING,
                         id_select_query='SELECT 2',
                         overwrite_html=False,
                         filename='index.cnxml',
                         no_modules=False,
                         no_abstracts=True)

        # Assert produce_html_for_abstracts is called
        self.assertEqual(self.call_abstracts_count, 1)
        self.assertEqual(self.call_modules_count, 0)
        self.assertEqual(str(type(self.abstracts_args[0])),
                         "<type 'psycopg2._psycopg.connection'>")
        self.assertEqual(self.abstracts_args[1], 'SELECT 2')
        self.assertEqual(self.abstracts_kwargs, {})

    def test_transform_modules(self):
        self.call_target(db_conn_str=DB_CONNECTION_STRING,
                         id_select_query='SELECT 2',
                         overwrite_html=False,
                         filename='index.cnxml',
                         no_modules=True,
                         no_abstracts=False)

        # Assert produce_html_for_modules is called
        self.assertEqual(self.call_abstracts_count, 0)
        self.assertEqual(self.call_modules_count, 1)
        self.assertEqual(str(type(self.modules_args[0])),
                         "<type 'psycopg2._psycopg.connection'>")
        self.assertEqual(self.modules_args[1], 'SELECT 2')
        self.assertEqual(self.modules_kwargs, {
            'source_filename': 'index.cnxml', 'overwrite_html': False})
