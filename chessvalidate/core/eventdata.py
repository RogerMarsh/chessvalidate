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

_EVENT_IDENTITY_NONE = (None, None, None)

# These should go in .gameresults or .constants
ONENIL = "1-0"
NILONE = "0-1"
DRAW = "draw"

GAME_RESULT = {ONENIL: (1, 0), NILONE: (0, 1), DRAW: (0.5, 0.5)}
NOMATCHSCORE = frozenset((("", ""),))


class Found:
    """Enumerated data type identifiers for EventData instances."""

    EVENT_AND_DATES = -1
    POSSIBLE_EVENT_NAME = -2
    SWISS_PAIRING_CARD = -3
    APA_PLAYER_CARD = -4
    COMPETITION_GAME_DATE = -5
    COMPETITION = -6
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


class EventData(object):
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
        """ """
        self.datatag = datatag
        self.found = found
        self.raw = raw
        self.headers = headers
        for a in self.__class__._attributes:
            if a in kargs:
                self.__dict__[a] = kargs[a]
        if isinstance(context, EventContext):
            for i, h in zip(
                self.__class__._inheritable,
                (context.event_identity, context.competition),
            ):
                for a, v in zip(i, h):
                    if v is not None:
                        if a not in self.__dict__:
                            self.__dict__[a] = v
                        elif not self.__dict__[a]:
                            self.__dict__[a] = v

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
        """ """
        if not self.is_result():
            return False
        if self.score in Score.conventional_match_game_results:
            return False
        return not self.is_match_result()

    def is_match_result(self):
        """ """
        if not self.is_result():
            return False
        # if self.score in Score.conventional_match_game_results:
        #    return True
        score = []
        for s in self.score.split():
            if s == "\xbd":
                score.append(0.5)
            elif s.endswith("\xbd"):
                return True
            else:
                try:
                    score.append(float(s))
                except ValueError:
                    return False
        return sum([float(s) for s in score]) != 1

    def is_match_and_game_result(self):
        """ """
        return self.found == Found.CSV_TABULAR

    def is_result(self):
        """ """
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
        """ """
        try:
            print(self.__dict__)
        except:
            print("\n>>>>>>>>")
            for k, v in self.__dict__.items():
                try:
                    print(repr(k), repr(v))
                except:
                    print(repr(k), "not printable")
            print("<<<<<<<<\n")

    def is_match_defaulted(self):
        """ """
        if self.found == Found.RESULT:
            return self.score == Score.match_defaulted
        return False

    def is_defaulting_side_known(self):
        """ """
        if self.found == Found.RESULT:
            return self.score in Score.included_in_team_score
        return False

    def is_default_counted(self):
        """ """
        if self.found == Found.RESULT:
            return self.score == Score.default
        return False

    def is_default_not_counted(self):
        """ """
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
        """ """
        super().__init__(context=context, **kargs)
        self.context = context
        d = self.result_date
        if TableEventData.gdate.parse_date(d) == len(d):
            self._date_played = TableEventData.gdate.iso_format_date()
        else:
            self._date_played = ""

    def __eq__(self, other):
        """ """
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
        """ """
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


