# configuration.py
# Copyright 2022 Roger Marsh
# Licence: See LICENCE (BSD licence)

"""Access and update names of last used database and configuration files.

The initial values are taken from file named in constants.RESULTS_CONF
in the user's home directory if the file exists.

"""

import os

from ..core import constants

_items = {}


def get_configuration_value(item, default=None):
    """Return value of configuration item or default if item not found.

    The return value is the default value or the most recent value saved
    by set_configuration_value().

    Changes in the configuration file since the file was read at start-up
    are not seen.  Use get_configuration_value_from_file() to see that.

    """
    return _items.get(item, default)


def get_configuration_value_from_file(item, default=None):
    """Return configuration item value on file or default if item not found.

    Use get_configuration_value() to avoid reading the configuration file
    on each call, but this may not return the current value on file.  After
    editing with another program for example.

    """
    return _items.get(item, default=default)


def get_configuration_text_for_items_from_file(items, values=False):
    """Return text in file configuration items.

    Values are cached if bool(values) evaluates True.

    """
    try:
        of = open(
            os.path.expanduser(os.path.join("~", constants.RESULTS_CONF))
        )
        try:
            config_text_on_file = of.read()
        finally:
            of.close()
            del of
    except:
        config_text_on_file = ""
    config_text_lines = []
    for item in config_text_on_file.splitlines():
        item = item.strip()
        if len(item) == 0:
            continue
        item = item.split(maxsplit=1)
        if len(item) == 1:
            continue
        k, v = item
        if k not in items:
            continue
        if values:
            _items[k] = v
        config_text_lines.append(" ".join(item))
    return "\n".join(config_text_lines)


def get_configuration_text_and_values_for_items_from_file(items):
    """Cache values and return text in file configuration items."""
    return get_configuration_text_for_items_from_file(items, values=True)


def set_configuration_value(item, value):
    """Set value of configuration item if item exists."""
    if item in _items:
        if _items[item] != value:
            _items[item] = value
            _save_configuration()


def set_configuration_values_from_text(text, config_items=None):
    """Set values of configuration items from text if item exists."""
    if config_items is None:
        config_items = {}
    default_values = {
        default[0]: default[1]
        for default in (constants.DEFAULT_URLS + constants.DEFAULT_RECENTS)
    }

    change = False
    for i in text.splitlines():
        i = i.split(maxsplit=1)
        if not i:
            continue
        key = i[0]
        if key not in config_items or key not in default_values:
            continue
        if len(i) == 1:
            value = default_values[key]
        else:
            value = i[1].strip()
        if key not in _items or _items[key] != value:
            _items[key] = value
            change = True
    for key, value in default_values.items():
        if key not in _items:
            _items[key] = value
            change = True
    if change:
        _save_configuration()


def convert_home_directory_to_tilde(path):
    """Return path with leading /home/<user> converted to ~."""
    home = os.path.expanduser("~")

    # removeprefix not available until Python3.9
    if path.startswith(home):
        return os.path.join("~", path[len(home) + 1 :])
    else:
        return path


def _save_configuration():
    """Save the configuration in file named in constants.RESULTS_CONF."""
    config_text = []
    for k in sorted(_items):
        config_text.append(" ".join((k, _items[k])))
    config_text = "\n".join(config_text)
    try:
        of = open(
            os.path.expanduser(os.path.join("~", constants.RESULTS_CONF)), "w"
        )
        try:
            of.write(config_text)
        finally:
            of.close()
    except:
        pass


# Set initial defaults on start-up.
set_configuration_values_from_text(
    get_configuration_text_and_values_for_items_from_file(
        {
            default[0]: default[1]
            for default in constants.DEFAULT_URLS + constants.DEFAULT_RECENTS
        }
    )
)
