# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###

from io import StringIO
import unittest
import urllib2

from . import (
        DB_CONNECTION_STRING,
        postgresql_fixture, db_connect,
        )


class MigrateGoogleAnalyticsTestCase(unittest.TestCase):
    fixture = postgresql_fixture

    @db_connect
    def setUp(self, cursor):
        self.fixture.setUp()

        # set up test data
        cursor.execute('''
INSERT INTO modules VALUES (1, 'Collection', 'col11406', 'e79ffde3-7fb4-4af3-9ec8-df648b391597', '1.7', 'College Physics', '2013-07-31 14:07:20.342798-05', '2013-07-31 14:07:20.342798-05', NULL, 11, '', '', '', NULL, NULL, 'en', '{e5a07af6-09b9-4b74-aa7a-b7510bee90b8}', '{e5a07af6-09b9-4b74-aa7a-b7510bee90b8, 1df3bab1-1dc7-4017-9b3a-960a87e706b1}', '{9366c786-e3c8-4960-83d4-aec1269ac5e5}', NULL, 'UA-XXXXX-Y', NULL, 1, 7);
INSERT INTO modules VALUES (2, 'Collection', 'col11594', 'a0e7e11c-3a81-4b57-995f-e722d308e122', '1.7', 'College Physics', '2013-07-31 14:07:20.342798-05', '2013-07-31 14:07:20.342798-05', NULL, 11, '', '', '', NULL, NULL, 'en', '{e5a07af6-09b9-4b74-aa7a-b7510bee90b8}', '{e5a07af6-09b9-4b74-aa7a-b7510bee90b8, 1df3bab1-1dc7-4017-9b3a-960a87e706b1}', '{9366c786-e3c8-4960-83d4-aec1269ac5e5}', NULL, NULL, NULL, 1, 7);
        ''')

        # Mock command line arguments for migrate_ga
        self.argv = ['--db-conn-str', DB_CONNECTION_STRING]

        # Mock response from plone site
        # responses should be assigned to self.responses by individual tests
        self.responses = ['']
        self.response_id = -1
        def urlopen(url):
            self.response_id += 1
            return StringIO(unicode(self.responses[self.response_id]))
        original_urlopen = urllib2.urlopen
        urllib2.urlopen = urlopen
        self.addCleanup(setattr, urllib2, 'urlopen', original_urlopen)

    def tearDown(self):
        self.fixture.tearDown()

    def call_target(self):
        from ..upgrades.migrate_ga import cli_command
        return cli_command(db_conn_str=DB_CONNECTION_STRING)

    @db_connect
    def get_ga_by_module_id(self, cursor, moduleid):
        cursor.execute('SELECT google_analytics FROM modules WHERE moduleid = %s',
                [moduleid])
        return cursor.fetchone()[0]

    def test(self):
        self.responses = ['', 'UA-30227798-1']
        self.call_target()
        self.assertEqual(self.get_ga_by_module_id('col11406'), 'UA-30227798-1')
        self.assertEqual(self.get_ga_by_module_id('col11594'), None)
