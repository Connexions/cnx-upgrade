# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import os
import sys
import unittest

import psycopg2


here = os.path.abspath(os.path.dirname(__file__))
_DB_CONNECTION_STRING_ENV_VAR_NAME = 'DB_CONNECTION_STRING'
_DB_CONNECTION_STRING_CLI_OPT_NAME = '--db-conn-str'
try:
    DB_CONNECTION_STRING = os.environ[_DB_CONNECTION_STRING_ENV_VAR_NAME]
except:
    try:
        arg_pos = sys.argv.index(_DB_CONNECTION_STRING_CLI_OPT_NAME)
    except ValueError:
        raise RuntimeError("MUST supply a means to connect to the database, "
                           "either via the environment variable '{}' or the "
                           "command-line option '{}'." \
                               .format(_DB_CONNECTION_STRING_ENV_VAR_NAME,
                                       _DB_CONNECTION_STRING_CLI_OPT_NAME)
                           )
    DB_CONNECTION_STRING = sys.argv[arg_pos+1]
TESTING_DATA_DIR = os.path.join(here, 'data')
TESTING_LEGACY_DATA_SQL_FILE = os.path.join(TESTING_DATA_DIR,
                                            'legacy-data.sql')


class PostgresqlFixture:
    """A testing fixture for a live (same as production) SQL database.
    This will set up the database once for a test case. After each test
    case has completed, the database will be cleaned (all tables dropped).

    On a personal note, this seems archaic... Why can't I rollback to a
    transaction?
    """

    def __init__(self):
        # Configure the database connection.
        self.connection_string = DB_CONNECTION_STRING
        # Drop all existing tables from the database.
        self._drop_all()

    def _drop_all(self):
        """Drop all tables in the database."""
        with psycopg2.connect(self.connection_string) as db_connection:
            with db_connection.cursor() as cursor:
                cursor.execute("DROP SCHEMA public CASCADE")
                cursor.execute("CREATE SCHEMA public")

    def setUp(self):
        # Initialize the database schema.
        from cnxarchive.database import initdb
        settings = {'db-connection-string': self.connection_string}
        initdb(settings)

    def tearDown(self):
        # Drop all tables.
        self._drop_all()

postgresql_fixture = PostgresqlFixture()


class ToHtmlTestCase(unittest.TestCase):
    fixture = postgresql_fixture

    @classmethod
    def setUpClass(cls):
        cls.connection_string = cls.fixture.connection_string
        cls.db_connection = psycopg2.connect(cls.connection_string)

    @classmethod
    def tearDownClass(cls):
        cls.db_connection.close()

    def setUp(self):
        self.fixture.setUp()
        # Load the database with example legacy data.
        with self.db_connection.cursor() as cursor:
            with open(TESTING_LEGACY_DATA_SQL_FILE, 'rb') as fp:
                cursor.execute(fp.read())
        self.db_connection.commit()

    def tearDown(self):
        self.fixture.tearDown()

    def test_collection_transform(self):
        # Case to test for a successful tranformation of a collection from
        #   collxml to html.
        from cnxupgrade.upgrades.to_html import produce_html_for_collections
        with psycopg2.connect(self.connection_string) as db_connection:
            iterator = produce_html_for_collections(db_connection)
            collection_id, message = iterator.next()
            db_connection.commit()

        with psycopg2.connect(self.connection_string) as db_connection:
            with db_connection.cursor() as cursor:
                cursor.execute("SELECT file FROM files "
                               "  WHERE fileid = "
                               "    (SELECT fileid FROM module_files "
                               "       WHERE module_ident = %s "
                               "         AND filename = 'collection.html');",
                               (collection_id,))
                collection_html = cursor.fetchone()[0][:]
        # We only need to test that the file got transformed and placed
        #   placed in the database, the transform itself should be verified.
        #   independent of this code.
        self.assertTrue(collection_html.find('<html') >= 0)

    def test_collection_transform_w_invalid_data(self):
        # Case to test for an unsuccessful tranformation of a collection from
        #   collxml to html.
        pass

    def test_collection_transform_exists(self):
        # Case to test for a successful tranformation with an existing
        #   transform from collxml to html has already been done.
        pass

    def test_module_transform(self):
        pass

    def test_module_transform_exists(self):
        pass

    def test_module_transform_w_invalid_data(self):
        pass
