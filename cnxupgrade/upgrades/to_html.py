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

DEFAULT_ID_SELECT_QUERY = """\
SELECT module_ident FROM modules AS m
  WHERE portal_type = 'Module'
        AND NOT EXISTS (SELECT 1 FROM module_files
                          WHERE module_ident = m.module_ident
                                AND filename = 'index.html');
"""
DEFAULT_FILENAME = 'index_auto_generated.cnxml'


def produce_html_for_modules(db_connection,
                             id_select_query=DEFAULT_ID_SELECT_QUERY,
                             source_filename='index.cnxml',
                             overwrite_html=False):
    """Produce HTML files of existing module documents. This will
    do the work on all modules in the database.

    Yields a state tuple after each module is handled.
    The state tuple contains the id of the document that was transformed
    and either None when no errors have occured
    or a message containing information about the issue.
    """
    with db_connection.cursor() as cursor:
        cursor.execute(id_select_query)
        # Note, the "ident" is different from the "id" in our tables.
        idents = [v[0] for v in cursor.fetchall()]

    for ident in idents:
        with db_connection.cursor() as cursor:
            try:
                message = produce_html_for_module(db_connection, cursor, ident,
                                                  source_filename,
                                                  overwrite_html)
            except Exception as exc:
                message = exc.message
        yield (ident, message)
    raise StopIteration


def produce_html_for_abstracts(db_connection,
                               id_select_query=DEFAULT_ID_SELECT_QUERY):
    """Produces HTML for abstract content.

    Yields a state tuple after each module is handled.
    The state tuple contains the id of the document that was transformed
    and either None when no errors have occured
    or a message containing information about the issue.
    """
    with db_connection.cursor() as cursor:
        cursor.execute(id_select_query)
        # Note, the "ident" is different from the "id" in our tables.
        idents = [v[0] for v in cursor.fetchall()]

    for ident in idents:
        with db_connection.cursor() as cursor:
            try:
                message = produce_html_for_abstract(db_connection, cursor,
                                                    ident)
            except Exception as exc:
                message = exc.message
        yield (ident, message)
    raise StopIteration


def cli_command(**kwargs):
    """The command used by the CLI to invoke the upgrade logic."""
    connection_string = kwargs['db_conn_str']
    id_select_query = kwargs['id_select_query']
    overwrite_html = kwargs['overwrite_html']
    filename = kwargs['filename']
    should_transform_abstracts = kwargs.get('no_abstracts', False)
    with psycopg2.connect(connection_string) as db_connection:
        for x in produce_html_for_modules(db_connection, id_select_query,
                                          source_filename=filename,
                                          overwrite_html=overwrite_html):
            print x
        if should_transform_abstracts:
           print "Transforming abstracts..."
           for x in produce_html_for_abstracts(db_connection, id_select_query):
               print x


def cli_loader(parser):
    """Used to load the CLI toggles and switches."""
    parser.add_argument('--id-select-query', default=DEFAULT_ID_SELECT_QUERY,
                        help="an SQL query that returns module_idents to " \
                             "be converted")
    parser.add_argument('--force', dest='overwrite_html', action='store_true',
                        default=False,
                        help='overwrite existing HTML files in the database')
    parser.add_argument('--filename', default=DEFAULT_FILENAME,
                        help='filename to use as source in the transformation,'
                             ' default {}'.format(DEFAULT_FILENAME))
    parser.add_argument('--no-abstracts', action='store_false',
                        help='do not transform abstracts')
    return cli_command
