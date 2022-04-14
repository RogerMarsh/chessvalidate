# season.py
# Copyright 2008 Roger Marsh
# Licence: See LICENCE (BSD licence)

"""Collect an event's results and schedules like fixtures or player lists.

Manage the result report and event schedule input documents and the
collation of the results with the schedule.

The data is entered directly to the program, from paper documents probably,
but emails or attachments that cannot be processed by the program are the
same here.  An alternative is to have a recognised format that is used to
report results and have a subclass of ReportedSeason extract the data.

"""

import difflib
import os
import tkinter.messagebox
import re

from emailextract.core.emailextractor import (
    COLLECTED,
    EXTRACTED,
    TEXT_CONTENT_TYPE,
    PDF_CONTENT_TYPE,
    CSV_CONTENT_TYPE,
)

from .schedule import Schedule
from .report import Report
from .collation import Collation
from .emailextractor import (
    EmailExtractor,
    TEXTENTRY,
    RESULTS_PREFIX,
    COMPETITION,
    TEAM_NAME,
    AUTHORIZATION_DELAY,
    DEFAULT_IF_DELAY_NOT_VALID,
)
from .eventparser import EventParser
from . import constants

# Content types always put in an event configuration file when created.
_CSV_CONTENT = "text/comma-separated-values"
_TEXT_CONTENT = "text/plain"
_PDF_CONTENT = "application/pdf"
# Lookup for calculation of match score
_GAMESCORE = {"0-1": (0, 1), "draw": (0.5, 0.5), "1-0": (1, 0)}

# The tags are defined here because they are used to cross-reference text
# displayed in several widgets from a single _DifferenceText instance.

# Tag prefixes; usage is '<prefix><separator><suffix>'
HEADER_TAG = "H"
TRAILER_TAG = "T"
DATA_TAG = "D"

# Tag suffix for non-email sourced data, usually typed in.
# Most suffixes are generated as str(enumeration integer)
LOCAL_SOURCE = "L"

# Tag separator
SEPARATOR = "x"


class SeasonError(Exception):
    """Exceptions raised in season module."""


