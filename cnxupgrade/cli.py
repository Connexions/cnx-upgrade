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
    parser.add_argument('-p', '--psycopg-conn-str',
                        default=DEFAULT_PSYCOPG_CONNECTION_STRING,
                        help="a psycopg2 connection string")
    upgrades.load_cli(parser)
    args = parser.parse_args(argv)

    try:
        cmmd = args.cmmd
    except AttributeError:
        cmmd = upgrades.get_default()

    return cmmd(**vars(args))


if __name__ == '__main__':
    sys.exit(main())
