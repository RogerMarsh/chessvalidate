# eventdata.py
# Copyright 2014 Roger Marsh
# Licence: See LICENCE (BSD licence)

"""Source data class chess results extracted from collection of emails.

An instance of EventData is created by the EventParser class for each extracted
data item, usually but not always one item per line.  The event configuration
file must contain regular expressions to drive the extraction from non-default
data formats.

"""
import tkinter.messagebox
from datetime import date

from solentware_misc.core import utilities

from . import names
from . import constants

_EVENT_IDENTITY_NONE = (None, None, None)

# These should go in .gameresults or .constants
ONENIL = "1-0"
NILONE = "0-1"

GAME_RESULT = {ONENIL: (1, 0), NILONE: (0, 1), constants.DRAW: (0.5, 0.5)}
NOMATCHSCORE = frozenset((("", ""),))


class Found:
    """Enumerated data type identifiers for EventData instances."""

    EVENT_AND_DATES = -1
    POSSIBLE_EVENT_NAME = -2
    SWISS_PAIRING_CARD = -3
    APA_PLAYER_CARD = -4
    COMPETITION_GAME_DATE = -5
    COMPETITION_NAME = -6
    COMPETITION_ROUND = -7
    ROUND_HEADER = -8
    COMPETITION_ROUND_GAME_DATE = -9
    FIXTURE_TEAMS = -10
    FIXTURE = -11
    COMPETITION_DATE = -12
    RESULT_NAMES = -13
    RESULT = -14
    COMPETITION_AND_DATES = -15
    CSV_TABULAR = -16

    IGNORE = 0

    SPLIT_SWISS_DATA = 1
    APA_IN_SWISS_DATA = 2
    EXTRA_PIN_SWISS_DATA = 3
    NAME_SPLIT_BY_PIN_SWISS = 4
    NO_PIN_SWISS = 5
    SPLIT_APA_DATA = 11
    EXTRA_PIN_APA_DATA = 12
    NAME_SPLIT_BY_PIN_APA = 13
    NO_PIN_APA = 14
    MORE_THAN_TWO_DATES = 21
    DATE_SPLITS_EVENT_NAME = 22
    EXTRA_SCORE_AND_BOARD_ITEMS = 31
    EXTRA_BOARD_ITEMS_SCORE = 32
    EXTRA_POINTS_ITEMS_SCORE = 33
    EXTRA_DRAW_ITEMS_SCORE = 34
    EXTRA_VOID_ITEMS_SCORE = 35
    EXTRA_BOARD_ITEMS_DRAW = 41
    EXTRA_POINTS_ITEMS_DRAW = 42
    EXTRA_VOID_ITEMS_DRAW = 43
    EXTRA_BOARD_ITEMS_VOID = 51
    EXTRA_POINTS_ITEMS_VOID = 52
    BAD_POINTS_FORMAT = 53
    EXTRA_ROUNDS_DATE_COMPETITION = 61
    NOT_DATE_ONLY = 62
    EXTRA_ROUNDS_DATE = 63
    NOT_COMPETITION_ROUND_ONLY = 64
    NOT_COMPETITION_ONLY = 65
    EXTRA_ROUNDS_COMPETITION = 66
    NOT_TWO_TEAMS = 67
    TABLE_FORMAT = 71

    real_result = frozenset((RESULT_NAMES, RESULT))


class Score:
    """Enumerate the exceptional scores of a game or match.

    The standard game results are '1-0' 'draw' and '0-1'.
    Match results are '3 3' '3.5 2.5' with '1 0' '0.5 0.5' and '0 1' being
    match scores not game scores.

    Emails and other documents reporting results may not follow these rules,
    or even have a rule on this point.

    """

    bad_score = "bad score"
    default = "default"
    away_win_default = "default 1"
    home_win_default = "1 default"
    unfinished = "unfinished"
    void = "void"
    match_defaulted = "match defaulted"
    double_default = "double default"
    error = "error"

    conventional_results = frozenset(
        (
            bad_score,
            default,
            away_win_default,
            home_win_default,
            unfinished,
            void,
            match_defaulted,
            double_default,
            error,
        )
    )

    conventional_match_game_results = frozenset(
        (
            default,
            away_win_default,
            home_win_default,
            # unfinished, # should unfinished be treated as a normal result?
            match_defaulted,
            double_default,
        )
    )

    included_in_team_score = frozenset(
        (
            away_win_default,
            home_win_default,
        )
    )

    excluded_from_match_score = frozenset(
        (
            void,  # void not in conventional_match_game_results at present
            double_default,
        )
    )


