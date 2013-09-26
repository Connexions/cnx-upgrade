# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Upgrades the schema form version 0 to version 1."""


__all__ = ('do_upgrade')


def do_upgrade(db_connection):
    """Does the upgrade from version 0 to version 1.

    This includes:

    - Adds a ``uuid_generate_v4`` function to the database for creating
      default UUID values.
    - Alter the ``modules`` and ``latest_modules`` tables to add
      a UUID column. And we make sure the UUID values between the two
      tables match the respective modules.
    """
    pass
