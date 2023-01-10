# downloadconf.py
# Copyright 2022 Roger Marsh
# Licence: See LICENCE (BSD licence)

"""Define URL from which results CSV file is downloaded."""

import re
import tkinter
from urllib.parse import urlparse

# Configuration file for setting the URL from which CSV file is downloaded.
CSV_DOWNLOAD_CONF = "csv_download.conf"

_DOWNLOAD_URL = "download_url"
_DOWNLOAD_LOGIN = "download_login"
_DOWNLOAD_ENCODING = "download_encoding"


class DownloadConfError:
    """Exception class for downloadconf module."""


class DownloadConf:
    """Extract text from CSV download containing chess game results."""

    # Here because emailextract.core.emailextractor has the equivalent
    # items too.  Not sure why though: used in Parser class only.
    csv_select_line = re.compile(
        "".join(
            (
                r"\A",
                "(?:",
                "(?:",  # whitespace line
                r"\s*",
                ")|",
                "(?:",  # comment line
                r"\s*#.*",
                ")|",
                "(?:",  # parameter line
                r"\s*(\S+?)\s+([^#]*).*",
                ")",
                ")",
                r"\Z",
            )
        )
    )

    def __init__(
        self,
        folder,
        configuration=None,
        parser=None,
        parent=None,
    ):
        """Define the email extraction rules from configuration.

        folder - the directory containing the event's data
        configuration - the rules for extracting emails

        """
        if parser is None:
            parser = Parser
        self._parser = parser
        self.configuration = configuration
        self.criteria = None
        self.parent = parent
        self._folder = folder

    @property
    def url(self):
        """Return URL name or None if not set."""
        return self.criteria.get(_DOWNLOAD_URL)

    @property
    def encoding(self):
        """Return encoding or "utf-8" if not set."""
        return self.criteria.get(_DOWNLOAD_ENCODING, "utf-8")

    def parse(self):
        """Set rules, from configuration file, for download extraction."""
        self.criteria = None
        criteria = self._parser(parent=self.parent).parse(self.configuration)
        if criteria:
            self.criteria = criteria
            return True
        if criteria is False:
            return False
        return True

    def verify_url(self):
        """Return True if URL is acceptable."""
        urlstr = self.criteria[_DOWNLOAD_URL]
        try:
            urlparse(urlstr)
        except ValueError:
            tkinter.messagebox.showinfo(
                parent=self.parent,
                title="URL Name",
                message=" ".join((repr(urlstr), "is not valid")),
            )
            return False
        return True


class Parser:
    """Parse configuration file."""

    def __init__(self, parent=None):
        """Set up keyword to method map."""
        self.parent = parent
        self.keyword_rules = {
            _DOWNLOAD_URL: self.assign_value,
            _DOWNLOAD_LOGIN: self.assign_value,
            _DOWNLOAD_ENCODING: self.assign_value,
        }

    def parse(self, configuration):
        """Return arguments from configuration file."""
        args = {}
        for line in configuration.split("\n"):
            match = DownloadConf.csv_select_line.match(line)
            if not match:
                self._parse_error_dialogue(line)
                return False
            key, value = match.groups()
            if key is None:
                continue
            if not value:
                self._parse_error_dialogue(line)
                return False
            args_type = self.keyword_rules.get(key.lower())
            if args_type is None:
                self._parse_error_dialogue(line)
                return False
            try:
                args_type(value, args, key.lower())
            except (re.error, ValueError):
                self._parse_error_dialogue(line)
                return False
        return args

    @staticmethod
    def assign_value(value, args, args_key):
        """Set dict item args[args_key] to v from configuration file."""
        args[args_key] = value

    def _parse_error_dialogue(self, message):
        """Show dialogue for errors reading configuration file."""
        tkinter.messagebox.showinfo(
            parent=self.parent,
            title="Configuration File",
            message="".join(
                (
                    "Download rules are invalid.\n\nFailed rule is:\n\n",
                    message,
                )
            ),
        )