class EventData:
    """Detail of a data item extracted from a collection of emails."""

    _attributes = (
        "eventname",
        "startdate",
        "enddate",
        "swiss",
        "person",
        "pin",
        "allplayall",
        "competition",
        "competition_round",
        "teamone",
        "teamtwo",
        "teams",
        "fixture_date",
        "fixture_day",
        "result_date",
        "nameone",
        "nametwo",
        "names",
        "score",
        "result_only",
        "numbers",
        "rounddates",
        "colour",
        "played_on",
        "source",
    )
    _inheritable = (
        ("eventname", "startdate", "enddate"),
        ("competition", "result_date", "competition_round"),
    )

    def __init__(
        self,
        datatag=None,
        context=None,
        found=None,
        raw=None,
        headers=None,
        **kargs
    ):
        """Initialiase EventData instance."""
        self.datatag = datatag
        self.found = found
        self.raw = raw
        self.headers = headers
        for attribute in self.__class__._attributes:
            if attribute in kargs:
                self.__dict__[attribute] = kargs[attribute]
        if isinstance(context, EventContext):
            for i, j in zip(
                self.__class__._inheritable,
                (context.event_identity, context.competition),
            ):
                for i_attr, j_attr in zip(i, j):
                    if j_attr is not None:
                        if i_attr not in self.__dict__:
                            self.__dict__[i_attr] = j_attr
                        elif not self.__dict__[i_attr]:
                            self.__dict__[i_attr] = j_attr

            # AttributeError is assumed to be absence of eventname, usually
            # because event name and date not given at top of input data.
            try:
                context.process(self)
            except AttributeError:
                self._ignore = found
                self.found = Found.IGNORE

        # The text generated for display in the schedule and report widgets.
        # The idea is tagging information can be picked from the containing
        # EventData instance when filling the widget provided the text is
        # picked by (EventData instance, serial number) where serial number,
        # indicating production order, is a key of the appropriate dictionary.
        # Though tagging has not percolated down this far yet!
        self._generated_schedule = {}
        self._generated_report = {}
        # tracer for fixing regular expressions
        # print(self.__dict__) # tracer
        # print() #tracer

    def is_game_result(self):
        """Return True if self represents a game result.

        The score text is tested againt conventional representations of
        game results in Score class to assist the decision.

        """
        if not self.is_result():
            return False
        if self.score in Score.conventional_match_game_results:
            return False
        return not self.is_match_result()

    def is_match_result(self):
        r"""Return True if self repesents a match result.

        If the score text is exactly '\xbd' self is assumed a game result.

        If the score text ends with '\xbd' self is assumed a match result.

        If the total score is 1 self is assumed a game result.

        Otherwise a match result.

        """
        if not self.is_result():
            return False
        # if self.score in Score.conventional_match_game_results:
        #    return True
        score = []
        for text in self.score.split():
            if text == "\xbd":
                score.append(0.5)
            elif text.endswith("\xbd"):
                return True
            else:
                try:
                    score.append(float(text))
                except ValueError:
                    return False
        return sum([float(text) for text in score]) != 1

    def is_match_and_game_result(self):
        """Return True if self represents a tabular result."""
        return self.found == Found.CSV_TABULAR

    def is_result(self):
        """Return True if self represents a ratable result."""
        return self.found in Found.real_result

    def append_generated_schedule(self, schedule, text):
        """Append generation reference for text to schedule."""
        self._generated_schedule[len(schedule)] = text
        schedule.append((len(schedule), self))

    def append_generated_report(self, report, text):
        """Append generation reference for text to report."""
        self._generated_report[len(report)] = text
        report.append((len(report), self))

    def get_report_tag_and_text(self, key):
        """Return (tag, text) for self._generated_report[key].

        Intended for tagging text with tag when inserted into a Text widget.

        """
        return (self.datatag, self._generated_report[key])

    def get_schedule_tag_and_text(self, key):
        """Return (tag, text) for self._generated_schedule[key].

        Intended for tagging text with tag when inserted into a Text widget.

        """
        return (self.datatag, self._generated_schedule[key])

    def _print(self):
        """Print trace when fixing problems."""
        try:
            print(self.__dict__)
        except Exception:
            print("\n>>>>>>>>")
            for k, value in self.__dict__.items():
                try:
                    print(repr(k), repr(value))
                except Exception:
                    print(repr(k), "not printable")
            print("<<<<<<<<\n")

    def is_match_defaulted(self):
        """Return True if match defaulted."""
        if self.found == Found.RESULT:
            return self.score == Score.match_defaulted
        return False

    def is_defaulting_side_known(self):
        """Return True if defaulting side can be decided."""
        if self.found == Found.RESULT:
            return self.score in Score.included_in_team_score
        return False

    def is_default_counted(self):
        """Return True if default counts to match result."""
        if self.found == Found.RESULT:
            return self.score == Score.default
        return False

    def is_default_not_counted(self):
        """Return True if default doed not count to match result."""
        if self.found == Found.RESULT:
            return self.score in Score.excluded_from_match_score
        return False


class TableEventData(EventData):
    """Add partial comparison to EventData."""

    _attributes = EventData._attributes + (
        "teamonescore",
        "teamtwoscore",
    )

    gdate = utilities.AppSysDate()

    def __init__(self, context=None, **kargs):
        """Initialiase TableEventData instance."""
        super().__init__(context=context, **kargs)
        self.context = context
        result_date = self.result_date
        if TableEventData.gdate.parse_date(result_date) == len(result_date):
            self._date_played = TableEventData.gdate.iso_format_date()
        else:
            self._date_played = ""

    def __eq__(self, other):
        """Return True if self equals other."""
        if self.competition != other.competition:
            return False
        if self._date_played != other._date_played:
            return False
        if self.competition_round != other.competition_round:
            return False
        if self.teamone != other.teamone:
            return False
        if self.teamtwo != other.teamtwo:
            return False
        if self.numbers[0] != other.numbers[0]:
            return False
        return True

    def __lt__(self, other):
        """Return True if self less than other."""
        if self.competition < other.competition:
            return True
        if self._date_played < other._date_played:
            return True

        # Adopt numeric string convention
        if len(self.competition_round) < len(other.competition_round):
            return True

        if self.competition_round < other.competition_round:
            return True
        if self.teamone < other.teamone:
            return True
        if self.teamtwo < other.teamtwo:
            return True

        # Adopt numeric string convention
        if len(self.numbers[0]) < len(other.numbers[0]):
            return True

        if self.numbers[0] < other.numbers[0]:
            return True
        return False


