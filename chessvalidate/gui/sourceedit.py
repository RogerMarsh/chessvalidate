# sourceedit.py
# Copyright 2022 Roger Marsh
# Licence: See LICENCE (BSD licence)

"""Schedule and results raw data edit class.

This class resurrects the original purpose of this application: to collate
the emails used to report Southampton League results for copy-typing into
the ECF's League program.  Class SourceEdit in the ChessResults package
extended the purpose to update a database from which ECF results submission
files could be generated with minimum fuss.  The ECF provided an API to the
Rating Database soon after switching to monthly rating from six-monthly
grading.  The API makes it reasonable to extend this class to generate the
ECF results submission files without the local database.

The original application preceded the ECF online presence by a year or two,
a Southampton League website capable of being a source of results by ten
years, and the ECF rating database with it's API by fifteen years.

The Update action was removed from SourceEdit in the ChessResults package
to produce SourceEdit provided by this module.

"""

import tkinter
import tkinter.messagebox
import os
import datetime
import collections

from solentware_misc.core.utilities import AppSysPersonName
from solentware_misc.gui import panel, textreadonly, texttab

from ..core.eventparser import EventParserError, IEIREE
from ..core.season import (
    LOCAL_SOURCE,
    HEADER_TAG,
    DATA_TAG,
    TRAILER_TAG,
    SEPARATOR,
)
from ..core.gameresults import displayresult
from ..core.schedule import ScheduleError

_SENDER_COLOUR = "#e0f113"  # a pale yellow
_EDITABLE = "Editable"
_NOT_EDITABLE = "NotEditable"
_NAVIGATION = {"Down", "Right", "Left", "Up", "Next", "Prior", "Home", "End"}
_BACKSPACE = "BackSpace"
_DELETE = "Delete"
_DELETION = {_BACKSPACE, _DELETE}
_SELECT_FROM_GENERATED = "".join((DATA_TAG, SEPARATOR))
_SELECT_ORIG_FROM_EDIT = frozenset(
    ("".join((HEADER_TAG, SEPARATOR)), "".join((TRAILER_TAG, SEPARATOR)))
)
_SELECT_FROM_EDIT = "".join((DATA_TAG, SEPARATOR))


class SourceEditError(Exception):
    """Exception class for sourceedit module."""


