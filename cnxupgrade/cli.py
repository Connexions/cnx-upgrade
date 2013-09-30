#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""The command-line interface for upgrading cnx-* package databases."""
import os
import sys
import argparse

from . import upgrades


DESCRIPTION = __doc__
DEFAULT_PSYCOPG_CONNECTION_STRING = "dbname=cnxarchive user=cnxarchive " \
                                    "password=cnxarchive host=localhost " \
                                    "port=5432"


def main(argv=None):
    """Main functions used to interface directly with the user."""
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument('--db-conn-str',
                        default=DEFAULT_PSYCOPG_CONNECTION_STRING,
                        help="a psycopg2 db connection string")
    parser.add_argument('--id-select-query',
                        default=None,
                        help="an SQL query that returns module_idents to be converted")
    subparsers = parser.add_subparsers(help="upgrade step")
    upgrades.load_cli(subparsers)

    if len(sys.argv) < 2 or sys.argv[0].startswith('-'):
        sys.argv.insert(1, upgrades.get_default_cli_command_name())
    args = parser.parse_args(argv)

    cmmd = args.cmmd
    return cmmd(**vars(args))


if __name__ == '__main__':
    sys.exit(main())
