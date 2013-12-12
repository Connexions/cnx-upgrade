# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###

"""Tests for the command-line interface cli.py
"""

import os
import sys
import tempfile
import unittest

from . import DB_CONNECTION_STRING

class CommandLineInterfaceTestCase(unittest.TestCase):

    def call_target(self, argv):
        from ..cli import main
        argv = ['--db-conn-str={}'.format(DB_CONNECTION_STRING)] + argv
        return main(argv=argv)

    def mock(self, module_name, function=None):
        # module_name is the module name in upgrades, of
        # which the cli_loader will be mocked
        # function is what will get called instead

        self.call_count = 0
        def default_mock_function(**kwargs):
            self.call_count += 1
            self.kwargs = kwargs
            return 'run {}'.format(module_name)
        if not function:
            function = default_mock_function

        # import module_name
        module_name = 'cnxupgrade.upgrades.{}'.format(module_name)
        __import__(module_name)
        module = sys.modules[module_name]

        # Unmock the cli_loader function in clean up
        cli_loader = getattr(module, 'cli_loader')
        self.addCleanup(setattr, module, 'cli_loader', cli_loader)

        # Return the mock cli_command from cli_loader instead
        def mock_cli_loader(*args, **kwargs):
            cli_loader(*args, **kwargs)
            return function

        # Mock the cli_loader function of module_name
        setattr(module, 'cli_loader', mock_cli_loader)
        return function

    def test_to_html(self):
        # Mock to_html.cli_command
        to_html = self.mock('to_html')

        # Invoke cnx-upgrade to_html
        result = self.call_target(['to_html'])

        from ..upgrades.to_html import (
                DEFAULT_ID_SELECT_QUERY, DEFAULT_FILENAME)

        # Assert to_html.cli_command was called
        self.assertEqual(self.call_count, 1)
        self.assertEqual(self.kwargs, {
            'cmmd': to_html,
            'db_conn_str': DB_CONNECTION_STRING,
            'id_select_query': DEFAULT_ID_SELECT_QUERY,
            'filename': DEFAULT_FILENAME,
            'no_modules': True,
            'no_abstracts': True,
            'overwrite_html': False})
        self.assertEqual(result, 'run cnxupgrade.upgrades.to_html')

    def test_to_html_with_id_select_query(self):
        # Mock to_html.cli_command
        to_html = self.mock('to_html')

        # Invoke cnx-upgrade to_html
        result = self.call_target(['to_html', '--id-select-query=SELECT 2'])

        from ..upgrades.to_html import DEFAULT_FILENAME

        # Assert to_html.cli_command was called
        self.assertEqual(self.call_count, 1)
        self.assertEqual(self.kwargs, {
            'cmmd': to_html,
            'db_conn_str': DB_CONNECTION_STRING,
            'id_select_query': 'SELECT 2',
            'filename': DEFAULT_FILENAME,
            'no_modules': True,
            'no_abstracts': True,
            'overwrite_html': False})
        self.assertEqual(result, 'run cnxupgrade.upgrades.to_html')

    def test_to_html_force_overwrite_html(self):
        # Mock to_html.cli_command
        to_html = self.mock('to_html')

        from ..upgrades.to_html import (
                DEFAULT_ID_SELECT_QUERY, DEFAULT_FILENAME)

        # Invoke cnx-upgrade to_html
        result = self.call_target(['to_html', '--force'])

        # Assert to_html.cli_command was called
        self.assertEqual(self.call_count, 1)
        self.assertEqual(self.kwargs, {
            'cmmd': to_html,
            'db_conn_str': DB_CONNECTION_STRING,
            'id_select_query': DEFAULT_ID_SELECT_QUERY,
            'filename': DEFAULT_FILENAME,
            'no_modules': True,
            'no_abstracts': True,
            'overwrite_html': True})
        self.assertEqual(result, 'run cnxupgrade.upgrades.to_html')

    def test_to_html_specify_filename(self):
        # Mock to_html.cli_command
        to_html = self.mock('to_html')

        from ..upgrades.to_html import DEFAULT_ID_SELECT_QUERY

        # Invoke cnx-upgrade to_html
        result = self.call_target(['to_html', '--filename', 'a.cnxml'])

        # Assert to_html.cli_command was called
        self.assertEqual(self.call_count, 1)
        self.assertEqual(self.kwargs, {
            'cmmd': to_html,
            'db_conn_str': DB_CONNECTION_STRING,
            'id_select_query': DEFAULT_ID_SELECT_QUERY,
            'filename': 'a.cnxml',
            'no_modules': True,
            'no_abstracts': True,
            'overwrite_html': False})
        self.assertEqual(result, 'run cnxupgrade.upgrades.to_html')

    def test_v1(self):
        # Mock v1.cli_command
        v1 = self.mock('v1')

        # Invoke cnx-upgrade v1
        result = self.call_target(['v1'])

        # Assert v1.cli_command was called
        self.assertEqual(self.call_count, 1)
        self.assertEqual(self.kwargs, {
            'cmmd': v1,
            'db_conn_str': DB_CONNECTION_STRING})
        self.assertEqual(result, 'run cnxupgrade.upgrades.v1')

    def test_migrate_hit_counts(self):
        # Mock migrate_hit_counts.cli_command
        migrate_hit_counts = self.mock('migrate_hit_counts')

        # Create a temporary file for migrate_hit_counts as input
        file_handle, filename = tempfile.mkstemp()
        self.addCleanup(os.remove, filename)

        # Invoke cnx-upgrade migrate_hit_counts
        result = self.call_target(['migrate_hit_counts',
            '--input={}'.format(filename)])

        # Assert migrate_hit_counts.cli_command was called
        self.assertEqual(self.call_count, 1)
        self.assertTrue(str(self.kwargs.pop('input')).startswith(
            "<open file '{}'".format(filename)))
        self.assertEqual(self.kwargs, {
            'cmmd': migrate_hit_counts,
            'db_conn_str': DB_CONNECTION_STRING})
        self.assertEqual(result, 'run cnxupgrade.upgrades.migrate_hit_counts')

    def test_create_collection_minor_versions(self):
        # Mock create_collection_minor_versions.cli_command
        create_collection = self.mock('create_collection_minor_versions')

        # Invoke cnx-upgrade create_collection_minor_versions
        result = self.call_target(['create_collection_minor_versions',
            '--id-select-query', 'select 2'])

        # Assert create_collection_minor_versions was called
        self.assertEqual(self.call_count, 1)
        self.assertEqual(self.kwargs, {
            'cmmd': create_collection,
            'db_conn_str': DB_CONNECTION_STRING,
            'id_select_query': 'select 2',
            })
        self.assertEqual(result, 'run cnxupgrade.upgrades.create_collection_minor_versions')
