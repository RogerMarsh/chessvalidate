# configure.py
# Copyright 2014 Roger Marsh
# Licence: See LICENCE (BSD licence)

"""Describe the emails and attachments containing event results."""

import os
import tkinter
import tkinter.messagebox

from emailextract.gui.select import Select

from ..core.emailextractor import EmailExtractor
from ..core import configuration
from ..core import constants


class Configure(Select):
    """Define and use an event result's extraction configuration file."""

    _READ_FILE_TITLE = "Validation Extraction Rules"

    def __init__(self, emailextractor=None, **kargs):
        """Initialise the emailextractor instance."""
        if emailextractor is None:
            emailextractor = EmailExtractor
        super().__init__(emailextractor=emailextractor, **kargs)

    def read_file(self, filename):
        """Display the content, text, of configuration file."""
        if self._configuration is not None:
            tkinter.messagebox.showinfo(
                parent=self.root,
                title=self._READ_FILE_TITLE,
                message="The configuration file has already been read.",
            )
            return
        config_file = os.path.join(self._folder, filename)
        with open(config_file, "r", encoding="utf-8") as conf:
            self.configctrl.delete("1.0", tkinter.END)
            self.configctrl.insert(tkinter.END, conf.read())
        self._configuration = config_file

    def file_new(self, conf=None):
        """Set configuration, delegate, note opened file in configuration."""
        if conf is None:
            conf = configuration
        conf = conf.Configuration()
        if self._folder is None:
            self._folder = conf.get_configuration_value(
                constants.RECENT_EMAIL_EXTRACTION
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
                constants.RECENT_EMAIL_EXTRACTION
            )
        super().file_open()
        self._update_configuration(conf)

    def _update_configuration(self, conf):
        """Update configuration using conf instance."""
        if self._configuration is not None:
            conf.set_configuration_value(
                constants.RECENT_EMAIL_EXTRACTION,
                conf.convert_home_directory_to_tilde(self._folder),
            )
