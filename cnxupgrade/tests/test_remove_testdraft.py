# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import os
import unittest

import psycopg2
from . import *
from .populates import populate_database


class SubjectRemovalTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.db_connection_string = DB_CONNECTION_STRING

    def setUp(self):
        # Initialize the database schema.
        from cnxarchive.database import initdb
        settings = {'db-connection-string': self.db_connection_string}
        initdb(settings)
        # # Initialize the cnxuser users shadow table.
        # from cnxarchive.database import DB_SCHEMA_DIRECTORY
        # with psycopg2.connect(self.db_connection_string) as db_connection:
        #     with db_connection.cursor() as cursor:
        #         cnxuser_schema_filepath = os.path.join(DB_SCHEMA_DIRECTORY,
        #                                                'cnx-user.schema.sql')
        #         with open(cnxuser_schema_filepath, 'r') as fb:
        #             cursor.execute(fb.read())
        # Set the target subject/tag for removal.
        # Note this is different from the actual one to be removed. This
        #   is because the actual one will eventually be removed from the
        #   schema and therefore not loaded into the database.
        self.target_subject = 'Business'
        # Load some data and tie in tag info.
        with psycopg2.connect(self.db_connection_string) as db_connection:
            population_records = ['v1/modules-299.json', 'v1/modules-300.json',
                                  ]
            populate_database(db_connection, population_records)
            with db_connection.cursor() as cursor:
                cursor.execute("WITH tag AS "
                               "  (SELECT tagid as id FROM tags "
                               "   WHERE tag = %s) "
                               "INSERT INTO moduletags VALUES "
                               "  (199, (select id from tag)), "
                               "  (200, (select id from tag));",
                               (self.target_subject,))

    def tearDown(self):
        # Drop all tables.
        with psycopg2.connect(self.db_connection_string) as db_connection:
            with db_connection.cursor() as cursor:
                cursor.execute("DROP SCHEMA public CASCADE;")
                cursor.execute("CREATE SCHEMA public;")

    def call_target(self, subject_name=None):
        if subject_name is None:
            subject_name = self.target_subject
        from ..upgrades.remove_testdraft import remove_subject
        with psycopg2.connect(self.db_connection_string) as db_connection:
            return remove_subject(subject_name, db_connection)

    def test_removal(self):
        # Verify the removal of the target subject from the subjects
        #   table.
        deleted_documents = self.call_target()
        with psycopg2.connect(self.db_connection_string) as db_connection:
            with db_connection.cursor() as cursor:
                cursor.execute("SELECT * from tags where tag = %s;",
                               (self.target_subject,))
                row = cursor.fetchone()
        self.assertEqual(row, None)
        self.assertEqual(deleted_documents, [199, 200])

    def test_removal_invalid(self):
        # Verify a run without failure even when the subject has already,
        #   been removed. This can be simulated by rerunning the process.
        #   This works as long as the previous test works.
        self.call_target()
        # No exceptions means it worked just fine.
        self.assertEqual(self.call_target(), [])

    def test_removal_of_documents(self):
        # Verify the removal of documents with the target subject.
        # This deletes the relationship but not the actual file entry.
        deleted_documents = self.call_target()
        with psycopg2.connect(self.db_connection_string) as db_connection:
            with db_connection.cursor() as cursor:
                for id in deleted_documents:
                    cursor.execute("SELECT * FROM module_files "
                                   "WHERE module_ident = %s", (id,))
                    self.assertEqual(cursor.fetchall(), [])
