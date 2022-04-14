# resultsroot.py
# Copyright 2010 Roger Marsh
# Licence: See LICENCE (BSD licence)

"""Results database application.
"""

import tkinter
import tkinter.messagebox
import tkinter.filedialog
import os

from solentware_misc.gui.exceptionhandler import ExceptionHandler
from solentware_misc.gui import fontchooser

from emailstore.gui import help_ as emailstore_help

from emailextract.gui import help as emailextract_help

from .. import APPLICATION_NAME
from . import help
from . import configure
from . import selectemail
from ..core.season import create_event_configuration_file
from ..core.constants import EVENT_CONF

ExceptionHandler.set_application_name(APPLICATION_NAME)


class Results(ExceptionHandler):

    """Results application."""

    def __init__(self, title, gui_module, width, height):
        """Create the Results application.

        title - the application title
        gui_module - module providing user interface
        width - initial width of application window in pixels
        height - initial height of application window in pixels

        """
        self.root = tkinter.Tk()
        self.root.wm_title(title)

        menubar = tkinter.Menu(self.root)
        self.root.configure(menu=menubar)

        menu0 = tkinter.Menu(menubar, name="sources", tearoff=False)
        menubar.add_cascade(label="Sources", menu=menu0, underline=0)

        self.mf = gui_module(
            master=self.root,
            background="cyan",
            width=width,
            height=height,
            # database_class=self._database_class,
            # datasourceset_class=self._datasourceset_class,
            menubar=menubar,
        )

        # subclasses of Leagues have done their results menu item additions
        del self.mf.menu_results

        menu0.add_command(
            label="Email selection",
            underline=0,
            command=self.try_command(self.configure_email_selection, menu0),
        )
        menu0.add_command(
            label="Result extraction",
            underline=0,
            command=self.try_command(
                self.configure_extract_text_from_emails, menu0
            ),
        )
        menu0.add_separator()
        menu0.add_command(
            label="Quit",
            underline=0,
            command=self.try_command(self.mf.database_quit, menu0),
        )

        menu3 = tkinter.Menu(menubar, name="tools", tearoff=False)
        menubar.add_cascade(label="Tools", menu=menu3, underline=0)
        menu3.add_separator()
        self.mf._add_ecf_url_item(menu3)
        menu3.add_command(
            label="Fonts",
            underline=0,
            command=self.try_command(self.select_fonts, menu3),
        )
        menu4 = tkinter.Menu(menubar, name="help", tearoff=False)
        menubar.add_cascade(label="Help", menu=menu4, underline=0)
        menu4.add_command(
            label="Guide",
            underline=0,
            command=self.try_command(self.help_guide, menu4),
        )
        menu4.add_command(
            label="Reference",
            underline=0,
            command=self.try_command(self.help_keyboard, menu4),
        )
        menu4.add_command(
            label="About",
            underline=0,
            command=self.try_command(self.help_about, menu4),
        )
        menu4.add_separator()
        menu4.add_command(
            label="Samples",
            underline=0,
            command=self.try_command(self.help_samples, menu4),
        )
        menu4.add_command(
            label="Table specifications",
            underline=0,
            command=self.try_command(self.help_tablespecs, menu4),
        )
        menu4.add_command(
            label="File size",
            underline=0,
            command=self.try_command(self.help_file_size, menu4),
        )
        menu4.add_command(
            label="Notes",
            underline=0,
            command=self.try_command(self.help_notes, menu4),
        )
        menu4.add_separator()
        menu4.add_command(
            label="Email Selection",
            underline=0,
            command=self.try_command(self.help_email_selection, menu4),
        )
        menu4.add_command(
            label="Text Extraction",
            underline=2,
            command=self.try_command(self.help_text_extraction, menu4),
        )
        self.mf.create_tabs()

        self.mf.get_widget().pack(fill=tkinter.BOTH, expand=True)
        self.mf.get_widget().pack_propagate(False)
        self.mf.show_state()

    def help_about(self):
        """Display information about Results application."""
        help.help_about(self.root)

    def help_file_size(self):
        """Display brief instructions for file size dialogue."""
        help.help_file_size(self.root)

    def help_guide(self):
        """Display brief User Guide for Results application."""
        help.help_guide(self.root)

    def help_keyboard(self):
        """Display list of keyboard actions for Results application."""
        help.help_keyboard(self.root)

    def help_notes(self):
        """Display technical notes about Results application."""
        help.help_notes(self.root)

    def help_samples(self):
        """Display description of sample files."""
        help.help_samples(self.root)

    def help_tablespecs(self):
        """Display csv file specifications."""
        help.help_tablespecs(self.root)

    def help_email_selection(self):
        """Display Emailstore Notes document."""
        emailstore_help.help_notes(self.root)

    def help_text_extraction(self):
        """Display EmailExtract Notes document."""
        emailextract_help.help_notes(self.root)

    def select_fonts(self):
        """Choose and set font for results input widgets."""
        if not tkinter.messagebox.askyesno(
            parent=self.root,
            message="".join(
                (
                    "Application of the font selected using the dialogue ",
                    "is not implemented.",
                    "\n\nDo you want to see the dialogue?\n\n",
                )
            ),
            title="Select a Font",
        ):
            return
        cs = fontchooser.AppSysFontChooser(self.root, "Select a Font")

    def configure_extract_text_from_emails(self):
        """Set parameters that control results extraction from emails."""
        configure.Configure(
            master=self.root,
            use_toplevel=True,
            application_name="".join((APPLICATION_NAME, " (extract text)")),
        )

    def configure_email_selection(self):
        """Set parameters that control email selection from mailboxes."""
        selectemail.SelectEmail(
            master=self.root,
            use_toplevel=True,
            application_name="".join((APPLICATION_NAME, " (select emails)")),
        )
