# emailextractor.py
# Copyright 2014 Roger Marsh
# Licence: See LICENCE (BSD licence)

"""Extract text from selected emails and save for results extraction.

These classes assume results for an event are held in files in a directory,
with no sub-directories, where each file contains a single email.

Each file may start with a 'From ' line, formatted as in mbox mailbox files,
but lines within the email which start 'From ' will only have been changed to
lines starting '>From ' if the email client which accepted delivery of the
email did so.  It depends on which mailbox format the email client uses.

"""

import re
import csv

from emailextract.core import emailextractor

# File containing typed-in results
TEXTENTRY = "textentry"

# Schedule files may be spreadsheet, csv, or txt files.
# The column names can be provided in the following conf file entries
_SCHED_DATE = "sched_date"
_SCHED_DAY = "sched_day"
_SCHED_SECTION = "sched_section"
_SCHED_HOME_TEAM = "sched_home_team"
_SCHED_AWAY_TEAM = "sched_away_team"
_SCHED_DATA_COLUMNS = "sched_data_columns"

# The column name order is chosen to be compatible with the result table order.
# _SCHED_DAY must not be present if _SCHED_DATE is not present.
SCHEDULE_TABLE = (
    _SCHED_SECTION,
    _SCHED_DAY,
    _SCHED_DATE,
    _SCHED_HOME_TEAM,
    _SCHED_AWAY_TEAM,
    _SCHED_DATA_COLUMNS,
)

# Report files may be spreadsheet, csv, or txt files.
# The column names can be provided in the following conf file entries.
# Note that the _REPORT_x_TEAM_x names are provided for the benefit of game per
# row layouts where each row describes a game in full.  In a match card layout
# the match result is syntactically identical to a game result, and having one
# or two item names makes no difference.
# The _REPORT_RESULT, _REPORT_HOME_PLAYER, and _REPORT_AWAY_PLAYER names are
# used by convention in match card layouts with value and context deciding what
# is being described.
# There is one _REPORT_RESULT column to allow '1 0' as a symbol for home player
# winning, with 1 and 0 being deduced when adding up to get the match score.
# The win bonus in points for grading is a constant: the concept of winning 2-0
# rather than 1-0 is not used.
# _REPORT_DAY must not be present if _REPORT_DATE is not present.
_REPORT_DATE = "report_date"
_REPORT_DAY = "report_day"
_REPORT_SECTION = "report_section"
_REPORT_HOME_TEAM = "report_home_team"
_REPORT_AWAY_TEAM = "report_away_team"
_REPORT_HOME_PLAYER = "report_home_player"
_REPORT_AWAY_PLAYER = "report_away_player"
_REPORT_RESULT = "report_result"
_REPORT_BOARD = "report_board"
_REPORT_ROUND = "report_round"
_REPORT_HOME_PLAYER_COLOUR = "report_home_player_colour"
_REPORT_DATA_COLUMNS = "report_data_columns"
_REPORT_AWAY_TEAM_SCORE = "report_away_team_score"
_REPORT_HOME_TEAM_SCORE = "report_home_team_score"
_REPORT_EVENT = "report_event"

# The column names are arranged in order in the table definition such that the
# common cases have a unique signature in terms of digit and alpha items.
# Then the whitespace delimiter used between items should not matter, except
# newline is the delimiter between rows (the csv convention).
REPORT_TABLE = (
    _REPORT_SECTION,
    _REPORT_DAY,
    _REPORT_DATE,
    _REPORT_ROUND,
    _REPORT_HOME_TEAM,
    _REPORT_HOME_TEAM_SCORE,
    _REPORT_HOME_PLAYER,
    _REPORT_RESULT,
    _REPORT_AWAY_PLAYER,
    _REPORT_AWAY_TEAM_SCORE,
    _REPORT_AWAY_TEAM,
    _REPORT_BOARD,
    _REPORT_HOME_PLAYER_COLOUR,
    _REPORT_EVENT,
    _REPORT_DATA_COLUMNS,
)

# Rows from spreadsheet sheets or csv files can be converted to tab delimited
# text for processing is a table with '' entries for SCHEDULE_TABLE and
# REPORT_TABLE not taken from the row.  The sheet or csv file names to be
# not treated this way are named in the following conf file entries: space is
# used as the delimiter when concatenating elements from a row.
TEXT_FROM_ROWS = "text_from_rows"
TABLE_DELIMITER = "\t"

