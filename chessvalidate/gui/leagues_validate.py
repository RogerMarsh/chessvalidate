# leagues_validate.py
# Copyright 2022 Roger Marsh
# Licence: See LICENCE (BSD licence)

"""Results validation Leagues frame class."""

import tkinter
import tkinter.messagebox
import tkinter.filedialog
import os

from solentware_misc.gui import threadqueue

from ..core import configuration
from ..core import constants
from ..core.season import Season
from . import sourceedit
from .. import ERROR_LOG


class Leagues(threadqueue.AppSysThreadQueue):
    """The Results frame for a Results database."""

    _menu_opendata = "leagues_validate_menu_opendata"

    _tab_sourceedit = "leagues_validate_tab_sourceedit"

    _state_dbclosed = "leagues_validate_state_dbclosed"
    _state_dataopen = "leagues_validate_state_dataopen"

    def __init__(self, menubar=None, **kargs):
        """Extend and define the results database results frame."""
        super().__init__(**kargs)

        self._results_folder = None  # folder shown in SourceOpen.folder
        self.results_data = None  # Season held in SourceOpen.data
        self.menubar = menubar
        self._resultsdbkargs = kargs

        self.define_menus()

        # Call self.define_tab() for all tabs in application.
        self.define_tabs()

        # Update the instance tab_state and switch_state dicts.
        self.define_state_transitions(
            tab_state=self.define_tab_states(),
            switch_state=self.define_state_switch_table(),
        )

    @property
    def results_folder(self):
        """Return path to folder containing open results data file."""
        return self._results_folder

    def define_menus(self):
        """Define the application menus."""
        menu2 = tkinter.Menu(self.menubar, tearoff=False)
        menu2.add_command(
            label="Open",
            underline=0,
            command=self.try_command(self.results_open, menu2),
        )
        menu2.add_command(
            label="Close",
            underline=0,
            command=self.try_command(self.results_close, menu2),
        )

        # subclasses may want to add commands to menu2
        self.menu_results = menu2

        self.menubar.add_cascade(label="Documents", menu=menu2, underline=0)

    def define_tabs(self):
        """Define the application tabs."""
        self.define_tab(
            self._tab_sourceedit,
            text="Edit",
            tooltip=(
                "Edit event source files and generate Results database input."
            ),
            underline=-1,
            tabclass=self.document_edit,
            destroy_actions=(sourceedit.SourceEdit.btn_closedata,),
        )

    def define_tab_states(self):
        """Return dict of <state>:tuple(<tab>, ...)."""
        return {
            self._state_dbclosed: (),
            self._state_dataopen: (self._tab_sourceedit,),
        }

    def define_state_switch_table(self):
        """Return dict of tuple(<state>, <action>):list(<state>, <tab>)."""
        return {
            (None, None): [self._state_dbclosed, None],
            (self._state_dbclosed, self._menu_opendata): [
                self._state_dataopen,
                self._tab_sourceedit,
            ],
            (self._state_dataopen, sourceedit.SourceEdit.btn_closedata): [
                self._state_dbclosed,
                None,
            ],
        }

    def close_event_edition_results(self):
        """Close results data source files."""
        self.results_data.close()
        self.results_data = None

    def database_quit(self):
        """Quit results application."""
        editor = self.get_tab_data(self._tab_sourceedit)
        if not editor:
            if not tkinter.messagebox.askyesno(
                parent=self.get_widget(),
                message="Do you really want to quit?",
                title="Quit Results",
            ):
                return False
        elif self.results_data:
            if editor.is_report_modified():
                if not tkinter.messagebox.askyesno(
                    parent=self.get_widget(),
                    message="".join(
                        (
                            "Event data has been modified.\n\n",
                            "Do you want to quit anyway?\n\n",
                            "The save dialogue will be shown before quitting.",
                        )
                    ),
                    title="Quit Results",
                ):
                    return False
                editor.save_data_folder()
            elif not tkinter.messagebox.askyesno(
                parent=self.get_widget(),
                message="Do you really want to quit?",
                title="Quit Results",
            ):
                return False
        self.get_widget().winfo_toplevel().destroy()
        return None

    @staticmethod
    def document_edit(**kargs):
        """Return sourceedit.SourceEdit class instance."""
        return sourceedit.SourceEdit(**kargs)

    def get_thread_queue(self):
        """Return queue for methods to be called in the background thread."""
        return self.queue

    def get_results_context(self):
        """Return the data input page."""
        return self

    def results_close(self):
        """Close results source document."""
        if self.results_data is None:
            return
        if tkinter.messagebox.askyesno(
            parent=self.get_widget(),
            message="".join(
                (
                    "Close\n",
                    self._results_folder,
                    "\nfolder containing results data",
                )
            ),
            title="Close",
        ):
            self.close_event_edition_results()
            self.switch_context(sourceedit.SourceEdit.btn_closedata)
            self.set_error_file_on_close_source()

    def results_open(self):
        """Open results source documents."""
        open_season = self._results_open()
        if open_season:
            self.set_error_file()
            self.set_results_edit_context()

    def set_results_edit_context(self):
        """Display the results edit page and hide open database if any."""
        self.switch_context(self._menu_opendata)

    def _results_open(self, title=" "):
        """Choose results folder and return True if documents are read."""
        title = "".join(("Open", title, "Documents"))

        if not self.is_state_switch_allowed(self._menu_opendata):
            tkinter.messagebox.showinfo(
                parent=self.get_widget(),
                message="Cannot open a Results folder from the current tab",
                title=title,
            )
            return None

        if self.results_data is not None:
            tkinter.messagebox.showinfo(
                parent=self.get_widget(),
                message="".join(
                    (
                        "Close the source documents in\n",
                        self._results_folder,
                        "\nfirst.",
                    )
                ),
                title=title,
            )
            return None

        conf = self.make_configuration_instance()
        if self._results_folder is None:
            initdir = conf.get_configuration_value(constants.RECENT_DOCUMENT)
        else:
            initdir = self._results_folder
        results_folder = tkinter.filedialog.askdirectory(
            parent=self.get_widget(),
            title=" ".join((title, "folder")),
            initialdir=initdir,
        )
        if results_folder:
            return self._read_results_documents(
                title, results_folder, conf=conf
            )
        return None

    def _read_results_documents(self, title, results_folder, conf=None):
        """Read results documents from results folder: return True if ok."""
        results_data = Season(results_folder)
        if not os.path.exists(results_folder):
            if not tkinter.messagebox.askyesno(
                parent=self.get_widget(),
                message="".join(
                    (
                        results_folder,
                        "\ndoes not exist.",
                        "\nConfirm that a folder is to be created ",
                        "containing new empty documents.",
                    )
                ),
                title=title,
            ):
                return None
            try:
                os.makedirs(results_folder)
            except OSError:
                tkinter.messagebox.showinfo(
                    parent=self.get_widget(),
                    message=" ".join(
                        (results_folder, "\ncould not be created.")
                    ),
                    title=title,
                )
                return None
        if results_data.open_documents(self.get_widget()):
            self.results_data = results_data
            if self._results_folder != results_folder:
                if conf is None:
                    conf = self.make_configuration_instance()
                conf.set_configuration_value(
                    constants.RECENT_DOCUMENT,
                    conf.convert_home_directory_to_tilde(results_folder),
                )
                self._results_folder = results_folder
            return True
        return None

    def set_ecf_url_defaults(self):
        """Do nothing.

        Override in classes which communicate with ECF website to set up
        default URLs for ECF uploads and downloads.

        """

    def set_error_file(self):
        """Set the error log for file being opened."""
        # Set the error file in folder of results source data
        Leagues.set_error_file_name(
            os.path.join(self._results_folder, ERROR_LOG)
        )

    def set_error_file_on_close_source(self):
        """Set the error log after source file is closed."""
        Leagues.set_error_file_name(None)

    def set_ecfdataimport_module(self, enginename):
        """Do nothing.  Subclass must override to import module."""

    def set_ecfogddataimport_module(self, enginename):
        """Do nothing.  Subclass must override to import module."""

    @staticmethod
    def make_configuration_instance():
        """Return Configuration() made with imported configuration module.

        Subclasses should override this method to use their configuration
        module if appropriate.

        """
        return configuration.Configuration()
