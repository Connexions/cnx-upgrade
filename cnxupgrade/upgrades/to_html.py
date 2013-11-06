# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Upgrades for munging/transforming Connexions XML formats to HTML."""
import logging
import sqlite3

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


HUMAN_READABLE_MESSAGE = "While attempting to transform the content we ran into an error: "
EVENT_DB_SCHEMA = (
    "CREATE TABLE messages (message_id INTEGER PRIMARY KEY ASC, message TEXT NOT NULL);",
    "CREATE TABLE problems (module_ident INTEGER PRIMARY KEY, message_id INTEGER NOT NULL, CONSTRAINT message_id_ref FOREIGN KEY (message_id) REFERENCES messages (message_id) ON DELETE CASCADE);",
    )


class EventCapture:
    """Given a module_ident as ``mid`` and an optional message,
    capture the event in a meaningful way for later processing.
    """

    def __init__(self, db_connection_string):
        self.conn_str = db_connection_string
        self.conn = sqlite3.connect(self.conn_str)
        self.cursor = self.conn.cursor()
        for statement in EVENT_DB_SCHEMA:
            self.cursor.execute(statement)
        self.conn.commit()

    def __call__(self, mid, message=None):
        if message is None:
            return
        elif message.startswith(HUMAN_READABLE_MESSAGE):
            message = message[len(HUMAN_READABLE_MESSAGE):]
        self.cursor.execute("select message_id from messages where message = ?", (message,))
        try:
            message_id = self.cursor.fetchone()[0]
        except TypeError:  # None type
            self.cursor.execute("insert into messages (message) values (?);",
                                (message,))
            self.cursor.execute("select last_insert_rowid() from messages;")
            message_id = self.cursor.fetchone()[0]
        self.cursor.execute("insert into problems values (?, ?);",
                            (mid, message_id,))

    def report(self):
        self.cursor.execute("select messages.message, group_concat(problems.module_ident) from messages natural left join problems group by messages.message")
        aggregated_problems = self.cursor.fetchall()
        logger.info("Message aggregation report:")
        for (msg, mids) in aggregated_problems:
            document_count = len(mids.split(','))
            logger.info("-- '{}' for {} documents at ({})" \
                        .format(msg, document_count, mids))


def cli_command(**kwargs):
    """The command used by the CLI to invoke the upgrade logic."""
    connection_string = kwargs['db_conn_str']
    id_select_query = kwargs['id_select_query']

    capture_event = EventCapture(':memory:')
    with psycopg2.connect(connection_string) as db_connection:
        [capture_event(mid, msg)
         for mid, msg in produce_html_for_modules(db_connection,
                                                  id_select_query)
         ]
    capture_event.report()


def cli_loader(parser):
    """Used to load the CLI toggles and switches."""
    parser.add_argument('--id-select-query', default=DEFAULT_ID_SELECT_QUERY,
                        help="an SQL query that returns module_idents to " \
                             "be converted")
    return cli_command