class EventContext(object):
    """Context for creation of an EventData instance."""

    def __init__(self):
        """ """

        # Event identity
        self._event_identity = _EVENT_IDENTITY_NONE
        self._eventname = None
        self._eventdate = None
        self._event_startdate = None
        self._event_enddate = None

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
            Found.COMPETITION: self._competition,
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
        """ """
        self._items.append(eventdata)
        return self._process.get(eventdata.found, self._exception)(eventdata)

    # Rvent identity is set once.
    # It is composed from the event's name, and start and end dates.
    # The two components, name and dates, can be set again until both are set.

    @property
    def event_identity(self):
        """ """
        return self._event_identity

    @event_identity.setter
    def event_identity(self, value):
        """ """
        if self._event_identity is not _EVENT_IDENTITY_NONE:
            return
        self._eventname, self._event_startdate, self._event_enddate = value
        self._event_identity = (
            self._eventname,
            self._event_startdate,
            self._event_enddate,
        )
        self._eventdate = (self._event_startdate, self._event_enddate)

    def set_eventname(self, value):
        """ """
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
        """ """
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
        """ """
        return (self._competition_name, self._gamedate, self._gameround)

    @competition.setter
    def competition(self, value):
        """ """
        if self._event_identity is _EVENT_IDENTITY_NONE:
            return
        self._competition_name, self._gamedate, self._gameround = value
        self._add_key()

    def set_gameround(self, value):
        """ """
        if self._competition_name is None:
            return
        self._gameround = value

    gameround = property(fset=set_gameround)

    def set_gamedate(self, value):
        """ """
        if self._competition_name is None:
            return
        self._gamedate = value

    gamedate = property(fset=set_gamedate)

    def set_competition_name(self, value):
        """ """
        if self._event_identity is _EVENT_IDENTITY_NONE:
            return
        self._competition_name = value
        self._gamedate = None
        self._gameround = None
        self._add_key()

    competition_name = property(fset=set_competition_name)

    def set_competition_name_gamedate(self, value):
        """ """
        if self._event_identity is _EVENT_IDENTITY_NONE:
            return
        self._competition_name, self._gamedate = value
        self._gameround = None
        self._add_key()

    competition_name_gamedate = property(fset=set_competition_name_gamedate)

    def set_competition_name_gameround(self, value):
        """ """
        if self._event_identity is _EVENT_IDENTITY_NONE:
            return
        self._competition_name, self._gameround = value
        self._gamedate = None
        self._add_key()

    competition_name_gameround = property(fset=set_competition_name_gameround)

    def _event_and_dates(self, eventdata):
        """ """
        self.set_eventdate((eventdata.startdate, eventdata.enddate))
        if "eventname" in eventdata.__dict__:
            self.set_eventname(eventdata.eventname)

    def _possible_event_name(self, eventdata):
        """ """
        # This is the default attempt at processing data which is not known to
        # be wrong.  Ignore unless an event name is still allowed.
        self.set_eventname(eventdata.eventname)

    def _swiss_pairing_card(self, eventdata):
        """ """
        if eventdata.competition in self._round_dates:
            self._swiss.append(self._round_dates[eventdata.competition])
            del self._round_dates[eventdata.competition]
        self._swiss.append(eventdata)

    def _apa_player_card(self, eventdata):
        """ """
        if eventdata.competition in self._round_dates:
            self._allplayall.append(self._round_dates[eventdata.competition])
            del self._round_dates[eventdata.competition]
        self._allplayall.append(eventdata)

    # *_game_* rather than *_result_* to imply game, not match, lines follow.
    def _competition_game_date(self, eventdata):
        """ """
        self.set_competition_name_gamedate(
            (eventdata.competition, eventdata.result_date)
        )

    def _competition(self, eventdata):
        """ """
        self.set_competition_name(eventdata.competition)

    def _competition_round(self, eventdata):
        """ """
        self.set_competition_name_gameround(
            (eventdata.competition, eventdata.competition_round)
        )

    def _round_header(self, eventdata):
        """ """
        self.set_gamedate(eventdata.competition_round)

    # *_game_* rather than *_result_* to imply game, not match, lines follow.
    def _competition_round_game_date(self, eventdata):
        """ """
        self.competition = (
            eventdata.competition,
            eventdata.result_date,
            eventdata.competition_round,
        )

    def _fixture_teams(self, eventdata):
        """A fixture is always accepted when event_identity is not None.

        The two teams are known.

        """
        if eventdata.competition in self._round_dates:
            self._fixtures.append(self._round_dates[eventdata.competition])
            del self._round_dates[eventdata.competition]
        self._fixtures.append(eventdata)

    def _fixture(self, eventdata):
        """A fixture is always accepted when event_identity is not None.

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
        """ """
        self.set_gamedate(eventdata.result_date)

    # Method named to imply games and matches cannot always be distinguished.
    def _result_names(self, eventdata):
        """ """
        if "competition" in eventdata.__dict__:
            self._results.add_key(eventdata.competition)
            self._results.append(eventdata)

    # Method named to imply games and matches cannot always be distinguished.
    def _result(self, eventdata):
        """ """
        if "competition" in eventdata.__dict__:
            self._results.add_key(eventdata.competition)
            self._results.append(eventdata)

    def _swiss_fixture_apa_round_dates(self, eventdata):
        """ """
        if eventdata.competition in self._round_dates:
            # Competition has round dates awaiting result data to choose type.
            return
        self.set_competition_name(eventdata.competition)
        for e in (self._swiss, self._fixtures, self._allplayall):
            for ed in e[eventdata.competition]:
                if ed.found is Found.COMPETITION_AND_DATES:
                    break
            else:
                e.append(eventdata)
                break
        else:
            self._round_dates[eventdata.competition] = eventdata

    def _csv_tabular(self, eventdata):
        """ """
        if eventdata.competition not in self._tabular:
            self._tabular.add_key(eventdata.competition)
        self._tabular.append(eventdata)

    def _ignore(self, eventdata):
        """ """

    def _exception(self, eventdata):
        """ """
        # self._players
        # self._print(eventdata)

    def _print(self, eventdata):
        """ """
        eventdata._print()

    def _add_key(self):
        """ """
        if self._competition_name:
            for e in (
                self._allplayall,
                self._swiss,
                self._fixtures,
                self._results,
                self._players,
                self._tabular,
            ):
                e.add_key(self._competition_name)

    def fixture_list_names(self, team_name_lookup, truncate=None):
        """ """
        for k, v in self._fixtures.items():
            names, truncate = get_names_from_joined_names(
                v, ("teams", "teamone", "teamtwo"), truncate
            )
            sr = self._fixtures[k]
            for nk, nv in names.items():
                if "teams" in sr[nk].__dict__:
                    sr[nk].__dict__.update(nv)
                    del sr[nk].teams
            if team_name_lookup:
                team_name_lookup = {
                    k.lower(): v for k, v in team_name_lookup.items()
                }
                for fixture in sr:
                    fixture.teamone = team_name_lookup.get(
                        fixture.teamone.lower(), fixture.teamone
                    )
                    fixture.teamtwo = team_name_lookup.get(
                        fixture.teamtwo.lower(), fixture.teamtwo
                    )
        return truncate

    def results_names(self, truncate=None):
        """ """
        for k, v in self._results.items():
            names, truncate = get_names_from_joined_names(
                v, ("names", "nameone", "nametwo"), truncate
            )
            sr = self._results[k]
            for nk, nv in names.items():
                if "names" in sr[nk].__dict__:
                    sr[nk].__dict__.update(nv)
                    del sr[nk].names
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
    name, nameone, nametwo = attrnames
    homename = set()
    awayname = set()
    nameset = {}
    for ed, eventdata in enumerate(joined_names):
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
        nameset[ed] = n = names.Names(
            string=" ".join([" ".join(c) for c in concat])
        )
        for h, a in n.namepairs:
            homename.add(h)
            awayname.add(a)
    splitnames = {}
    consistent = set()
    guesses = {}
    allnames = homename.intersection(awayname)
    for k, v in nameset.items():
        v.namepairs = tuple(
            [(h, a) for h, a in v.namepairs if h in allnames and a in allnames]
        )
        try:
            sn = {}
            sn[nameone] = v.namepairs[-1][0]
            sn[nametwo] = v.namepairs[-1][-1]
            consistent.add(sn[nameone])
            consistent.add(sn[nametwo])
            splitnames[k] = sn
        except:
            v.guess_names_from_known_names(allnames)
            guesses[k] = {
                nameone: v.namepairs[-1][0],
                nametwo: v.namepairs[-1][-1],
            }
    del allnames, homename, awayname
    prevlenguesses = 0
    while len(guesses) != prevlenguesses:
        prevlenguesses = len(guesses)
        stillguesses = {}
        while guesses:
            k, v = guesses.popitem()
            awaywords = " ".join((v[nameone], v[nametwo])).split()
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
                stillguesses[k] = v
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
        t = [t for t in text.split(sep=" ") if len(t)]
        if t[0].lower() in {
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
            t[0] = "".join((t[0][0], t[0]))
            return " ".join(t)
        return text

    @staticmethod
    def translate_score(result):
        """Translate score of result to style understood by report module."""
        score = AdaptEventContext.adapted_scores.get(result.score)
        if score:
            return score
        score = []
        for s in result.score.split():
            if s == "\xbd":
                score.append("0.5")
            elif s.endswith("\xbd"):
                score.append("".join((s[:-1], ".5")))
            else:
                try:
                    float(s)
                except ValueError:
                    return result.score
                score.append(s)
        if sum([float(s) for s in score]) == 1:
            score = "-".join(score)
            if score == "0.5-0.5":
                return "draw"
            return score
        else:
            return "-".join(score)

    gdate = utilities.AppSysDate()

    @staticmethod
    def mangle_date(board, date):
        """Mangle date if board not given so board is not taken from date.

        Convert date to ISO format or replace spaces in date by '-'.

        """
        if board:
            return date
        if len(date.split()) == 1:
            return date
        if AdaptEventContext.gdate.parse_date(date) == len(date):
            return AdaptEventContext.gdate.iso_format_date()
        return "-".join(date.split())

    @staticmethod
    def game_text(game_result):
        """Return game result text for player name convention.

        If the lower-case version of either player name is exactly 'default'
        the game is assumed to have been defaulted by one or both players; and
        neither player name is relevant to subsequent processing because the
        goal is grading the result.

        """
        board = game_result.__dict__.get("numbers", ("",))[0]
        for n in (
            game_result.nameone,
            game_result.nametwo,
        ):
            if n.lower() == "default":
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
        elif game_result.nameone.lower() == "default":
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
        else:
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
        """ """
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
            if not len(results):
                continue
            text.append((" ".join(("allplayall", competition)), None))
            for r in results:
                if r.found is Found.COMPETITION_AND_DATES:
                    for e, d in enumerate(r.rounddates):
                        text.append((" ".join((str(e + 1), d)), r))
                    break
            for r in results:
                if r.found is Found.APA_PLAYER_CARD:
                    # No mechanism for an affiliation ('\t' separated).
                    # May add a 'grading code or ECF membership number' hint.
                    text.append((" ".join((r.pin, r.person)), r))

        for competition, results in self._swiss.items():
            if not len(results):
                continue
            text.append((" ".join(("swiss", competition)), None))
            for r in results:
                if r.found is Found.COMPETITION_AND_DATES:
                    for e, d in enumerate(r.rounddates):
                        text.append((" ".join((str(e + 1), d)), r))
                    break
            for r in results:
                if r.found is Found.SWISS_PAIRING_CARD:
                    # No mechanism for an affiliation ('\t' separated).
                    # May add a 'grading code or ECF membership number' hint.
                    text.append((" ".join((r.pin, r.person)), r))

        for competition, results in self._results.items():
            if not len(results):
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
            if not len(fixtures):
                continue
            for f in fixtures:
                if f.found in (Found.FIXTURE_TEAMS, Found.FIXTURE):
                    if not fixture_list_found:
                        text.append(("fixturelist", f))
                        fixture_list_found = True

                    day = f.fixture_day
                    if not day:

                        # Report class expects day to be provided, even if the
                        # source did not quote one.
                        if gdate.parse_date(f.fixture_date) != -1:
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
                                    f.fixture_date,
                                    competition,
                                    f.teamone.title(),
                                    f.teamtwo.title(),
                                )
                            ),
                            f,
                        )
                    )

        return text

    def get_results_text(self):
        """ """
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
            if not len(results):
                continue
            text.append((" ".join(("allplayall", competition)), None))
            for r in results:
                if r.found is Found.APA_PLAYER_CARD:
                    source = self._set_source(r, source, text)

                    # Report class does accept (pin, person, allplayall) as
                    # well, but not the affiliation accepted by Schedule.
                    text.append(
                        (
                            " ".join(
                                (
                                    r.pin,
                                    " ".join(
                                        [
                                            "x" if t == "*" else t
                                            for t in r.allplayall
                                        ]
                                    ),
                                )
                            ),
                            r,
                        )
                    )

        for competition, results in self._swiss.items():
            if not len(results):
                continue
            text.append((" ".join(("swiss", competition)), None))
            for r in results:
                if r.found is Found.SWISS_PAIRING_CARD:
                    source = self._set_source(r, source, text)

                    # Report class does accept (pin, person, swiss) as well,
                    # but not the affiliation accepted by Schedule.
                    text.append(
                        (
                            " ".join(
                                (
                                    r.pin,
                                    " ".join(
                                        [
                                            "x" if t == "*" else t
                                            for t in r.swiss
                                        ]
                                    ),
                                )
                            ),
                            r,
                        )
                    )

        for competition, results in self._results.items():
            if not len(results):
                continue
            if self._is_results_individual(results):
                text.append((" ".join(("individual", competition)), None))
                for r in results:
                    source = self._set_source(r, source, text)
                    text.append(
                        (
                            AdaptEventContext.mangle(
                                " ".join(
                                    (
                                        r.__dict__.get("result_date", ""),
                                        r.__dict__.get("nameone", ""),
                                        AdaptEventContext.translate_score(r),
                                        r.__dict__.get("nametwo", ""),
                                    )
                                )
                            ),
                            r,
                        )
                    )
            else:
                text.append((" ".join(("fixturelist", competition)), None))

                # Hack colour rule for boards in matches
                text.append(("blackonodd", None))

                for r in results:
                    if r.is_game_result():
                        source = self._set_source(r, source, text)
                        text.append(AdaptEventContext.game_text(r))
                    elif r.is_match_result():
                        source = self._set_source(r, source, text)
                        # Should this be looking at numbers like for board?
                        round_ = r.__dict__.get("competition_round", "")
                        if round_:
                            text.append((" ".join(("round", round_)), r))
                        date = r.__dict__.get("result_date", "")
                        if date:
                            text.append((" ".join(("date", date)), r))
                        played_on = r.__dict__.get("played_on", "")
                        if played_on:
                            text.append((played_on, r))
                        text.append(
                            (
                                AdaptEventContext.mangle(
                                    " ".join(
                                        (
                                            r.nameone.title(),
                                            AdaptEventContext.translate_score(
                                                r
                                            ),
                                            r.nametwo.title(),
                                        )
                                    )
                                ),
                                r,
                            )
                        )
                    elif r.is_match_and_game_result():
                        tkinter.messagebox.showinfo(
                            message="".join(
                                (
                                    "A tabular natch or game line is not ",
                                    "processed.",
                                )
                            ),
                            title="Match and Game Result",
                        )
                    elif r.is_match_defaulted():
                        text.append(
                            (
                                AdaptEventContext.mangle(
                                    " ".join(
                                        (
                                            "matchdefaulted",
                                            AdaptEventContext.mangle_date(
                                                "",
                                                r.__dict__.get(
                                                    "result_date", ""
                                                ),
                                            ),
                                        )
                                    )
                                ),
                                r,
                            )
                        )
                    elif r.is_defaulting_side_known():
                        source = self._set_source(r, source, text)
                        board = r.__dict__.get("numbers", ("",))[0]
                        score = AdaptEventContext.translate_score(r)
                        text.append(
                            (
                                AdaptEventContext.mangle(
                                    " ".join(
                                        (
                                            board,
                                            AdaptEventContext.mangle_date(
                                                board,
                                                r.__dict__.get(
                                                    "result_date", ""
                                                ),
                                            ),
                                            score,
                                        )
                                    )
                                ),
                                r,
                            )
                        )
                    elif r.is_default_counted():
                        source = self._set_source(r, source, text)
                        board = r.__dict__.get("numbers", ("",))[0]
                        text.append(
                            (
                                AdaptEventContext.mangle(
                                    " ".join(
                                        (
                                            board,
                                            AdaptEventContext.mangle_date(
                                                board,
                                                r.__dict__.get(
                                                    "result_date", ""
                                                ),
                                            ),
                                            "default",
                                        )
                                    )
                                ),
                                r,
                            )
                        )
                    elif r.is_default_not_counted():
                        source = self._set_source(r, source, text)
                        board = r.__dict__.get("numbers", ("",))[0]
                        text.append(
                            (
                                AdaptEventContext.mangle(
                                    " ".join(
                                        (
                                            board,
                                            AdaptEventContext.mangle_date(
                                                board,
                                                r.__dict__.get(
                                                    "result_date", ""
                                                ),
                                            ),
                                            "void",
                                        )
                                    )
                                ),
                                r,
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
        for k, v in self._tabular.items():
            for r in v:
                if r.teamone and r.teamtwo and (r.nameone or r.nametwo):
                    umkey = (r.teamone, r.teamtwo, r.result_date)
                    if r.numbers:
                        board = r.numbers[0]
                    else:
                        board = str(len(report) + 1)
                    game = (
                        matchgames.setdefault(r.source, {})
                        .setdefault(r.competition, {})
                        .setdefault(umkey, {})
                        .setdefault(board, (set(), set(), set(), [], set()))
                    )

                    # Used in validation then discarded.
                    game[0].add((r.nameone, r.score, r.nametwo, r.colour))
                    game[1].add(r.competition_round)
                    game[2].add(r._date_played)

                    # Keep the original data.
                    game[3].append(r)

                    # Moved to match if all games say the same.
                    game[-1].add((r.teamonescore, r.teamtwoscore))

        for emailgames in matchgames.values():
            for kc, vc in emailgames.items():
                mkeys = tuple(vc.keys())
                for km in mkeys:
                    vm = vc[km]
                    rowmatchscore = set()

                    # Allow for the table not including the match score.
                    totalscore = [0, 0]

                    for kb, g in vm.items():
                        for s in g:
                            if len(s) != 1:
                                errors.append(((kc, km, kb), s))
                        for e in g[-1]:
                            rowmatchscore.add(e)
                        for r in g[0]:
                            for e, s in enumerate(
                                GAME_RESULT.get(r[1], (0, 0))
                            ):
                                totalscore[e] += s
                    if not rowmatchscore:
                        rowmatchscore = NOMATCHSCORE
                    if len(rowmatchscore) > 1:
                        totalscore = [
                            t * len(rowmatchscore) for t in totalscore
                        ]
                        errors.append(((kc, km, kb), rowmatchscore))
                    if rowmatchscore == NOMATCHSCORE or len(rowmatchscore) > 1:

                        # move match score from game details to match details.
                        totalscore = [str(t) for t in totalscore]
                        totalscore = [
                            t if t.endswith(".5") else str(int(float(t)))
                            for t in totalscore
                        ]
                        rowmatchscore = set(((totalscore[0], totalscore[1]),))

                    # Delete the validation structure.
                    vc[km + tuple(rowmatchscore)] = vm
                    del vc[km]
                    for kb, g in vm.items():
                        vm[kb] = g[-2][0]

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

        for v in self._tabular.values():
            if len(matchgames):
                ev = v[0]
                EventData(
                    datatag=ev.datatag,
                    found=Found.EVENT_AND_DATES,
                    context=ev.context,
                    startdate=ev.startdate,
                    enddate=ev.enddate,
                    source=ev.source,
                    headers=ev.headers,
                    eventname=ev.eventname,
                )
            break

        for emailsource in sorted(matchgames):
            for kc, vc in matchgames[emailsource].items():
                EventData(
                    datatag=ev.datatag,
                    found=Found.COMPETITION,
                    context=ev.context,
                    competition=kc if kc else ev.competition,
                    source=emailsource,
                    headers=ev.headers,
                )
                for km, vm in vc.items():
                    for g in vm.values():
                        EventData(
                            datatag=g.datatag,
                            found=Found.RESULT_NAMES,
                            context=g.context,
                            result_date=km[2],
                            source=emailsource,
                            headers=g.headers,
                            nameone=km[0],
                            nametwo=km[1],
                            competition=kc if kc else g.competition,
                            score=" ".join(km[-1]),
                        )
                        break
                    for kb, g in sorted(vm.items()):
                        EventData(
                            datatag=g.datatag,
                            found=Found.RESULT_NAMES,
                            context=g.context,
                            result_date=g._date_played,
                            source=emailsource,
                            headers=g.headers,
                            nameone=g.nameone,
                            nametwo=g.nametwo,
                            competition=kc if kc else g.competition,
                            score=g.score,
                            numbers=[kb],
                        )

    def _is_results_individual(self, results):
        """Return True if no EventData instances describe a match result."""
        for r in results:
            if r.is_match_result():
                return False
        return True

    def _print_text(self, text):
        """ """
        print("\n")
        for t in text:
            try:
                print(t)
            except:
                print("\n>>>>>>>>")
                print("".join([c if ord(c) < 128 else "@@" for c in t]))
                print("<<<<<<<<\n")

    def _set_source(self, eventdata, source, text):
        """Emit source command if eventdata changes source and return source."""
        if eventdata.source != source:
            text.append((" ".join(("source", eventdata.source)), None))
        return eventdata.source


class _EventItems(dict):
    """Container for EventData instances of some specific category."""

    def append(self, eventdata):
        """ """
        self[eventdata.competition].append(eventdata)

    def add_key(self, competition_name):
        """ """
        if competition_name not in self:
            self[competition_name] = []