# Identify a spreadsheet sheet name or csv file name to be included in the
# extracted data.  Schedule and report names are listed separately
_SCHEDULE_CSV_DATA_NAME = "sched_csv_data_name"
_REPORT_CSV_DATA_NAME = "report_csv_data_name"

# Name the rules to transform input lines for inclusion in difference file
# Added to guide transformation of game per row csv files to fit report style.
# Absence means no transformation.
_REPLACE = "replace"
_PARTIAL_REPLACE = "partial_replace"

# The regular expressions which look for relevant items in the extracted text.
# By default items are expected in a newline separated format.
# Sometimes a set of regular expressions can be defined to transform extracted
# text into the expected newline separated format.
# The *_PREFIX' names are used as regular expression split() arguments
# The *_BODY' names are used as regular expression findall() arguments
# Usually SECTION_PREFIX and SECTION_BODY will be different, as will be the
# *PLAYED_ON* versions from their roots.
RESULTS_PREFIX = "results_prefix"
SECTION_PREFIX = "section_prefix"
SECTION_BODY = "section_body"
MATCH_BODY = "match_body"
TEAMS_BODY = "teams_body"
GAMES_BODY = "games_body"
FINISHED = "finished"
UNFINISHED = "unfinished"
DEFAULT = "default"
MATCH_DEFAULT = "match_default"
MATCH_DATE_BODY = "match_date_body"
PLAYED_ON_BODY = "played_on_body"
TEAMS_PLAYED_ON_BODY = "teams_played_on_body"
GAMES_PLAYED_ON_BODY = "games_played_on_body"
FINISHED_PLAYED_ON = "finished_played_on"
UNFINISHED_PLAYED_ON = "unfinished_played_on"
MATCH_DATE_PLAYED_ON_BODY = "match_date_played_on_body"
SCHEDULE_BODY = "schedule_body"
FIXTURE_BODY = "fixture_body"
KEEP_WORD_SPLITTERS = "keep_word_splitters"
SOURCE = "source"
DROP_FORWARDED_MARKERS = "drop_forwarded_markers"

# Names of lists of dictionaries of rules to apply to extracted text.
# The dictionaries will have the *_BODY names as keys, excluding SECTION_BODY.
# A section body is associated with one each of the two lists.
MATCH_FORMATS = "match_formats"
PLAYED_ON_FORMATS = "played_on_formats"
FIXTURE_FORMATS = "fixture_formats"

# Word splitters which are not translated to ' ' by default.  That's '\x20'.
# These are the common ones used when expressing names, numbers, and results.
DEFAULT_KEEP_WORD_SPLITTERS = "+=-,.'"

# Name of competition as supplied in text extracted from a format defined in a
# RESULTS_PREFIX sequence, and it's translation.
SECTION_NAME = "section_name"

# Name of competition expected in text outside defined formats.
# Must be on it's own line or at start of line containing valid data.
# This is not the event name, which is defined as the extra text in the line
# containing two dates or the text on the previous non-empty line if none.
# These values allow any line which does not look like a fixture, game, or
# match result to be ignored by the event parser.
COMPETITION = "competition"

# Team name translation to align names on fixture list with names in match
# result reports.  At least one league emphasises where a team plays in the
# fixture list, but emphasises the rank of the team within the club in result
# reports, by using different names.  In the case I know both names are 12
# characters but only first 3 characters are the same.
TEAM_NAME = "team_name"

# Email headers relevant to authorizing results, matches in particular, for
# grading.

# Delay, in days, since date of sending or receipt, before it is assumed the
# results in the email can be graded.
AUTHORIZATION_DELAY = "authorization_delay"
DEFAULT_IF_DELAY_NOT_VALID = 5


class EmailExtractorError(emailextractor.EmailExtractorError):
    """Exception class for emailextractor module."""


class EmailExtractor(emailextractor.EmailExtractor):
    """Extract text from emails containing chess game results."""

    def __init__(
        self,
        folder,
        configuration=None,
        parser=None,
        extractemail=None,
        parent=None,
    ):
        """Define the email extraction rules from configuration.

        folder - the directory containing the event's data
        configuration - the rules for extracting emails

        """
        if parser is None:
            parser = Parser
        if extractemail is None:
            extractemail = ExtractEmail
        super().__init__(
            folder,
            configuration=configuration,
            parser=parser,
            extractemail=extractemail,
        )


