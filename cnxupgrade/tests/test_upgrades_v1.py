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

    def test_import(self):
        # XXX tick tick boom
        from ..upgrades.v1 import do_upgrade
        self.assertTrue(callable(do_upgrade))