class EventContext:
    """Context for creation of an EventData instance."""

    def __init__(self, event_identity):
        """Initialise event context."""
        # Event identity
        # The event_identity property implementation was not changed when
        # event_identity argument to __init__ was added.
        self._event_identity = _EVENT_IDENTITY_NONE
        self.event_identity = event_identity

        # Default competition data if not given for a result
        self._competition_name = None
        self._gamedate = None
        self._gameround = None

        # Event data in receipt order
        self._items = []

        # Event data by category in receipt order
        self._allplayall = _EventItems()
        self._swiss = _EventItems()
        self._fixtures = _EventItems()
        self._results = _EventItems()
        self._players = _EventItems()
        self._round_dates = _EventItems()
        self._tabular = _EventItems()

        # Method switch for event data
        self._process = {
            Found.EVENT_AND_DATES: self._event_and_dates,
            Found.POSSIBLE_EVENT_NAME: self._possible_event_name,
            Found.SWISS_PAIRING_CARD: self._swiss_pairing_card,
            Found.APA_PLAYER_CARD: self._apa_player_card,
            Found.COMPETITION_GAME_DATE: self._competition_game_date,
            Found.COMPETITION_NAME: self._competition,
            Found.COMPETITION_ROUND: self._competition_round,
            Found.ROUND_HEADER: self._round_header,
            Found.COMPETITION_ROUND_GAME_DATE: self._competition_round_game_date,
            Found.FIXTURE_TEAMS: self._fixture_teams,
            Found.FIXTURE: self._fixture,
            Found.COMPETITION_DATE: self._competition_date,
            Found.RESULT_NAMES: self._result_names,
            Found.RESULT: self._result,
            Found.COMPETITION_AND_DATES: self._swiss_fixture_apa_round_dates,
            Found.CSV_TABULAR: self._csv_tabular,
            Found.IGNORE: self._ignore,
        }

    def process(self, eventdata):
        """Retun state after processing eventdata."""
        self._items.append(eventdata)
        return self._process.get(eventdata.found, self._exception)(eventdata)

    # Rvent identity is set once.
    # It is composed from the event's name, and start and end dates.
    # The two components, name and dates, can be set again until both are set.

    @property
    def event_identity(self):
        """Return event identity."""
        return self._event_identity

    @event_identity.setter
    def event_identity(self, value):
        """Set event name and identity (name plus start and end dates)."""
        if self._event_identity != _EVENT_IDENTITY_NONE:
            return
        self._eventname, self._event_startdate, self._event_enddate = value
        self._event_identity = (
            self._eventname,
            self._event_startdate,
            self._event_enddate,
        )
        self._eventdate = (self._event_startdate, self._event_enddate)

    def set_eventname(self, value):
        """Set event name and identity (name plus start and end dates)."""
        if self._event_identity is not _EVENT_IDENTITY_NONE:
            return
        self._eventname = value
        if self._eventdate is not None:
            self._event_identity = (
                self._eventname,
                self._event_startdate,
                self._event_enddate,
            )

    eventname = property(fset=set_eventname)

    def set_eventdate(self, value):
        """Set event start date and event end date."""
        if self._event_identity is not _EVENT_IDENTITY_NONE:
            return
        self._event_startdate, self._event_enddate = value
        self._eventdate = (self._event_startdate, self._event_enddate)
        if self._eventname is not None:
            self._event_identity = (
                self._eventname,
                self._event_startdate,
                self._event_enddate,
            )

    eventdate = property(fset=set_eventdate)

    # Competition name, game date, and game round can have default values which
    # are used if not specified by the individual games.
    # These can be set if event identity is set.
    # Game date and game round can be set independently if competition name is
    # already set.
    # When competition name is set, game date and game round are cleared unless
    # given at the same time.

    @property
    def competition(self):
        """Return competition_name, gamedate, and gameround."""
        return (self._competition_name, self._gamedate, self._gameround)

    @competition.setter
    def competition(self, value):
        """Set competition_name, gamedate, and gameround."""
        if self._event_identity is _EVENT_IDENTITY_NONE:
            return
        self._competition_name, self._gamedate, self._gameround = value
        self._add_key()

    def set_gameround(self, value):
        """Set gameround."""
        if self._competition_name is None:
            return
        self._gameround = value

    gameround = property(fset=set_gameround)

    def set_gamedate(self, value):
        """Set gamedate."""
        if self._competition_name is None:
            return
        self._gamedate = value

    gamedate = property(fset=set_gamedate)

    def set_competition_name(self, value):
        """Set competition name."""
        if self._event_identity is _EVENT_IDENTITY_NONE:
            return
        self._competition_name = value
        self._gamedate = None
        self._gameround = None
        self._add_key()

    competition_name = property(fset=set_competition_name)

    def set_competition_name_gamedate(self, value):
        """Set competition_name, gamedate, and gameround."""
        if self._event_identity is _EVENT_IDENTITY_NONE:
            return
        self._competition_name, self._gamedate = value
        self._gameround = None
        self._add_key()

    competition_name_gamedate = property(fset=set_competition_name_gamedate)

    def set_competition_name_gameround(self, value):
        """Set competition_name and gameround."""
        if self._event_identity is _EVENT_IDENTITY_NONE:
            return
        self._competition_name, self._gameround = value
        self._gamedate = None
        self._add_key()

    competition_name_gameround = property(fset=set_competition_name_gameround)

    def _event_and_dates(self, eventdata):
        """Process Found.EVENT_AND_DATES eventdata instances."""
        self.event_identity = (
            eventdata.eventname, eventdata.startdate, eventdata.enddate
        )
        self.set_eventdate((eventdata.startdate, eventdata.enddate))
        if "eventname" in eventdata.__dict__:
            self.set_eventname(eventdata.eventname)

    def _possible_event_name(self, eventdata):
        """Process Found.POSSIBLE_EVENT_NAME eventdata instances."""
        # This is the default attempt at processing data which is not known to
        # be wrong.  Ignore unless an event name is still allowed.
        self.set_eventname(eventdata.eventname)

    def _swiss_pairing_card(self, eventdata):
        """Process Found.SWISS_PAIRING_CARD eventdata instances."""
        if eventdata.competition in self._round_dates:
            self._swiss.append(self._round_dates[eventdata.competition])
            del self._round_dates[eventdata.competition]
        self._swiss.append(eventdata)

    def _apa_player_card(self, eventdata):
        """Process Found.APA_PLAYER_CARD eventdata instances."""
        if eventdata.competition in self._round_dates:
            self._allplayall.append(self._round_dates[eventdata.competition])
            del self._round_dates[eventdata.competition]
        self._allplayall.append(eventdata)

    # *_game_* rather than *_result_* to imply game, not match, lines follow.
    def _competition_game_date(self, eventdata):
        """Process Found.COMPETITION_GAME_DATE eventdata instances."""
        self.set_competition_name_gamedate(
            (eventdata.competition, eventdata.result_date)
        )

    def _competition(self, eventdata):
        """Process Found.COMPETITION_NAME eventdata instances."""
        self.set_competition_name(eventdata.competition)

    def _competition_round(self, eventdata):
        """Process Found.COMPETITION_ROUND eventdata instances."""
        self.set_competition_name_gameround(
            (eventdata.competition, eventdata.competition_round)
        )

    def _round_header(self, eventdata):
        """Process Found.ROUND_HEADER eventdata instances."""
        self.set_gamedate(eventdata.competition_round)

    # *_game_* rather than *_result_* to imply game, not match, lines follow.
    def _competition_round_game_date(self, eventdata):
        """Process Found.COMPETITION_ROUND_GAME_DATE eventdata instances."""
        self.competition = (
            eventdata.competition,
            eventdata.result_date,
            eventdata.competition_round,
        )

    def _fixture_teams(self, eventdata):
        """Process Found.FIXTURE_TEAMS eventdata instances.

        A fixture is always accepted when event_identity is not None.

        The two teams are known.

        """
        if eventdata.competition in self._round_dates:
            self._fixtures.append(self._round_dates[eventdata.competition])
            del self._round_dates[eventdata.competition]
        self._fixtures.append(eventdata)

    def _fixture(self, eventdata):
        """Process Found.FIXTURE eventdata instances.

        A fixture is always accepted when event_identity is not None.

        The two teams have to be deduced from a single string containing both
        team names.  It is assumed this can be done provided teams appear first
        in some lines and last in others.

        """
        if eventdata.competition in self._round_dates:
            self._fixtures.append(self._round_dates[eventdata.competition])
            del self._round_dates[eventdata.competition]
        self._fixtures.add_key(eventdata.competition)
        self._fixtures.append(eventdata)

    def _competition_date(self, eventdata):
        """Process Found.COMPETITION_DATE eventdata instances."""
        self.set_gamedate(eventdata.result_date)

    # Method named to imply games and matches cannot always be distinguished.
    def _result_names(self, eventdata):
        """Process Found.RESULT_NAMES eventdata instances."""
        if "competition" in eventdata.__dict__:
            self._results.add_key(eventdata.competition)
            self._results.append(eventdata)

    # Method named to imply games and matches cannot always be distinguished.
    def _result(self, eventdata):
        """Process Found.RESULT eventdata instances."""
        if "competition" in eventdata.__dict__:
            self._results.add_key(eventdata.competition)
            self._results.append(eventdata)

    def _swiss_fixture_apa_round_dates(self, eventdata):
        """Process Found.COMPETITION_AND_DATES eventdata instances."""
        if eventdata.competition in self._round_dates:
            # Competition has round dates awaiting result data to choose type.
            return
        self.set_competition_name(eventdata.competition)
        for event in (self._swiss, self._fixtures, self._allplayall):
            for item in event[eventdata.competition]:
                if item.found is Found.COMPETITION_AND_DATES:
                    break
            else:
                event.append(eventdata)
                break
        else:
            self._round_dates[eventdata.competition] = eventdata

    def _csv_tabular(self, eventdata):
        """Process Found.CSV_TABULAR eventdata instances."""
        if eventdata.competition not in self._tabular:
            self._tabular.add_key(eventdata.competition)
        self._tabular.append(eventdata)

    def _ignore(self, eventdata):
        """Process Found.IGNORE eventdata instances."""

    def _exception(self, eventdata):
        """Wrap print trace functions on exceptions when fixing problems."""
        # self._players
        # self._print(eventdata)

    def _print(self, eventdata):
        """Wrap print eventdata method used when fixing problems.

        Otherwise not used.

        """
        eventdata._print()

    def _add_key(self):
        """Add self._competition_name for processing by all report styles."""
        if self._competition_name:
            for report_style in (
                self._allplayall,
                self._swiss,
                self._fixtures,
                self._results,
                self._players,
                self._tabular,
            ):
                report_style.add_key(self._competition_name)

    def fixture_list_names(self, team_name_lookup, truncate=None):
        """Return True if abbreviated team name search was done.

        The normal return is None.

        If get_names_from_joined_names() function suggested truncating the
        search, the return is True or False depending on user choice.

        """
        for k, value in self._fixtures.items():
            team_names, truncate = get_names_from_joined_names(
                value, ("teams", "teamone", "teamtwo"), truncate
            )
            fixtures = self._fixtures[k]
            for nkey, nvalue in team_names.items():
                if "teams" in fixtures[nkey].__dict__:
                    fixtures[nkey].__dict__.update(nvalue)
                    del fixtures[nkey].teams
            if team_name_lookup:
                team_name_lookup = {
                    k.lower(): v for k, v in team_name_lookup.items()
                }
                for fixture in fixtures:
                    fixture.teamone = team_name_lookup.get(
                        fixture.teamone.lower(), fixture.teamone
                    )
                    fixture.teamtwo = team_name_lookup.get(
                        fixture.teamtwo.lower(), fixture.teamtwo
                    )
        return truncate

    def results_names(self, truncate=None):
        """Return True if abbreviated player name search was done.

        The normal return is None.

        If get_names_from_joined_names() function suggested truncating the
        search, the return is True or False depending on user choice.

        """
        for k, value in self._results.items():
            player_names, truncate = get_names_from_joined_names(
                value, ("names", "nameone", "nametwo"), truncate
            )
            results = self._results[k]
            for nkey, nvalue in player_names.items():
                if "names" in results[nkey].__dict__:
                    results[nkey].__dict__.update(nvalue)
                    del results[nkey].names
        return truncate


