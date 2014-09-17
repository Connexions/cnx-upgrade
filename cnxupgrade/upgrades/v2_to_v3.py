# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Upgrades the schema from version 2 to version 3.

The Foreign Data Wrapper (FDW) is set up to create a user mapping
between the databases using the current user this script uses when
connecting to the archive database and the user configured in
the osc-accounts connection string. Any additional configurations will
need to be added manually.
"""

__all__ = ('cli_loader', 'do_upgrade',)


def do_upgrade(db_connection_string, oscaccounts_connection_string):
    """Does the upgrade from version 2 to version 3."""
    # Make something that looks like the cnx-archive settings dictionary.
    from cnxarchive import config
    settings = {
        config.CONNECTION_STRING: db_connection_string,
        config.ACCOUNTS_CONNECTION_STRING: oscaccounts_connection_string,
        }

    # Call the function that initializes the foreign data wrapper
    # SQL statements.
    from cnxarchive.database import _init_foreign_db
    _init_foreign_db(settings)


def cli_command(**kwargs):
    """The command used by the CLI to invoke the upgrade logic."""
    connection_string = kwargs['db_conn_str']
    oscaccounts_connection_string = kwargs['accounts_conn_str']
    do_upgrade(connection_string, oscaccounts_connection_string)


def cli_loader(parser):
    """Used to load the CLI toggles and switches."""
    parser.add_argument('--accounts-conn-str',
                        help="a psycopg2 db connection string used when " \
                             "connecting to the osc-accounts database.")
    return cli_command
