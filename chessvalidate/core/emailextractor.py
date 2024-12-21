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
# The column names can be provided in the following conf file entries.
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
# Spreadsheet and csv files might include various player code columns;
# typically containing the ECF reference data relevant to the player.
# These values are ignored in emailextractor: except perhaps for checking the
# format is numeric digits with optional either leading or trailing alpha
# characters (ECF rating, membership number, or code, are seen in reports)
# and including in the player name.
# Spreadsheet and csv files might include club name and, or, club code
# columns; typically containing the ECF reference data relevant to the team.
# The club and club code values are ignored in emailextractor except perhaps
# for checking it's the same for all mentions of a team name.
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
REPORT_HOME_PLAYER_CODE = "report_home_player_code"
REPORT_AWAY_PLAYER_CODE = "report_away_player_code"
REPORT_HOME_CLUB = "report_home_club"
REPORT_AWAY_CLUB = "report_away_club"
REPORT_HOME_CLUB_CODE = "report_home_club_code"
REPORT_AWAY_CLUB_CODE = "report_away_club_code"

# Some columns may not be provided: these items define default values or
# actions which cannot be assumed.
# _REPORT_MISSING_EVENT can use the event name from event.conf file.
# _REPORT_AWAY_TEAM_SCORE and _REPORT_HOME_TEAM_SCORE have obvious defaults.
# _REPORT_DAY, _REPORT_BOARD and _REPORT_ROUND are optional, so the default
# is null.
REPORT_MISSING_COLOUR = "report_missing_colour"
REPORT_HOME_WIN = "report_home_win"
REPORT_AWAY_WIN = "report_away_win"
REPORT_DRAW = "report_draw"

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
# extracted data.  Schedule and report names are listed separately.
SCHEDULE_CSV_DATA_NAME = "sched_csv_data_name"
REPORT_CSV_DATA_NAME = "report_csv_data_name"

# Name the rules to transform input lines for inclusion in difference file.
# Added to guide transformation of game per row csv files to fit report style.
# Absence means no transformation.
REPLACE = "replace"
PARTIAL_REPLACE = "partial_replace"

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
        parser=None,
        extractemail=None,
        **kwargs,
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
            parser=parser,
            extractemail=extractemail,
            **kwargs,
        )

    def _get_report_item_description(self, name):
        """Return name description or None if not set."""
        table = self.criteria.get(REPORT_CSV_DATA_NAME)
        if table is None:
            return (name, None)
        return (name, table[-1][-1].get(name))

    @property
    def home_player_colour(self):
        """Return home player colour description or None if not set."""
        return self._get_report_item_description(_REPORT_HOME_PLAYER_COLOUR)

    @property
    def section(self):
        """Return section description or None if not set."""
        return self._get_report_item_description(_REPORT_SECTION)

    @property
    def day(self):
        """Return day description or None if not set."""
        return self._get_report_item_description(_REPORT_DAY)

    @property
    def date(self):
        """Return date description or None if not set."""
        return self._get_report_item_description(_REPORT_DATE)

    @property
    def round(self):
        """Return round description or None if not set."""
        return self._get_report_item_description(_REPORT_ROUND)

    @property
    def home_team(self):
        """Return home team description or None if not set."""
        return self._get_report_item_description(_REPORT_HOME_TEAM)

    @property
    def home_team_score(self):
        """Return home team score description or None if not set."""
        return self._get_report_item_description(_REPORT_HOME_TEAM_SCORE)

    @property
    def home_player(self):
        """Return home player description or None if not set."""
        return self._get_report_item_description(_REPORT_HOME_PLAYER)

    @property
    def result(self):
        """Return result description or None if not set."""
        return self._get_report_item_description(_REPORT_RESULT)

    @property
    def away_team(self):
        """Return away team description or None if not set."""
        return self._get_report_item_description(_REPORT_AWAY_TEAM)

    @property
    def away_team_score(self):
        """Return away team score description or None if not set."""
        return self._get_report_item_description(_REPORT_AWAY_TEAM_SCORE)

    @property
    def away_player(self):
        """Return away player description or None if not set."""
        return self._get_report_item_description(_REPORT_AWAY_PLAYER)

    @property
    def board(self):
        """Return round description or None if not set."""
        return self._get_report_item_description(_REPORT_BOARD)

    @property
    def event(self):
        """Return round description or None if not set."""
        return self._get_report_item_description(_REPORT_EVENT)

    @property
    def missing_colour_rule(self):
        """Return missing colour rule or None if not set.

        Typically 'home player black on odd' for example.  Define value
        in configuration file to fit caller's requirement.  It is default
        rule for cases where self.home_player_colour returns None.

        """
        return self.criteria.get(REPORT_MISSING_COLOUR)

    @property
    def home_win(self):
        """Return value representing home player win."""
        return self.criteria.get(REPORT_HOME_WIN)

    @property
    def away_win(self):
        """Return value representing home player win."""
        return self.criteria.get(REPORT_AWAY_WIN)

    @property
    def draw(self):
        """Return value representing draw."""
        return self.criteria.get(REPORT_DRAW)