class Parser(emailextractor.Parser):
    """Parse configuration file."""

    def __init__(self, parent=None):
        """Set up keyword to method map."""
        super().__init__(parent=parent)
        self.keyword_rules.update(
            {
                TEXTENTRY: self.assign_value,
                _SCHED_DATE: self.csv_schedule_columns,
                _SCHED_DAY: self.csv_schedule_columns,
                _SCHED_SECTION: self.csv_schedule_columns,
                _SCHED_HOME_TEAM: self.csv_schedule_columns,
                _SCHED_AWAY_TEAM: self.csv_schedule_columns,
                _SCHED_DATA_COLUMNS: self.csv_schedule_columns,
                _REPORT_DATE: self.csv_report_columns,
                _REPORT_DAY: self.csv_report_columns,
                _REPORT_SECTION: self.csv_report_columns,
                _REPORT_HOME_TEAM: self.csv_report_columns,
                _REPORT_AWAY_TEAM: self.csv_report_columns,
                _REPORT_HOME_TEAM_SCORE: self.csv_report_columns,
                _REPORT_AWAY_TEAM_SCORE: self.csv_report_columns,
                _REPORT_HOME_PLAYER: self.csv_report_columns,
                _REPORT_AWAY_PLAYER: self.csv_report_columns,
                _REPORT_RESULT: self.csv_report_columns,
                _REPORT_BOARD: self.csv_report_columns,
                _REPORT_ROUND: self.csv_report_columns,
                _REPORT_HOME_PLAYER_COLOUR: self.csv_report_columns,
                _REPORT_EVENT: self.csv_report_columns,
                _REPORT_DATA_COLUMNS: self.csv_report_columns,
                _SCHEDULE_CSV_DATA_NAME: self.csv_data_name,
                _REPORT_CSV_DATA_NAME: self.csv_data_name,
                _REPLACE: self.csv_value_replace,
                _PARTIAL_REPLACE: self.csv_value_partial_replace,
                TEXT_FROM_ROWS: self.add_value_to_set,
                RESULTS_PREFIX: self.add_event_re,
                SECTION_PREFIX: self.add_re,
                SECTION_BODY: self.add_re,
                MATCH_BODY: self.add_match_format_re,
                TEAMS_BODY: self.add_match_item_re,
                GAMES_BODY: self.add_match_item_re,
                FINISHED: self.add_match_item_re,
                UNFINISHED: self.add_match_item_re,
                DEFAULT: self.add_match_item_re,
                MATCH_DEFAULT: self.add_match_item_re,
                MATCH_DATE_BODY: self.add_match_item_re,
                PLAYED_ON_BODY: self.add_played_on_format_re,
                TEAMS_PLAYED_ON_BODY: self.add_played_on_item_re,
                GAMES_PLAYED_ON_BODY: self.add_played_on_item_re,
                FINISHED_PLAYED_ON: self.add_played_on_item_re,
                UNFINISHED_PLAYED_ON: self.add_played_on_item_re,
                MATCH_DATE_PLAYED_ON_BODY: self.add_played_on_item_re,
                SCHEDULE_BODY: self.add_fixture_format_re,
                FIXTURE_BODY: self.add_fixture_item_re,
                KEEP_WORD_SPLITTERS: self.assign_event_value,
                SECTION_NAME: self.add_section_name,
                COMPETITION: self.add_value_to_set,
                SOURCE: self.add_re,
                DROP_FORWARDED_MARKERS: self.assign_event_value,
                TEAM_NAME: self.add_value_to_lookup,
                AUTHORIZATION_DELAY: self.assign_value,
            }
        )
        self.context_keys = {
            _REPLACE: [None, None, None],
        }

    @staticmethod
    def re_from_value(val):
        """Process elements for various keyword methods."""
        return re.compile(val, flags=re.IGNORECASE | re.DOTALL)

    @staticmethod
    def add_value_to_lookup(val, args, args_key):
        """Process TEAM_NAME keyword."""
        val, rep = val.split(sep=val[0], maxsplit=2)[1:]
        if args_key not in args:
            args[args_key] = dict()
        args[args_key][val] = rep

    @staticmethod
    def add_value_to_lookup_set(val, args, args_key):
        """Process lookup set values. (Not used currently)."""
        val, rep = val.split(sep=val[0], maxsplit=2)[1:]
        if args_key not in args:
            args[args_key] = dict()
        args[args_key].setdefault(val, set()).add(rep)

    @staticmethod
    def add_defaulted_value_to_lookup(val, args, args_key):
        """Process COMPETITION keyword. (Commented alternative)."""
        val = val.split(sep=val[0], maxsplit=2)[1:]
        if args_key not in args:
            args[args_key] = dict()
        args[args_key][val[0]] = val[-1]

    @staticmethod
    def csv_data_name(val, args, args_key):
        """Process the keywords listed below.

        _SCHEDULE_CSV_DATA_NAME
        _REPORT_CSV_DATA_NAME

        """
        elements = val.split(sep=" ")
        csv_name = elements.pop(0)
        args.setdefault(args_key, []).append((csv_name, elements, {}))

    def csv_columns(self, key, val, args, args_key):
        """Perform detail for csv_..._columns methods."""
        elements = EmailExtractor.replace_value_columns.split(val)
        sep = [""]
        sep.extend(
            [
                " " if s == "+" else ""
                for s in EmailExtractor.replace_value_columns.findall(val)
            ]
        )
        args[key][-1][-1][args_key] = (
            elements,
            {e: sep[i] for i, e in enumerate(elements)},
            {e: {} for e in elements},
        )
        self.context_keys[_REPLACE][0] = key
        self.context_keys[_REPLACE][1] = args_key
        self.context_keys[_REPLACE][2] = val

    def csv_schedule_columns(self, val, *a):
        """Process the keywords listed below.

        _SCHED_DATE
        _SCHED_DAY
        _SCHED_SECTION
        _SCHED_HOME_TEAM
        _SCHED_AWAY_TEAM
        _SCHED_DATA_COLUMNS

        """
        self.csv_columns(_SCHEDULE_CSV_DATA_NAME, val, *a)

    def csv_report_columns(self, val, *a):
        """Process the keywords listed below.

        _REPORT_DATE
        _REPORT_DAY
        _REPORT_SECTION
        _REPORT_HOME_TEAM
        _REPORT_AWAY_TEAM
        _REPORT_HOME_TEAM_SCORE
        _REPORT_AWAY_TEAM_SCORE
        _REPORT_HOME_PLAYER
        _REPORT_AWAY_PLAYER
        _REPORT_RESULT
        _REPORT_BOARD
        _REPORT_ROUND
        _REPORT_HOME_PLAYER_COLOUR
        _REPORT_EVENT
        _REPORT_DATA_COLUMNS

        """
        self.csv_columns(_REPORT_CSV_DATA_NAME, val, *a)

    def csv_value_partial_replace(self, val, args, args_key):
        """Process _PARTIAL_REPLACE keyword."""
        del args_key
        pvc, val, rep = val.split(sep=val[0], maxsplit=3)[1:]
        cdn, dti, i = self.context_keys[_REPLACE]
        if pvc not in EmailExtractor.replace_value_columns.split(i):
            raise EmailExtractorError(" ".join((pvc, "is not included in", i)))
        args[cdn][-1][-1][dti][-1][pvc][val] = rep

    def csv_value_replace(self, val, args, args_key):
        """Process _REPLACE keyword."""
        del args_key
        val, rep = val.split(sep=val[0], maxsplit=2)[1:]
        cdn, dti, i = self.context_keys[_REPLACE]
        args[cdn][-1][-1][dti][-1][i][val] = rep

    def add_event_re(self, val, args, args_key):
        """Process RESULTS_PREFIX keyword."""
        if args_key not in args:
            args[args_key] = list()
        args[args_key].append(
            {
                args_key: self.re_from_value(val),
                SECTION_PREFIX: self.re_from_value(""),
                SECTION_BODY: self.re_from_value(""),
                MATCH_FORMATS: [],
                PLAYED_ON_FORMATS: [],
                FIXTURE_FORMATS: [],
                KEEP_WORD_SPLITTERS: DEFAULT_KEEP_WORD_SPLITTERS,
                SECTION_NAME: {},
                SOURCE: self.re_from_value(""),
                DROP_FORWARDED_MARKERS: "",
            },
        )

    def add_re(self, val, args, args_key):
        """Process the keywords listed below.

        SECTION_PREFIX
        SECTION_BODY
        SOURCE

        """
        args[RESULTS_PREFIX][-1][args_key] = self.re_from_value(val)

    def add_format_re(self, fin, val, args, args_key):
        """Perform detail for ..._format_re methods."""
        args[RESULTS_PREFIX][-1][fin].append(
            {args_key: self.re_from_value(val)}
        )

    def add_match_format_re(self, *a):
        """Process MATCH_BODY keyword."""
        self.add_format_re(MATCH_FORMATS, *a)

    def add_played_on_format_re(self, *a):
        """Process PLAYED_ON_BODY keyword."""
        self.add_format_re(PLAYED_ON_FORMATS, *a)

    def add_fixture_format_re(self, *a):
        """Process SCHEDULE_BODY keyword."""
        self.add_format_re(FIXTURE_FORMATS, *a)

    def add_item_re(self, fin, val, args, args_key):
        """Perform detail for ..._item_re methods."""
        args[RESULTS_PREFIX][-1][fin][-1][args_key] = self.re_from_value(val)

    def add_match_item_re(self, *a):
        """Process the keywords listed below.

        TEAMS_BODY
        GAMES_BODY
        FINISHED
        UNFINISHED
        DEFAULT
        MATCH_DEFAULT
        MATCH_DATE_BODY

        """
        self.add_item_re(MATCH_FORMATS, *a)

    def add_played_on_item_re(self, *a):
        """Process the keywords listed below.

        TEAMS_PLAYED_ON_BODY
        GAMES_PLAYED_ON_BODY
        FINISHED_PLAYED_ON
        UNFINISHED_PLAYED_ON
        MATCH_DATE_PLAYED_ON_BODY

        """
        self.add_item_re(PLAYED_ON_FORMATS, *a)

    def add_fixture_item_re(self, *a):
        """Process FIXTURE_BODY keyword."""
        self.add_item_re(FIXTURE_FORMATS, *a)

    @staticmethod
    def assign_event_value(val, args, args_key):
        """Process KEEP_WORD_SPLITTERS and DROP_FORWARDED_MARKERS keywords."""
        args[RESULTS_PREFIX][-1][args_key] = val

    @staticmethod
    def add_format_replace(fin, val, args, args_key):
        """Set value lookup for <fin> keyword."""
        del args_key
        val, rep = val.split(sep=val[0], maxsplit=2)[1:]
        args[RESULTS_PREFIX][-1][fin][val] = rep

    def add_section_name(self, *a):
        """Process SECTION_NAME keyword."""
        self.add_format_replace(SECTION_NAME, *a)


