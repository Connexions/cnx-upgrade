# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import os
import csv
import datetime
import calendar
import tempfile
import unittest

import pytz
import psycopg2
from . import DB_CONNECTION_STRING

TZ = 'US/Eastern'
SQL_FOR_TESTED_DOCUMENTS = """
ALTER TABLE modules DISABLE TRIGGER ALL;
INSERT INTO abstracts VALUES (1, '');
INSERT INTO modules VALUES (
  1, 'Module', 'm1', '88cd206d-66d2-48f9-86bb-75d5366582ee',
  '1.1', 'Name of m1',
  '2013-07-31 12:00:00.000000+02', '2013-10-03 21:14:11.000000+02',
  1, 11, '', '', '', NULL, NULL, 'en', '{}', '{}', '{}',
  NULL, NULL, NULL, 1, NULL);
INSERT INTO modules VALUES (
  2, 'Module', 'm1', '88cd206d-66d2-48f9-86bb-75d5366582ee',
  '1.2', 'Name of m1',
  '2013-07-31 12:00:00.000000+02', '2013-10-03 21:16:20.000000+02',
  1, 11, '', '', '', NULL, NULL, 'en', '{}', '{}', '{}',
  NULL, NULL, NULL, 2, NULL);
INSERT INTO modules VALUES (
  3, 'Module', 'm2', 'f122af91-5f4f-4736-a502-67bd0a1628aa',
  '1.1', 'Name of m2',
  '2013-07-31 12:00:00.000000+02', '2013-10-03 21:16:20.000000+02',
  1, 11, '', '', '', NULL, NULL, 'en', '{}', '{}', '{}',
  NULL, NULL, NULL, 1, NULL);
INSERT INTO modules VALUES (
  4, 'Module', 'm3', 'c8ee8dc5-bb73-47c8-b10f-3f37123cf607',
  '1.1', 'Name of m2',
  '2013-07-31 12:00:00.000000+02', '2013-10-03 21:16:20.000000+02',
  1, 11, '', '', '', NULL, NULL, 'en', '{}', '{}', '{}',
  NULL, NULL, NULL, 1, 1);
INSERT INTO modules VALUES (
  5, 'Module', 'm4', 'dd7b92c2-e82e-43bb-b224-accbc3cd395a',
  '1.1', 'Name of m4',
  '2013-07-31 12:00:00.000000+02', '2013-10-03 21:16:20.000000+02',
  1, 11, '', '', '', NULL, NULL, 'en', '{}', '{}', '{}',
  NULL, NULL, NULL, 1, 1);
INSERT INTO modules VALUES (
  6, 'Module', 'm5', '84b98813-928b-4f3f-b7d0-0472c82bfd1c',
  '1.1', 'Name of m5',
  '2013-07-31 12:00:00.000000+02', '2013-10-03 21:16:20.000000+02',
  1, 11, '', '', '', NULL, NULL, 'en', '{}', '{}', '{}',
  NULL, NULL, NULL, 1, 1);
INSERT INTO latest_modules SELECT * FROM modules WHERE module_ident = 2;
INSERT INTO latest_modules SELECT * FROM modules WHERE module_ident = 3;
INSERT INTO latest_modules SELECT * FROM modules WHERE module_ident = 4;
INSERT INTO latest_modules SELECT * FROM modules WHERE module_ident = 5;
INSERT INTO latest_modules SELECT * FROM modules WHERE module_ident = 6;
ALTER TABLE modules ENABLE TRIGGER ALL;
"""
TZINFO = pytz.timezone(TZ)
def _to_timestamp(*datetime_args):
    dt = datetime.datetime(*datetime_args)
    dt = TZINFO.localize(dt)
    return calendar.timegm(dt.utctimetuple())
INTERVAL = 604800  # 7 days in seconds.
END_DATE = (2013, 10, 14,)
LEGACY_HITS = (
    ('m1', (5, 3, _to_timestamp(2013, 10, 1),
           _to_timestamp(*END_DATE), INTERVAL,),),
    ('m2', (5, 3, _to_timestamp(2013, 10, 1),
           _to_timestamp(*END_DATE), INTERVAL,),),
    ('m3', (5, 3, _to_timestamp(2013, 10, 1),
           _to_timestamp(*END_DATE), INTERVAL,),),
    # Case for all hits being recent.
    ('m4', (5, 5, _to_timestamp(2013, 10, 1),
           _to_timestamp(*END_DATE), INTERVAL,),),
    # Case for start time within the recent timeframe.
    ('m5', (5, 5, _to_timestamp(2013, 10, 10),
           _to_timestamp(*END_DATE), INTERVAL,),),
    # Case for a module without an entry in the database.
    ('m6', (5, 5, _to_timestamp(2013, 10, 1),
            _to_timestamp(*END_DATE), INTERVAL,),),
    )


class HitCountMigrationTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.db_connection_string = DB_CONNECTION_STRING
        # Enforce a blank slate.
        with psycopg2.connect(cls.db_connection_string) as db_connection:
            with db_connection.cursor() as cursor:
                cursor.execute("DROP SCHEMA public CASCADE; "
                               "CREATE SCHEMA public;")
        os.environ['PGTZ'] = TZ

    @classmethod
    def tearDownClass(cls):
        del os.environ['PGTZ']


    def setUp(self):
        from cnxarchive.database import initdb, CONNECTION_SETTINGS_KEY
        initdb({CONNECTION_SETTINGS_KEY: self.db_connection_string})
        with psycopg2.connect(self.db_connection_string) as db_connection:
            with db_connection.cursor() as cursor:
                cursor.execute(SQL_FOR_TESTED_DOCUMENTS)

    def tearDown(self):
        with psycopg2.connect(self.db_connection_string) as db_connection:
            with db_connection.cursor() as cursor:
                cursor.execute("DROP SCHEMA public CASCADE;"
                               "CREATE SCHEMA public;")

    def call_target(self):
        from ..upgrades.migrate_hit_counts import migration
        with psycopg2.connect(self.db_connection_string) as db_connection:
            migration.do_migration(LEGACY_HITS, db_connection)

    def test_migration(self):
        self.call_target()
        with psycopg2.connect(self.db_connection_string) as db_connection:
            with db_connection.cursor() as cursor:
                cursor.execute("select start_timestamp, end_timestamp, hits "
                               "from document_hits where documentid = 4 "
                               "order by start_timestamp asc;")
                m3_rows = cursor.fetchall()
        interval = datetime.timedelta(seconds=INTERVAL)
        # Test the m3 row for insertion of both past and recent.
        self.assertEqual(len(m3_rows), 2)
        start, stop, hits = m3_rows[0]
        self.assertEqual(stop.date(), datetime.date(*END_DATE) - interval)
        self.assertEqual(hits, 2)
        # ... and now the recent.
        start, stop, hits = m3_rows[1]
        self.assertEqual(start.date(), datetime.date(*END_DATE) - interval)
        self.assertEqual(stop.date(), datetime.date(*END_DATE))
        self.assertEqual(hits, 3)

    def test_migrate_recent_only(self):
        self.call_target()
        with psycopg2.connect(self.db_connection_string) as db_connection:
            with db_connection.cursor() as cursor:
                cursor.execute("select start_timestamp, end_timestamp, hits "
                               "from document_hits where documentid = 5;")
                m4_rows = cursor.fetchall()
        interval = datetime.timedelta(seconds=INTERVAL)
        # Test the m4 row for insertion of only the recent rows.
        self.assertEqual(len(m4_rows), 1)
        start, stop, hits = m4_rows[0]
        self.assertEqual(start.date(), datetime.date(*END_DATE) - interval)
        self.assertEqual(stop.date(), datetime.date(*END_DATE))
        self.assertEqual(hits, 5)

    def test_migrate_overlapping_start(self):
        self.call_target()
        with psycopg2.connect(self.db_connection_string) as db_connection:
            with db_connection.cursor() as cursor:
                cursor.execute("select start_timestamp, end_timestamp, hits "
                               "from document_hits where documentid = 6;")
                m5_rows = cursor.fetchall()
        interval = datetime.timedelta(seconds=INTERVAL)
        # Test the m5 row for insertion of only the recent rows,
        #   because the module was recently published (date overlap).
        self.assertEqual(len(m5_rows), 1)
        start, stop, hits = m5_rows[0]
        self.assertEqual(start.date(), datetime.date(2013, 10, 10))
        self.assertEqual(stop.date(), datetime.date(*END_DATE))
        self.assertEqual(hits, 5)


class CLITestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # This test case doesn't actually read or write to the database,
        #   it only makes a connection, which means the db needs to exist.
        cls.db_connection_string = DB_CONNECTION_STRING

    def setUp(self):
        # Mock the 'do_migration' function, because that is tested elsewhere.
        # It is only important to test the interface.
        from cnxupgrade.upgrades.migrate_hit_counts import migration
        orig_func = migration.do_migration
        self.addCleanup(setattr, migration, 'do_migration', orig_func)
        setattr(migration, 'do_migration', self.grab_params)

    def grab_params(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.addCleanup(delattr, self, 'args')
        self.addCleanup(delattr, self, 'kwargs')

    def test_interface(self):
        tmpfile_pointer, tmpfile_path = tempfile.mkstemp()
        with open(tmpfile_path, 'w') as fb:
            writer = csv.writer(fb)
            for mid, info in LEGACY_HITS:
                row = list(info)
                row.insert(0, mid)
                writer.writerow(row)
        kwargs = {'db_conn_str': self.db_connection_string,
                  'input': open(tmpfile_path, 'r'),
                  }
        from cnxupgrade.upgrades.migrate_hit_counts import migration
        migration.cli_command(**kwargs)

        ids = [x[0] for x in self.args[0]]
        ids.sort()
        self.assertEqual(ids, ['m1', 'm2', 'm3', 'm4', 'm5', 'm6'])
        # Check that everything ended up as an int.
        types = set([type(x) for x in self.args[0][0][1]])
        self.assertEqual(types, set([int]))