class Parser(emailextractor.Parser):
    """Parse configuration file."""

    def __init__(self, parent=None):
        """Set up keyword to method map."""
        super().__init__(parent=parent)
        self.keyword_rules.update(
            {
                TEXTENTRY: self.assign_value,
                _SCHED_DATE: self._csv_schedule_columns,
                _SCHED_DAY: self._csv_schedule_columns,
                _SCHED_SECTION: self._csv_schedule_columns,
                _SCHED_HOME_TEAM: self._csv_schedule_columns,
                _SCHED_AWAY_TEAM: self._csv_schedule_columns,
                _SCHED_DATA_COLUMNS: self._csv_schedule_columns,
                _REPORT_DATE: self._csv_report_columns,
                _REPORT_DAY: self._csv_report_columns,
                _REPORT_SECTION: self._csv_report_columns,
                _REPORT_HOME_TEAM: self._csv_report_columns,
                _REPORT_AWAY_TEAM: self._csv_report_columns,
                _REPORT_HOME_TEAM_SCORE: self._csv_report_columns,
                _REPORT_AWAY_TEAM_SCORE: self._csv_report_columns,
                _REPORT_HOME_PLAYER: self._csv_report_columns,
                _REPORT_AWAY_PLAYER: self._csv_report_columns,
                _REPORT_RESULT: self._csv_report_columns,
                _REPORT_BOARD: self._csv_report_columns,
                _REPORT_ROUND: self._csv_report_columns,
                _REPORT_HOME_PLAYER_COLOUR: self._csv_report_columns,
                _REPORT_EVENT: self._csv_report_columns,
                _REPORT_DATA_COLUMNS: self._csv_report_columns,
                REPORT_HOME_PLAYER_CODE: self._csv_report_columns,
                REPORT_AWAY_PLAYER_CODE: self._csv_report_columns,
                REPORT_HOME_CLUB: self._csv_report_columns,
                REPORT_AWAY_CLUB: self._csv_report_columns,
                REPORT_HOME_CLUB_CODE: self._csv_report_columns,
                REPORT_AWAY_CLUB_CODE: self._csv_report_columns,
                REPORT_MISSING_COLOUR: self.assign_value,
                REPORT_HOME_WIN: self.assign_value,
                REPORT_AWAY_WIN: self.assign_value,
                REPORT_DRAW: self.assign_value,
                SCHEDULE_CSV_DATA_NAME: self._csv_data_name,
                REPORT_CSV_DATA_NAME: self._csv_data_name,
                REPLACE: self._csv_value_replace,
                PARTIAL_REPLACE: self._csv_value_partial_replace,
                TEXT_FROM_ROWS: self.add_value_to_set,
                RESULTS_PREFIX: self._add_event_re,
                SECTION_PREFIX: self._add_re,
                SECTION_BODY: self._add_re,
                MATCH_BODY: self._add_match_format_re,
                TEAMS_BODY: self._add_match_item_re,
                GAMES_BODY: self._add_match_item_re,
                FINISHED: self._add_match_item_re,
                UNFINISHED: self._add_match_item_re,
                DEFAULT: self._add_match_item_re,
                MATCH_DEFAULT: self._add_match_item_re,
                MATCH_DATE_BODY: self._add_match_item_re,
                PLAYED_ON_BODY: self._add_played_on_format_re,
                TEAMS_PLAYED_ON_BODY: self._add_played_on_item_re,
                GAMES_PLAYED_ON_BODY: self._add_played_on_item_re,
                FINISHED_PLAYED_ON: self._add_played_on_item_re,
                UNFINISHED_PLAYED_ON: self._add_played_on_item_re,
                MATCH_DATE_PLAYED_ON_BODY: self._add_played_on_item_re,
                SCHEDULE_BODY: self._add_fixture_format_re,
                FIXTURE_BODY: self._add_fixture_item_re,
                KEEP_WORD_SPLITTERS: self._assign_event_value,
                SECTION_NAME: self._add_section_name,
                COMPETITION: self.add_value_to_set,
                SOURCE: self._add_re,
                DROP_FORWARDED_MARKERS: self._assign_event_value,
                TEAM_NAME: self._add_value_to_lookup,
                AUTHORIZATION_DELAY: self.assign_value,
            }
        )
        self.context_keys = {
            REPLACE: [None, None, None],
        }

    @staticmethod
    def _re_from_value(val):
        """Process elements for various keyword methods."""
        return re.compile(val, flags=re.IGNORECASE | re.DOTALL)

    @staticmethod
    def _add_value_to_lookup(val, args, args_key):
        """Process TEAM_NAME keyword."""
        val, rep = val.split(sep=val[0], maxsplit=2)[1:]
        if args_key not in args:
            args[args_key] = {}
        args[args_key][val] = rep

    @staticmethod
    def _add_value_to_lookup_set(val, args, args_key):
        """Process lookup set values. (Not used currently)."""
        val, rep = val.split(sep=val[0], maxsplit=2)[1:]
        if args_key not in args:
            args[args_key] = {}
        args[args_key].setdefault(val, set()).add(rep)

    @staticmethod
    def _add_defaulted_value_to_lookup(val, args, args_key):
        """Process COMPETITION keyword. (Commented alternative)."""
        val = val.split(sep=val[0], maxsplit=2)[1:]
        if args_key not in args:
            args[args_key] = {}
        args[args_key][val[0]] = val[-1]

    @staticmethod
    def _csv_data_name(val, args, args_key):
        """Process the keywords listed below.

        SCHEDULE_CSV_DATA_NAME
        REPORT_CSV_DATA_NAME

        """
        elements = val.split(sep=" ")
        csv_name = elements.pop(0)
        args.setdefault(args_key, []).append((csv_name, elements, {}))

    def _csv_columns(self, key, val, args, args_key):
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
        self.context_keys[REPLACE][0] = key
        self.context_keys[REPLACE][1] = args_key
        self.context_keys[REPLACE][2] = val

    def _csv_schedule_columns(self, val, *a):
        """Process the keywords listed below.

        _SCHED_DATE
        _SCHED_DAY
        _SCHED_SECTION
        _SCHED_HOME_TEAM
        _SCHED_AWAY_TEAM
        _SCHED_DATA_COLUMNS

        """
        self._csv_columns(SCHEDULE_CSV_DATA_NAME, val, *a)

    def _csv_report_columns(self, val, *a):
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
        self._csv_columns(REPORT_CSV_DATA_NAME, val, *a)

    def _csv_value_partial_replace(self, val, args, args_key):
        """Process PARTIAL_REPLACE keyword."""
        del args_key
        pvc, val, rep = val.split(sep=val[0], maxsplit=3)[1:]
        cdn, dti, i = self.context_keys[REPLACE]
        if pvc not in EmailExtractor.replace_value_columns.split(i):
            raise EmailExtractorError(" ".join((pvc, "is not included in", i)))
        args[cdn][-1][-1][dti][-1][pvc][val] = rep

    def _csv_value_replace(self, val, args, args_key):
        """Process REPLACE keyword."""
        del args_key
        val, rep = val.split(sep=val[0], maxsplit=2)[1:]
        cdn, dti, i = self.context_keys[REPLACE]
        args[cdn][-1][-1][dti][-1][i][val] = rep

    def _add_event_re(self, val, args, args_key):
        """Process RESULTS_PREFIX keyword."""
        if args_key not in args:
            args[args_key] = []
        args[args_key].append(
            {
                args_key: self._re_from_value(val),
                SECTION_PREFIX: self._re_from_value(""),
                SECTION_BODY: self._re_from_value(""),
                MATCH_FORMATS: [],
                PLAYED_ON_FORMATS: [],
                FIXTURE_FORMATS: [],
                KEEP_WORD_SPLITTERS: DEFAULT_KEEP_WORD_SPLITTERS,
                SECTION_NAME: {},
                SOURCE: self._re_from_value(""),
                DROP_FORWARDED_MARKERS: "",
            },
        )

    def _add_re(self, val, args, args_key):
        """Process the keywords listed below.

        SECTION_PREFIX
        SECTION_BODY
        SOURCE

        """
        args[RESULTS_PREFIX][-1][args_key] = self._re_from_value(val)

    def _add_format_re(self, fin, val, args, args_key):
        """Perform detail for ..._format_re methods."""
        args[RESULTS_PREFIX][-1][fin].append(
            {args_key: self._re_from_value(val)}
        )

    def _add_match_format_re(self, *a):
        """Process MATCH_BODY keyword."""
        self._add_format_re(MATCH_FORMATS, *a)

    def _add_played_on_format_re(self, *a):
        """Process PLAYED_ON_BODY keyword."""
        self._add_format_re(PLAYED_ON_FORMATS, *a)

    def _add_fixture_format_re(self, *a):
        """Process SCHEDULE_BODY keyword."""
        self._add_format_re(FIXTURE_FORMATS, *a)

    def _add_item_re(self, fin, val, args, args_key):
        """Perform detail for ..._item_re methods."""
        args[RESULTS_PREFIX][-1][fin][-1][args_key] = self._re_from_value(val)

    def _add_match_item_re(self, *a):
        """Process the keywords listed below.

        TEAMS_BODY
        GAMES_BODY
        FINISHED
        UNFINISHED
        DEFAULT
        MATCH_DEFAULT
        MATCH_DATE_BODY

        """
        self._add_item_re(MATCH_FORMATS, *a)

    def _add_played_on_item_re(self, *a):
        """Process the keywords listed below.

        TEAMS_PLAYED_ON_BODY
        GAMES_PLAYED_ON_BODY
        FINISHED_PLAYED_ON
        UNFINISHED_PLAYED_ON
        MATCH_DATE_PLAYED_ON_BODY

        """
        self._add_item_re(PLAYED_ON_FORMATS, *a)

    def _add_fixture_item_re(self, *a):
        """Process FIXTURE_BODY keyword."""
        self._add_item_re(FIXTURE_FORMATS, *a)

    @staticmethod
    def _assign_event_value(val, args, args_key):
        """Process KEEP_WORD_SPLITTERS and DROP_FORWARDED_MARKERS keywords."""
        args[RESULTS_PREFIX][-1][args_key] = val

    @staticmethod
    def _add_format_replace(fin, val, args, args_key):
        """Set value lookup for <fin> keyword."""
        del args_key
        val, rep = val.split(sep=val[0], maxsplit=2)[1:]
        args[RESULTS_PREFIX][-1][fin][val] = rep

    def _add_section_name(self, *a):
        """Process SECTION_NAME keyword."""
        self._add_format_replace(SECTION_NAME, *a)