class ExtractEmail(emailextractor.ExtractEmail):
    """Extract emails matching selection criteria from email store."""

    def __init__(
        self,
        extracttext=None,
        sched_csv_data_name=None,
        report_csv_data_name=None,
        text_from_rows=None,
        **soak
    ):
        """Define the email extraction rules from configuration.

        mailstore - the directory containing the email files
        earliestdate - emails before this date are ignored
        mostrecentdate - emails after this date are ignored
        emailsender - iterable of from addressees to select emails
        eventdirectory - directory to contain the event's data
        ignore - iterable of email filenames to be ignored
        schedule - difference file for event schedule
        reports - difference file for event result reports

        """
        if extracttext is None:
            extracttext = ExtractText
        super().__init__(extracttext=extracttext, **soak)
        if sched_csv_data_name is None:
            self._sched_csv_data_name = []
        else:
            self._sched_csv_data_name = sched_csv_data_name
        if report_csv_data_name is None:
            self._report_csv_data_name = []
        else:
            self._report_csv_data_name = report_csv_data_name
        if text_from_rows is None:
            self._text_from_rows = frozenset()
        else:
            self._text_from_rows = text_from_rows
        # Selectors data will probably be somewhere in sched_csv_data_name or
        # report_csv_data_name, following the example of translations.
        self._selectors = {}


