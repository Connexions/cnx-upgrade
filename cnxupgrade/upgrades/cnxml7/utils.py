# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import xml.parsers.expat
from io import BytesIO
from lxml import etree


__all__ = (
    'apply_xslt', 'cnxml_parser',
    'determine_cnxml_version', 'normalize_xml',
    )


CHUNK_SIZE = 400


class VersionRecognizer:
    """Class to do CNXML version recognition."""
    # Copied from Products.CNXMLDocument.CNXMLVersionRecognizer

    def __init__(self, doctext):
        self._doctext = doctext
        self.version = None
        self.p = xml.parsers.expat.ParserCreate()
        self.p.StartElementHandler = self.start_element
        self.p.StartDoctypeDeclHandler = self.start_doctype

    def start_element(self, name, attrs):
        if name == "document":
            if attrs.has_key('cnxml-version'):
                self.version = attrs['cnxml-version']

    def start_doctype(self, doctypeName, systemId, publicId,
                      has_internal_subset):
        if publicId and publicId.find("CNXML") != -1:
            # publicId like "-//CNX//DTD CNXML 0.5//EN"
            dtdstr = publicId.split("//")[2]
            dtdstr = dtdstr.split()[2]
            self.version = dtdstr

    def get_version(self):
        """Attempt to recognize the version of a CNXML document.
        Specifically focused on 0.6+, but we also try to detect 0.5/0.4 by doctype.
        Will return strings like "0.5" or "0.6". None if not detectable.
        """
        # expat can parse in chunks; do this so we only handle as much as we need to,
        # which is probably only one chunk
        doctext = self._doctext
        startat = 0
        endidx = len(doctext)
        while not self.version and startat < endidx:
            upto = startat + CHUNK_SIZE
            chunk = doctext[startat:upto]
            if type(chunk) is unicode:  # expat should be able to handle unicode, but chokes, so go old-style
                chunk = chunk.encode('utf-8')
            
            try:
                self.p.Parse(chunk)
            except xml.parsers.expat.ExpatError:
                return None
            startat = upto
        return self.version


def determine_cnxml_version(source):
    """Given a CNXML document as ``source``,
    determine what version of CNXML is being used.
    """
    recognizer = VersionRecognizer(source)
    return recognizer.get_version()


XML_PARSER_KWARGS = dict(load_dtd=True, resolve_entities=True,
                         no_network=True, attribute_defaults=False)
cnxml_parser = etree.XMLParser(**XML_PARSER_KWARGS)
xml_parser = etree.XMLParser(**XML_PARSER_KWARGS)


def normalize_xml(xml):
    """Given an xml string as ``xml`` expanding entities and recode in UTF-8.
    """
    doc = etree.parse(BytesIO(xml), parser=cnxml_parser)
    normalized_xml = etree.tostring(doc.getroot())
    return normalized_xml


def apply_xslt(xml, stylesheets, messages=None):
    """Apply a stylesheet (or list of stylesheets) given as ``stylesheets``
    to an XML document given as ``xml``. The stylesheets must be urls to
    XSLT files.
    """
    if not isinstance(stylesheets, (list, set, tuple,)):
        stylesheets = [stylesheets]

    xml_in = xml
    xml_out = xml
    for stylesheet in stylesheets:
        ss_xml = etree.parse(stylesheet, parser=xml_parser)
        xslt = etree.XSLT(ss_xml)
        if xslt.error_log and messages is not None:
            for entry in xslt.error_log:
                messages.write("{}\n".format(entry))
        xml_out = xslt(xml_in)
        # Pipeline input/output
        xml_in = xml_out

    return str(xml_out)