class Season:
    """Default management of source and derived data files for an event.

    Details of an event are collected in a directory <event>nn which is created
    with a configuration file (conf), two empty difference files for the event
    schedule and the event results(schedule<nn>.txt and reports<nn>.txt by
    default), and some directories each containing empty reports and schedule
    directories for source documents from which the difference files are
    populated.

    The initial schedule and results difference files are empty and the user
    creates these by entering all data.  In effect there is  no audit of the
    data entered.

    Three source document directories are created. mailbox for files which are
    unix-style mailboxes, spreadsheet for gnumeric compatible spreadsheets (xls
    is good), and plaintext for text documents (doc and ods and other word
    processor formats are not good, and pdf is not good either).

    Only one of these can be used for each kind of source document.  But using
    mailbox/reports and plaintext/schedule, for example, is allowed.  It is
    anticipated that the most common combination will be mailbox/reports on its
    own with the addition of mailbox/schedule in some cases (league fixture
    lists in particular).

    The mailbox option provides an audit trail from received email through to
    edits of extracted data stored on the difference files.  This includes the
    cases where data extracted from a <reports> source document is moved to a
    <schedule> file.

    Each file in a mailbox subdirectory must be identical to all smaller files
    in the same directory up to the length of the smaller file for the source
    data to be accepted.  The largest file in the directory must be identical
    to the original data on the difference file up to the length of the original
    data.  In other words a dump of the mailbox into the source directory must
    include all emails that are in earlier dumps (and in the same order).

    Text is extracted from all text/plain and application/pdf parts into the
    reports file, and extrcted from csv dumps of the 'ForGrader' sheet in all
    application/vnd.ms-excel parts with the first column put in the schedule
    file and the second column put in the reports file.

    """

    def __init__(self, folder):
        """Create Season instance for event results in folder.

        folder - contains files of event data

        """
        self.folder = folder
        self.fixtures = None
        self.fixturesfile = None
        self.results = None
        self.resultsfile = None
        self._fixtures = None
        self._collation = None
        self._event_parser = None
        self._difference_text = None
        self._entry_text = None
        self._event_extraction_rules = None

    def get_results_from_file(self):
        """Override, create Collation object from text files.

        The Schedule and Report objects deal with various ways of laying out
        the data in text files.  The Collation object holds the data in
        a format convenient for comparison with existing contents of results
        database and subsequent updates.

        """
        if self._collation is None:
            self.get_schedule_from_file()
            results = Report()
            results.build_results(self._event_data.get_results_text())
            self._collation = Collation(results, self._fixtures)

    def open_documents(self, parent):
        """Override, extract data from text files and return True if ok."""
        if self._entry_text is not None:
            tkinter.messagebox.showinfo(
                parent=parent,
                message="An event folder is already open",
                title="Open event results data",
            )
            return False
        config = os.path.join(self.folder, constants.EVENT_CONF)
        if not os.path.exists(config):
            create_event_configuration_file(config)

            tkinter.messagebox.showinfo(
                parent=parent,
                message=" ".join(
                    (
                        "Configuration file\n\n",
                        config,
                        "\n\ncreated.\n\n",
                        "The mailbox and extract folders will be created when ",
                        "this message is dismissed.",
                    )
                ),
                title="Open event results data",
            )

        emc = EmailExtractor(
            self.folder,
            configuration=open(config, "r", encoding="utf8").read(),
            parent=parent,
        )
        if not emc.parse():
            tkinter.messagebox.showinfo(
                parent=parent,
                title="Open event results data",
                message="Email selection rules are invalid.",
            )
            return False

        # Create document folders and files if all specified and none exist.
        folders = {COLLECTED, EXTRACTED, TEXTENTRY}
        if not folders.issubset(emc.criteria):
            tkinter.messagebox.showinfo(
                parent=parent,
                title="Open event results data",
                message="".join(
                    (
                        "Mailbox or extracts folder or text entry file not ",
                        "named in configuration file.",
                    )
                ),
            )
            return False
        folders.remove(TEXTENTRY)
        if not os.path.exists(os.path.join(self.folder, EXTRACTED)):
            if os.path.isdir(os.path.join(self.folder, COLLECTED)):
                try:
                    os.mkdir(os.path.join(self.folder, EXTRACTED))
                except:
                    pass
        fcount = len(
            [
                f
                for f in folders
                if os.path.exists(os.path.join(self.folder, emc.criteria[f]))
            ]
        )
        if fcount != 0 and fcount != len(folders):
            tkinter.messagebox.showinfo(
                parent=parent,
                title="Open event results data",
                message="Only one of Mailbox and extracts folders exist.",
            )
            return False
        if not os.path.isfile(os.path.join(self.folder, TEXTENTRY)):
            if os.path.exists(os.path.join(self.folder, TEXTENTRY)):
                tkinter.messagebox.showinfo(
                    parent=parent,
                    title="Open event results data",
                    message="Textentry is not a file.",
                )
                return False
            tkinter.messagebox.showinfo(
                parent=parent,
                title="Open event results data",
                message="".join(
                    (
                        "Textentry file does not exist.\n\nAn empty one ",
                        "will be created.",
                    )
                ),
            )
            empty_text = ["\n"]
            ofile = open(
                os.path.join(self.folder, emc.criteria[TEXTENTRY]),
                mode="x",
                encoding="utf8",
            )
            try:
                ofile.writelines(difflib.ndiff(empty_text, empty_text))
            finally:
                ofile.close()
        fcount = len(
            [
                f
                for f in folders
                if os.path.isdir(os.path.join(self.folder, emc.criteria[f]))
            ]
        )
        if fcount != 0 and fcount != len(folders):
            tkinter.messagebox.showinfo(
                parent=parent,
                title="Open event results data",
                message="Either or both mailbox and extracts is not a folder.",
            )
            return False
        if fcount == 0:
            for fname in folders:
                os.mkdir(os.path.join(self.folder, emc.criteria[fname]))
            tkinter.messagebox.showinfo(
                parent=parent,
                title="Open event results data",
                message="Mailbox and extracts folders created.",
            )

        # Extract the event text
        # This will probably and eventually be put in season.Season which still
        # works the old way to support the takenonseason module.
        fpath = os.path.join(self.folder, emc.criteria[TEXTENTRY])
        try:
            ofile = open(fpath, mode="r", encoding="utf8")
        except FileNotFoundError as exc:
            tkinter.messagebox.showinfo(
                parent=parent,
                title="Open event results data",
                message="".join(
                    (
                        "Open event file or directory\n\n",
                        os.path.basename(exc.filename),
                        "\n\nfailed.\n\nAny files in the directory which do ",
                        "exist have been ignored.",
                    )
                ),
            )
            return None
        try:
            entry_text = _DifferenceText(fpath, ofile.readlines())
        finally:
            ofile.close()

        email_text = []
        email_headers = {}
        for sem in emc.selected_emails:
            email_text.append((sem.filename, "\n".join(sem.extracted_text)))
            email_headers[os.path.splitext(sem.filename)[0]] = _Headers(
                dates=sem.dates,
                authorization_delay=emc.criteria.get(AUTHORIZATION_DELAY),
            )
        diff_text = []
        extracted_text = []
        folder = os.path.join(self.folder, emc.criteria[EXTRACTED])

        # Process works without sort at this point, but the file names are
        # in date order and that is a good order for display.
        for fname in sorted(os.listdir(folder)):
            fpath = os.path.join(folder, fname)
            try:
                ofile = open(fpath, mode="r", encoding="utf8")
            except FileNotFoundError as exc:
                tkinter.messagebox.showinfo(
                    parent=parent,
                    title="Open event results data",
                    message="".join(
                        (
                            "Open event file or directory\n\n",
                            os.path.basename(exc.filename),
                            "\n\nfailed.\n\nAny files in the directory which do ",
                            "exist have been ignored.",
                        )
                    ),
                )
                return None
            try:
                diff_text.append(
                    _DifferenceText(
                        fpath, ofile.readlines(), headers=email_headers
                    )
                )
                extracted_text.append((fname, diff_text[-1].original_text))
            finally:
                ofile.close()

        # Extract text from all emails to make initial difference text if none
        # already exist.
        if not extracted_text:
            for efile, etext in email_text:
                epath = os.path.splitext(efile)[0]
                etext = etext.splitlines(True)
                diff_text.append(
                    _DifferenceText(
                        os.path.join(folder, epath),
                        list(difflib.ndiff(etext, etext)),
                        headers=email_headers,
                    )
                )
                extracted_text.append((epath, diff_text[-1].original_text))

        # The original version from the difference files must be consistent
        # with the version extracted from the available email files.
        emt = {emi[0] for emi in email_text}
        ext = {exi[0] for exi in extracted_text}
        if len(emt) != len(email_text) or len(ext) != len(extracted_text):
            tkinter.messagebox.showinfo(
                parent=parent,
                title="Open event results data",
                message="".join(
                    (
                        "Duplicate file names in email or extracted ",
                        "text folders.",
                    )
                ),
            )
            return False
        if len(ext) > len(emt):
            tkinter.messagebox.showinfo(
                parent=parent,
                title="Open event results data",
                message="".join(
                    (
                        "Some files in extracted folder are not present in ",
                        "email folder.",
                    )
                ),
            )
            return False
        if len(ext) < len(emt):
            if not ext.issubset(emt):
                tkinter.messagebox.showinfo(
                    parent=parent,
                    title="Open event results data",
                    message="".join(
                        (
                            "Some files in extracted folder are not present in ",
                            "email folder.",
                        )
                    ),
                )
                return False
            if sorted(ext) + sorted(emt.difference(ext)) == sorted(emt):
                if (
                    tkinter.messagebox.askquestion(
                        parent=parent,
                        title="Open event results data",
                        message="".join(
                            (
                                "Emails dated after latest in extract are available.",
                                "\n\nDo you wish to continue without including the ",
                                "new emails?",
                            )
                        ),
                    )
                    != tkinter.messagebox.YES
                ):
                    return False
            elif (
                tkinter.messagebox.askquestion(
                    parent=parent,
                    title="Open event results data",
                    message="".join(
                        (
                            "Emails not in the extract are available.  Some, maybe ",
                            "all, are dated earlier than latest in extract.",
                            "\n\nDo you wish to continue without including the ",
                            "new emails?",
                        )
                    ),
                )
                != tkinter.messagebox.YES
            ):
                return False

            # Prune email_text for detailed comparison with extracted_text
            email_text = [t for t in email_text if t[0] in ext]

        # Extracted text must match email text allowing for universal newlines.
        extracted_matches_emails = False
        for ext, emt in zip(sorted(extracted_text), email_text):
            if ext[-1] == emt[-1]:
                continue
            ext_lines = ext[-1].splitlines()
            emt_lines = emt[-1].splitlines()
            if ext_lines != emt_lines:
                ext_file = ext[0]
                emt_file = emt[0]
                format_fault = True
                format_fault_count = 0
                for x_line, mail_line in zip(ext_lines, emt_lines):
                    if "".join(x_line.split()) != "".join(mail_line.split()):
                        format_fault = False
                    elif x_line != mail_line:
                        format_fault_count += 1
                    fx_line, fm_line = x_line, mail_line
                preamble = "".join(
                    (
                        "The text extracted previously to file:\n\n",
                        ext_file,
                        "\n\nin the extract folder is not consisent with ",
                        "that just taken from file:\n\n",
                        emt_file,
                        "\n\nin the email folder.\n\nDeleting the extracted ",
                        "file and repeating the extract process will clear the ",
                        "problem assuming the email file contains the correct ",
                        "data.  Any edits done to the extracted file will be ",
                        "lost.",
                    )
                )
                if format_fault:
                    detail = "".join(
                        (
                            "\n\n\nThe files are identical if whitespace is ",
                            "removed from each line.  The last different ",
                            "line previously extracted is:\n\n",
                            repr(fx_line),
                            "\n\nand the same line just taken from the ",
                            "email is:\n\n",
                            repr(fm_line),
                            "\n\n",
                            str(format_fault_count),
                            " lines are affected.\n",
                            str(max(len(ext_lines), len(emt_file))),
                            " lines in file.",
                        )
                    )
                else:
                    detail = ""
                tkinter.messagebox.showinfo(
                    parent=parent,
                    title="Open event results data",
                    message="".join((preamble, detail)),
                )
                break
        else:
            extracted_matches_emails = True
        if not extracted_matches_emails:
            return False

        # The original text extracted from email is unlikely to be used again,
        # but the version of edited text currently on file will be displayed
        # first of all and used to detect substantive edits.
        entry_text.clear_original_text()
        entry_text.edited_text_on_file
        for dte in diff_text:
            dte.clear_original_text()
            dte.edited_text_on_file

        # Make the list of difference files and their source data available via
        # the difference_text property'
        self._difference_text = diff_text
        self._entry_text = entry_text
        self._event_extraction_rules = emc.criteria.get(RESULTS_PREFIX, ())
        self._event_competitions = emc.criteria.get(COMPETITION, set())
        self._event_team_name_lookup = emc.criteria.get(TEAM_NAME, dict())
        return True

    def extract_event(self):
        """Extend, specify Schedule as class used to process newfixtures."""
        difflistcopy = [dt for dt in self._difference_text]
        difflistcopy.insert(0, self._entry_text)
        # The old code allowed for different classes for varying formats.
        # The idea here is that 'one class fits all' and any differences can
        # be dealt with in the configuration file. There are only a few ways of
        # structuring fixture lists and match results, but syntax will vary.
        # It seems a lot of messing about can be avoided by just doing:
        self._event_parser = EventParser(difflistcopy)
        self._event_data = self._event_parser.build_event(
            self._event_extraction_rules,
            self._event_competitions,
            self._event_team_name_lookup,
        )

    @property
    def difference_text(self):
        """Return list of _DifferenceText instances for text from emails."""
        return self._difference_text

    @property
    def entry_text(self):
        """Return the _DifferenceText instance for typed-in text."""
        return self._entry_text

    def get_schedule_from_file(self):
        """Extract schedule from text file using getfixtures.build_schedule.

        getfixtures - the Schedule class or a subclass

        """
        if self._fixtures is None:
            self._fixtures = Schedule()
            self._fixtures.build_schedule(self._event_data.get_schedule_text())

    def extract_schedule(self):
        """Override, specify Schedule as class used to process newfixtures."""
        self._fixtures = None
        self.get_schedule_from_file()

    def extract_results(self):
        """Override, specify Schedule as class used to process newfixtures."""
        self._collation = None
        self.get_results_from_file()

    @property
    def collation(self):
        """Return the Collation instance."""
        return self._collation

    # Copied from Season

    def get_collated_games(self):
        """Return the Collation.games object."""
        return self._collation.games

    def close(self):
        """Discard references to the event data."""
        self.fixtures = None
        self.fixturesfile = None
        self.results = None
        self.resultsfile = None
        self._fixtures = None
        self._collation = None

    # Copied from PDLSeason and SLSeason

    def get_collated_unfinished_games(self):
        """Return dictionary of unfinished games."""
        return self._collation.gamesxref


