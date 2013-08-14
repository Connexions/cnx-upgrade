# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""A CNXML document version recognizer."""
import xml.parsers.expat


CHUNK_SIZE = 400


class VersionRecognizer:
    """Class to do CNXML version recognition.
    Implmented with Python expat.
    Construct with 'doctext' as text of CNXML document, and call 'getVersion'.
    You probably don't need to keep the class around, so call anonymously::
      Recognizer(text).getVersion()
    """

    def __init__(self, doctext):
        self._doctext = doctext
        self.version = None

        # expat parsers are only for a single use, apparently,
        #   so create them on the fly
        self.p = xml.parsers.expat.ParserCreate()
        self.p.StartElementHandler     = self.start_element
        self.p.StartDoctypeDeclHandler = self.start_doctype

    def __call__(self):
        """Attempt to recognize the version of a CNXML document.
        Specifically focused on 0.6+, but we also try to detect 0.5/0.4
        by doctype.

        Will return strings like "0.5" or "0.6". None if not detectable.
        """
        # expat can parse in chunks;
        #   do this so we only handle as much as we need to,
        #   which is probably only one chunk
        doctext = self._doctext
        startat = 0
        endidx = len(doctext)
        while not self.version and startat < endidx:
            upto = startat + CHUNK_SIZE
            chunk = doctext[startat:upto]
            try:
                self.p.Parse(chunk)
            except xml.parsers.expat.ExpatError:
                return None
            startat = upto
        return self.version

    # Handler functions
    def start_element(self, name, attrs):
        if name == "document":
            if attrs.has_key('cnxml-version'):
                self.version = attrs['cnxml-version']

    def start_doctype(self, doctypeName, systemId, publicId,
                      has_internal_subset):
        if publicId.find("CNXML") != -1:
            # publicId like "-//CNX//DTD CNXML 0.5//EN"
            dtdstr = publicId.split("//")[2]
            dtdstr = dtdstr.split()[2]
            self.version = dtdstr
