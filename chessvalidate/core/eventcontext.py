# eventcontext.py
# Copyright 2014 Roger Marsh
# Licence: See LICENCE (BSD licence)

"""Collect a sequence of EventData instances for game results.

An EventContext holds the event identity for game results described in
EventData instances.  The event identity is expected to be given in a
configuration file, but the identity can still be taken from the data
stream.

Game result data is collected by type: all play all, swiss, fixtures,
results, players, round dates, and tabular.

"""
import tkinter.messagebox

from . import names
from .found import Found

_EVENT_IDENTITY_NONE = (None, None, None)


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


class _EventItems(dict):
    """Container for EventData instances of some specific category."""

    def append(self, eventdata):
        """Append eventdata to existing list at self[eventdata.competition]."""
        self[eventdata.competition].append(eventdata)

    def add_key(self, competition_name):
        """Add list() to self.__dict uder key competition_name."""
        if competition_name not in self:
            self[competition_name] = []
