# selectemail.py
# Copyright 2022 Roger Marsh
# Licence: See LICENCE (BSD licence)

"""Email selection filter User Interface for Validate Results application."""
from emailstore.gui import select

from ..core import configuration
from ..core import constants


class SelectEmail(select.Select):
    """Add store configuration file to select.Select for opening files."""

    def file_new(self, conf=None):
        """Set configuration, delegate, note opened file in configuration."""
        if conf is None:
            conf = configuration
        conf = conf.Configuration()
        if self._folder is None:
            self._folder = conf.get_configuration_value(
                constants.RECENT_EMAIL_SELECTION
            )
        super().file_new()
        self._update_configuration(conf)

    def file_open(self, conf=None):
        """Set configuration, delegate, note opened file in configuration."""
        if conf is None:
            conf = configuration
        conf = conf.Configuration()
        if self._folder is None:
            self._folder = conf.get_configuration_value(
                constants.RECENT_EMAIL_SELECTION
            )
        super().file_open()
        self._update_configuration(conf)

    def _update_configuration(self, conf):
        """Update configuration file with directory name of opened file."""
        if self._configuration is not None:
            conf.set_configuration_value(
                constants.RECENT_EMAIL_SELECTION,
                conf.convert_home_directory_to_tilde(self._folder),
            )
