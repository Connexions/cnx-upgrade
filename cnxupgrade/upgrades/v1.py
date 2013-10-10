# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Upgrades the schema form version 0 to version 1."""
import os
import psycopg2

__all__ = ('cli_loader', 'do_upgrade',)

here = os.path.abspath(os.path.dirname(__file__))
RESOURCES_DIRECTORY = os.path.join(here, 'v1-resources')


def do_upgrade(db_connection):
    """Does the upgrade from version 0 to version 1.

    This includes:

    - Adds a ``uuid_generate_v4`` function to the database for creating
      default UUID values.
    - Alter the ``modules`` and ``latest_modules`` tables to add
      a UUID column. And we make sure the UUID values between the two
      tables match the respective modules.
    - Alter the ``modules`` and ``latest_modules`` tables to add
      the major and minor version columns. And we parse the current text
      version to populate these new values.
    - Alter the ``modules`` and ``latest_modules`` tables to add
      the ``buylink`` and ``google_analytics`` columns.
    - Adjusts the ``update_latest`` trigger function to include the new
      columns
    - Adds the ``trees`` table and related population code.
    - Adds the ``shred_collxml`` function for shredding collection.xml
      documents to ``trees`` table records.
    - Adds the ``tree_to_json`` function.
    """
    with db_connection.cursor() as cursor:
        # Make sure to look at the comments in the SQL file.
        alterations_filepath = os.path.join(RESOURCES_DIRECTORY,
                                            'alterations.sql')
        with open(alterations_filepath, 'rb') as alterations:
            cursor.execute(alterations.read())
    db_connection.commit()


def cli_command(**kwargs):
    """The command used by the CLI to invoke the upgrade logic."""
    connection_string = kwargs['db_conn_str']
    with psycopg2.connect(connection_string) as db_connection:
        do_upgrade(db_connection)


def cli_loader(parser):
    """Used to load the CLI toggles and switches."""
    return cli_command
