# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Upgrades for munging/transforming Connexions XML formats to HTML."""
import logging
import psycopg2

from cnxarchive.to_html import *


__all__ = ('cli_loader',)

DEFAULT_ID_SELECT_QUERY = """\
SELECT module_ident FROM modules AS m
  WHERE portal_type = 'Module'
        AND NOT EXISTS (SELECT 1 FROM module_files
                          WHERE module_ident = m.module_ident
                                AND filename = 'index.html');
"""

logger = logging.getLogger('to_html')
logger.setLevel(logging.DEBUG)
console_log_handler = logging.StreamHandler()
console_log_handler.setLevel(logging.DEBUG)
logger.addHandler(console_log_handler)


def cli_command(**kwargs):
    """The command used by the CLI to invoke the upgrade logic."""
    connection_string = kwargs['db_conn_str']
    id_select_query = kwargs['id_select_query']
    with psycopg2.connect(connection_string) as db_connection:
        # TODO Ideally, logging would be part of these for loops.
        # [x for x in produce_html_for_collections(db_connection)]
        for (mid, msg) in produce_html_for_modules(db_connection, id_select_query):
            log.debug("module_ident = {}, message = '{}'".format(mid, message))


def cli_loader(parser):
    """Used to load the CLI toggles and switches."""
    parser.add_argument('--id-select-query', default=DEFAULT_ID_SELECT_QUERY,
                        help="an SQL query that returns module_idents to " \
                             "be converted")
    return cli_command
