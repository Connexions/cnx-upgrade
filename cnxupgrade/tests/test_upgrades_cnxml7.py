# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###

"""Tests for cnx-upgrades cnxml7
"""

import os
import psycopg2
import unittest

import lxml.etree

from . import *

def get_data_file(filename):
    path = os.path.join(TESTING_DATA_DIRECTORY, filename)
    with open(path) as f:
        return f.read()


class MainTestCase(unittest.TestCase):
    """Tests for cnxupgrade.upgrades.cnxml7.main
    """
    fixture = postgresql_fixture

    def setUp(self):
        self.fixture.setUp()

    @db_connect
    def setup_test_data(self, cursor, moduleid, version):
        cursor.execute("INSERT INTO abstracts VALUES (1, '', '');")
        cursor.execute('''
INSERT INTO modules VALUES (1, 'Module', %s, '209deb1f-1a46-4369-9e0d-18674cf58a3e', %s, 'Preface to College Physics', '2013-07-31 14:07:20.542211-05', '2013-07-31 14:07:20.542211-05', 1, 11, '', '', '', NULL, NULL, 'en', '{e5a07af6-09b9-4b74-aa7a-b7510bee90b8}', '{e5a07af6-09b9-4b74-aa7a-b7510bee90b8, 1df3bab1-1dc7-4017-9b3a-960a87e706b1}', '{9366c786-e3c8-4960-83d4-aec1269ac5e5}', NULL, NULL, NULL, 7, NULL);
INSERT INTO files (file) VALUES (%s);
INSERT INTO module_files (fileid, module_ident, filename, uuid) VALUES (1, 1, 'index.cnxml', '209deb1f-1a46-4369-9e0d-18674cf58a3e');
        ''', (moduleid, version,
              memoryview(get_data_file(
                  '{}-{}.cnxml'.format(moduleid, version)))))
        # remove index.cnxml.html
        cursor.execute("DELETE FROM module_files WHERE filename = 'index.cnxml.html'")

    def tearDown(self):
        self.fixture.tearDown()

    def call_target(self):
        from ..upgrades.cnxml7.main import main
        with psycopg2.connect(DB_CONNECTION_STRING) as db_conn:
            return list(main(db_conn))

    @db_connect
    def get_new_cnxml(self, cursor):
        cursor.execute('SELECT f.file FROM module_files mf '
                       'JOIN files f ON mf.fileid = f.fileid '
                       "WHERE mf.filename = 'index_auto_generated.cnxml'")
        return cursor.fetchone()[0][:]

    def test_successful(self):
        self.setup_test_data('m10470', '2.2')

        result = self.call_target()

        self.assertEqual(result, [('m10470', '2.2', 1, u'0.5', True, '')])
        self.assertTrue('cnxml-version="0.7"' in self.get_new_cnxml())

    def test_no_upgrade_necessary(self):
        self.setup_test_data('m11425', '1.19')

        result = self.call_target()

        self.assertEqual(result, [('m11425', '1.19', 1, u'0.7', True, '')])
        self.assertTrue('cnxml-version="0.7"' in self.get_new_cnxml())

    def test_missing_namespace_declaration(self):
        self.setup_test_data('m12563', '1.6')

        result = self.call_target()

        self.assertEqual(result, [('m12563', '1.6', 1, u'0.5', True, '')])
        self.assertTrue('cnxml-version="0.7"' in self.get_new_cnxml())


class TransformsTestCase(unittest.TestCase):
    """Tests for cnxupgrade.upgrades.cnxml7.transforms
    """

    def call_target(self, source, version=None):
        from ..upgrades.cnxml7 import transforms
        return transforms.upgrade_document(source, version=version)

    def test_no_upgrade_necessary(self):
        cnxml = get_data_file('m11425-1.19.cnxml')
        new_cnxml, result, message = self.call_target(cnxml, version='0.7')
        self.assertEqual(message, '')
        self.assertEqual(result, True)
        self.assertEqual(new_cnxml, cnxml)

    def test_successful(self):
        cnxml = get_data_file('m10470-2.2.cnxml')
        new_cnxml, result, message = self.call_target(cnxml, version='0.5')
        self.assertEqual(message, '')
        self.assertTrue(result)
        self.assertTrue('cnxml-version="0.7"' in new_cnxml)
        # Assert generated cnxml is valid xml
        self.assertTrue(lxml.etree.fromstring(new_cnxml) is not None)

    def test_missing_namespace_declaration(self):
        cnxml = get_data_file('m12563-1.6.cnxml')
        new_cnxml, result, message = self.call_target(cnxml, version='0.5')
        self.assertEqual(message, '')
        self.assertTrue(result)
        self.assertTrue('cnxml-version="0.7"' in new_cnxml)
        # Assert generated cnxml is valid xml
        self.assertTrue(lxml.etree.fromstring(new_cnxml) is not None)
