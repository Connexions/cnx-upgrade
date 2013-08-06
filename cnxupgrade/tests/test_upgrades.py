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
        connection_string = cls.fixture.connection_string
        cls.db_connection = psycopg2.connect(connection_string)

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

    def test_something(self):
        pass