class _DifferenceText:
    """Repreresent stages of processing text containing event information."""

    def __init__(self, filepath, diff_lines, headers=None, junk_rules=None):
        """Initialise difference texts for event data."""
        self._folder = os.path.dirname(filepath)
        self._filename = os.path.basename(filepath)
        self._diff_lines = diff_lines
        self._junk_rules = junk_rules
        self._original_text = None
        self._edited_text = None
        self._edited_text_on_file = None
        self._data_tag = None
        self._header_tag = None
        self._trailer_tag = None
        if headers is None:
            self._headers = None
        else:
            self._headers = headers[self._filename]

    def __eq__(self, other):
        """Return True if self.filename == other.filename."""
        return self._filename == other._filename

    def __lt__(self, other):
        """Return True if self.filename < other.filename."""
        return self._filename < other._filename

    @property
    def filename_header(self):
        """Return header text for type-in text area."""
        return "\n".join((self._filename, "Results added by typing."))

    @property
    def original_text(self):
        """Return original version of text built from difference files."""
        if self._original_text is None:
            self._original_text = "".join(difflib.restore(self._diff_lines, 1))
        return self._original_text

    @property
    def data_tag(self):
        """Return data tag set for most recent suffix."""
        return self._data_tag

    @property
    def header_tag(self):
        """Return header tag set for most recent suffix."""
        return self._header_tag

    @property
    def trailer_tag(self):
        """Return trailer tag set for most recent suffix."""
        return self._trailer_tag

    @property
    def headers(self):
        """Return headers for this _DifferenceText instance."""
        return self._headers

    def set_tags(self, suffix):
        """Set header, data, and trailer, tags for suffix."""
        if (
            self._data_tag is None
            and self._header_tag is None
            and self._trailer_tag is None
        ):
            self._data_tag = SEPARATOR.join((DATA_TAG, suffix))
            self._header_tag = SEPARATOR.join((HEADER_TAG, suffix))
            self._trailer_tag = SEPARATOR.join((TRAILER_TAG, suffix))

    @property
    def edited_text(self):
        """Return edited version of text in difference files."""
        if self._edited_text is None:
            self._edited_text = "".join(difflib.restore(self._diff_lines, 2))
        return self._edited_text

    @edited_text.setter
    def edited_text(self, value):
        """Set edited version of text to value."""
        if isinstance(value, str):
            self._edited_text = value
        else:
            tkinter.messagebox.showinfo(
                title="Save event results data",
                message="".join(
                    (
                        "Edited results data must be a string.\n\n",
                        "Data on file for this section will not be changed ",
                        "if save action is confirmed.",
                    )
                ),
            )

    @property
    def edited_text_on_file(self):
        """Return edited version of text on file in difference files."""
        if self._edited_text_on_file is None:
            self._edited_text_on_file = self._edited_text
        return self._edited_text_on_file

    @property
    def sender_and_date(self):
        """Return sender and date derived from filename."""
        try:
            if (
                self._filename[:14].isdigit()
                and self._filename[-4:].isdigit()
                and self._filename[-5] in "+-"
            ):
                if len(self._filename.split("@")) == 2:
                    return "\n".join(
                        (
                            self._filename[14:-5],
                            " ".join(
                                (
                                    self._filename[:8],
                                    self._filename[8:14],
                                    self._filename[-5:],
                                )
                            ),
                        )
                    )
        except:
            pass
        return "Unknown sender and date"

    def clear_original_text(self):
        """Clear out origial text."""
        self._original_text = None

    def save_edited_text_as_new(self):
        """Save edited text in file self._filename with "new" suffix."""
        newdiff = list(
            difflib.ndiff(
                self.original_text.splitlines(True),
                self._edited_text.splitlines(True),
            )
        )
        with open(
            os.path.join(self._folder, "".join((self._filename, "new"))),
            mode="w",
            encoding="utf8",
        ) as newfile:
            newfile.writelines(newdiff)
        self._edited_text_on_file = self._edited_text

    def rename_new_edited_text(self):
        """Rename self._filename removing "new"."""
        try:
            os.replace(
                os.path.join(self._folder, "".join((self._filename, "new"))),
                os.path.join(self._folder, self._filename),
            )
        except:
            tkinter.messagebox.showinfo(
                title="Save event results data",
                message="".join(
                    (
                        "Rename new file as\n\n",
                        os.path.join(self._folder, self._filename),
                        "\n\n fails.\n\nRenaming other new files will continue ",
                        "on dismissing this report.",
                    )
                ),
            )


