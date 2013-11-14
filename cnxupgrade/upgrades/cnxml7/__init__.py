# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import sys
import argparse
import csv

import psycopg2

from .main import main


__all__ = ('cli_loader',)


def cli_command(**kwargs):
    """The command used by the CLI to invoke the upgrade logic."""
    connection_string = kwargs['db_conn_str']
    report = csv.writer(kwargs['report_file'])

    with psycopg2.connect(connection_string) as db_connection:
        for processed in main(db_connection):
            ##mid, version, ident, xml_version, state, message = processed
            ##print("%7s @ %4s - %s (%s) - %s - %s" % processed)
            report.writerow(processed)


def cli_loader(parser):
    """Used to load the CLI toggles and switches."""
    parser.add_argument('--report-file', type=argparse.FileType('w'),
                        default=sys.stdout,
                        help="output file (defaults to stdout)")
    return cli_command
