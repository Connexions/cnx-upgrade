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

Upgrades in this package are required to have a ``cli_loader`` function
that is given a subparser to add additional parsing options, if necessary,
and must return a function for the cli to hand arguments to
(conventionally named, ``cli_command``).

"""
import sys

from .create_collection_minor_versions import create_collection_minor_versions


__all__ = ('load_cli', 'get_default', 'create_collection_minor_versions')


# TODO Make upgrade discovery magical. In other words, load the upgrade
#      modules through scanning rather than reading a constant.
UPGRADES = (
    'to_html',
    'v1',
    'migrate_hit_counts',
    )
# TODO Look this up via setuptools entry-point so that it only needs to be
#      changed at the distribution level on say release or tag.
DEFAULT_UPGRADE = 'to_html'


def _import_attr_n_module(module_name, attr):
    """From the given ``module_name`` import
    the value for ``attr`` (attribute).
    """
    __import__(module_name)
    module = sys.modules[module_name]
    attr = getattr(module, attr)
    return attr, module

def _import_loader(module_name):
    """Given a ``module`` name import the cli loader."""
    loader, module = _import_attr_n_module(module_name, 'cli_loader')
    return loader, module.__doc__


def load_cli(subparsers):
    """Given a parser, load the upgrades as CLI subcommands"""
    for upgrade_name in UPGRADES:
        module = 'cnxupgrade.upgrades.{}'.format(upgrade_name)
        loader, description = _import_loader(module)
        parser = subparsers.add_parser(upgrade_name,
                                       help=description)
        command = loader(parser)
        if command is None:
            raise RuntimeError("Failed to load '{}'.".format(upgrade_name))
        parser.set_defaults(cmmd=command)


def get_default_cli_command_name():
    """Discover and return the default upgrade name (same as the
    subcommand name).
    """
    return DEFAULT_UPGRADE
