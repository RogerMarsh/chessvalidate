# selectemail.py
# Copyright 2022 Roger Marsh
# Licence: See LICENCE (BSD licence)

"""Email selection filter User Interface for Results application.

"""
import os

from emailstore.gui import select

from ..core import configuration
from ..core import constants


class SelectEmail(select.Select):

    """Add store configuration file to select.Select for opening files."""

    def file_new(self):
        """Delegate then update configuration if a file was opened."""
        if self._folder is None:
            self._folder = configuration.get_configuration_value(
                constants.RECENT_EMAIL_SELECTION
            )
        super().file_new()
        self._update_configuration()

    def file_open(self):
        """Delegate then update configuration if a file was opened."""
        if self._folder is None:
            self._folder = configuration.get_configuration_value(
                constants.RECENT_EMAIL_SELECTION
            )
        super().file_open()
        self._update_configuration()

    def _update_configuration(self):
        if self._configuration is not None:
            configuration.set_configuration_value(
                constants.RECENT_EMAIL_SELECTION,
                configuration.convert_home_directory_to_tilde(self._folder),
            )
