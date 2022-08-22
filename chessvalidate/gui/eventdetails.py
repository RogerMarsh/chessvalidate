# eventdetails.py
# Copyright 2022 Roger Marsh
# Licence: See LICENCE (BSD licence)

"""Set and modify event details."""
from ecfformat.gui import header
import ecfformat.core.constants

from ..core import configuration


class EventDetails(header.Header):
    """Customise Header for setting event details.

    Header can be used 'as-is' but conventions such as field name styles
    and file storage options assume the target is always an ECF result
    submission file.

    """

    _sequences = ()
    _allowed_inserts = {}
    _popup_menu_label_map = {}
    _NEW_FILE_TEXT = "\n".join(
        (
            "#EVENT DETAILS",
            "#EVENT CODE=",
            "#SUBMISSION INDEX=",
            "#EVENT NAME=",
            "#EVENT DATE=",
            "#FINAL RESULT DATE=",
            "#RESULTS OFFICER=",
            "#RESULTS OFFICER ADDRESS=",
            "#TREASURER=",
            "#TREASURER ADDRESS=",
        )
    )
    _NO_VALUE_TAGS = (
        ecfformat.core.constants.EVENT_CODE,
        ecfformat.core.constants.SUBMISSION_INDEX,
    )

    def _set_field_delete_binding(self):
        """Suppress Alt-KeyPress-Delete binding in all circumstances.

        This customisation of Header presents an immutable form where only
        the values entered can be changed.

        """

    def _make_configuration(self):
        """Return a configuration.Configuration instance."""
        return configuration.Configuration()

    def _show_value_boundary(self, conf):
        """Return True if configuration file SHOW_VALUE_BOUNDARY is true."""
        return bool(
            conf.get_configuration_value(
                ecfformat.core.constants.SHOW_VALUE_BOUNDARY
            )
            == ecfformat.core.constants.SHOW_VALUE_BOUNDARY_TRUE
        )
