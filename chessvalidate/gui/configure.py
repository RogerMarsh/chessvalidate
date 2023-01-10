# configure.py
# Copyright 2014 Roger Marsh
# Licence: See LICENCE (BSD licence)

"""Describe the emails and attachments containing event results."""

from emailextract.gui.select import Select

from ..core.emailextractor import EmailExtractor
from ..core import configuration
from ..core import constants
from ..gui import configfile


class Configure(configfile.ConfigFile, Select):
    """Define and use an event result's extraction configuration file."""

    _READ_FILE_TITLE = "Validation Extraction Rules"

    def __init__(self, emailextractor=None, **kargs):
        """Initialise the emailextractor instance."""
        if emailextractor is None:
            emailextractor = EmailExtractor
        super().__init__(emailextractor=emailextractor, **kargs)

    # Arguments adjusted in response to pylint arguments-differ reports
    # which appeared after ConfigFile class introduced to resolve some
    # duplicate-code reports.
    def file_new(
        self, conf=configuration, recent=constants.RECENT_EMAIL_EXTRACTION
    ):
        """Set configuration, delegate, note opened file in configuration."""
        super().file_new(conf, recent)

    # Arguments adjusted in response to pylint arguments-differ reports
    # which appeared after ConfigFile class introduced to resolve some
    # duplicate-code reports.
    def file_open(
        self, conf=configuration, recent=constants.RECENT_EMAIL_EXTRACTION
    ):
        """Set configuration, delegate, note opened file in configuration."""
        super().file_open(conf, recent)
