# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Upgrades for munging/transforming Connexions XML formats to HTML."""

import psycopg2

from cnxarchive.to_html import *


__all__ = ('cli_loader',)


def cli_command(**kwargs):
    """The command used by the CLI to invoke the upgrade logic."""
    connection_string = kwargs['db_conn_str']
    id_select_query = kwargs['id_select_query']
    with psycopg2.connect(connection_string) as db_connection:
        # TODO Ideally, logging would be part of these for loops.
        # [x for x in produce_html_for_collections(db_connection)]
        for x in produce_html_for_modules(db_connection, id_select_query):
            print x


def cli_loader(parser):
    """Used to load the CLI toggles and switches."""
    parser.add_argument('--id-select-query', default=DEFAULT_ID_SELECT_QUERY,
                        help="an SQL query that returns module_idents to " \
                             "be converted")
    return cli_command
