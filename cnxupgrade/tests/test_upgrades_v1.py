# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import os
import unittest
import uuid

import psycopg2
from . import *
from .populates import populate_database


TABLE_DESCRIPTION_STATEMENT = """\
SELECT
    f.attnum AS number,
    f.attname AS name,
    f.attnum,
    f.attnotnull AS notnull,
    pg_catalog.format_type(f.atttypid,f.atttypmod) AS type,
    CASE
        WHEN p.contype = 'p' THEN 't'::boolean
        ELSE 'f'::boolean
    END AS primarykey,
    CASE
        WHEN p.contype = 'u' THEN 't'::boolean
        ELSE 'f'::boolean
    END AS uniquekey,
    CASE
        WHEN p.contype = 'f' THEN g.relname
    END AS foreignkey,
    CASE
        WHEN p.contype = 'f' THEN p.confkey
    END AS foreignkey_fieldnum,
    CASE
        WHEN p.contype = 'f' THEN p.conkey
    END AS foreignkey_connnum,
    CASE
        WHEN f.atthasdef = 't' THEN d.adsrc
    END AS default
FROM pg_attribute f
    JOIN pg_class c ON c.oid = f.attrelid
    JOIN pg_type t ON t.oid = f.atttypid
    LEFT JOIN pg_attrdef d ON d.adrelid = c.oid AND d.adnum = f.attnum
    LEFT JOIN pg_namespace n ON n.oid = c.relnamespace
    LEFT JOIN pg_constraint p ON p.conrelid = c.oid AND f.attnum = ANY (p.conkey)
    LEFT JOIN pg_class AS g ON p.confrelid = g.oid
WHERE c.relkind = 'r'::char
    AND n.nspname = %s  -- Replace with Schema name
    AND c.relname = %s  -- Replace with table name
    AND f.attnum > 0 ORDER BY number
;"""  # Acquired from http://stackoverflow.com/questions/109325


def describe_table(cursor, table_name):
    """Given a database cursor and table name, describe the table's columns."""
    record_titles = ('number', 'name', 'attnum', 'notnull', 'type',
                     'primarykey', 'uniquekey', 'foreignkey',
                     'foreignkey_fieldnum', 'foreignkey_connnum', 'default',
                     )
    cursor.execute(TABLE_DESCRIPTION_STATEMENT, ('public', table_name,))
    descriptions = cursor.fetchall()
    return {x[1]:dict(zip(record_titles, x)) for x in descriptions}


class V1TestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Configure the database connection.
        cls.connection_string = DB_CONNECTION_STRING
        cls._db_connection = psycopg2.connect(cls.connection_string)
        cls._drop_all()

    @classmethod
    def tearDownClass(cls):
        cls._drop_all()
        cls._db_connection.close()

    @classmethod
    def _drop_all(cls):
        """Drop all tables in the database."""
        with psycopg2.connect(cls.connection_string) as db_connection:
            with db_connection.cursor() as cursor:
                cursor.execute("DROP SCHEMA public CASCADE")
                cursor.execute("CREATE SCHEMA public")

    def setUp(self):
        # Initialize the legacy database schema.
        legacy_schema_filepath = os.path.join(TESTING_DATA_DIRECTORY,
                                              'legacy-schema.sql')
        with psycopg2.connect(self.connection_string) as db_connection:
            with db_connection.cursor() as cursor:
                with open(legacy_schema_filepath, 'rb') as schema:
                    cursor.execute(schema.read())
            db_connection.commit()

    def tearDown(self):
        self._drop_all()

    def call_target(self):
        from ..upgrades.v1 import do_upgrade
        with psycopg2.connect(self.connection_string) as db_connection:
            do_upgrade(db_connection)

    def test_uuid_function(self):
        # Check the uuid_generate_v4 function works.
        self.call_target()

        with psycopg2.connect(self.connection_string) as db_connection:
            with db_connection.cursor() as cursor:
                cursor.execute("SELECT uuid_generate_v4();")
                function_value = cursor.fetchone()[0]

        # Test for a value uuid value.
        self.assertTrue(uuid.UUID(function_value))

    def test_uuid_alteration(self):
        # Verify the alterations to the tables where UUID columns have
        #   been added.
        self.call_target()

        with psycopg2.connect(self.connection_string) as db_connection:
            with db_connection.cursor() as cursor:
                table_description = describe_table(cursor, 'modules')
                target_column = table_description['uuid']
                self.assertEqual(target_column['type'], 'uuid')
                self.assertTrue(target_column['notnull'])
                self.assertEqual(target_column['default'],
                                 'uuid_generate_v4()')

    def test_uuid_content_migration(self):
        # Verify that existing content contains new uuid values
        #   and that these values match between the ``modules``
        #   and ``latest_modules`` tables.

        # Populate the database with some quality hand-crafted
        #   locally-made fairly-traded modules.
        with psycopg2.connect(self.connection_string) as db_connection:
            populate_database(db_connection, ['v0/modules-1.json'])

        self.call_target()

        with psycopg2.connect(self.connection_string) as db_connection:
            with db_connection.cursor() as cursor:
                cursor.execute("SELECT uuid FROM modules "
                               "  WHERE module_ident = 1;")
                module_uuid = cursor.fetchone()[0]
                self.assertTrue(uuid.UUID(module_uuid))
                cursor.execute("SELECT uuid FROM latest_modules "
                               "  WHERE module_ident = 1;")
                latest_module_uuid = cursor.fetchone()[0]
                self.assertEqual(latest_module_uuid, module_uuid)