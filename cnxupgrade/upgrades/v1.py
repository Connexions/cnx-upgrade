# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Upgrades the schema form version 0 to version 1."""
import os

__all__ = ('do_upgrade')

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
    """
    with db_connection.cursor() as cursor:
        # Create the UUID generation function.
        uuid_function_filepath = os.path.join(RESOURCES_DIRECTORY,
                                              'uuid-function.sql')
        with open(uuid_function_filepath, 'rb') as uuid_function:
            cursor.execute(uuid_function.read())
        uuid_alteration_filepath = os.path.join(RESOURCES_DIRECTORY,
                                                'uuid-alteration.sql')
        with open(uuid_alteration_filepath, 'rb') as uuid_alteration:
            cursor.execute(uuid_alteration.read())

        db_connection.commit()
