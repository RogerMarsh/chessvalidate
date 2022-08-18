# eventdetails.py
# Copyright 2022 Roger Marsh
# Licence: See LICENCE (BSD licence)

"""Set and modify event details."""
from ecfformat.gui import header


class EventDetails(header.Header):
    """Customise Header for setting event details.

    Header can be used 'as-is' but conventions such as field name styles
    and file storage options assume the target is always an ECF result
    submission file.

    """