class ExtractEmail(emailextractor.ExtractEmail):
    """Extract emails matching selection criteria from email store."""

    def __init__(
        self,
        extracttext=None,
        sched_csv_data_name=None,
        report_csv_data_name=None,
        text_from_rows=None,
        **soak,
    ):
        """Extend with attributes for collecting chess results.

        These are sched_csv_data_name, report_csv_data_name, and
        text_from_rows.

        extracttext argument default is ExtractText.

        extracttext and **soak arguments are passed to superclass.

        """
        if extracttext is None:
            extracttext = ExtractText
        super().__init__(extracttext=extracttext, **soak)
        if sched_csv_data_name is None:
            self.sched_csv_data_name = []
        else:
            self.sched_csv_data_name = sched_csv_data_name
        if report_csv_data_name is None:
            self.report_csv_data_name = []
        else:
            self.report_csv_data_name = report_csv_data_name
        if text_from_rows is None:
            self.text_from_rows = frozenset()
        else:
            self.text_from_rows = text_from_rows
        # Selectors data will probably be somewhere in sched_csv_data_name or
        # report_csv_data_name, following the example of translations.
        # Not used at present.  Intended for selecting rows for a particular
        # event whene several events in same CSV file or spreadsheet.
        self._selectors = {}


class ExtractText(emailextractor.ExtractText):
    """Repreresent the stages in processing an email."""

    def get_spreadsheet_text(self, *a):
        """Return (sheetname, text) matching schedule and report data names."""
        ems = self._emailstore
        fsn = set(n[0] for n in ems.sched_csv_data_name).union(
            [n[0] for n in ems.report_csv_data_name]
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
        schedule_sheets = {s[0] for s in ems.sched_csv_data_name}
        report_sheets = {s[0] for s in ems.report_csv_data_name}
        csvlines = text.readlines()
        all_text = []
        for cdn in ems.sched_csv_data_name + ems.report_csv_data_name:
            if cdn[0] != sheet and sheet is not None:
                continue

            # I think "not in" version was intended to turn the tabular code
            # off until the "batch of future code" cited at end of build_event
            # in EventParser class is ready.
            # tabular = cdn[0] not in ems.text_from_rows
            tabular = cdn[0] in ems.text_from_rows

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
