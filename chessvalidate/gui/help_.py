# help.py
# Copyright 2009 Roger Marsh
# Licence: See LICENCE (BSD licence)

"""Functions to create Help widgets for Results.
"""

import tkinter

import solentware_misc.gui.textreadonly
from solentware_misc.gui.help import help_widget

from .. import help


def help_about(master):
    """Display About document"""

    help_widget(master, help.ABOUT, help)


def help_file_size(master):
    """Display File Size document"""

    help_widget(master, help.FILESIZE, help)


def help_guide(master):
    """Display Guide document"""

    help_widget(master, help.GUIDE, help)


def help_keyboard(master):
    """Display Keyboard actions document"""

    help_widget(master, help.ACTIONS, help)


def help_samples(master):
    """Display Samples document"""

    help_widget(master, help.SAMPLES, help)


def help_tablespecs(master):
    """Display csv file layouts document"""

    help_widget(master, help.TABLESPECS, help)


def help_notes(master):
    """Display Notes document"""

    help_widget(master, help.NOTES, help)


if __name__ == "__main__":
    # Display all help documents without running ChessResults application

    root = tkinter.Tk()
    help_about(root)
    help_file_size(root)
    help_guide(root)
    help_keyboard(root)
    help_notes(root)
    help_samples(root)
    help_tablespecs(root)
    root.mainloop()
