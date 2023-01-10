# csvdownload.py
# Copyright 2022 Roger Marsh
# Licence: See LICENCE (BSD licence)

"""Download CSV file containing event results from URL."""

import os
import tkinter
import tkinter.messagebox

from solentware_bind.gui.bindings import Bindings

from solentware_misc.gui import textreadonly
from solentware_misc.gui.configuredialog import ConfigureDialog

from ..core.downloadconf import DownloadConf, CSV_DOWNLOAD_CONF
from ..core.downloadconvert import DownloadConvert
from ..core import configuration
from ..core import constants
from .. import APPLICATION_NAME
from ..gui import configfile

STARTUP_MINIMUM_WIDTH = 340
STARTUP_MINIMUM_HEIGHT = 400


class CSVDownload(configfile.ConfigFile, Bindings):
    """Define and use an event result's extraction configuration file."""

    _READ_FILE_TITLE = "Validation Extraction Rules"

    def __init__(
        self,
        use_toplevel=False,
        downloadconf=None,
        application_name=APPLICATION_NAME,
        **kargs
    ):
        """Initialise the CSV download instance."""
        super().__init__()
        if downloadconf:
            self._downloadconf = downloadconf
        else:
            self._downloadconf = DownloadConf
        if use_toplevel:
            self.root = tkinter.Toplevel(**kargs)
        else:
            self.root = tkinter.Tk()
        try:
            self.application_name = application_name
            self.root.wm_title(application_name)
            self.root.wm_minsize(
                width=STARTUP_MINIMUM_WIDTH, height=STARTUP_MINIMUM_HEIGHT
            )

            self._downloader = None
            self._configuration = None
            self._converter = None
            self._configuration_edited = False

            self._build_menus()

            self.statusbar = Statusbar(self.root)
            frame = tkinter.PanedWindow(
                self.root,
                background="cyan2",
                opaqueresize=tkinter.FALSE,
                orient=tkinter.HORIZONTAL,
            )
            frame.pack(fill=tkinter.BOTH, expand=tkinter.TRUE)

            toppane = tkinter.PanedWindow(
                master=frame,
                opaqueresize=tkinter.FALSE,
                orient=tkinter.HORIZONTAL,
            )
            originalpane = tkinter.PanedWindow(
                master=toppane,
                opaqueresize=tkinter.FALSE,
                orient=tkinter.VERTICAL,
            )
            tabularpane = tkinter.PanedWindow(
                master=toppane,
                opaqueresize=tkinter.FALSE,
                orient=tkinter.VERTICAL,
            )
            self.configctrl = textreadonly.make_text_readonly(
                master=originalpane, width=80
            )
            self.csvdownloadctrl = textreadonly.make_text_readonly(
                master=originalpane, width=80
            )
            self.tabulartextctrl = textreadonly.make_text_readonly(
                master=tabularpane
            )
            originalpane.add(self.configctrl)
            originalpane.add(self.csvdownloadctrl)
            tabularpane.add(self.tabulartextctrl)
            toppane.add(originalpane)
            toppane.add(tabularpane)
            toppane.pack(side=tkinter.TOP, expand=True, fill=tkinter.BOTH)
            self._folder = None

        except (AttributeError, tkinter.TclError):
            self.root.destroy()
            del self.root

    # Avoid pylint too-many-statements for __init__() method.
    def _build_menus(self):
        """Build the menubar."""
        menubar = tkinter.Menu(self.root)

        menufile = tkinter.Menu(menubar, name="file", tearoff=False)
        menubar.add_cascade(label="File", menu=menufile, underline=0)
        menufile.add_command(
            label="Open",
            underline=0,
            command=self.try_command(self.file_open, menufile),
        )
        menufile.add_command(
            label="New",
            underline=0,
            command=self.try_command(self.file_new, menufile),
        )
        menufile.add_separator()
        menufile.add_command(
            label="Save Copy As...",
            underline=7,
            command=self.try_command(self.file_save_copy_as, menufile),
        )
        menufile.add_separator()
        menufile.add_command(
            label="Close",
            underline=0,
            command=self.try_command(self.file_close, menufile),
        )
        menufile.add_separator()
        menufile.add_command(
            label="Quit",
            underline=0,
            command=self.try_command(self.file_quit, menufile),
        )

        menuactions = tkinter.Menu(menubar, name="actions", tearoff=False)
        menubar.add_cascade(label="Actions", menu=menuactions, underline=0)
        menuactions.add_command(
            label="Show URL content",
            underline=0,
            command=self.try_command(self._show_url_content, menuactions),
        )
        menuactions.add_command(
            label="Tabular text",
            underline=0,
            command=self.try_command(self._show_tabular_text, menuactions),
        )
        menuactions.add_command(
            label="Update",
            underline=0,
            command=self.try_command(
                self._update_difference_files, menuactions
            ),
        )
        menuactions.add_command(
            label="Clear selection",
            underline=0,
            command=self.try_command(self._clear_selection, menuactions),
        )
        menuactions.add_separator()
        menuactions.add_command(
            label="Option editor",
            underline=0,
            command=self.try_command(
                self._configure_csv_download, menuactions
            ),
        )

        menuhelp = tkinter.Menu(menubar, name="help", tearoff=False)
        menubar.add_cascade(label="Help", menu=menuhelp, underline=0)
        menuhelp.add_command(
            label="Guide",
            underline=0,
            command=self.try_command(self.help_guide, menuhelp),
        )
        menuhelp.add_command(
            label="Notes",
            underline=0,
            command=self.try_command(self.help_notes, menuhelp),
        )

        self.root.configure(menu=menubar)

    def file_new(
        self, conf=configuration, recent=constants.RECENT_CSV_DOWNLOAD
    ):
        """Set configuration, delegate, note opened file in configuration."""
        conf = self._set_folder_from_configuration(conf, recent)
        if self._configuration is not None:
            tkinter.messagebox.showinfo(
                parent=self.get_toplevel(),
                title=self.application_name,
                message="Close the current extraction rules first.",
            )
            return
        config_file = tkinter.filedialog.asksaveasfilename(
            parent=self.get_toplevel(),
            title=" ".join(("New", self.application_name)),
            defaultextension=".conf",
            filetypes=(("CSV Download Rules", "*.conf"),),
            initialfile=CSV_DOWNLOAD_CONF,
            initialdir=self._folder if self._folder else "~",
        )
        if not config_file:
            return
        self.configctrl.delete("1.0", tkinter.END)
        self.configctrl.insert(
            tkinter.END,
            "".join(("# ", os.path.basename(config_file), " download rules"))
            + os.linesep,
        )
        with open(config_file, "w", encoding="utf8") as file:
            file.write(
                self.configctrl.get("1.0", " ".join((tkinter.END, "-1 chars")))
            )
        self._configuration = config_file
        self._folder = os.path.dirname(config_file)
        self.root.wm_title(" - ".join((self.application_name, config_file)))
        self._update_configuration(conf, recent)

    def file_open(
        self, conf=configuration, recent=constants.RECENT_CSV_DOWNLOAD
    ):
        """Set configuration, delegate, note opened file in configuration."""
        conf = self._set_folder_from_configuration(conf, recent)
        if self._configuration is not None:
            tkinter.messagebox.showinfo(
                parent=self.get_toplevel(),
                title=self.application_name,
                message="Close the current extraction rules first.",
            )
            return
        config_file = tkinter.filedialog.askopenfilename(
            parent=self.get_toplevel(),
            title=" ".join(("Open", self.application_name)),
            defaultextension=".conf",
            filetypes=(("CSV Download Rules", "*.conf"),),
            initialfile=CSV_DOWNLOAD_CONF,
            initialdir=self._folder if self._folder else "~",
        )
        if not config_file:
            return
        with open(config_file, "r", encoding="utf8") as file:
            self.configctrl.delete("1.0", tkinter.END)
            self.configctrl.insert(tkinter.END, file.read())
        self._configuration = config_file
        self._folder = os.path.dirname(config_file)
        self.root.wm_title(" - ".join((self.application_name, config_file)))
        self._update_configuration(conf, recent)

    def file_save_copy_as(self):
        """Save copy of open extraction rules and keep current open."""
        if self._configuration is None:
            tkinter.messagebox.showinfo(
                parent=self.get_toplevel(),
                title="Save Copy As",
                message="Cannot save.\n\nDownload rules file not open.",
            )
            return
        config_file = tkinter.filedialog.asksaveasfilename(
            parent=self.get_toplevel(),
            title=self.application_name.join(("Save ", " As")),
            defaultextension=".conf",
            filetypes=(("Download Rules", "*.conf"),),
            initialfile=os.path.basename(self._configuration),
            initialdir=os.path.dirname(self._configuration),
        )
        if not config_file:
            return
        if config_file == self._configuration:
            tkinter.messagebox.showinfo(
                parent=self.get_toplevel(),
                title="Save Copy As",
                message="".join(
                    (
                        'Cannot use "Save Copy As" to overwite the open ',
                        "download rules file.",
                    )
                ),
            )
            return
        with open(config_file, "w") as file:
            file.write(
                self.configctrl.get("1.0", " ".join((tkinter.END, "-1 chars")))
            )

    def file_close(self):
        """Close the open download rules file."""
        if self._configuration is None:
            tkinter.messagebox.showinfo(
                parent=self.get_toplevel(),
                title=self.application_name,
                message="Cannot close.\n\nThere is no file open.",
            )
            return
        dlg = tkinter.messagebox.askquestion(
            parent=self.get_toplevel(),
            title=self.application_name,
            message="Confirm Close.",
        )
        if dlg == tkinter.messagebox.YES:
            self.configctrl.delete("1.0", tkinter.END)
            self.tabulartextctrl.delete("1.0", tkinter.END)
            self.csvdownloadctrl.delete("1.0", tkinter.END)
            self.statusbar.set_status_text()
            self._configuration = None
            self._configuration_edited = False
            self.root.wm_title(
                " - ".join((self.application_name, self._folder))
            )

    def file_quit(self):
        """Quit the extraction application."""
        dlg = tkinter.messagebox.askquestion(
            parent=self.get_toplevel(),
            title=self.application_name,
            message="Confirm Quit.",
        )
        if dlg == tkinter.messagebox.YES:
            self.root.destroy()

    def _show_url_content(self):
        """Show the content retrieved from URL, expected to be CSV text."""
        if self._configuration is None:
            tkinter.messagebox.showinfo(
                parent=self.get_toplevel(),
                title="Show URL Content",
                message="Open a download rules file",
            )
            return False
        if self._configuration_edited:
            tkinter.messagebox.showinfo(
                parent=self.get_toplevel(),
                title="Show URL Content",
                message="".join(
                    (
                        "The edited configuration file has not been saved. ",
                        'It must be saved before "Show" action can be done.',
                    )
                ),
            )
            return False
        if self._converter is None:
            dlr = self._downloadconf(
                self._folder,
                configuration=self.configctrl.get(
                    "1.0", " ".join((tkinter.END, "-1 chars"))
                ),
                parent=self.get_toplevel(),
            )
            if not dlr.parse():
                return False
            if not dlr.verify_url():
                return False
            self._converter = DownloadConvert(dlr, self.get_toplevel())
        return self._converter.show_url_content(self.csvdownloadctrl)

    def _show_tabular_text(self):
        """Show the text derived from the CSV file retrieved from URL."""
        if self._converter is None:
            if not self._show_url_content():
                return False
            if self._converter is None:
                return False
        return self._converter.show_tabular_text(
            self.tabulartextctrl,
            self.csvdownloadctrl.get(
                "1.0", " ".join((tkinter.END, "-1 chars"))
            ),
            self._folder,
        )

    def _update_difference_files(self):
        """Show the text derived from the CSV file retrieved from URL."""
        if self._converter is None:
            if not self._show_tabular_text():
                return False
            if self._converter is None:
                return False
        return self._converter.update_difference_files(
            self.tabulartextctrl.get(
                "1.0", " ".join((tkinter.END, "-1 chars"))
            ).splitlines(keepends=True),
            self._folder,
        )

    def _clear_selection(self):
        """Clear the lists of extracted text."""
        if (
            tkinter.messagebox.askquestion(
                parent=self.get_toplevel(),
                title="Clear Extracted Text",
                message="Confirm request to clear lists of extracted text.",
            )
            != tkinter.messagebox.YES
        ):
            return
        self.tabulartextctrl.delete("1.0", tkinter.END)
        self.csvdownloadctrl.delete("1.0", tkinter.END)
        self.statusbar.set_status_text()
        self._converter = None

    def _configure_csv_download(self):
        """Set parameters that control CSV download from URL."""
        if self._configuration is None:
            tkinter.messagebox.showinfo(
                parent=self.get_toplevel(),
                title="Configure Download from URL",
                message="Open a download rules file.",
            )
            return
        config_text = ConfigureDialog(
            master=self.root,
            configuration=self.configctrl.get(
                "1.0", " ".join((tkinter.END, "-1 chars"))
            ),
            dialog_title=" ".join(
                (self.application_name, "configuration editor")
            ),
        ).config_text
        if config_text is None:
            return
        self._configuration_edited = True
        self.configctrl.delete("1.0", tkinter.END)
        self.configctrl.insert(tkinter.END, config_text)
        with open(self._configuration, "w", encoding="utf-8") as file:
            file.write(config_text)
            self.tabulartextctrl.delete("1.0", tkinter.END)
            self.csvdownloadctrl.delete("1.0", tkinter.END)
            self.statusbar.set_status_text()
            self._configuration_edited = False
        if self._converter:
            converter = self._converter
            self._converter = None
            if (
                converter.most_recent_action.__name__
                == converter.show_url_content.__name__
            ):
                self._show_url_content()
            elif (
                converter.most_recent_action.__name__
                == converter.show_tabular_text.__name__
            ):
                self._show_tabular_text()
            elif (
                converter.most_recent_action.__name__
                == converter.update_difference_files.__name__
            ):
                self._update_difference_files()

    def help_guide(self):
        """Display brief User Guide for CSV download."""
        tkinter.messagebox.showinfo(
            parent=self.root,
            message="Placeholder for CSV download Guide",
            title=self.get_application_name,
        )

    def help_notes(self):
        """Display technical notes about CSV download."""
        tkinter.messagebox.showinfo(
            parent=self.root,
            message="Placeholder for CSV download Notes",
            title=self.get_application_name,
        )

    def get_toplevel(self):
        """Return the toplevel widget."""
        return self.root


class Statusbar:
    """Status bar for CSV download application.."""

    def __init__(self, root):
        """Create status bar widget."""
        self.status = tkinter.Text(
            root,
            height=0,
            width=0,
            background=root.cget("background"),
            relief=tkinter.FLAT,
            state=tkinter.DISABLED,
            wrap=tkinter.NONE,
        )
        self.status.pack(side=tkinter.BOTTOM, fill=tkinter.X)

    def get_status_text(self):
        """Return text displayed in status bar."""
        return self.status.cget("text")

    def set_status_text(self, text=""):
        """Display text in status bar."""
        self.status.configure(state=tkinter.NORMAL)
        self.status.delete("1.0", tkinter.END)
        self.status.insert(tkinter.END, text)
        self.status.configure(state=tkinter.DISABLED)
