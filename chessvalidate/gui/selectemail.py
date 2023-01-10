# selectemail.py
# Copyright 2022 Roger Marsh
# Licence: See LICENCE (BSD licence)

"""Email selection filter User Interface for Validate Results application."""
from emailstore.gui import select

from ..core import configuration
from ..core import constants
from ..gui import configfile


class SelectEmail(configfile.ConfigFile, select.Select):
    """Add store configuration file to select.Select for opening files."""

    # Arguments adjusted in response to pylint arguments-differ reports
    # which appeared after ConfigFile class introduced to resolve some
    # duplicate-code reports.
    def file_new(
        self, conf=configuration, recent=constants.RECENT_EMAIL_SELECTION
    ):
        """Set configuration, delegate, note opened file in configuration."""
        super().file_new(conf, recent)

    # Arguments adjusted in response to pylint arguments-differ reports
    # which appeared after ConfigFile class introduced to resolve some
    # duplicate-code reports.
    def file_open(
        self, conf=configuration, recent=constants.RECENT_EMAIL_SELECTION
    ):
        """Set configuration, delegate, note opened file in configuration."""
        super().file_open(conf, recent)
