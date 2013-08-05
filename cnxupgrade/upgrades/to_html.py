# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Upgrades for munging/transforming Connexions XML formats to HTML."""

__all__ = ('cli_loader',)


def cli_command():
    """The command used by the CLI to invoke the upgrade logic."""
    pass


def cli_loader(parser):
    """Used to load the CLI toggles and switches."""
    return cli_command