class SourceEdit(panel.PlainPanel):
    """The Edit panel for raw results data."""

    _btn_generate = "sourceedit_generate"
    btn_closedata = "sourceedit_close"
    _btn_save = "sourceedit_save"
    _btn_toggle_compare = "sourceedit_toggle_compare"
    _btn_toggle_generate = "sourceedit_toggle_generate"
    _btn_report = "sourceedit_report"

    _months = {
        "01": "Jan",
        "02": "Feb",
        "03": "Mar",
        "04": "Apr",
        "05": "May",
        "06": "Jun",
        "07": "Jul",
        "08": "Aug",
        "09": "Sep",
        "10": "Oct",
        "11": "Nov",
        "12": "Dec",
    }  # assumes dates held in ISO format

    def __init__(self, parent=None, cnf=None, **kargs):
        """Extend and define results data input panel for results database."""
        super().__init__(parent=parent, cnf=cnf, **kargs)
        self.generated_schedule = []
        self.generated_results = []
        self.originaltext = None
        self.editedtext = None
        self.schedulectrl = None
        self.resultsctrl = None
        self.originalpane = None
        self.editpane = None
        self.generatedpane = None
        self.show_buttons_for_generate()
        self.create_buttons()
        self.folder = tkinter.Label(
            master=self.get_widget(),
            text=self.get_context().results_folder,
        )
        self.folder.pack(side=tkinter.TOP, fill=tkinter.X)
        self.toppane = tkinter.PanedWindow(
            master=self.get_widget(),
            opaqueresize=tkinter.FALSE,
            orient=tkinter.HORIZONTAL,
        )
        self.toppane.pack(side=tkinter.TOP, expand=True, fill=tkinter.BOTH)
        self._show_edits_and_generated()
        self.editedtext.edit_modified(tkinter.FALSE)

    def close(self):
        """Close resources prior to destroying this instance.

        Used, at least, as callback from AppSysFrame container.

        """

    def close_data_folder(self):
        """Show close data input file dialogue and return True if closed."""
        if self.is_report_modified():
            if not tkinter.messagebox.askyesno(
                parent=self.get_widget(),
                message="".join(
                    (
                        "Event data has been modified.\n\n",
                        "Do you want to close without saving?",
                    )
                ),
                title="Close",
            ):
                return
        self.get_context().results_close()

    def describe_buttons(self):
        """Define all action buttons that may appear on data input page."""
        self.define_button(
            self._btn_generate,
            text="Generate",
            tooltip="Generate data for input to League database.",
            underline=0,
            command=self.on_generate,
        )
        self.define_button(
            self._btn_toggle_compare,
            text="Show Original",
            tooltip=" ".join(
                (
                    "Display original and edited results data but not",
                    "generated data.",
                )
            ),
            underline=5,
            command=self.on_toggle_compare,
        )
        self.define_button(
            self._btn_toggle_generate,
            text="Hide Original",
            tooltip=" ".join(
                (
                    "Display edited source and generated data but not",
                    "original source.",
                )
            ),
            underline=5,
            command=self.on_toggle_generate,
        )
        self.define_button(
            self._btn_save,
            text="Save",
            tooltip=(
                "Save edited results data with changes from original noted."
            ),
            underline=2,
            command=self.on_save,
        )
        self.define_button(
            self._btn_report,
            text="Report",
            tooltip="Save reports generated from source data.",
            underline=2,
            command=self.on_report,
        )
        self.define_button(
            self.btn_closedata,
            text="Close",
            tooltip="Close the folder containing data.",
            underline=0,
            switchpanel=True,
            command=self.on_close_data,
        )

    def get_context(self):
        """Return the data input page."""
        return self.get_appsys().get_results_context()

    def get_schedule(self, data):
        """Extract event schedule and prepare report of errors."""
        data.extract_schedule()
        fixdata = data.fixture_schedule
        genfix = self.generated_schedule
        del genfix[:]
        if len(fixdata.error):
            genfix.append(("Errors\n", None))
            genfix.extend(fixdata.error)

    def get_results(self, data):
        """Extract event results and prepare report of errors."""
        data.extract_results()
        resdata = data.collation.reports
        genres = self.generated_results
        del genres[:]
        if len(resdata.error):
            genres.append(("Errors\n", None))
            genres.extend(resdata.error)

    def on_close_data(self, event=None):
        """Close the source document."""
        del event
        self.close_data_folder()
        self.inhibit_context_switch(self.btn_closedata)

    def on_generate(self, event=None):
        """Generate a validation report."""
        del event
        if self._generate_event_report():
            self.show_buttons_for_update()
            self.create_buttons()

    def on_report(self, event=None):
        """Save validation report."""
        del event
        self._save_reports()

    def on_save(self, event=None):
        """Save source document."""
        del event
        self.save_data_folder()

    def on_toggle_compare(self, event=None):
        """Display original source document next to edited source document."""
        del event
        self._show_buttons_for_compare()
        self.create_buttons()
        self._show_originals_and_edits()

    def on_toggle_generate(self, event=None):
        """Display edited source document next to validation report widgets."""
        del event
        self.show_buttons_for_generate()
        self.create_buttons()
        self._show_edits_and_generated()

    def save_data_folder(self):
        """Show save data input file dialogue and return True if saved."""
        if not self.is_report_modified():
            if not tkinter.messagebox.askyesno(
                parent=self.get_widget(),
                message="".join(
                    (
                        "Event data has not been edited.\n\n",
                        "Do you want to save event data anyway?",
                    )
                ),
                title="Save",
            ):
                return
        results_data = self.get_context().results_data
        entry_text = results_data.entry_text

        # Ensure edited_text_on_file is set to initial value of edited_text
        # before updating edited_text from widget.
        # Perhaps this should be done earlier?
        etof = entry_text.edited_text_on_file
        self._copy_data_from_widget()

        modified = entry_text.edited_text != etof
        if not modified:
            for difference_text in results_data.difference_text:
                if (
                    difference_text.edited_text
                    != difference_text.edited_text_on_file
                ):
                    modified = True
                    break
        if not modified:
            if self.is_report_modified():
                if not tkinter.messagebox.askyesno(
                    parent=self.get_widget(),
                    message="".join(
                        (
                            "Event data is unchanged by editing action.\n\n",
                            "Do you want to save anyway?",
                        )
                    ),
                    title="Save",
                ):
                    return
        if tkinter.messagebox.askyesno(
            parent=self.get_widget(),
            message=" ".join(
                (
                    "Save\n\n",
                    self.get_context().results_folder,
                    "\n\nfolder containing results data",
                )
            ),
            title="Save",
        ):
            results_data.entry_text.save_edited_text_as_new()
            for difference_text in results_data.difference_text:
                difference_text.save_edited_text_as_new()
            results_data.entry_text.rename_new_edited_text()
            for difference_text in results_data.difference_text:
                difference_text.rename_new_edited_text()
            self.editedtext.edit_modified(False)
            tkinter.messagebox.showinfo(
                parent=self.get_widget(),
                message="Event data saved.",
                title="Save",
            )
        return

    def _save_reports(self):
        """Show save data report file dialogue and return True if saved."""
        reports = os.path.join(self.get_context().results_folder, "Reports")
        if not tkinter.messagebox.askyesno(
            parent=self.get_widget(),
            message="".join(
                ("Do you want to save reports in\n\n", reports, "\n\nfolder.")
            ),
            title="Save Reports",
        ):
            return False
        if not os.path.isdir(reports):
            try:
                os.mkdir(reports)
            except (TypeError, PermissionError):
                tkinter.messagebox.showinfo(
                    parent=self.get_widget(),
                    message="".join(
                        (
                            "Unable to create folder\n\n",
                            reports,
                            "\n\nfor reports.",
                        )
                    ),
                    title="Save Reports",
                )
                return None
        today = datetime.datetime.today().isoformat()
        for control, filename in (
            (self.schedulectrl, "rep_schedule"),
            (self.resultsctrl, "rep_results"),
            (self.editedtext, "src_results"),
        ):
            report_file = os.path.join(reports, "_".join((today, filename)))
            with open(report_file, "w", encoding="utf8") as file:
                file.write(control.get("1.0", tkinter.END))
        tkinter.messagebox.showinfo(
            parent=self.get_widget(),
            message="".join(("Reports saved in folder\n\n", reports)),
            title="Save Reports",
        )
        return None

    def _show_buttons_for_compare(self):
        """Show buttons for actions allowed comparing input data versions."""
        self.hide_panel_buttons()
        self.show_panel_buttons(
            (self._btn_toggle_generate, self.btn_closedata, self._btn_save)
        )

    def show_buttons_for_generate(self):
        """Show buttons for actions allowed displaying current input data."""
        self.hide_panel_buttons()
        self.show_panel_buttons(
            (
                self._btn_generate,
                self._btn_toggle_compare,
                self.btn_closedata,
                self._btn_save,
                self._btn_report,
            )
        )

    def show_buttons_for_update(self):
        """Show buttons for actions allowed after generating reports."""
        self.hide_panel_buttons()
        self.show_panel_buttons(
            (
                self._btn_generate,
                self._btn_toggle_compare,
                self.btn_closedata,
                self._btn_save,
                self._btn_report,
            )
        )

    def _show_edits_and_generated(self):
        """Display widgets showing current data and generated reports."""
        self._hide_panes()
        if self.editpane is None:
            self.editpane = tkinter.PanedWindow(
                master=self.toppane,
                opaqueresize=tkinter.FALSE,
                orient=tkinter.VERTICAL,
            )
        if self.generatedpane is None:
            self.generatedpane = tkinter.PanedWindow(
                master=self.toppane,
                opaqueresize=tkinter.FALSE,
                orient=tkinter.VERTICAL,
            )
        if self.editedtext is None:
            self.editedtext = self._make_textedit_tab()
            self.bind(
                self.editedtext,
                "<ButtonPress-3>",
                function=self._editedtext_popup,
            )
            self._populate_editedtext()
        if self.schedulectrl is None:
            self.schedulectrl = textreadonly.make_text_readonly(
                master=self.generatedpane
            )
            self.bind(
                self.schedulectrl,
                "<ButtonPress-3>",
                function=self._schedule_popup,
            )
        if self.resultsctrl is None:
            self.resultsctrl = textreadonly.make_text_readonly(
                master=self.generatedpane
            )
            self.bind(
                self.resultsctrl,
                "<ButtonPress-3>",
                function=self._results_popup,
            )
        self.editpane.add(self.editedtext)
        self.generatedpane.add(self.schedulectrl)
        self.generatedpane.add(self.resultsctrl)
        self.toppane.add(self.editpane)
        self.toppane.add(self.generatedpane)

        # To preserve existing content of schedulectrl and resultsctrl.
        # Have not yet considered it safe to allow Report and Update buttons to
        # come back if Generate had been done.
        # self.schedulectrl.delete('1.0', tkinter.END)
        # self.resultsctrl.delete('1.0', tkinter.END)

        # self._populate_editedtext()

        # generated_schedule and generated_results are empty at this point so
        # inserts are commented now. Also wrong when tagging ready.
        # self.schedulectrl.insert(tkinter.END, '\n'.join(
        #    self.generated_schedule))
        # self.resultsctrl.insert(tkinter.END,
        #                        '\n'.join(self.generated_results))

    def _show_originals_and_edits(self):
        """Display widgets comparing database and edited versions of data."""
        self._hide_panes()
        if self.editpane is None:
            self.editpane = tkinter.PanedWindow(
                master=self.toppane,
                opaqueresize=tkinter.FALSE,
                orient=tkinter.VERTICAL,
            )
        if self.originalpane is None:
            self.originalpane = tkinter.PanedWindow(
                master=self.toppane,
                opaqueresize=tkinter.FALSE,
                orient=tkinter.VERTICAL,
            )
        if self.editedtext is None:
            self.editedtext = self._make_textedit_tab()
            self._populate_editedtext()
        if self.originaltext is None:
            self.originaltext = textreadonly.make_text_readonly(
                master=self.originalpane
            )
            self._populate_originaltext()
        self.originalpane.add(self.originaltext)
        self.editpane.add(self.editedtext)
        self.toppane.add(self.originalpane)
        self.toppane.add(self.editpane)
        # self._populate_originaltext()
        # self._populate_editedtext()

    @staticmethod
    def _date_text(date):
        """Return dd mmm yyyy given ISO format yyyy-mm-dd."""
        year, month, day = date.split("-")
        return " ".join((day, SourceEdit._months[month], year))

    def _hide_panes(self):
        """Forget the configuration of PanedWindows on data input page."""
        for pane in (
            self.originalpane,
            self.editpane,
            self.generatedpane,
            self.toppane,
        ):
            if pane is not None:
                for widget in pane.panes():
                    pane.forget(widget)

    def is_report_modified(self):
        """Return Text.edit_modified(). Work around see Python issue 961805."""
        # return self.editedtext.edit_modified()
        return self.editedtext.winfo_toplevel().tk.call(
            "eval", "%s edit modified" % self.editedtext
        )

    def _make_textedit_tab(self):
        """Return a TextTab with bindings for editing chess results.

        The usual actions on the selection are modified to take account of the
        descriptive items inserted into the text.

        Cut to the clipboard is not supported.  Use copy then delete instead.

        When the selection includes text either side of one or more descriptive
        items replacement by typing a character is not supported.  Use delete
        followed by typing instead.

        Deletion of selected text either side of one or more descriptive items
        is allowed so large amounts of junk can be deleted in one go.  This may
        be removed in future for consistency with the replacement case.

        Descriptive items are never copied to the clipboard.

        """
        widget = texttab.make_text_tab(master=self.editpane)

        def key(event=None):
            if event.keysym == _DELETE:
                if _NOT_EDITABLE in widget.tag_names(
                    widget.index(tkinter.INSERT + " +1 char")
                ):
                    return "break"
                if _NOT_EDITABLE in widget.tag_names(
                    widget.index(tkinter.INSERT)
                ):
                    return "break"
            elif event.keysym == _BACKSPACE:
                if _NOT_EDITABLE in widget.tag_names(
                    widget.index(tkinter.INSERT + " -1 char")
                ):
                    return "break"
                if _NOT_EDITABLE in widget.tag_names(
                    widget.index(tkinter.INSERT)
                ):
                    return "break"
            elif event.keysym not in _NAVIGATION:
                tag_names = widget.tag_names(widget.index(tkinter.INSERT))
                if _NOT_EDITABLE in tag_names or _EDITABLE not in tag_names:
                    return "break"
                if widget.tag_ranges(tkinter.SEL):
                    if widget.tag_nextrange(
                        _EDITABLE,
                        tkinter.SEL_FIRST,
                        tkinter.SEL_LAST + " +1 char",
                    ):
                        return "break"
            return None

        def clear(event=None):
            if not widget.tag_ranges(tkinter.SEL):
                return key(event)
            range_ = widget.tag_nextrange(_EDITABLE, tkinter.SEL_LAST)
            if range_:
                range_ = widget.tag_prevrange(
                    _EDITABLE, widget.index(range_[0])
                )
            else:
                range_ = widget.tag_prevrange(_EDITABLE, tkinter.END)
            while range_:

                # Minimize future adjustment by 1 char
                start = widget.index(range_[0])
                end = widget.index(range_[1] + "-1 char")

                if widget.compare(end, "<", tkinter.SEL_FIRST):
                    widget.tag_remove(
                        tkinter.SEL, tkinter.SEL_FIRST, tkinter.SEL_LAST
                    )
                    break
                range_ = widget.tag_prevrange(_EDITABLE, widget.index(start))
                cstart = widget.compare(
                    tkinter.SEL_FIRST, "<=", start + "+1 char"
                )
                cend = widget.compare(tkinter.SEL_LAST, ">=", end)

                # Adjust end by 1 char if necessary to compensate for the extra
                # newline which may have been added by _insert_entry() method.
                pee = widget.index(end + "-1 char")
                if widget.compare(pee, "==", pee + "lineend"):
                    end = pee

                if cstart and cend:
                    widget.delete(start + "+1 char", end)
                elif cstart:
                    widget.delete(start + "+1 char", tkinter.SEL_LAST)
                    if not widget.tag_ranges(tkinter.SEL):
                        break
                elif cend:
                    if widget.compare(
                        tkinter.SEL_FIRST,
                        "!=",
                        tkinter.SEL_FIRST + "linestart",
                    ):
                        widget.delete(tkinter.SEL_FIRST, end)
                    elif widget.compare(tkinter.SEL_FIRST, ">", start):
                        widget.delete(tkinter.SEL_FIRST + "-1 char", end)
                    else:
                        widget.delete(tkinter.SEL_FIRST, end)
                else:
                    widget.delete(tkinter.SEL_FIRST, tkinter.SEL_LAST)
                    break
            return "break"

        # Copy the _EDITABLE characters between SEL_FIRST and SEL_LAST to the
        # clipboard.  The _NON_EDITABLE characters which may split the
        # selection into regions are present to preserve source identification
        # of text, and are not copied.  These are in the highlighted areas.
        def clip(event=None):
            del event
            ranges = list(widget.tag_ranges(_EDITABLE))
            widget.clipboard_clear()
            while ranges:
                start, end = ranges.pop(0), ranges.pop(0)
                if widget.compare(end, "<", tkinter.SEL_FIRST):
                    continue
                if widget.compare(start, ">", tkinter.SEL_LAST):
                    break
                if widget.compare(start, "<", tkinter.SEL_FIRST):
                    start = tkinter.SEL_FIRST
                if widget.compare(end, ">", tkinter.SEL_LAST):
                    end = tkinter.SEL_LAST
                widget.clipboard_append(
                    widget.get(start, end), type="UTF8_STRING"
                )
            return "break"

        widget.event_add("<<Clear>>", "<BackSpace>")
        widget.event_add("<<Clear>>", "<Delete>")
        self.bind(widget, "<<Clear>>", function=clear)
        self.bind(widget, "<KeyPress>", function=key)
        self.bind(widget, "<Control-x>", function=lambda e: "break")
        self.bind(widget, "<Control-c>", function=clip)

        # An explicit binding is needed on Microsoft Windows XP, and other
        # versions I assume, for the paste part of copy-and-paste to do the
        # paste in the presence of the <Control-c> binding to the clip function
        # for the copy part.
        # This paste binding is not needed if the copy binding is not done.
        # Neither paste binding nor paste function is needed on FreeBSD.
        # The situation with other BSDs, and any Linux, is not known.
        def paste(event=None):
            del event
            widget.insert(
                tkinter.INSERT, widget.clipboard_get(type="UTF8_STRING")
            )
            return "break"

        self.bind(widget, "<Control-v>", function=paste)

        return widget

    @staticmethod
    def _insert_entry(widget, tagsuffix, entry, text):  # title, text):
        """Insert entry header and tagged text into widget."""
        # Just the whole text tag is put back in the _DifferenceText instance.
        # To be extended later when it is clear how it works exactly.
        # The tagging is the same for edited and original text but different
        # versions of text, chosen by caller, are displayed.
        # Generated reports will use the same tags to refer to the source text.
        if tagsuffix == LOCAL_SOURCE:
            title = entry.filename_header
        else:
            title = entry.sender_and_date

        # Maybe put all these tags in the entry instance and retrieve them.
        entry.set_tags(tagsuffix)
        data = entry.data_tag
        header = entry.header_tag
        trailer = entry.trailer_tag

        widget.tag_configure(header, background=_SENDER_COLOUR)
        widget.tag_configure(trailer, background=_SENDER_COLOUR)
        start = widget.index(tkinter.INSERT)
        widget.insert(tkinter.INSERT, title)
        widget.insert(tkinter.INSERT, "\n")
        datastart = widget.index(tkinter.INSERT)
        widget.insert(tkinter.INSERT, "\n")
        widget.tag_add(header, start, widget.index(tkinter.INSERT))
        widget.tag_add(_NOT_EDITABLE, start, widget.index(tkinter.INSERT))
        widget.insert(tkinter.INSERT, text)
        start = widget.index(tkinter.INSERT)
        widget.insert(tkinter.INSERT, "\n")
        widget.tag_add(_EDITABLE, datastart, widget.index(tkinter.INSERT))
        widget.tag_add(data, datastart, widget.index(tkinter.INSERT))

        # Put an extra newline in the trailer if the previous editable section
        # of text did not end with a newline.  This ensures a full highlighted
        # blank line appears before the header rather than a partial one.
        # This may be redundant now: see comments in extracted_text property in
        # ExtractText class in emailextractor module.
        if (
            widget.get(" ".join((widget.index(tkinter.INSERT), "-2 char")))
            != "\n"
        ):
            start = widget.index(tkinter.INSERT)
            widget.insert(tkinter.INSERT, "\n")

        widget.tag_add(trailer, start, widget.index(tkinter.INSERT))
        widget.tag_add(_NOT_EDITABLE, start, widget.index(tkinter.INSERT))

    def _populate_editedtext(self):
        """Put edited document in it's Text widget for display."""
        wedit = self.editedtext
        wedit.delete("1.0", tkinter.END)
        entry_text = self.get_context().results_data.entry_text
        self._insert_entry(
            wedit, LOCAL_SOURCE, entry_text, entry_text.edited_text
        )
        for i, difference_text in enumerate(
            self.get_context().results_data.difference_text
        ):
            self._insert_entry(
                wedit, str(i), difference_text, difference_text.edited_text
            )

    def _populate_originaltext(self):
        """Put original document in it's Text widget for display."""
        worig = self.originaltext
        worig.delete("1.0", tkinter.END)
        entry_text = self.get_context().results_data.entry_text
        self._insert_entry(
            worig, LOCAL_SOURCE, entry_text, entry_text.original_text
        )
        for i, difference_text in enumerate(
            self.get_context().results_data.difference_text
        ):
            self._insert_entry(
                worig, str(i), difference_text, difference_text.original_text
            )

    def _copy_data_from_widget(self):
        """Copy current widget data to season's event data attributes."""
        wedit = self.editedtext
        results_data = self.get_context().results_data

        # Strip off the place-holder newline characters returned by get.
        # These were added by insert when the data was displayed.
        for difference_text in results_data.difference_text:
            start, end = wedit.tag_ranges(difference_text.data_tag)
            difference_text.edited_text = wedit.get(
                wedit.index(start) + " +1 char", wedit.index(end) + " -1 char"
            )
        entry_text = results_data.entry_text
        start, end = wedit.tag_ranges(entry_text.data_tag)
        entry_text.edited_text = wedit.get(
            wedit.index(start) + " +1 char", wedit.index(end) + " -1 char"
        )

    def _results_popup(self, event=None):
        """Scroll edited document to selected text in result report."""
        wedit = self.editedtext
        wresults = self.resultsctrl
        tags = wresults.tag_names(
            wresults.index("".join(("@", str(event.x), ",", str(event.y))))
        )
        for tag in tags:
            if tag.startswith(_SELECT_FROM_GENERATED):
                tredit = wedit.tag_ranges(tag)
                if tredit:
                    wedit.see(tredit[0])
                    return

    def _schedule_popup(self, event=None):
        """Scroll edited document to selected text in schedule report."""
        wedit = self.editedtext
        wschedule = self.schedulectrl
        tags = wschedule.tag_names(
            wschedule.index("".join(("@", str(event.x), ",", str(event.y))))
        )
        for tag in tags:
            if tag.startswith(_SELECT_FROM_GENERATED):
                tredit = wedit.tag_ranges(tag)
                if tredit:
                    wedit.see(tredit[0])
                    return

    def _editedtext_popup(self, event=None):
        """Scroll source document to selected text in edited document."""
        worig = self.originaltext
        wedit = self.editedtext
        tags = wedit.tag_names(
            wedit.index("".join(("@", str(event.x), ",", str(event.y))))
        )
        for tag in tags:
            if tag[:2] in _SELECT_ORIG_FROM_EDIT:
                if worig:
                    trorig = worig.tag_ranges(tag)
                    if worig:
                        worig.see(trorig[0])
                        return

    def _generate_event_report(self):
        """Generate report on data input and return True if data is ok.

        Data can be ok and still be wrong.  ok means merely that the data
        input is consistent.  A number of formats are acceptable and named
        in sectiontypes below.

        """
        sectiontypes = {
            "allplayall": self._report_allplayall,  # individuals
            "league": lambda s, d: None,  # team all play all
            "swiss": self._report_swiss,  # individuals
            "fixturelist": lambda s, d: None,  # matches from fixture list
            "individual": self._report_individual,  # games between players
        }
        self._copy_data_from_widget()
        data = self.get_context().results_data
        try:
            data.extract_event()
        except EventParserError as exp:
            tkinter.messagebox.showinfo(
                parent=self.get_widget(),
                message=str(exp),
                title="Event Extract Error",
            )
            return False
        except RuntimeError as exp:
            if str(exp) == IEIREE:
                tkinter.messagebox.showinfo(
                    parent=self.get_widget(),
                    message=" ".join(
                        (
                            "An exception has occurred while extracting",
                            "result information using one of the default",
                            "regular expressions.\n\nThe latest version of",
                            "Python, or at least a different version (change",
                            "between 3.3.1 and 3.3.2 for example) may process",
                            "the text correctly.\n\nAn exception will be",
                            "raised on dismissing this dialogue.",
                        )
                    ),
                    title="Regular Expression Runtime Error",
                )
            raise
        try:
            self.get_schedule(data)
        except ScheduleError as exp:
            tkinter.messagebox.showinfo(
                parent=self.get_widget(),
                message="".join(
                    (
                        str(exp).join(('Exception "', '" has occurred.\n\n')),
                        "This probably indicates an invalid combination of ",
                        "settings in the result extraction configuration ",
                        "file.",
                    )
                ),
                title="Extract Schedule Error",
            )
            return False
        except:
            tkinter.messagebox.showinfo(
                parent=self.get_widget(),
                message="".join(
                    (
                        "An exception has occured and will be reported on ",
                        "dismissing this dialogue.\n\nPlease consider the ",
                        "possibility text in one of the emails has been ",
                        "misinterpreted as unexpected information about ",
                        "a result, rather than being ignored.\n\nWords like ",
                        "'default' and 'draw', or a sprinkling of numbers ",
                        "like '1', '12' and '2', are likely culprits ",
                        "because they have a place in identifying results.",
                        "\n\nThe possibility is a consequence of not being ",
                        "too fussy about how results are presented.",
                    )
                ),
                title="Generate",
            )
            raise
        self._report_fixtures(data)

        # Remove the 'try' wrapping once the problem is fixed.
        # The KeyError might be fixable but the AttributeError is a genuine
        # problem found by accident; and probably deserves an Exception of
        # it's own.
        try:
            self.get_results(data)
        except KeyError:
            tkinter.messagebox.showinfo(
                parent=self.get_widget(),
                message="".join(
                    (
                        "Known causes of this exception are:\n\n",
                        "A badly-formed entry in a swiss table: for example ",
                        "'x' or 'w12w'.\n",
                        "\nA well-formed entry in a swiss table refering to ",
                        "a row which does not exist: for example 'w12+' ",
                        "where '12' is not a player's PIN.\n",
                        "\nAn ECF code or membership number missing the ",
                        "single alpha character suffix or prefix.\n",
                        "\n Edit document as workaround (or solution).",
                    )
                ),
                title="Generate Report KeyError Exception",
            )
            return False
        except AttributeError as exc:
            if str(exc) != "".join(
                ("'NoneType' object has no attribute 'authorization_delay'",)
            ):
                raise
            tkinter.messagebox.showinfo(
                parent=self.get_widget(),
                message="".join(
                    (
                        "The known cause of this exception is:\n\n",
                        "Type a match result in the textentry area, ",
                        "perhaps because the usual email report is ",
                        "not available, with date, competition, ",
                        "match score, and each game result, on their ",
                        "own line.  This is the format accepted by ",
                        "default without rules in configuration file.\n\n",
                        "Copy, paste, and edit, a match result in it's ",
                        "usual email format to the textentry area leads ",
                        "to a normal error report expected in other ",
                        "situations.\n\nIf the match report must be ",
                        "typed do the copy, paste, and edit, in the ",
                        "copied report's original email area.",
                    )
                ),
                title="Generate Report AttributeError Exception",
            )
            return False

        if (
            len(data.collation.reports.error) == 0
            and len(data.fixture_schedule.error) == 0
        ):

            schedule = data.collation.schedule
            self.generated_schedule.insert(0, (schedule.es_name, None))
            self.generated_schedule.insert(
                1,
                (
                    " ".join(
                        (
                            "From",
                            self._date_text(schedule.es_startdate),
                            "to",
                            self._date_text(schedule.es_enddate),
                        )
                    ),
                    None,
                ),
            )

            report = data.collation.reports
            genres = self.generated_results
            genres.append((report.er_name, None))
            self._report_players(data)
            league_processed = False
            for section in data.collation.report_order:
                process = sectiontypes.get(
                    data.collation.section_type[section],
                    self._section_type_unknown,
                )
                if not isinstance(process, collections.abc.Callable):
                    process = self._report_not_implemented
                process(section, data)
                if process is sectiontypes["league"]:
                    league_processed = True
                elif process is sectiontypes["fixturelist"]:
                    league_processed = True
            if league_processed:
                self._report_league(None, data)
        self.schedulectrl.delete("1.0", tkinter.END)

        widget = self.schedulectrl
        while self.generated_schedule:
            report_text, report_error = self.generated_schedule.pop(0)
            if report_error is None:
                widget.insert(tkinter.END, report_text)
                if self.generated_schedule:
                    widget.insert(tkinter.END, "\n")
            else:
                datastart = widget.index(tkinter.INSERT)
                tag, text = report_error.get_schedule_tag_and_text(report_text)
                widget.insert(tkinter.END, text)
                if self.generated_schedule:
                    widget.insert(tkinter.END, "\n")
                widget.tag_add(tag, datastart, widget.index(tkinter.INSERT))

        self.resultsctrl.delete("1.0", tkinter.END)

        widget = self.resultsctrl
        while self.generated_results:
            report_text, report_error = self.generated_results.pop(0)
            if report_error is None:
                widget.insert(tkinter.END, report_text)
                if self.generated_results:
                    widget.insert(tkinter.END, "\n")
            else:
                datastart = widget.index(tkinter.INSERT)
                tag, text = report_error.get_report_tag_and_text(report_text)
                widget.insert(tkinter.END, text)
                if self.generated_results:
                    widget.insert(tkinter.END, "\n")
                widget.tag_add(tag, datastart, widget.index(tkinter.INSERT))

        return len(data.collation.reports.error) == 0

    def _report_fixtures(self, data):
        """Append fixtures to event schedule report."""
        fixdata = data.fixture_schedule
        if len(fixdata.error):
            return
        genfix = self.generated_schedule
        genfix.append(("", None))
        divisions = sorted(list(fixdata.es_summary.keys()))
        for division in divisions:
            genfix.append((division, None))
            teams = sorted(list(fixdata.es_summary[division]["teams"].keys()))
            for team in teams:
                team_data = fixdata.es_summary[division]["teams"][team]
                genfix.append(
                    (
                        "".join(
                            (
                                team,
                                "   ",
                                str(team_data["homematches"]),
                                " home, ",
                                str(team_data["awaymatches"]),
                                " away matches",
                            )
                        ),
                        None,
                    )
                )
            genfix.append(("", None))
        fixtures = []
        if len(fixdata.es_fixtures):
            for fixture in fixdata.es_fixtures:
                fixtures.append(
                    (
                        (
                            fixture.competition,
                            "  ",
                            fixture.hometeam,
                            " - ",
                            fixture.awayteam,
                        ),
                        len(
                            fixtures
                        ),  # to hide unorderable fixture.tagger from sort
                        fixture.tagger,
                    )
                )
            fixtures.sort()
            for fixture, count, tagger in fixtures:
                del count
                tagger.append_generated_schedule(genfix, "".join(fixture))
            genfix.append(("", None))

    def _report_fixtures_played_status(self, data):
        """Append list of unreported fixtures to results report."""
        if len(data.collation.reports.error):
            return
        genres = self.generated_results
        fnp = data.collation.get_fixtures_not_played()
        if len(fnp) == 0:
            return
        today = datetime.date.today().isoformat()
        genres.append(
            (
                "".join(
                    ("Fixtures not played or not reported at ", today, "\n")
                ),
                None,
            )
        )
        for match in fnp:
            if match.date > today:
                dfnp = "          "
            else:
                dfnp = match.date
            match.tagger.append_generated_report(
                genres,
                " ".join(
                    (
                        dfnp,
                        match.competition,
                        match.hometeam,
                        "-",
                        match.awayteam,
                    )
                ),
            )
        genres.append(("", None))

    def _report_matches(self, data):
        """Append list of reported fixtures to results report."""
        resdata = data.collation
        if len(resdata.reports.error):
            return
        genres = self.generated_results
        genres.append(("Matches in event by competition\n", None))
        for match in resdata.get_reports_by_match():
            hts = match.homescore
            if not hts:
                hts = ""
            ats = match.awayscore
            if not ats:
                ats = ""
            match.tagger.append_generated_report(
                genres,
                " ".join(
                    (
                        match.hometeam,
                        hts,
                        "-",
                        ats,
                        match.awayteam,
                        "\t\t\t\t\t",
                        match.competition,
                    )
                ),  # source
            )
            if match.default:
                genres.append(("    Match defaulted", None))
            for game in match.games:
                result, uftag, gradetag = game.get_print_result()
                if game in resdata.gamesxref:
                    uftag = displayresult.get(
                        resdata.gamesxref[game].result, uftag
                    )
                if len(uftag) or len(gradetag):
                    uftag = "    ".join(("", uftag, gradetag))
                if not result:
                    result = "     "
                homeplayer = game.homeplayer.name
                if not homeplayer:
                    homeplayer = ""
                awayplayer = game.awayplayer.name
                if not awayplayer:
                    awayplayer = ""
                game.tagger.append_generated_report(
                    genres,
                    " ".join(
                        (
                            "   ",
                            homeplayer,
                            result,
                            awayplayer,
                            "       ",
                            uftag,
                        )
                    ),
                )
            genres.append(("", None))

    def _report_matches_by_source(self, data):
        """Override, append list of fixtures by source to results report.

        Source may be a file name or some kind of heading within the file.  The
        report for each fixture may include a comment that game scores for the
        fixture are not consistent with total score.

        """
        # The PDLEdit and SLEdit references are long since deleted, but they
        # are why code is as is here.
        # PDLEdit should have had some tests on source attribute according to
        # docstring for _report_matches_by_source.

        # Only SLEdit had this check.
        if len(data.collation.reports.error):
            return

        # Part of SLEdit hack to spot matches played before fixture date when
        # no dates reported on match results.
        today = datetime.date.today().isoformat()

        genres = self.generated_results
        genres.append(
            ("\nMatch reports sorted by email date and team names\n", None)
        )
        matches, playedongames = data.collation.get_reports_by_source()
        if matches:
            currtag = matches[0][0].tagger.datatag
        for match, ufg, consistent in matches:
            del ufg
            if currtag != match.tagger.datatag:
                currtag = match.tagger.datatag
                genres.append(("", None))
            match.tagger.append_generated_report(
                genres,
                " ".join((match.hometeam, "-", match.awayteam)),
            )

            # Part of SLEdit hack to spot matches played before fixture date.
            # Need to test 'date report sent' for correct answer always.
            try:
                if len(today) == len(match.date):
                    if match.date > today:
                        match.tagger.append_generated_report(
                            genres,
                            "".join(("   match reported early at ", today)),
                        )
            except (TypeError, AttributeError):
                pass

            if not consistent:
                genres.append(
                    ("   match score not consistent with game reports", None)
                )
            for game in match.games:
                if game.result is None:
                    homeplayer = game.homeplayer
                    if homeplayer:
                        homeplayer = homeplayer.name
                    else:
                        homeplayer = ""
                    awayplayer = game.awayplayer
                    if awayplayer:
                        awayplayer = awayplayer.name
                    else:
                        awayplayer = ""
                    game.tagger.append_generated_report(
                        genres,
                        " ".join(
                            ("   unfinished  ", homeplayer, "-", awayplayer)
                        ),
                    )
        if len(playedongames):
            genres.append(("\nPlayed-on Games in entry order\n", None))
            currtag = playedongames[0].tagger.datatag
            for game in playedongames:
                if game.result is None:
                    continue
                if currtag != game.tagger.datatag:
                    currtag = game.tagger.datatag
                    genres.append(("", None))
                game.tagger.append_generated_report(
                    genres,
                    " ".join(("   ", game.hometeam, "-", game.awayteam)),
                )
                homeplayer = game.homeplayer
                if homeplayer:
                    homeplayer = homeplayer.name
                else:
                    homeplayer = ""
                awayplayer = game.awayplayer
                if awayplayer:
                    awayplayer = awayplayer.name
                else:
                    awayplayer = ""
                game.tagger.append_generated_report(
                    genres,
                    "".join(
                        (
                            "        ",
                            " ".join(
                                (
                                    homeplayer,
                                    displayresult.get(game.result, "unknown"),
                                    awayplayer,
                                )
                            ),
                        )
                    ),
                )
        genres.append(("", None))

    def _report_non_fixtures_played(self, data):
        """Append list of results additional to fixtures to results report."""
        if len(data.collation.reports.error):
            return
        genres = self.generated_results
        nfp = data.collation.get_non_fixtures_played()
        if len(nfp) == 0:
            return
        genres.append(("Reported matches not on fixture list\n", None))
        for match in nfp:
            match.tagger.append_generated_report(
                genres,
                " ".join(
                    (
                        match.competition,
                        "",
                        match.hometeam,
                        "-",
                        match.awayteam,
                    )
                ),
            )
        genres.append(("", None))

    def _report_players(self, data):
        """Append list of players sorted by affiliation to schedule report."""
        if len(data.collation.reports.error):
            return
        schedule = data.collation.schedule
        genfix = self.generated_schedule
        if len(data.collation.players):
            genfix.append(("", None))
            genfix.append(
                (
                    " ".join(
                        (
                            "Player identities (with club or place",
                            "association and reported codes)",
                        )
                    ),
                    None,
                )
            )
            genfix.append(("", None))
        drp = data.collation.players
        for name, player in [
            p[-1]
            for p in sorted(
                [
                    (
                        AppSysPersonName(drp[p].name).name,
                        (drp[p].get_brief_identity(), p),
                    )
                    for p in drp
                ]
            )
        ]:
            section = drp[player].section
            if section in schedule.es_players:
                if name in schedule.es_players[section]:
                    genfix.append(
                        (
                            "\t".join(
                                (
                                    drp[player].get_short_identity(),
                                    "".join(
                                        (
                                            "(",
                                            schedule.es_players[section][
                                                name
                                            ].affiliation,
                                            ")",
                                        )
                                    ),
                                    drp[player].get_reported_codes(),
                                )
                            ).strip(),
                            None,
                        )
                    )
                    continue
            genfix.append(
                (
                    "\t".join(
                        (
                            self.get_player_brief(drp[player]),
                            drp[player].get_reported_codes(),
                        )
                    ).strip(),
                    None,
                )
            )

    @staticmethod
    def get_player_brief(player):
        """Return player identity for schedule report."""
        return player.get_short_identity()

    def _report_player_matches(self, data):
        """Append list of fixtures for each player to results report."""
        if len(data.collation.reports.error):
            return
        teamplayers = data.collation.get_reports_by_player()
        genres = self.generated_results
        genres.append(("Player reports\n", None))
        for player in sorted(teamplayers.keys()):
            genres.append((player[-1][0], None))
            match_games = []
            for team, match in teamplayers[player]:
                match_games.append(
                    (match.date if match.date is not None else "", team, match)
                )
            for team, match in [m[-2:] for m in sorted(match_games)]:
                hometeam = match.hometeam
                awayteam = match.awayteam
                if hometeam == team:
                    hometeam = "*"
                if awayteam == team:
                    awayteam = "*"
                match.tagger.append_generated_report(
                    genres,
                    " ".join(
                        (
                            "  ",
                            team,
                            "  ",
                            hometeam,
                            "-",
                            awayteam,
                            "    ",
                            match.source,
                        )
                    ),
                )
            genres.append(("", None))

    def report_players_by_club(self, data):
        """Append list of players sorted by club to results report."""
        if len(data.collation.reports.error):
            return
        clubs = data.collation.get_players_by_club()
        eventname = set()
        for club_players in clubs.values():
            for player_name in club_players:
                eventname.add(player_name[1:-1])
        genres = self.generated_results

        genres.append(("Players by club\n", None))
        genres.append(
            (
                "".join(
                    (
                        "This report was generated without a database open ",
                        "to look up grading codes.",
                    )
                ),
                None,
            )
        )
        genres.append(
            (
                "".join(
                    (
                        "Any reported codes, usually grading codes, follow ",
                        "the player name.\n",
                    )
                ),
                None,
            )
        )
        for club_name in sorted(clubs.keys()):
            clubplayers = data.collation.clubplayers[club_name]
            genres.append((club_name + "\n", None))
            for player_name in clubs[club_name]:
                genres.append(
                    (
                        "\t\t\t\t".join(
                            (
                                player_name[0],
                                " ".join(clubplayers[player_name]),
                            )
                        ),
                        None,
                    )
                )
            genres.append(("", None))
        return

    def _report_unfinished_games(self, data):
        """Append list of unfinished reported games to results report."""
        if len(data.collation.reports.error):
            return
        genres = self.generated_results
        unfinished_games = data.collation.get_unfinished_games()
        if len(unfinished_games) == 0:
            return
        genres.append(("Unfinished games\n", None))
        for match, game in unfinished_games:
            match.tagger.append_generated_report(
                genres,
                " ".join(
                    (match.hometeam, "-", match.awayteam, "   ", match.source)
                ),
            )
            game.tagger.append_generated_report(
                genres,
                " ".join(
                    (
                        "  ",
                        game.board,
                        game.homeplayer.name,
                        "-",
                        game.awayplayer.name,
                    )
                ),
            )
        genres.append(("", None))

    # Method used in three subclasses but not this class.
    # Code originally in update_event_results() method of ChessResults
    # version of SourceEdit class (when it was only version).
    # In the real chess world unfinished games are rapidly becoming
    # something that does not happen, and may become against the rules
    # in future.
    def collate_unfinished_games(self):
        """Add completed unfinished games into game results."""
        cug = self.get_context().results_data.get_collated_unfinished_games()
        cfg = self.get_context().results_data.get_collated_games()
        for report in cfg:
            for game in cfg[report].games:
                if game in cug:
                    if cug[game].result is not None:
                        game.result = cug[game].result

    # Preserve original method name for a while.
    _collate_unfinished_games = collate_unfinished_games

    def _report_allplayall(self, section, data):
        """Generate results report for all play all event."""
        schedule = data.collation.schedule
        genres = self.generated_results
        if section not in data.collation.games:
            genres.append(("", None))
            genres.append((section, None))
            genres.append(("No games reported for this competition", None))
            genres.append(("", None))
            return
        if section in data.collation.reports.er_section:
            games = data.collation.games[section].games
            genres.append(("", None))
            genres.append((section, None))

            # Hack round for wallcharts and swiss tournaments presented in
            # an all-play-all format, because the deduced round is wrong or
            # irrelevant.
            if len(schedule.es_round_dates[section]):
                genres.append(("Games in round order", None))
            else:
                genres.append(
                    ("All-play-all format games in entry order", None)
                )
                round_date = None

            round_ = None
            for game in games:
                if round_ != game.round:
                    round_ = game.round
                    genres.append(("", None))
                    if round_ in schedule.es_round_dates[section]:
                        round_date = schedule.es_round_dates[section][round_]
                    else:
                        round_date = schedule.es_startdate
                    game.tagger.append_generated_report(
                        genres,
                        " ".join(
                            (
                                section,
                                "Round",
                                str(round_),
                                "played on",
                                self._date_text(round_date),
                            )
                        ),
                    )
                    genres.append(("", None))
                if round_date == game.date:
                    game.tagger.append_generated_report(
                        genres,
                        " ".join(
                            (
                                game.homeplayer.name,
                                game.get_print_result()[0],
                                game.awayplayer.name,
                            )
                        ),
                    )
                else:
                    game.tagger.append_generated_report(
                        genres,
                        " ".join(
                            (
                                self._date_text(game.date),
                                game.homeplayer.name,
                                game.get_print_result()[0],
                                game.awayplayer.name,
                            )
                        ),
                    )

    def _report_individual(self, section, data):
        """Generate results report for collection of games for individuals."""
        genres = self.generated_results
        if section not in data.collation.games:
            genres.append(("", None))
            genres.append((section, None))
            genres.append(("No games reported for this competition", None))
            genres.append(("", None))
            return
        schedule = data.collation.schedule
        report = data.collation.games[section]
        if section in data.collation.reports.er_section:
            games = report.games
            genres.append(("", None))
            genres.append((section, None))
            genres.append(("Games in entry order", None))
            event_date = schedule.es_startdate
            for game in games:
                if event_date == game.date:
                    game.tagger.append_generated_report(
                        genres,
                        " ".join(
                            (
                                game.homeplayer.name,
                                game.get_print_result()[0],
                                game.awayplayer.name,
                            )
                        ),
                    )
                else:
                    game.tagger.append_generated_report(
                        genres,
                        " ".join(
                            (
                                self._date_text(game.date),
                                game.homeplayer.name,
                                game.get_print_result()[0],
                                game.awayplayer.name,
                            )
                        ),
                    )

    def _report_league(self, section, data):
        """Generate results report for matches in a league."""
        del section
        self._report_matches_by_source(data)
        self._report_fixtures_played_status(data)
        self._report_non_fixtures_played(data)
        self._report_unfinished_games(data)
        self._report_matches(data)
        self.report_players_by_club(data)
        self._report_player_matches(data)

    @staticmethod
    def _report_not_implemented(section, data):
        data.collation.error.append(("", None))
        data.collation.error.append(
            (
                " ".join(("Support for", section, "format not implemented")),
                None,
            )
        )
        data.collation.error.append(("", None))

    def _report_swiss(self, section, data):
        """Generate results report for swiss tournament for individuals."""
        genfix = self.generated_schedule
        genres = self.generated_results
        schedule = data.collation.schedule
        report = data.collation.reports
        if section not in data.collation.games:
            genres.append(("", None))
            genres.append((section, None))
            genres.append(("No games reported for this competition", None))
            genres.append(("", None))
            return
        games = data.collation.games[section].games
        if section in schedule.es_section:
            genfix.append(("", None))
            genfix.append((section, None))
            rounds = sorted(list(schedule.es_round_dates[section].keys()))
            round_count = 0
            for pin in report.er_swiss_table[section]:
                round_count = max(
                    round_count, len(report.er_swiss_table[section][pin])
                )
            genfix.append(("Round dates", None))
            if len(rounds):
                for round_ in rounds:
                    genfix.append(
                        (
                            "\t".join(
                                (
                                    str(round_),
                                    self._date_text(
                                        schedule.es_round_dates[section][
                                            round_
                                        ]
                                    ),
                                )
                            ),
                            None,
                        )
                    )
                if len(rounds) != round_count:
                    genfix.append(
                        (
                            " ".join(
                                (
                                    "The following rounds have no specified",
                                    "date. These are deemed played on the",
                                    "eventstart date.",
                                )
                            ),
                            None,
                        )
                    )
                    for round_ in range(1, round_count + 1):
                        if round_ not in rounds:
                            genfix.append(
                                (" ".join(("Round", str(round_))), None)
                            )
            else:
                genfix.append(
                    (
                        " ".join(
                            (
                                "All rounds are deemed played on the event",
                                "start date because no round dates are",
                                "specified.",
                            )
                        ),
                        None,
                    )
                )
        if section in report.er_section:
            games = data.collation.games[section].games
            genres.append(("", None))
            genres.append((section, None))
            genres.append(("Games in round order", None))
            round_ = None
            for game in games:
                if round_ != game.round:
                    round_ = game.round
                    genres.append(("", None))
                    intr = int(round_) if round_.isdigit() else round_
                    if intr in schedule.es_round_dates[section]:
                        round_date = schedule.es_round_dates[section][intr]
                    else:
                        round_date = schedule.es_startdate
                    game.tagger.append_generated_report(
                        genres,
                        " ".join(
                            (
                                section,
                                "Round",
                                str(round_),
                                "played on",
                                self._date_text(round_date),
                            )
                        ),
                    )
                    genres.append(("", None))
                if round_date == game.date:
                    game.tagger.append_generated_report(
                        genres,
                        " ".join(
                            (
                                game.homeplayer.name,
                                game.get_print_result()[0],
                                game.awayplayer.name,
                            )
                        ),
                    )
                else:
                    game.tagger.append_generated_report(
                        genres,
                        " ".join(
                            (
                                self._date_text(game.date),
                                game.homeplayer.name,
                                game.get_print_result()[0],
                                game.awayplayer.name,
                            )
                        ),
                    )

    @staticmethod
    def _section_type_unknown(section, data):
        data.collation.error.append(("", None))
        data.collation.error.append(
            (" ".join((section, "type not known")), None)
        )
        data.collation.error.append(("", None))
