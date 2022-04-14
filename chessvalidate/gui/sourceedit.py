# sourceedit.py
# Copyright 2008 Roger Marsh
# Licence: See LICENCE (BSD licence)

"""Schedule and results raw data edit class.

This class is based on SLEdit in results/hampshire/gui/sledit.py (no longer
included in distribution).  This emphasises the history of this application:
which started as a way of collating the emails used to report Southampton
League results for input into the ECF's League program and was then extended to
update a database directly.  Note that SLEdit is a subclass of SourceEdit in
contrast to the development history.

"""

import tkinter
import tkinter.messagebox
import difflib
import os
import datetime
import collections

from solentware_misc.core.utilities import AppSysPersonName
from solentware_misc.gui import panel, dialogue, textreadonly, texttab

from ..core.eventparser import EventParserError, IEIREE
from ..core import collationdb
from ..core import filespec
from ..core.season import (
    LOCAL_SOURCE,
    HEADER_TAG,
    DATA_TAG,
    TRAILER_TAG,
    SEPARATOR,
)
from ..core.gameresults import displayresult
from ..core.resultsrecord import (
    get_events_matching_event_name,
    get_aliases_for_event,
    get_name,
    get_alias,
)
from ..core.ecfmaprecord import (
    get_grading_code_for_person,
    get_person,
)
from ..core.ecfrecord import get_ecf_player_for_grading_code
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


