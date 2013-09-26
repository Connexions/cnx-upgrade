# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import os
import sys


__all__ = ('DB_CONNECTION_STRING', 'TESTING_DATA_DIRECTORY',)


here = os.path.abspath(os.path.dirname(__file__))
_DB_CONNECTION_STRING_ENV_VAR_NAME = 'DB_CONNECTION_STRING'
_DB_CONNECTION_STRING_CLI_OPT_NAME = '--db-conn-str'
try:
    DB_CONNECTION_STRING = os.environ[_DB_CONNECTION_STRING_ENV_VAR_NAME]
except:
    try:
        arg_pos = sys.argv.index(_DB_CONNECTION_STRING_CLI_OPT_NAME)
    except ValueError:
        raise RuntimeError("MUST supply a means to connect to the database, "
                           "either via the environment variable '{}' or the "
                           "command-line option '{}'." \
                               .format(_DB_CONNECTION_STRING_ENV_VAR_NAME,
                                       _DB_CONNECTION_STRING_CLI_OPT_NAME)
                           )
    DB_CONNECTION_STRING = sys.argv[arg_pos+1]
TESTING_DATA_DIRECTORY = os.path.join(here, 'data')