# Derived from get_team_names_from_match_names method of class ConvertResults
# in module convertresults
def get_names_from_joined_names(joined_names, attrnames, truncate):
    """Generate possible names from a set of concatenated pairs of names.

    Try to get names from fixture or result names using the MatchTeams class.
    If that fails use the _Names class to do the best possible by splitting
    the match name in two.

    MatchTeams, given enough consistent concatenated team or player names, will
    get names 'Team A' and 'Team B' from 'Team A - Team B' but _Names might get
    as far as names 'Team A -' and 'Team B'.

    """
    nameone, nametwo = attrnames[1:]
    homename = set()
    awayname = set()
    nameset = {}
    for item, eventdata in enumerate(joined_names):
        edict = eventdata.__dict__
        concat = [edict[n].split() for n in attrnames if n in edict]
        if sum([len(c) for c in concat]) > 50:
            if truncate is None:
                truncate = tkinter.messagebox.askyesno(
                    message="".join(
                        (
                            "Truncate to 20 words?\n\n",
                            "Attempting to decide how to split more than 50 words ",
                            "into 2 names, which is unlikely to be worth the time ",
                            "it will take.  This is probably happening because ",
                            "you have not had chances to delete text which is ",
                            "obviously irrelevant.\n\nYou may have to not ",
                            "truncate eventually but saying 'No' at first may ",
                            "waste a lot of time.",
                        )
                    ),
                    title="Calculating Names",
                )
            if truncate:
                concat = [c[:10] for c in concat]
        nameset[item] = nset = names.Names(
            string=" ".join([" ".join(c) for c in concat])
        )
        for hname, aname in nset.namepairs:
            homename.add(hname)
            awayname.add(aname)
    splitnames = {}
    consistent = set()
    guesses = {}
    allnames = homename.intersection(awayname)
    for k, gvalue in nameset.items():
        gvalue.namepairs = tuple(
            [
                (h, a)
                for h, a in gvalue.namepairs
                if h in allnames and a in allnames
            ]
        )
        try:
            nset = {}
            nset[nameone] = gvalue.namepairs[-1][0]
            nset[nametwo] = gvalue.namepairs[-1][-1]
            consistent.add(nset[nameone])
            consistent.add(nset[nametwo])
            splitnames[k] = nset
        except:
            gvalue.guess_names_from_known_names(allnames)
            guesses[k] = {
                nameone: gvalue.namepairs[-1][0],
                nametwo: gvalue.namepairs[-1][-1],
            }
    del allnames, homename, awayname
    prevlenguesses = 0
    while len(guesses) != prevlenguesses:
        prevlenguesses = len(guesses)
        stillguesses = {}
        while guesses:
            k, gvalue = guesses.popitem()
            awaywords = " ".join((gvalue[nameone], gvalue[nametwo])).split()
            if not awaywords:
                continue  # No names for defaulted games
            homewords = [awaywords.pop(0)]
            while awaywords:
                homename = " ".join(homewords)
                awayname = " ".join(awaywords)
                if homename in consistent or awayname in consistent:
                    splitnames[k] = {nameone: homename, nametwo: awayname}
                    break
                homewords.append(awaywords.pop(0))
            else:
                stillguesses[k] = gvalue
        guesses = stillguesses
    splitnames.update(guesses)
    return (splitnames, truncate)


