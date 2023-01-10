# configfile.py
# Copyright 2022 Roger Marsh
# Licence: See LICENCE (BSD licence)

"""ConfigFile class provides methods to create and open configuration files.

The methods are shared by the Configure, CSVDownload, and SelectEmail
classes.

"""
import os
import tkinter


# ConfigFile class introduced to avoid pylint duplicate-code reports.
class ConfigFile:
    """Provide methods shared by subclasses."""

    def file_new(self, conf, recent):
        """Set configuration, delegate, note opened file in configuration."""
        config = self._set_folder_from_configuration(conf, recent)
        super().file_new()
        self._update_configuration(config, recent)

    def file_open(self, conf, recent):
        """Set configuration, delegate, note opened file in configuration."""
        config = self._set_folder_from_configuration(conf, recent)
        super().file_open()
        self._update_configuration(config, recent)

    def _set_folder_from_configuration(self, conf, recent):
        """Set folder from configuration and return configuration instance.

        The conf module must have a Configuration class.

        """
        conf = conf.Configuration()
        if self._folder is None:
            # Avoid pylint access-member-before-definition report for
            # previous line 'if self._folder is None:'.
            # Avoid pylint report attribute-defined-outside-init for next
            # line if it is expressed 'self._folder = ...'.
            # Both reports are suppressed by the __dict__ version of
            # binding.
            self.__dict__["_folder"] = conf.get_configuration_value(recent)
        return conf

    def _update_configuration(self, conf, recent):
        """Update configuration file with directory name of opened file."""
        if self._configuration is not None:
            conf.set_configuration_value(
                recent,
                conf.convert_home_directory_to_tilde(self._folder),
            )

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
        # Avoid pylint access-member-before-definition report for earlier
        # line 'if self._configuration is not None:'.
        # Avoid pylint report attribute-defined-outside-init for next
        # line if it is expressed 'self._configuration = ...'.
        # Both reports are suppressed by the __dict__ version of binding.
        self.__dict__["_configuration"] = config_file
