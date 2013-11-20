# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import os
from io import BytesIO
import re
from lxml import etree
from .utils import apply_xslt, cnxml_parser, determine_cnxml_version


__all__ = ('upgrade_document',)


here = os.path.abspath(os.path.dirname(__file__))
resources = os.path.join(here, 'resources')
UPGRADE_05_TO_06_XSL = os.path.join(resources, 'cnxml05to06.xsl')
UPGRADE_06_TO_07_XSL = os.path.join(resources, 'cnxml06to07.xsl')
##UPGRADE_05_TO_06_XSL = 'http://cnx.rice.edu/technology/cnxml/stylesheet/cnxml05to06.xsl'
##UPGRADE_06_TO_07_XSL = 'http://cnx.rice.edu/technology/cnxml/stylesheet/cnxml06to07.xsl'

NAMESPACES = {
    'cnx': 'http://cnx.rice.edu/cnxml',
    'md': 'http://cnx.rice.edu/mdml/0.4',
    'bib': 'http://bibtexml.sf.net/',
    'm': 'http://www.w3.org/1998/Math/MathML',
    'x': 'http://www.w3.org/1999/xhtml',
    'q': 'http://cnx.rice.edu/qml/1.0',
    }

def add_namespace(source):
    decls = []
    for ns in NAMESPACES:
        tag = '<{}:'.format(ns)
        close_tag = '</{}:'.format(ns)
        xmlns = 'xmlns:{}='.format(ns)
        if tag in source and xmlns not in source:
            decls.append('xmlns:{}="{}"'.format(ns, NAMESPACES[ns]))
    if decls:
        # Find the first tag in the xml document and add the namespace
        # declarations
        source = re.sub('(<[a-z]+)([ >])', r'\1 {}\2'.format(' '.join(decls)),
                        source, count=1)
    return source

def upgrade_document(source, version=None):
    """Turn older CNXML (0.5/0.6) into newer (0.7).
    Checks version to determine if upgrade is needed.
    With a newer version, we may add additional stylesheets to the pipeline.
    Return tuple of (new_source, boolean_was_converted)
    """
    if version is None:
        version = determine_cnxml_version(source)

    stylesheets = []
    if version == '0.7':
        pass # Do nothing. 0.7 is the latest
    elif version == '0.6':
        stylesheets.append(UPGRADE_06_TO_07_XSL)
    else:
        stylesheets.append(UPGRADE_05_TO_06_XSL)
        stylesheets.append(UPGRADE_06_TO_07_XSL)

    source = add_namespace(source)
    try:
        doc = etree.ElementTree(etree.fromstring(source, parser=cnxml_parser))
    except etree.XMLSyntaxError as exc:
        return None, False, exc.message
    messages = BytesIO()
    result = apply_xslt(doc, stylesheets, messages)
    messages.seek(0)
    return result, True, messages.read()