class AdaptEventContext(EventContext):
    """Adapt EventContext to drive the old Report and Schedule classes.

    The Report.build_results() and Schedule.build_schedule() methods expect
    str.splitlines() as the argument containing the event results.  These
    methods build and validate the data structures used to update the results
    database.

    EventContext extracts results from text files, including emails and their
    attachments, and populates some _EventItems instances with data structures
    representing fixtures, match results, and game results.  It replaces the
    the separate modules which deal with typed results, including thoses sent
    by email, and the specific formats used by PDL and SL in the hampshire.core
    package.

    The easiest way to get data from an EventContext instance to the database
    is generate input expected by the two methods in the Report and Schedule
    classes.  This is done by the get_schedule_text() and get_results_text()
    methods.

    """

    adapted_scores = {
        Score.bad_score: "badscore",  # forces result to be not recognised
        Score.default: "default",
        Score.away_win_default: "def-",
        Score.home_win_default: "def+",
        Score.unfinished: "unfinished",
        Score.void: "void",
        Score.match_defaulted: "matchdefaulted",
        Score.double_default: "dbld",
        Score.error: "error",  # forces result to be not recognised
    }

    @staticmethod
    def mangle(text):
        """Mangle lines starting with colour_rule or sectiontype keywords."""
        words = [t for t in text.split(sep=" ") if len(t)]
        if words[0].lower() in {
            "allplayall",
            "knockout",
            "league",
            "cup",
            "swiss",
            "swissteam",
            "jamboree",
            "team",
            "fixturelist",
            "individual",
            "whiteonodd",
            "blackonodd",
            "whiteonall",
            "blackonall",
            "notspecified",
        }:
            words[0] = "".join((words[0][0], words[0]))
            return " ".join(words)
        return text

    @staticmethod
    def translate_score(result):
        """Translate score of result to style understood by report module."""
        score = AdaptEventContext.adapted_scores.get(result.score)
        if score:
            return score
        score = []
        for text in result.score.split():
            if text == "\xbd":
                score.append("0.5")
            elif text.endswith("\xbd"):
                score.append("".join((text[:-1], ".5")))
            else:
                try:
                    float(text)
                except ValueError:
                    return result.score
                score.append(text)
        if sum([float(text) for text in score]) == 1:
            score = "-".join(score)
            if score == "0.5-0.5":
                return "draw"
            return score
        return "-".join(score)

    gdate = utilities.AppSysDate()

    @staticmethod
    def mangle_date(board, datestr):
        """Mangle date if board not given so board is not taken from date.

        Convert date to ISO format or replace spaces in date by '-'.

        """
        if board:
            return datestr
        if len(datestr.split()) == 1:
            return datestr
        if AdaptEventContext.gdate.parse_date(datestr) == len(datestr):
            return AdaptEventContext.gdate.iso_format_date()
        return "-".join(datestr.split())

    @staticmethod
    def game_text(game_result):
        """Return game result text for player name convention.

        If the lower-case version of either player name is exactly 'default'
        the game is assumed to have been defaulted by one or both players; and
        neither player name is relevant to subsequent processing because the
        goal is grading the result.

        """
        board = game_result.__dict__.get("numbers", ("",))[0]
        for name in (
            game_result.nameone,
            game_result.nametwo,
        ):
            if name.lower() == "default":
                break
        else:

            # The game was not defaulted.
            return (
                AdaptEventContext.mangle(
                    " ".join(
                        (
                            board,
                            AdaptEventContext.mangle_date(
                                board,
                                game_result.__dict__.get("result_date", ""),
                            ),
                            game_result.nameone,
                            AdaptEventContext.translate_score(game_result),
                            game_result.nametwo,
                        )
                    )
                ),
                game_result,
            )

        # The game was defaulted.
        if game_result.nameone.lower() == game_result.nametwo.lower():
            return (
                AdaptEventContext.mangle(
                    " ".join(
                        (
                            board,
                            AdaptEventContext.mangle_date(
                                board,
                                game_result.__dict__.get("result_date", ""),
                            ),
                            AdaptEventContext.adapted_scores[
                                Score.double_default
                            ],
                        )
                    )
                ),
                game_result,
            )
        if game_result.nameone.lower() == "default":
            return (
                AdaptEventContext.mangle(
                    " ".join(
                        (
                            board,
                            AdaptEventContext.mangle_date(
                                board,
                                game_result.__dict__.get("result_date", ""),
                            ),
                            AdaptEventContext.adapted_scores[
                                Score.away_win_default
                            ],
                            game_result.nametwo,
                        )
                    )
                ),
                game_result,
            )
        return (
            AdaptEventContext.mangle(
                " ".join(
                    (
                        board,
                        AdaptEventContext.mangle_date(
                            board,
                            game_result.__dict__.get("result_date", ""),
                        ),
                        game_result.nameone,
                        AdaptEventContext.adapted_scores[
                            Score.home_win_default
                        ],
                    )
                )
            ),
            game_result,
        )

    def get_schedule_text(self):
        """Return list of text lines giving fixture and player details."""
        if not self._eventname:
            return []
        text = [(self._eventname, None)]

        # Force an error from old-style processing, usually absence of event
        # name and dates.
        try:
            text.append((" ".join(self._eventdate), None))
        except TypeError:
            text.append(("", None))

        # Although any kind of result is allowed in an _EventItems instance,
        # the Schedule (and Report) classes will object if it happens.
        for competition, results in self._allplayall.items():
            if len(results) == 0:
                continue
            text.append((" ".join(("allplayall", competition)), None))
            for row in results:
                if row.found is Found.COMPETITION_AND_DATES:
                    for item, datestr in enumerate(row.rounddates):
                        text.append((" ".join((str(item + 1), datestr)), row))
                    break
            for row in results:
                if row.found is Found.APA_PLAYER_CARD:
                    # No mechanism for an affiliation ('\t' separated).
                    # May add a 'grading code or ECF membership number' hint.
                    text.append((" ".join((row.pin, row.person)), row))

        for competition, results in self._swiss.items():
            if len(results) == 0:
                continue
            text.append((" ".join(("swiss", competition)), None))
            for row in results:
                if row.found is Found.COMPETITION_AND_DATES:
                    for item, datestr in enumerate(row.rounddates):
                        text.append((" ".join((str(item + 1), datestr)), row))
                    break
            for row in results:
                if row.found is Found.SWISS_PAIRING_CARD:
                    # No mechanism for an affiliation ('\t' separated).
                    # May add a 'grading code or ECF membership number' hint.
                    text.append((" ".join((row.pin, row.person)), row))

        for competition, results in self._results.items():
            if len(results) == 0:
                continue
            if self._is_results_individual(results):
                # The Report class requires the Schedule class to hold the
                # competition identity but the player affiliation details are
                # optional.
                # The EventParser class does not collect these details so just
                # meet the requirement.
                text.append((" ".join(("individual", competition)), None))

        gdate = AdaptEventContext.gdate
        fixture_list_found = False
        for competition, fixtures in self._fixtures.items():
            if len(fixtures) == 0:
                continue
            for fixture in fixtures:
                if fixture.found in (Found.FIXTURE_TEAMS, Found.FIXTURE):
                    if not fixture_list_found:
                        text.append(("fixturelist", fixture))
                        fixture_list_found = True

                    day = fixture.fixture_day
                    if not day:

                        # Report class expects day to be provided, even if the
                        # source did not quote one.
                        if gdate.parse_date(fixture.fixture_date) != -1:
                            day = date(
                                *[
                                    int(d)
                                    for d in gdate.iso_format_date().split("-")
                                ]
                            ).strftime("%A")
                        else:
                            day = "xxx"  # Force bad day, which it must be.

                    text.append(
                        (
                            "\t".join(
                                (
                                    day,
                                    fixture.fixture_date,
                                    competition,
                                    fixture.teamone.title(),
                                    fixture.teamtwo.title(),
                                )
                            ),
                            fixture,
                        )
                    )

        return text

    def get_results_text(self):
        """Return list of text lines giving game result details."""
        if not self._eventname:
            return []
        text = [(self._eventname, None)]

        # source is used as an alternative to match or game date to identify
        # repeated reports of results.  Often it is a date but any reference
        # will do provided it is unique to a set of results.  The date is not
        # used as a game date.  Needed only if games are reported without date
        # played and reports are repeated.
        source = None

        # Although any kind of result is allowed in an _EventItems instance,
        # the Report (and Schedule) classes will object if it happens.
        for competition, results in self._allplayall.items():
            if len(results) == 0:
                continue
            text.append((" ".join(("allplayall", competition)), None))
            for row in results:
                if row.found is Found.APA_PLAYER_CARD:
                    source = self._set_source(row, source, text)

                    # Report class does accept (pin, person, allplayall) as
                    # well, but not the affiliation accepted by Schedule.
                    text.append(
                        (
                            " ".join(
                                (
                                    row.pin,
                                    " ".join(
                                        [
                                            "x" if t == "*" else t
                                            for t in row.allplayall
                                        ]
                                    ),
                                )
                            ),
                            row,
                        )
                    )

        for competition, results in self._swiss.items():
            if len(results) == 0:
                continue
            text.append((" ".join(("swiss", competition)), None))
            for row in results:
                if row.found is Found.SWISS_PAIRING_CARD:
                    source = self._set_source(row, source, text)

                    # Report class does accept (pin, person, swiss) as well,
                    # but not the affiliation accepted by Schedule.
                    text.append(
                        (
                            " ".join(
                                (
                                    row.pin,
                                    " ".join(
                                        [
                                            "x" if t == "*" else t
                                            for t in row.swiss
                                        ]
                                    ),
                                )
                            ),
                            row,
                        )
                    )

        for competition, results in self._results.items():
            if len(results) == 0:
                continue
            if self._is_results_individual(results):
                text.append((" ".join(("individual", competition)), None))
                for row in results:
                    source = self._set_source(row, source, text)
                    text.append(
                        (
                            AdaptEventContext.mangle(
                                " ".join(
                                    (
                                        row.__dict__.get("result_date", ""),
                                        row.__dict__.get("nameone", ""),
                                        AdaptEventContext.translate_score(row),
                                        row.__dict__.get("nametwo", ""),
                                    )
                                )
                            ),
                            row,
                        )
                    )
            else:
                text.append((" ".join(("fixturelist", competition)), None))

                # Hack colour rule for boards in matches
                text.append(("blackonodd", None))

                for row in results:
                    if row.is_game_result():
                        source = self._set_source(row, source, text)
                        text.append(AdaptEventContext.game_text(row))
                    elif row.is_match_result():
                        source = self._set_source(row, source, text)
                        # Should this be looking at numbers like for board?
                        round_ = row.__dict__.get("competition_round", "")
                        if round_:
                            text.append((" ".join(("round", round_)), row))
                        datestr = row.__dict__.get("result_date", "")
                        if datestr:
                            text.append((" ".join(("date", datestr)), row))
                        played_on = row.__dict__.get("played_on", "")
                        if played_on:
                            text.append((played_on, row))
                        text.append(
                            (
                                AdaptEventContext.mangle(
                                    " ".join(
                                        (
                                            row.nameone.title(),
                                            AdaptEventContext.translate_score(
                                                row
                                            ),
                                            row.nametwo.title(),
                                        )
                                    )
                                ),
                                row,
                            )
                        )
                    elif row.is_match_and_game_result():
                        tkinter.messagebox.showinfo(
                            message="".join(
                                (
                                    "A tabular natch or game line is not ",
                                    "processed.",
                                )
                            ),
                            title="Match and Game Result",
                        )
                    elif row.is_match_defaulted():
                        text.append(
                            (
                                AdaptEventContext.mangle(
                                    " ".join(
                                        (
                                            "matchdefaulted",
                                            AdaptEventContext.mangle_date(
                                                "",
                                                row.__dict__.get(
                                                    "result_date", ""
                                                ),
                                            ),
                                        )
                                    )
                                ),
                                row,
                            )
                        )
                    elif row.is_defaulting_side_known():
                        source = self._set_source(row, source, text)
                        board = row.__dict__.get("numbers", ("",))[0]
                        score = AdaptEventContext.translate_score(row)
                        text.append(
                            (
                                AdaptEventContext.mangle(
                                    " ".join(
                                        (
                                            board,
                                            AdaptEventContext.mangle_date(
                                                board,
                                                row.__dict__.get(
                                                    "result_date", ""
                                                ),
                                            ),
                                            score,
                                        )
                                    )
                                ),
                                row,
                            )
                        )
                    elif row.is_default_counted():
                        source = self._set_source(row, source, text)
                        board = row.__dict__.get("numbers", ("",))[0]
                        text.append(
                            (
                                AdaptEventContext.mangle(
                                    " ".join(
                                        (
                                            board,
                                            AdaptEventContext.mangle_date(
                                                board,
                                                row.__dict__.get(
                                                    "result_date", ""
                                                ),
                                            ),
                                            "default",
                                        )
                                    )
                                ),
                                row,
                            )
                        )
                    elif row.is_default_not_counted():
                        source = self._set_source(row, source, text)
                        board = row.__dict__.get("numbers", ("",))[0]
                        text.append(
                            (
                                AdaptEventContext.mangle(
                                    " ".join(
                                        (
                                            board,
                                            AdaptEventContext.mangle_date(
                                                board,
                                                row.__dict__.get(
                                                    "result_date", ""
                                                ),
                                            ),
                                            "void",
                                        )
                                    )
                                ),
                                row,
                            )
                        )
                    else:
                        tkinter.messagebox.showinfo(
                            message="".join(
                                ("A result line has been ignored.",)
                            ),
                            title="Result",
                        )
        return text

    def convert_tabular_data_to_sequence(self):
        """Convert table of data to sequence of data for an event."""
        matchgames = {}
        errors = []
        for value in self._tabular.values():
            for row in value:
                if (
                    row.teamone
                    and row.teamtwo
                    and (row.nameone or row.nametwo)
                ):
                    umkey = (row.teamone, row.teamtwo, row.result_date)
                    report = (
                        matchgames.setdefault(row.source, {})
                        .setdefault(row.competition, {})
                        .setdefault(umkey, {})
                    )
                    if row.numbers:
                        board = row.numbers[0]
                    else:
                        board = str(len(report) + 1)
                    game = report.setdefault(
                        board, (set(), set(), set(), [], set())
                    )

                    # Used in validation then discarded.
                    game[0].add(
                        (row.nameone, row.score, row.nametwo, row.colour)
                    )
                    game[1].add(row.competition_round)
                    game[2].add(row._date_played)

                    # Keep the original data.
                    game[3].append(row)

                    # Moved to match if all games say the same.
                    game[-1].add((row.teamonescore, row.teamtwoscore))

        for emailgames in matchgames.values():
            for ckey, cvalue in emailgames.items():
                mkeys = tuple(cvalue.keys())
                for mkey in mkeys:
                    mvalue = cvalue[mkey]
                    rowmatchscore = set()

                    # Allow for the table not including the match score.
                    totalscore = [0, 0]

                    for bkey, game in mvalue.items():
                        for i in game:
                            if len(i) != 1:
                                errors.append(((ckey, mkey, bkey), i))
                        for i in game[-1]:
                            rowmatchscore.add(i)
                        for i in game[0]:
                            for j, k in enumerate(
                                GAME_RESULT.get(i[1], (0, 0))
                            ):
                                totalscore[j] += k
                    if not rowmatchscore:
                        rowmatchscore = NOMATCHSCORE
                    if len(rowmatchscore) > 1:
                        totalscore = [
                            t * len(rowmatchscore) for t in totalscore
                        ]
                        errors.append(((ckey, mkey, bkey), rowmatchscore))
                    if rowmatchscore == NOMATCHSCORE or len(rowmatchscore) > 1:

                        # move match score from game details to match details.
                        totalscore = [str(t) for t in totalscore]
                        totalscore = [
                            t if t.endswith(".5") else str(int(float(t)))
                            for t in totalscore
                        ]
                        rowmatchscore = set(((totalscore[0], totalscore[1]),))

                    # Delete the validation structure.
                    cvalue[mkey + tuple(rowmatchscore)] = mvalue
                    del cvalue[mkey]
                    for bkey, game in mvalue.items():
                        mvalue[bkey] = game[-2][0]

        if errors:

            # The match card style validation will produce an error of some
            # kind if necessary, but a dialogue to indicate this will happen
            # may be helpful here.
            # Some things which are reported as errors later are not seen as
            # errors here. Change the date in one of the rows for example, so
            # all games in a match are not given the same date.
            tkinter.messagebox.showinfo(
                message="".join(
                    (
                        "An inconsistency has been found in the match results ",
                        "data extracted from a CSV file.\n\n",
                        "One or more errors will be reported but it may not be ",
                        "immediately obvious what is wrong with the CSV file ",
                        "data, or where the problems are.",
                    )
                ),
                title="Tabular Results Error",
            )

        for value in self._tabular.values():
            if len(matchgames):
                evalue = value[0]
                EventData(
                    datatag=evalue.datatag,
                    found=Found.EVENT_AND_DATES,
                    context=evalue.context,
                    startdate=evalue.startdate,
                    enddate=evalue.enddate,
                    source=evalue.source,
                    headers=evalue.headers,
                    eventname=evalue.eventname,
                )
            break

        for emailsource in sorted(matchgames):
            for ckey, cvalue in matchgames[emailsource].items():
                EventData(
                    datatag=evalue.datatag,
                    found=Found.COMPETITION_NAME,
                    context=evalue.context,
                    competition=ckey if ckey else evalue.competition,
                    source=emailsource,
                    headers=evalue.headers,
                )
                for mkey, mvalue in cvalue.items():
                    for game in mvalue.values():
                        EventData(
                            datatag=game.datatag,
                            found=Found.RESULT_NAMES,
                            context=game.context,
                            result_date=mkey[2],
                            source=emailsource,
                            headers=game.headers,
                            nameone=mkey[0],
                            nametwo=mkey[1],
                            competition=ckey if ckey else game.competition,
                            score=" ".join(mkey[-1]),
                        )
                        break
                    for bkey, game in sorted(mvalue.items()):
                        EventData(
                            datatag=game.datatag,
                            found=Found.RESULT_NAMES,
                            context=game.context,
                            result_date=game._date_played,
                            source=emailsource,
                            headers=game.headers,
                            nameone=game.nameone,
                            nametwo=game.nametwo,
                            competition=ckey if ckey else game.competition,
                            score=game.score,
                            numbers=[bkey],
                        )

    def _is_results_individual(self, results):
        """Return True if no EventData instances describe a match result."""
        for data in results:
            if data.is_match_result():
                return False
        return True

    def _print_text(self, text):
        """Print lines in text.  Intended for tracing bugs."""
        print("\n")
        for line in text:
            try:
                print(line)
            except Exception:
                print("\n>>>>>>>>")
                print("".join([c if ord(c) < 128 else "@@" for c in line]))
                print("<<<<<<<<\n")

    def _set_source(self, eventdata, source, text):
        """Emit source command if eventdata changes source and return source."""
        if eventdata.source != source:
            text.append((" ".join(("source", eventdata.source)), None))
        return eventdata.source


class _EventItems(dict):
    """Container for EventData instances of some specific category."""

    def append(self, eventdata):
        """Append eventdata to existing list at self[eventdata.competition]."""
        self[eventdata.competition].append(eventdata)

    def add_key(self, competition_name):
        """Add list() to self.__dict uder key competition_name."""
        if competition_name not in self:
            self[competition_name] = []