def create_event_configuration_file(file_path):
    """Create event configuration file with default settings."""
    if upgrade_event_configuration_files(file_path):
        return
    with open(file_path, "w", encoding="utf8") as config_file:
        config_file.writelines((" ".join((COLLECTED, COLLECTED)), os.linesep))
        config_file.writelines((" ".join((EXTRACTED, EXTRACTED)), os.linesep))
        config_file.writelines((" ".join((TEXTENTRY, TEXTENTRY)), os.linesep))
        config_file.writelines(
            (" ".join((TEXT_CONTENT_TYPE, _TEXT_CONTENT)), os.linesep)
        )
        config_file.writelines(
            (" ".join((PDF_CONTENT_TYPE, _PDF_CONTENT)), os.linesep)
        )
        config_file.writelines(
            (" ".join((CSV_CONTENT_TYPE, _CSV_CONTENT)), os.linesep)
        )


def upgrade_event_configuration_files(file_path):
    """Upgrade conf and *.ems files to event.conf and collected.conf."""
    directory = os.path.dirname(file_path)
    names = os.listdir(directory)
    if COLLECTED + ".conf" not in names:
        conflictname = os.path.splitext(constants.EVENT_CONF)[0] + ".ems"
        if conflictname in names:
            tkinter.messagebox.showinfo(
                title="Upgrade Event Configuration Files",
                message="".join(
                    (
                        "Cannot upgrade file:\n\n",
                        conflictname,
                        "\n\nbecause new filename is the event configuration ",
                        "filename.\n",
                    )
                ),
            )
        ems = [name for name in names if os.path.splitext(name)[-1] == ".ems"]
        for name in ems:
            bname, ename = os.path.splitext(name)
            if ename == ".ems" and name != conflictname:
                with open(
                    os.path.join(directory, name), encoding="utf8"
                ) as ocf:
                    newname = bname if len(ems) > 1 else COLLECTED
                    with open(
                        os.path.join(directory, newname + ".conf"),
                        "w",
                        encoding="utf8",
                    ) as ncf:
                        for line in ocf:
                            match = re.match(
                                r"([\s#]*)(outputdirectory)(\s+)(.*)", line
                            )
                            if match:
                                data = os.path.basename(match.group(4))
                                ncf.writelines(
                                    (
                                        "".join(
                                            (
                                                match.group(1),
                                                COLLECTED,
                                                match.group(3),
                                                data,
                                            )
                                        ),
                                        os.linesep,
                                    )
                                )
                            else:
                                ncf.write(line)
        if not ems:
            with open(
                os.path.join(directory, COLLECTED + ".conf"),
                "w",
                encoding="utf8",
            ) as config_file:
                config_file.writelines(
                    ("# collected.conf email collection rules.", os.linesep)
                )
                config_file.writelines(
                    (" ".join((COLLECTED, COLLECTED)), os.linesep)
                )
    if constants.EVENT_CONF in names:
        return True
    if "conf" not in names:
        return False
    keymap = dict(mailbox=COLLECTED, extracts=EXTRACTED)
    with open(
        os.path.join(directory, "conf"), encoding="utf8"
    ) as old_config_file:
        with open(file_path, "w", encoding="utf8") as config_file:
            for line in old_config_file:
                match = re.match(r"([\s#]*)([^=\s]+)(\s*)(=)(.*)", line)
                if match:
                    k = match.group(2)
                    config_file.writelines(
                        (
                            "".join(
                                (
                                    match.group(1),
                                    keymap.get(k, k),
                                    match.group(3),
                                    " ",
                                    match.group(5),
                                )
                            ),
                            os.linesep,
                        )
                    )
                else:
                    config_file.write(line)
            return True


class _Headers:
    """Data relevant to authorization of matches from email headers."""

    def __init__(self, dates=None, authorization_delay=None):
        """Initialise dates for email authorisation."""
        self.dates = dates
        if authorization_delay is None:
            self.authorization_delay = None
        elif authorization_delay.isdigit():
            self.authorization_delay = int(authorization_delay) * 86400
        else:
            self.authorization_delay = DEFAULT_IF_DELAY_NOT_VALID * 86400
