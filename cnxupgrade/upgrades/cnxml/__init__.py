# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Upgrades CNXML documents to the latest CNXML version."""


UPGRADE_05_TO_06_XSL = \
    "http://cnx.rice.edu/technology/cnxml/stylesheet/cnxml05to06.xsl"
UPGRADE_06_TO_07_XSL = \
    "http://cnx.rice.edu/technology/cnxml/stylesheet/cnxml06to07.xsl"


__all__ = (
    'cli_loader',
    )


def determine_version(cnxml):
    """Given the source document as ``cnxml``,
    determine and return the version.
    """
    return None


def upgrade(cnxml):
    """Given the source document as ``cnxml``,
    return an upgraded version of the cnxml document.
    """
    return cnxml


def cli_command():
    """The command used by the CLI to invoke the upgrade logic."""
    pass


def cli_loader(parser):
    """Used to load the CLI toggles and switches."""
    return cli_command
