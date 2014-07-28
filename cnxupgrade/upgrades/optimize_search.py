# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Adds search optimization indexes to the cnx-archive database."""
import os
import psycopg2
from cnxarchive.database import DB_SCHEMA_FILES, _read_sql_file

__all__ = ('cli_loader', 'do_upgrade',)

here = os.path.abspath(os.path.dirname(__file__))
SQL_UPGRADE = """\
CREATE INDEX moduletags_module_ident_idx ON moduletags (module_ident);
CREATE UNIQUE INDEX moduletags_module_ident_tagid_idx ON moduletags (module_ident, tagid);
"""

def do_upgrade(db_connection):
    with db_connection.cursor() as cursor:
        cursor.execute(SQL_UPGRADE)
    db_connection.commit()


def cli_command(**kwargs):
    """The command used by the CLI to invoke the upgrade logic."""
    connection_string = kwargs['db_conn_str']
    with psycopg2.connect(connection_string) as db_connection:
        do_upgrade(db_connection)


def cli_loader(parser):
    """Used to load the CLI toggles and switches."""
    return cli_command
