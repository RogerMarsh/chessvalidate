# eventdetails.py
# Copyright 2022 Roger Marsh
# Licence: See LICENCE (BSD licence)

"""Extract information from event configuration file."""
import os
import tkinter

from ecfformat.core.content import HeaderContent
from ecfformat.core import constants

from .constants import EVENT_CONF


def get_text_at_value_after_name(name, widget):
    """Return text in widget at value range immediately after name's range.

    Most fields have a name and a value, but the value may be absent.  The
    text in the next value range is returned if the prior name range at that
    value range is range_.

    """
    range_ = widget.tag_nextrange(name, "1.0")
    if not range_:
        return None
    value_range = widget.tag_nextrange(constants.FIELD_VALUE_TAG, range_[-1])
    if not value_range:
        return None
    if range_ != widget.tag_prevrange(
        constants.FIELD_NAME_TAG, value_range[0]
    ):
        return None
    return widget.get(*value_range)


def get_event_details(folder):
    """Return event name, start date, and end date, from event details."""
    widget = tkinter.Text()
    with open(os.path.join(folder, EVENT_CONF)) as file_:
        text = file_.read()
    HeaderContent(text, False, ()).parse(widget)
    event = get_text_at_value_after_name(constants.EVENT_NAME, widget)
    date = get_text_at_value_after_name(constants.EVENT_DATE, widget)
    final = get_text_at_value_after_name(constants.FINAL_RESULT_DATE, widget)
    if event and date and final:
        return (event, date, final)
    return (None, None, None)