class ExtractText(emailextractor.ExtractText):
    """Repreresent the stages in processing an email."""

    def get_spreadsheet_text(self, *a):
        """Return (sheetname, text) matching schedule and report data names."""
        ems = self._emailstore
        fsn = set(n[0] for n in ems._sched_csv_data_name).union(
            [n[0] for n in ems._report_csv_data_name]
        )
        return [t for t in super().get_spreadsheet_text(*a) if t[0] in fsn]

    def extract_text_from_csv(self, text, sheet=None, filename=None):
        """Extract text using all profiles in configuration file.

        text is a StringIO object.

        Compare the columns that are in the csv file with those in each entry
        in the report and schedule definitions.  If all the defined columns
        exist extract the text and repeat for each definition.

        """
        ems = self._emailstore
        schedule_sheets = {s[0] for s in ems._sched_csv_data_name}
        report_sheets = {s[0] for s in ems._report_csv_data_name}
        csvlines = text.readlines()
        all_text = []
        for cdn in ems._sched_csv_data_name + ems._report_csv_data_name:
            if cdn[0] != sheet and sheet is not None:
                continue

            # I think "not in" version was intended to turn the tabular code
            # off until the "batch of future code" cited at end of build_event
            # in EventParser class is ready.
            # tabular = cdn[0] not in ems._text_from_rows
            tabular = cdn[0] in ems._text_from_rows

            if not tabular:
                delimiter = TABLE_DELIMITER
                if cdn[0] in schedule_sheets:
                    all_columns = SCHEDULE_TABLE
                elif cdn[0] in report_sheets:
                    all_columns = REPORT_TABLE
                else:
                    all_columns = ()
            elif len(cdn[-1]) == 1:
                delimiter = ""
            else:
                delimiter = TABLE_DELIMITER
            csv_text = []
            column_identities = set()
            translate = {}
            for columns in [v[-1].items() for v in cdn[-1].values()]:
                for k, value in columns:
                    column_identities.add(k)
                    translate[k] = value
            try:
                for col in column_identities:
                    int(col)
                column_names = False
            except ValueError:
                column_names = True
            if column_names:
                reader = csv.DictReader(csvlines)
                srm = set(reader.fieldnames)
                if column_identities != column_identities.intersection(srm):
                    csv_text.clear()
                    continue
            else:
                reader = csv.reader(csvlines)
            for row in reader:
                if column_names:
                    rowmap = row
                else:
                    rowmap = {str(e): v for e, v in enumerate(row)}
                    srm = set(rowmap)
                    if column_identities != srm.intersection(
                        column_identities
                    ):
                        csv_text.clear()
                        break
                for key, value in rowmap.items():
                    if key in translate:
                        rowmap[key] = translate[key].get(value, value)
                evtext = []
                if not tabular:
                    for ename in all_columns:
                        acf = cdn[-1].get(ename)
                        if acf is None:
                            evtext.append("")
                        else:
                            prefix = acf[1]
                            acev = []
                            for col in acf[0]:
                                if prefix[col]:
                                    acev.append(prefix[col])
                                acev.append(rowmap[col])
                            evtext.append(" ".join(acev))
                else:
                    for ename in cdn[1]:

                        # This test requires all the relevant columns to be
                        # named in the format's report_csv_data_name line in
                        # the event conf file, including those not used.
                        # Assumption is len(cdn[-1]) == 1 and
                        # set(cdn[0]) == set(cdn[-1]) when this style of report
                        # is not used.
                        if ename in cdn[-1]:

                            prefix = cdn[-1][ename][1]
                            acev = []
                            for col in cdn[-1][ename][0]:
                                if prefix[col]:
                                    acev.append(prefix[col])
                                acev.append(rowmap[col])
                            if acev:
                                evtext.append(" ".join(acev))
                        else:
                            evtext.append("")
                csv_text.append(delimiter.join(evtext))

                # Left over from Hampshire website database interface where
                # both Portsmouth District League and Southampton League could
                # be sent in same CSV file. The selector was used to pick rows
                # for the appropriate event.
                # _REPORT_EVENT allows this feature to be implemented if
                # needed.
                # if len(selector):
                #    if selector not in row:
                #        continue
                #    if row[selector] != value:
                #        continue

            all_text.append("\n".join(csv_text))
        return "\n\n".join(all_text)
