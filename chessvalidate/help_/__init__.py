# __init__.py
# Copyright 2011 Roger Marsh
# Licence: See LICENCE (BSD licence)

"""Help files for Results Reports."""

import os

ABOUT = "About"
GUIDE = "Guide"
ACTIONS = "Actions"
NOTES = "Notes"
SAMPLES = "Samples"
TABLESPECS = "Tablespecs"

_textfile = {
    ABOUT: ("aboutresults",),
    GUIDE: ("guide",),
    ACTIONS: ("keyboard",),
    NOTES: ("results",),
    SAMPLES: ("samples",),
    TABLESPECS: ("tablespecs",),
}

folder = os.path.dirname(__file__)

for k in list(_textfile.keys()):
    _textfile[k] = tuple(
        os.path.join(folder, ".".join((n, "txt"))) for n in _textfile[k]
    )

del folder, os
