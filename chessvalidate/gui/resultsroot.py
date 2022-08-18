# resultsroot.py
# Copyright 2010 Roger Marsh
# Licence: See LICENCE (BSD licence)

"""Results validation application."""

import tkinter
import tkinter.messagebox
import tkinter.filedialog

from solentware_misc.gui.exceptionhandler import ExceptionHandler
from solentware_misc.gui import fontchooser

from emailstore.gui import help_ as emailstore_help

from emailextract.gui import help as emailextract_help

from .. import APPLICATION_NAME
from . import help_
from . import configure
from . import selectemail
from . import eventdetails

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

        menu0 = tkinter.Menu(menubar, tearoff=False)
        menubar.add_cascade(label="Sources", menu=menu0, underline=0)

        self.app_module = gui_module(
            master=self.root,
            background="cyan",
            width=width,
            height=height,
            # database_class=self._database_class,
            # datasourceset_class=self._datasourceset_class,
            menubar=menubar,
        )

        # subclasses of Leagues have done their results menu item additions
        del self.app_module.menu_results

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
        menu0.add_command(
            label="Event Details",
            underline=6,
            command=self.try_command(
                self.configure_event_details, menu0
            ),
        )
        menu0.add_separator()
        menu0.add_command(
            label="Quit",
            underline=0,
            command=self.try_command(self.app_module.database_quit, menu0),
        )

        self.make_tools_menu(menubar)
        self.make_help_menu(menubar)
        self.app_module.create_tabs()

        self.app_module.get_widget().pack(fill=tkinter.BOTH, expand=True)
        self.app_module.get_widget().pack_propagate(False)
        self.app_module.show_state()

    def make_tools_menu(self, menubar):
        """Return Tools menu with Fonts entry."""
        menu3 = tkinter.Menu(menubar, tearoff=False)
        menubar.add_cascade(label="Tools", menu=menu3, underline=0)
        menu3.add_command(
            label="Fonts",
            underline=0,
            command=self.try_command(self.select_fonts, menu3),
        )
        return menu3

    def make_help_menu(self, menubar):
        """Return Help menu with validation entries."""
        menu4 = tkinter.Menu(menubar, tearoff=False)
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
        return menu4

    def help_about(self):
        """Display information about Results application."""
        help_.help_about(self.root)

    def help_guide(self):
        """Display brief User Guide for Results application."""
        help_.help_guide(self.root)

    def help_keyboard(self):
        """Display list of keyboard actions for Results application."""
        help_.help_keyboard(self.root)

    def help_notes(self):
        """Display technical notes about Results application."""
        help_.help_notes(self.root)

    def help_samples(self):
        """Display description of sample files."""
        help_.help_samples(self.root)

    def help_tablespecs(self):
        """Display csv file specifications."""
        help_.help_tablespecs(self.root)

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
        fontchooser.AppSysFontChooser(self.root, "Select a Font")

    def configure_extract_text_from_emails(self):
        """Set parameters that control results extraction from emails."""
        configure.Configure(
            master=self.root,
            use_toplevel=True,
            application_name="".join(
                (self.get_application_name(), " (extract text)")
            ),
        )

    def configure_email_selection(self):
        """Set parameters that control email selection from mailboxes."""
        selectemail.SelectEmail(
            master=self.root,
            use_toplevel=True,
            application_name="".join(
                (self.get_application_name(), " (select emails)")
            ),
        )

    def configure_event_details(self):
        """Set event details to event and for ECF results submission files."""
        eventdetails.EventDetails(
            master=self.root,
            use_toplevel=True,
            application_name="".join(
                (self.get_application_name(), " (event details)")
            ),
        )
