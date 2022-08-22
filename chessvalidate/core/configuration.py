# configuration.py
# Copyright 2022 Roger Marsh
# Licence: See LICENCE (BSD licence)

"""Access and update items in a configuration file.

The initial values are taken from file named in self._CONFIGURATION in the
user's home directory if the file exists.

"""
from solentware_misc.core import configuration

import ecfformat.core.constants

from . import constants


class Configuration(configuration.Configuration):
    """Identify configuration file and access and update item values."""

    _CONFIGURATION = ".chessvalidate.conf"
    _DEFAULT_ITEM_VAULES = (
        (constants.RECENT_EMAIL_SELECTION, "~"),
        (constants.RECENT_EMAIL_EXTRACTION, "~"),
        (constants.RECENT_DOCUMENT, "~"),
        (ecfformat.core.constants.RECENT_RESULTS_FORMAT_FILE, "~"),
        (
            ecfformat.core.constants.SHOW_VALUE_BOUNDARY,
            ecfformat.core.constants.SHOW_VALUE_BOUNDARY_TRUE,
        ),
    )