class SourceEdit(panel.PlainPanel):

    """The Edit panel for raw results data."""

    _btn_generate = "sourceedit_generta"
    _btn_closedata = "sourceedit_close"
    _btn_save = "sourceedit_save"
    _btn_toggle_compare = "sourceedit_toggle_compare"
    _btn_toggle_generate = "sourceedit_toggle_generate"
    _btn_update = "sourceedit_update"
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

    def __init__(self, parent=None, cnf=dict(), **kargs):
        """Extend and define results data input panel for a results database"""
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
            text=self.get_context().get_season_folder(),
        )
        self.folder.pack(side=tkinter.TOP, fill=tkinter.X)
        self.toppane = tkinter.PanedWindow(
            master=self.get_widget(),
            opaqueresize=tkinter.FALSE,
            orient=tkinter.HORIZONTAL,
        )
        self.toppane.pack(side=tkinter.TOP, expand=True, fill=tkinter.BOTH)
        self.show_edits_and_generated()
        self.editedtext.edit_modified(tkinter.FALSE)

    def close(self):
        """Close resources prior to destroying this instance.

        Used, at least, as callback from AppSysFrame container.

        """
        pass

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
                    "Display original and edited results data but not generated",
                    "data.",
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
                    "Display edited source and generated data but not original",
                    "source.",
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
            self._btn_update,
            text="Update",
            tooltip="Update results database from generated data.",
            underline=0,
            command=self.on_update,
        )
        self.define_button(
            self._btn_closedata,
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
        fixdata = data._fixtures
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
        self.close_data_folder()
        self.inhibit_context_switch(self._btn_closedata)

    def on_generate(self, event=None):
        """Generate a validation report."""
        if self.generate_event_report():
            self.show_buttons_for_update()
            self.create_buttons()

    def on_report(self, event=None):
        """Save validation report."""
        self.save_reports()

    def on_save(self, event=None):
        """Save source document."""
        self.save_data_folder()

    def on_toggle_compare(self, event=None):
        """Display original source document alongside edited source document."""
        self.show_buttons_for_compare()
        self.create_buttons()
        self.show_originals_and_edits()

    def on_toggle_generate(self, event=None):
        """Display edited source document alongside validation report widgets."""
        self.show_buttons_for_generate()
        self.create_buttons()
        self.show_edits_and_generated()

    def on_update(self, event=None):
        """Update database from validated source document."""
        if self.update_event_results():
            db = self.get_appsys().get_results_database()
            self.refresh_controls(
                (
                    (
                        db,
                        filespec.PLAYER_FILE_DEF,
                        filespec.PLAYERPARTIALNEW_FIELD_DEF,
                    ),
                    (
                        db,
                        filespec.EVENT_FILE_DEF,
                        filespec.EVENTNAME_FIELD_DEF,
                    ),
                )
            )
            self.show_buttons_for_generate()
            self.create_buttons()

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
        dt = results_data.entry_text

        # Ensure edited_text_on_file is set to initial value of edited_text
        # before updating edited_text from widget.
        # Perhaps this should be done earlier?
        etof = dt.edited_text_on_file
        self.copy_data_from_widget()

        modified = dt.edited_text != etof
        if not modified:
            for e, dt in enumerate(results_data.difference_text):
                if dt.edited_text != dt.edited_text_on_file:
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
                    self.get_context().get_season_folder(),
                    "\n\nfolder containing results data",
                )
            ),
            title="Save",
        ):
            results_data.entry_text.save_edited_text_as_new()
            for dt in results_data.difference_text:
                dt.save_edited_text_as_new()
            results_data.entry_text.rename_new_edited_text()
            for dt in results_data.difference_text:
                dt.rename_new_edited_text()
            self.editedtext.edit_modified(False)
            tkinter.messagebox.showinfo(
                parent=self.get_widget(),
                message="Event data saved.",
                title="Save",
            )
        return

    def save_reports(self):
        """Show save data report file dialogue and return True if saved."""
        reports = os.path.join(
            self.get_context().get_season_folder(), "Reports"
        )
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
            except:
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
                return
        dt = datetime.datetime.today().isoformat()
        for control, filename in (
            (self.schedulectrl, "rep_schedule"),
            (self.resultsctrl, "rep_results"),
            (self.editedtext, "src_results"),
        ):
            report_file = os.path.join(reports, "_".join((dt, filename)))
            f = open(report_file, "w", encoding="utf8")
            try:
                f.write(control.get("1.0", tkinter.END))
            finally:
                f.close()
        tkinter.messagebox.showinfo(
            parent=self.get_widget(),
            message="".join(("Reports saved in folder\n\n", reports)),
            title="Save Reports",
        )

    def show_buttons_for_compare(self):
        """Show buttons for actions allowed comparing input data versions."""
        self.hide_panel_buttons()
        self.show_panel_buttons(
            (self._btn_toggle_generate, self._btn_closedata, self._btn_save)
        )

    def show_buttons_for_generate(self):
        """Show buttons for actions allowed displaying current input data."""
        self.hide_panel_buttons()
        self.show_panel_buttons(
            (
                self._btn_generate,
                self._btn_toggle_compare,
                self._btn_closedata,
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
                self._btn_closedata,
                self._btn_save,
                self._btn_report,
                self._btn_update,
            )
        )

    def show_edits_and_generated(self):
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
        if self.editedtext == None:
            self.editedtext = self._make_textedit_tab()
            self.editedtext.bind(
                "<ButtonPress-3>", self.try_event(self.editedtext_popup)
            )
            self._populate_editedtext()
        if self.schedulectrl == None:
            self.schedulectrl = textreadonly.make_text_readonly(
                master=self.generatedpane
            )
            self.schedulectrl.bind(
                "<ButtonPress-3>", self.try_event(self.schedule_popup)
            )
        if self.resultsctrl == None:
            self.resultsctrl = textreadonly.make_text_readonly(
                master=self.generatedpane
            )
            self.resultsctrl.bind(
                "<ButtonPress-3>", self.try_event(self.results_popup)
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
        # self.resultsctrl.insert(tkinter.END, '\n'.join(self.generated_results))

    def show_originals_and_edits(self):
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
        if self.editedtext == None:
            self.editedtext = self._make_textedit_tab()
            self._populate_editedtext()
        if self.originaltext == None:
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
        y, m, d = date.split("-")
        return " ".join((d, SourceEdit._months[m], y))

    def _hide_panes(self):
        """Forget the configuration of PanedWindows on data input page."""
        for p in (
            self.originalpane,
            self.editpane,
            self.generatedpane,
            self.toppane,
        ):
            if p is not None:
                for w in p.panes():
                    p.forget(w)

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
        w = texttab.make_text_tab(master=self.editpane)

        def key(event=None):
            if event.keysym == _DELETE:
                if _NOT_EDITABLE in w.tag_names(
                    w.index(tkinter.INSERT + " +1 char")
                ):
                    return "break"
                if _NOT_EDITABLE in w.tag_names(w.index(tkinter.INSERT)):
                    return "break"
            elif event.keysym == _BACKSPACE:
                if _NOT_EDITABLE in w.tag_names(
                    w.index(tkinter.INSERT + " -1 char")
                ):
                    return "break"
                if _NOT_EDITABLE in w.tag_names(w.index(tkinter.INSERT)):
                    return "break"
            elif event.keysym not in _NAVIGATION:
                tn = w.tag_names(w.index(tkinter.INSERT))
                if _NOT_EDITABLE in tn or _EDITABLE not in tn:
                    return "break"
                elif w.tag_ranges(tkinter.SEL):
                    if w.tag_nextrange(
                        _EDITABLE,
                        tkinter.SEL_FIRST,
                        tkinter.SEL_LAST + " +1 char",
                    ):
                        return "break"

        def clear(event=None):
            if not w.tag_ranges(tkinter.SEL):
                return key(event)
            e = w.tag_nextrange(_EDITABLE, tkinter.SEL_LAST)
            if e:
                e = w.tag_prevrange(_EDITABLE, w.index(e[0]))
            else:
                e = w.tag_prevrange(_EDITABLE, tkinter.END)
            while e:

                # Minimize future adjustment by 1 char
                se = w.index(e[0])
                ee = w.index(e[1] + "-1 char")

                if w.compare(ee, "<", tkinter.SEL_FIRST):
                    w.tag_remove(
                        tkinter.SEL, tkinter.SEL_FIRST, tkinter.SEL_LAST
                    )
                    break
                e = w.tag_prevrange(_EDITABLE, w.index(se))
                sc = w.compare(tkinter.SEL_FIRST, "<=", se + "+1 char")
                ec = w.compare(tkinter.SEL_LAST, ">=", ee)

                # Adjust ee by 1 char if necessary to compensate for the extra
                # newline which may have been added by _insert_entry() method.
                pee = w.index(ee + "-1 char")
                if w.compare(pee, "==", pee + "lineend"):
                    ee = pee

                if sc and ec:
                    w.delete(se + "+1 char", ee)
                elif sc:
                    w.delete(se + "+1 char", tkinter.SEL_LAST)
                    if not w.tag_ranges(tkinter.SEL):
                        break
                elif ec:
                    if w.compare(
                        tkinter.SEL_FIRST,
                        "!=",
                        tkinter.SEL_FIRST + "linestart",
                    ):
                        w.delete(tkinter.SEL_FIRST, ee)
                    elif w.compare(tkinter.SEL_FIRST, ">", se):
                        w.delete(tkinter.SEL_FIRST + "-1 char", ee)
                    else:
                        w.delete(tkinter.SEL_FIRST, ee)
                else:
                    w.delete(tkinter.SEL_FIRST, tkinter.SEL_LAST)
                    break
            return "break"

        # Copy the _EDITABLE characters between SEL_FIRST and SEL_LAST to the
        # clipboard.  The _NON_EDITABLE characters which may split the selection
        # into regions are present to preserve source identification of text,
        # and are not copied.  These are in the highlighted areas,
        def clip(event=None):
            tr = list(w.tag_ranges(_EDITABLE))
            w.clipboard_clear()
            while tr:
                s, e = tr.pop(0), tr.pop(0)
                if w.compare(e, "<", tkinter.SEL_FIRST):
                    continue
                if w.compare(s, ">", tkinter.SEL_LAST):
                    break
                if w.compare(s, "<", tkinter.SEL_FIRST):
                    s = tkinter.SEL_FIRST
                if w.compare(e, ">", tkinter.SEL_LAST):
                    e = tkinter.SEL_LAST
                w.clipboard_append(w.get(s, e), type="UTF8_STRING")
            return "break"

        w.event_add("<<Clear>>", "<BackSpace>")
        w.event_add("<<Clear>>", "<Delete>")
        w.bind("<<Clear>>", clear)
        w.bind("<KeyPress>", key)
        w.bind("<Control-x>", lambda e: "break")
        w.bind("<Control-c>", clip)

        # An explicit binding is needed on Microsoft Windows XP, and other
        # versions I assume, for the paste part of copy-and-paste to do the
        # paste in the presence of the <Control-c> binding to the clip function
        # for the copy part.
        # This paste binding is not needed if the copy binding is not done.
        # Neither paste binding nor paste function is needed on FreeBSD.
        # The situation with other BSDs, and any Linux, is not known.
        def paste(event=None):
            w.insert(tkinter.INSERT, w.clipboard_get(type="UTF8_STRING"))
            return "break"

        w.bind("<Control-v>", paste)

        return w

    def _insert_entry(self, widget, tagsuffix, entry, text):  # title, text):
        """ """
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
        """ """
        w = self.editedtext
        w.delete("1.0", tkinter.END)
        et = self.get_context().results_data.entry_text
        self._insert_entry(w, LOCAL_SOURCE, et, et.edited_text)
        for e, dt in enumerate(
            self.get_context().results_data.difference_text
        ):
            self._insert_entry(w, str(e), dt, dt.edited_text)

    def _populate_originaltext(self):
        """ """
        w = self.originaltext
        w.delete("1.0", tkinter.END)
        et = self.get_context().results_data.entry_text
        self._insert_entry(w, LOCAL_SOURCE, et, et.original_text)
        for e, dt in enumerate(
            self.get_context().results_data.difference_text
        ):
            self._insert_entry(w, str(e), dt, dt.original_text)

    def copy_data_from_widget(self):
        """Copy current widget data to season's event data attributes."""
        tw = self.editedtext
        results_data = self.get_context().results_data

        # Strip off the place-holder newline characters returned by get.
        # These were added by insert when the data was displayed.
        for dt in results_data.difference_text:
            st, et = tw.tag_ranges(dt.data_tag)
            dt.edited_text = tw.get(
                tw.index(st) + " +1 char", tw.index(et) + " -1 char"
            )
        dt = results_data.entry_text
        st, et = tw.tag_ranges(dt.data_tag)
        dt.edited_text = tw.get(
            tw.index(st) + " +1 char", tw.index(et) + " -1 char"
        )

    def results_popup(self, event=None):
        """ """
        wedit = self.editedtext
        wresults = self.resultsctrl
        tags = wresults.tag_names(
            wresults.index("".join(("@", str(event.x), ",", str(event.y))))
        )
        for t in tags:
            if t.startswith(_SELECT_FROM_GENERATED):
                tredit = wedit.tag_ranges(t)
                if tredit:
                    wedit.see(tredit[0])
                    return

    def schedule_popup(self, event=None):
        """ """
        wedit = self.editedtext
        wschedule = self.schedulectrl
        tags = wschedule.tag_names(
            wschedule.index("".join(("@", str(event.x), ",", str(event.y))))
        )
        for t in tags:
            if t.startswith(_SELECT_FROM_GENERATED):
                tredit = wedit.tag_ranges(t)
                if tredit:
                    wedit.see(tredit[0])
                    return

    def editedtext_popup(self, event=None):
        """ """
        worig = self.originaltext
        wedit = self.editedtext
        tags = wedit.tag_names(
            wedit.index("".join(("@", str(event.x), ",", str(event.y))))
        )
        for t in tags:
            if t[:2] in _SELECT_ORIG_FROM_EDIT:
                if worig:
                    trorig = worig.tag_ranges(t)
                    if worig:
                        worig.see(trorig[0])
                        return

    def generate_event_report(self):
        """Generate report on data input and return True if data is ok.

        Data can be ok and still be wrong.  ok means merely that the data
        input is consistent.  A number of formats are acceptable and named
        in sectiontypes below.

        """
        sectiontypes = {
            "allplayall": self._report_allplayall,  # individuals
            "league": lambda s, d: None,  # self._report_league, #team all play all
            "swiss": self._report_swiss,  # individuals
            "fixturelist": lambda s, d: None,  # matches from fixture list
            "individual": self._report_individual,  # games between players
        }
        self.copy_data_from_widget()
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
                    message="".join(
                        (
                            "An exception has occurred while extracting result ",
                            "information using one of the default regular ",
                            "expressions.\n\nThe latest version of Python, or at ",
                            "least a different version (change between 3.3.1 and ",
                            "3.3.2 for example) may process the text correctly.",
                            "\n\nAn exception will be raised on dismissing this ",
                            "dialogue.",
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
        self.report_fixtures(data)

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
                        "A badly-formed entry in a swiss table: for example 'x' ",
                        "or 'w12w'.\n",
                        "\nA well-formed entry in a swiss table refering to a ",
                        "row which does not exist: for example 'w12+' where ",
                        "'12' is not a player's PIN.\n",
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

        if not len(data.collation.reports.error) and not len(
            data._fixtures.error
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
            self.report_players(data)
            league_processed = False
            for section in data.collation.report_order:
                process = sectiontypes.get(
                    data.collation.section_type[section],
                    self._section_type_unknown,
                )
                if not isinstance(process, collections.Callable):
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
            t, m = self.generated_schedule.pop(0)
            if m is None:
                widget.insert(tkinter.END, t)
                if self.generated_schedule:
                    widget.insert(tkinter.END, "\n")
            else:
                datastart = widget.index(tkinter.INSERT)
                tag, text = m.get_schedule_tag_and_text(t)
                widget.insert(tkinter.END, text)
                if self.generated_schedule:
                    widget.insert(tkinter.END, "\n")
                widget.tag_add(tag, datastart, widget.index(tkinter.INSERT))

        self.resultsctrl.delete("1.0", tkinter.END)

        widget = self.resultsctrl
        while self.generated_results:
            t, m = self.generated_results.pop(0)
            if m is None:
                widget.insert(tkinter.END, t)
                if self.generated_results:
                    widget.insert(tkinter.END, "\n")
            else:
                datastart = widget.index(tkinter.INSERT)
                tag, text = m.get_report_tag_and_text(t)
                widget.insert(tkinter.END, text)
                if self.generated_results:
                    widget.insert(tkinter.END, "\n")
                widget.tag_add(tag, datastart, widget.index(tkinter.INSERT))

        return not len(data.collation.reports.error)

    def report_fixtures(self, data):
        """Append fixtures to event schedule report."""
        fixdata = data._fixtures
        if len(fixdata.error):
            return
        genfix = self.generated_schedule
        genfix.append(("", None))
        divisions = sorted(list(fixdata.es_summary.keys()))
        for d in divisions:
            genfix.append((d, None))
            teams = sorted(list(fixdata.es_summary[d]["teams"].keys()))
            for t in teams:
                td = fixdata.es_summary[d]["teams"][t]
                genfix.append(
                    (
                        "".join(
                            (
                                t,
                                "   ",
                                str(td["homematches"]),
                                " home, ",
                                str(td["awaymatches"]),
                                " away matches",
                            )
                        ),
                        None,
                    )
                )
            genfix.append(("", None))
        fixtures = []
        if len(fixdata.es_fixtures):
            for f in fixdata.es_fixtures:
                fixtures.append(
                    (
                        (
                            f.competition,
                            "  ",
                            f.hometeam,
                            " - ",
                            f.awayteam,
                        ),
                        len(
                            fixtures
                        ),  # to hide unorderable f.tagger from sort
                        f.tagger,
                    )
                )
            fixtures.sort()
            for f, n, tagger in fixtures:
                tagger.append_generated_schedule(genfix, "".join(f))
            genfix.append(("", None))

    def report_fixtures_played_status(self, data):
        """Append list of unreported fixtures to results report."""
        if len(data.collation.reports.error):
            return
        genres = self.generated_results
        fnp = data.collation.get_fixtures_not_played()
        if len(fnp) == 0:
            return
        dt = datetime.date.today().isoformat()
        genres.append(
            (
                "".join(("Fixtures not played or not reported at ", dt, "\n")),
                None,
            )
        )
        for m in fnp:
            if m.date > dt:
                dfnp = "          "
            else:
                dfnp = m.date
            m.tagger.append_generated_report(
                genres,
                " ".join((dfnp, m.competition, m.hometeam, "-", m.awayteam)),
            )
        genres.append(("", None))

    def report_matches(self, data):
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
                r, uftag, gradetag = game.get_print_result()
                if game in resdata.gamesxref:
                    uftag = displayresult.get(
                        resdata.gamesxref[game].result, uftag
                    )
                if len(uftag) or len(gradetag):
                    uftag = "    ".join(("", uftag, gradetag))
                if not r:
                    r = "     "
                hp = game.homeplayer.name
                if not hp:
                    hp = ""
                ap = game.awayplayer.name
                if not ap:
                    ap = ""
                game.tagger.append_generated_report(
                    genres,
                    " ".join(("   ", hp, r, ap, "       ", uftag)),
                )
            genres.append(("", None))

    # The versions of report_matches_by_source in SourceEdit, PDLEdit and SLEdit
    # are slightly different.
    # Seems best to take the PDLEdit version and fit the differences somehow.

    def report_matches_by_source(self, data):
        """Override, append list of fixtures by source to results report.

        Source may be a file name or some kind of heading within the file.  The
        report for each fixture may include a comment that game scores for the
        fixture are not consistent with total score.

        """
        # PDLEdit should have had some tests on source attribute according to
        # docstring for report_matches_by_source.

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
        for m, ufg, consistent in matches:
            if currtag != m.tagger.datatag:
                currtag = m.tagger.datatag
                genres.append(("", None))
            m.tagger.append_generated_report(
                genres,
                " ".join((m.hometeam, "-", m.awayteam)),
            )

            # Part of SLEdit hack to spot matches played before fixture date.
            # Need to test 'date report sent' for correct answer always.
            try:
                if len(today) == len(m.date):
                    if m.date > today:
                        m.tagger.append_generated_report(
                            genres,
                            "".join(("   match reported early at ", today)),
                        )
            except:
                pass

            if not consistent:
                genres.append(
                    ("   match score not consistent with game reports", None)
                )
            for g in m.games:
                if g.result is None:
                    hp = g.homeplayer
                    if hp:
                        hp = hp.name
                    else:
                        hp = ""
                    ap = g.awayplayer
                    if ap:
                        ap = ap.name
                    else:
                        ap = ""
                    g.tagger.append_generated_report(
                        genres,
                        " ".join(("   unfinished  ", hp, "-", ap)),
                    )
        if len(playedongames):
            genres.append(("\nPlayed-on Games in entry order\n", None))
            currtag = playedongames[0].tagger.datatag
            for g in playedongames:
                if g.result is None:
                    continue
                if currtag != g.tagger.datatag:
                    currtag = g.tagger.datatag
                    genres.append(("", None))
                g.tagger.append_generated_report(
                    genres,
                    " ".join(("   ", g.hometeam, "-", g.awayteam)),
                )
                hp = g.homeplayer
                if hp:
                    hp = hp.name
                else:
                    hp = ""
                ap = g.awayplayer
                if ap:
                    ap = ap.name
                else:
                    ap = ""
                g.tagger.append_generated_report(
                    genres,
                    "".join(
                        (
                            "        ",
                            " ".join(
                                (
                                    hp,
                                    displayresult.get(g.result, "unknown"),
                                    ap,
                                )
                            ),
                        )
                    ),
                )
        genres.append(("", None))

    def report_non_fixtures_played(self, data):
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

    def report_players(self, data, separator=None):
        """Append list of players sorted by affiliation to schedule report."""
        if len(data.collation.reports.error):
            return
        schedule = data.collation.schedule
        genfix = self.generated_schedule
        if len(data.collation.players):
            genfix.append(("", None))
            genfix.append(
                (
                    "".join(
                        (
                            "Player identities (with club or place association ",
                            "and reported codes)",
                        )
                    ),
                    None,
                )
            )
            genfix.append(("", None))
        drp = data.collation.players
        for n, p in [
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
            section = drp[p].section
            if section in schedule.es_players:
                if n in schedule.es_players[section]:
                    genfix.append(
                        (
                            "\t".join(
                                (
                                    drp[p].get_short_identity(),
                                    "".join(
                                        (
                                            "(",
                                            schedule.es_players[section][
                                                n
                                            ].affiliation,
                                            ")",
                                        )
                                    ),
                                    drp[p].get_reported_codes(),
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
                            self.get_player_brief(drp[p]),
                            drp[p].get_reported_codes(),
                        )
                    ).strip(),
                    None,
                )
            )

    def get_player_brief(self, player):
        """Return player identity for schedule report."""
        return player.get_short_identity()

    def report_player_matches(self, data, separator=None):
        """Append list of fixtures for each player to results report."""
        if len(data.collation.reports.error):
            return
        teamplayers = data.collation.get_reports_by_player(separator)
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

    def report_players_by_club(self, data, separator=None):
        """Append list of players sorted by club to results report."""
        if len(data.collation.reports.error):
            return
        gca = self.get_appsys().show_master_list_grading_codes
        db = self.get_appsys().get_results_database()
        clubs = data.collation.get_players_by_club(separator)
        eventname = set()
        for cp in clubs.values():
            for pn in cp:
                eventname.add(pn[1:-1])
        event, events = get_events_matching_event_name(
            db, eventname, data.collation.matches
        )
        genres = self.generated_results

        # No database open or not using ecf module.
        if not event or not gca:
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
            for cp in sorted(clubs.keys()):
                clubplayers = data.collation.clubplayers[cp]
                genres.append((cp + "\n", None))
                for pn in clubs[cp]:
                    genres.append(
                        (
                            "\t\t\t\t".join(
                                (pn[0], " ".join(clubplayers[pn]))
                            ),
                            None,
                        )
                    )
                genres.append(("", None))
            return

        # Database open.
        aliases = {}  # (name, section):(start, end, eventkey, aliaskey, merge)
        known = {}
        nogcode = {}

        def populate_aliases(e, a):
            evkey = e[1].key.recno
            sd = e[1].value.startdate
            ed = e[1].value.enddate
            for k, v in get_aliases_for_event(db, e[1]).items():
                ns = v.value.name, get_name(db, v.value.section).value.name
                nsd = sd, ed, evkey, v.key.recno, v.value.merge
                a.setdefault(ns, []).append(nsd)
                if v.value.merge is not None:
                    known.setdefault(ns[1], set()).add(ns[0])

        populate_aliases(event, aliases)
        for e in events:
            populate_aliases(e, aliases)
        startdate = event[1].value.startdate
        enddate = event[1].value.enddate
        genres.append(("Players by club\n", None))
        genres.append(
            (
                "".join(
                    (
                        "Names prefixed with same number or grading code ",
                        "are assumed to be same person.",
                    )
                ),
                None,
            )
        )
        genres.append(
            (
                "".join(
                    (
                        "If it is a number please give the player's grading ",
                        "code or confirm the player\ndoes not have one.",
                    )
                ),
                None,
            )
        )
        genres.append(
            (
                "".join(
                    (
                        "If neither is given please give the player's grading ",
                        "code or confirm the player\ndoes not have one.",
                    )
                ),
                None,
            )
        )
        genres.append(
            (
                "".join(
                    (
                        "The '!', '!!', '?', and '*', prefixes are asking for ",
                        "confirmation or correction\nof the grading code. ",
                        "Their absence means only corrections are needed.",
                    )
                ),
                None,
            )
        )
        genres.append(
            (
                "".join(
                    (
                        "'!' means name used in previous season and '!!' ",
                        "means at least a season gap\nsince previous use.",
                    )
                ),
                None,
            )
        )
        genres.append(
            (
                "".join(
                    (
                        "'?' means name referred to different person in at ",
                        "least one earlier season.",
                    )
                ),
                None,
            )
        )
        genres.append(
            (
                "".join(
                    (
                        "'*' means it was not possible to decide which of '!', ",
                        "'!!' is appropriate\n(because of a date error).\n",
                    )
                ),
                None,
            )
        )
        genres.append(
            (
                "".join(
                    (
                        "A grading code in brackets immediately following the ",
                        "name is the code shown\non the ECF Grading Database ",
                        "rather than the one before the name.\n",
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
                        "the player name after a\nnoticable gap.\n",
                    )
                ),
                None,
            )
        )
        for cp in sorted(clubs.keys()):
            clubplayers = data.collation.clubplayers[cp]
            genres.append((cp + "\n", None))
            for pn in clubs[cp]:
                grading_code = ""
                merged_grading_code = ""
                ns = pn[0], pn[4]
                nsdate = pn[2], pn[3]
                tag = ""
                peopletag = ""
                recenttag = ""
                if ns in aliases:
                    refs = aliases[ns]
                    if nsdate == refs[0][:2]:
                        merge = refs[0][4]
                        if merge is False:
                            person = refs[0][3]
                        elif merge is None:
                            person = refs[0][3]
                        else:
                            person = refs[0][4]
                    else:
                        merge = None
                        person = None
                    if len(refs) != 1:
                        try:
                            y1 = int(pn[2].split("-")[0])
                            y2 = int(refs[1][0].split("-")[0])
                            if abs(y1 - y2) == 1:
                                recenttag = "!" if merge is None else ""
                            else:
                                recenttag = "!!" if merge is None else ""
                        except:
                            recenttag = "*"
                    players = []
                    for r in refs:
                        if r[4] is False:
                            players.append(r[3])
                        elif r[4] is not None:
                            players.append(r[4])
                    if len(set(players)) > 1:
                        peopletag = "?"
                    if len(players):
                        grading_code = get_grading_code_for_person(
                            db, get_alias(db, players[0])
                        )
                        playerecf = get_ecf_player_for_grading_code(
                            db, grading_code
                        )
                        if playerecf:
                            if playerecf.value.ECFmerge:
                                merged_grading_code = grading_code
                                grading_code = playerecf.value.ECFmerge
                    else:
                        grading_code = ""
                    if grading_code == "":
                        if person not in nogcode:
                            nogcode[person] = len(nogcode) + 1
                        if merge is not None:
                            grading_code = nogcode[person]
                tag = "{:>3}".format(peopletag + recenttag)
                grading_code = "{:>7}".format(grading_code)
                if merged_grading_code:
                    pnrc = "\t\t\t\t\t".join(
                        (
                            " ".join(
                                (
                                    pn[0],
                                    merged_grading_code.join(("(", ")")),
                                )
                            ),
                            " ".join(clubplayers[pn]),
                        )
                    )
                    genres.append(
                        (
                            " ".join(
                                (
                                    tag,
                                    grading_code,
                                    " ",
                                    pnrc,
                                )
                            ),
                            None,
                        )
                    )
                else:
                    pnrc = "\t\t\t\t\t".join(
                        (pn[0], " ".join(clubplayers[pn]))
                    )
                    genres.append(
                        (" ".join((tag, grading_code, " ", pnrc)), None)
                    )
            genres.append(("", None))

    def report_unfinished_games(self, data):
        """Append list of unfinished reported games to results report."""
        if len(data.collation.reports.error):
            return
        genres = self.generated_results
        ug = data.collation.get_unfinished_games()
        if len(ug) == 0:
            return
        genres.append(("Unfinished games\n", None))
        for match, game in ug:
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

    def update_event_results(self):
        """Show dialogue to update database and return true if updated."""
        if self.is_report_modified():
            tkinter.messagebox.showinfo(
                parent=self.get_widget(),
                message="".join(
                    (
                        "Event data has been modified.\n\n",
                        "Save the data first.",
                    )
                ),
                title="Update",
            )
            return False
        db = self.get_appsys().get_results_database()
        if not db:
            dlg = tkinter.messagebox.showinfo(
                parent=self.get_widget(),
                message="".join(
                    (
                        "Cannot update. No results database open.\n\n",
                        "To proceed open a results database",
                    )
                ),
                title="Update",
            )
            return False
        if not tkinter.messagebox.askyesno(
            parent=self.get_widget(),
            message="".join(("Do you want to update results?")),
            title="Update",
        ):
            return False

        # Unfinished games, now completed, added into game results.
        # Used to be done by update_event_results() in subclasses PDLEdit and
        # SLEdit which then delegated rest of work to this class.
        xr = self.get_context().results_data.get_collated_unfinished_games()
        mr = self.get_context().results_data.get_collated_games()
        for r in mr:
            for g in mr[r].games:
                if g in xr:
                    if xr[g].result is not None:
                        g.result = xr[g].result

        collatedb = collationdb.CollationDB(
            self.get_context().results_data.get_collated_games(), db
        )
        db.start_transaction()
        u = collatedb.update_results()
        if isinstance(u, tuple):
            db.backout()
            dialogue.Report(
                parent=self,
                title="Player records blocking update",
                action_titles={"Save": "Save Blocking Update Details"},
                wrap=tkinter.WORD,
                tabstyle="tabular",
            ).append("\n\n".join(u))
        else:
            db.commit()
            dlg = tkinter.messagebox.showinfo(
                parent=self.get_widget(),
                message="".join(("Results database updated")),
                title="Update",
            )
        return True

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
        report = data.collation.games[section]
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

            r = None
            for g in games:
                if r != g.round:
                    r = g.round
                    genres.append(("", None))
                    if r in schedule.es_round_dates[section]:
                        round_date = schedule.es_round_dates[section][r]
                    else:
                        round_date = schedule.es_startdate
                    g.tagger.append_generated_report(
                        genres,
                        " ".join(
                            (
                                section,
                                "Round",
                                str(r),
                                "played on",
                                self._date_text(round_date),
                            )
                        ),
                    )
                    genres.append(("", None))
                if round_date == g.date:
                    g.tagger.append_generated_report(
                        genres,
                        " ".join(
                            (
                                g.homeplayer.name,
                                g.get_print_result()[0],
                                g.awayplayer.name,
                            )
                        ),
                    )
                else:
                    g.tagger.append_generated_report(
                        genres,
                        " ".join(
                            (
                                self._date_text(g.date),
                                g.homeplayer.name,
                                g.get_print_result()[0],
                                g.awayplayer.name,
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
            for g in games:
                if event_date == g.date:
                    g.tagger.append_generated_report(
                        genres,
                        " ".join(
                            (
                                g.homeplayer.name,
                                g.get_print_result()[0],
                                g.awayplayer.name,
                            )
                        ),
                    )
                else:
                    g.tagger.append_generated_report(
                        genres,
                        " ".join(
                            (
                                self._date_text(g.date),
                                g.homeplayer.name,
                                g.get_print_result()[0],
                                g.awayplayer.name,
                            )
                        ),
                    )

    def _report_league(self, section, data):
        """Generate results report for matches in a league."""
        self.report_matches_by_source(data)
        self.report_fixtures_played_status(data)
        self.report_non_fixtures_played(data)
        self.report_unfinished_games(data)
        self.report_matches(data)
        self.report_players_by_club(data)
        self.report_player_matches(data)

    def _report_not_implemented(self, section, data):
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
                for r in rounds:
                    genfix.append(
                        (
                            "\t".join(
                                (
                                    str(r),
                                    self._date_text(
                                        schedule.es_round_dates[section][r]
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
                                    "The following rounds have no specified date.",
                                    "These are deemed played on the event",
                                    "start date.",
                                )
                            ),
                            None,
                        )
                    )
                    for r in range(1, round_count + 1):
                        if r not in rounds:
                            genfix.append((" ".join(("Round", str(r))), None))
            else:
                genfix.append(
                    (
                        " ".join(
                            (
                                "All rounds are deemed played on the event start date",
                                "because no round dates are specified.",
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
            r = None
            for g in games:
                if r != g.round:
                    r = g.round
                    genres.append(("", None))
                    intr = int(r) if r.isdigit() else r
                    if intr in schedule.es_round_dates[section]:
                        round_date = schedule.es_round_dates[section][intr]
                    else:
                        round_date = schedule.es_startdate
                    g.tagger.append_generated_report(
                        genres,
                        " ".join(
                            (
                                section,
                                "Round",
                                str(r),
                                "played on",
                                self._date_text(round_date),
                            )
                        ),
                    )
                    genres.append(("", None))
                if round_date == g.date:
                    g.tagger.append_generated_report(
                        genres,
                        " ".join(
                            (
                                g.homeplayer.name,
                                g.get_print_result()[0],
                                g.awayplayer.name,
                            )
                        ),
                    )
                else:
                    g.tagger.append_generated_report(
                        genres,
                        " ".join(
                            (
                                self._date_text(g.date),
                                g.homeplayer.name,
                                g.get_print_result()[0],
                                g.awayplayer.name,
                            )
                        ),
                    )

    def _section_type_unknown(self, section, data):
        data.collation.error.append(("", None))
        data.collation.error.append(
            (" ".join((section, "type not known")), None)
        )
        data.collation.error.append(("", None))
