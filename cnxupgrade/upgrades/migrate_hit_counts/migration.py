# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""\
Migrates hit counts from legacy to cnx-archive's database at
schema version 1.
"""
import os
import sys
import csv
import argparse
from datetime import datetime, timedelta

import psycopg2


__all__ = ('cli_loader', 'do_migration',)

here = os.path.abspath(os.path.dirname(__file__))
RESOURCES_DIRECTORY = os.path.join(here, 'resources')
EXTRACTION_SCRIPT_PATH = os.path.join(RESOURCES_DIRECTORY, 'hit_extractor.py')


def get_ident(legacy_id, cursor):
    cursor.execute("SELECT module_ident FROM latest_modules "
                   "WHERE moduleid = %s", (legacy_id,))
    try:
        ident = cursor.fetchone()[0]
    except TypeError:  # None
        ident = None
    return ident


def do_migration(hits, db_connection):
    """Given a list of hit objects migrate them to the SQL document_hits
    table.
    """
    with db_connection.cursor() as cursor:
        for legacy_id, info in hits:
            document_id = get_ident(legacy_id, cursor)
            if document_id is None:
                continue
            past_hits, recent_hits, start, end, interval = info
            start = datetime.fromtimestamp(start)
            end = datetime.fromtimestamp(end)
            interval = timedelta(seconds=interval)

            if start < end - interval and (past_hits - recent_hits) > 0:
                # Insert past hits
                payload = (document_id, start, end - interval,
                           past_hits - recent_hits,)
                cursor.execute("INSERT into document_hits "
                               "VALUES (%s, %s, %s, %s)",
                               payload)
            # Insert recent hits
            start = start > end - interval and start or end - interval
            payload = (document_id, start, end, recent_hits,)
            cursor.execute("INSERT into document_hits "
                           "VALUES (%s, %s, %s, %s)",
                           payload)
    db_connection.commit()


def cli_command(**kwargs):
    """The command used by the CLI to invoke the upgrade logic."""
    connection_string = kwargs['db_conn_str']
    input = kwargs['input']
    hits = [(row[0], [int(x) for x in row[1:]],) for row in csv.reader(input)]
    with psycopg2.connect(connection_string) as db_connection:
        do_migration(hits, db_connection)


def cli_loader(parser):
    """Used to load the CLI toggles and switches."""
    parser.add_argument('--input', type=argparse.FileType('r'),
                        default=sys.stdin,
                        help="CSV extracted using '{}' on the zope instance" \
                            .format(EXTRACTION_SCRIPT_PATH))
    return cli_command
