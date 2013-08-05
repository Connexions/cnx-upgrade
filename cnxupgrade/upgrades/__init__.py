#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""\
Package that houses the individual upgrade steps as modules.

The utilities found in the root of this package provide magical
functionality for upgrade CLI loading, default upgrade discover,
and upgrade registration.

"""


__all__ = ('load_cli', 'get_default',)


def load_cli(parser):
    """Given a parser, load the upgrades as CLI subcommands"""
    pass


def get_default():
    """Discover and return the default upgrade name (same as the
    subcommand name).
    """
    return None
