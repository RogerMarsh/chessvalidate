# gameobjects.py
# Copyright 2008 Roger Marsh
# Licence: See LICENCE (BSD licence)

"""Fixture, Game, Match, and Player classes for events.

MatchFixture represents an item on a fixture list while MatchReport
represents the reported result of a match. Sometimes (cup matches for
example) a reported match may not appear on a fixture list. Thus it is
correct that MatchReport is not a subclass of MatchFixture despite the
similarity of the class definitions.

"""
import re
from collections import namedtuple

from solentware_misc.core.null import Null

from .gameresults import (
    displayresult,
    home_player_pieces,
    displayresulttag,
    resultmap,
    match_score_difference,
    match_score_total,
)
from . import constants

_GRADE_ONLY_TAG = {
    True: "grading only",
}

# Grading code is [0-9]{6}[A-M] but accept [0-9]{3} embedded in a word to allow
# for a one character typo in the grading code or a one character digit typo in
# the name.
# This also catches ECF Membership numbers, 3-digit ECF grades, and 4-digit
# ratings; although the tolerance for typing errors is less.
# Text in brackets containing a digit are treated as a code: '(UG est 170)' for
# example. The '{}', '[]', and '<>', pairs are not treated as codes at present
# because they do not survive till code_in_name is used.
code_in_name = re.compile(r"\([^0-9]*[0-9].*?\)|\s*[^\s]*[0-9]{3}[^\s]*\s*")


class GameObjectsError(Exception):
    """Exception class for gameobjects module."""


def split_codes_from_name(name_and_codes):
    """Return tuple(name, set(codes)) from name_and_codes."""
    codes = set(s.strip() for s in code_in_name.findall(name_and_codes))
    name = " ".join(
        [s.strip() for s in code_in_name.split(name_and_codes)]
    ).strip()
    return (name, codes)


class MatchFixture:
    """Detail of a fixture extracted from a fixture list file."""

    attributes = {
        "competition": None,
        "source": None,
        "round": None,
        "hometeam": None,
        "awayteam": None,
        "date": None,
        "day": None,
        "pdate": None,
        "dateok": None,
    }

    def __init__(self, tagger=None, **kargs):
        """Override, set default values for <class>.attributes not in kargs."""
        self.__dict__["tagger"] = tagger
        for attribute in kargs:
            if attribute not in self.__class__.attributes:
                raise AttributeError(attribute)
        self.__dict__.update(self.attributes)
        self.__dict__.update(kargs)

    def __eq__(self, other):
        """Return True if self[a]==other[a] for MatchFixture.attributes."""
        for attribute in MatchFixture.attributes:
            if self.__dict__[attribute] != other.__dict__[attribute]:
                return False
        return True

    def __setattr__(self, name, value):
        """Allow self[name] = value if name is in <class>.attributes."""
        if name in self.__class__.attributes:
            self.__dict__[name] = value
        else:
            raise AttributeError(name)

    def __hash__(self):
        """Return object identity as hash value."""
        return id(self)


class Game:
    """Detail of a game result extracted from event report."""

    attributes = {
        "result": None,
        "date": None,
        "homeplayerwhite": None,  # True|False|None. None means "not known"
        "homeplayer": None,  # the leftmost player in "Smith 1-0 Jones" etc
        "awayplayer": None,  # the rightmost player in "Smith 1-0 Jones" etc
        "gradegame": True,  # True|False. True means store result for grading
    }

    def __init__(self, tagger=None, **kargs):
        """Override, set default values for <class>.attributes not in kargs."""
        # SLMatchGame sets gradegame to False if homeplayer or awayplayer is
        # default.  Should that come here or should caller be responsible for
        # setting gradegame argument.  Round by round swiss results, not match
        # games, may say something like 'J Smith 1-0 default' too.
        self.__dict__["tagger"] = tagger
        for attribute in kargs:
            if attribute not in self.__class__.attributes:
                raise AttributeError(attribute)
        self.__dict__.update(self.attributes)
        self.__dict__.update(kargs)

    def __eq__(self, other):
        """Return True if self[a] == other[a] for a in Game.attributes."""
        for attribute in self.__class__.attributes:
            if self.__dict__[attribute] != other.__dict__[attribute]:
                return False
        return True

    def __ne__(self, other):
        """Return True if self[a] != other[a] for a in Game.attributes."""
        for attribute in self.__class__.attributes:
            if self.__dict__[attribute] != other.__dict__[attribute]:
                return True
        return False

    def __setattr__(self, name, value):
        """Allow self[name] = value if name is in <class>.attributes."""
        if name in self.__class__.attributes:
            self.__dict__[name] = value
        else:
            raise AttributeError(name)

    def __hash__(self):
        """Return object identity as hash value."""
        return id(self)

    @staticmethod
    def game_result_exists(result):
        """Return True if game result is allowed."""
        return result in resultmap

    def get_print_result(self):
        """Return (<printable result>, <status comment>).

        Typically returns ('', 'unfinished') where match report includes an
        unfinished game

        """
        return (
            displayresult.get(self.result, ""),
            displayresulttag.get(self.result, ""),
        )

    def is_inconsistent(self, other, problems):
        """Return True if attribute values of self and other are inconsistent.

        Used to check that duplicate reports of a game are consistent allowing
        for previously unknown detail to be added.  Such as the result of an
        unfinished game.

        """
        state = False
        if self.homeplayer.is_inconsistent(other.homeplayer, problems):
            problems.add(constants.HOME_PLAYER)
            state = True
        if self.awayplayer.is_inconsistent(other.awayplayer, problems):
            problems.add(constants.AWAY_PLAYER)
            state = True
        if self.homeplayerwhite != other.homeplayerwhite:
            if other.homeplayer:
                problems.add(constants.HOME_PLAYER_WHITE)
                state = True
        if self.result != other.result:
            if other.result:
                problems.add(constants.RESULT_DUP_REP)
                state = True
        return state

    def get_game_board_and_round(self):
        """Return tuple of ""s for game details in tabular format."""
        return ("",) * 2


class MatchGame(Game):
    """Detail of a game result extracted from a file of match reports.

    MatchGame.attributes is Game.attributes plus board

    """

    # PDLRapidplayMatchGame is not used because each game is reported in full.
    # The problem is interpreting scores like 1-1.  Is that two draws or one
    # win by each player, and who had white pieces in each game?  The result
    # '1.5-0.5' retains the white pieces question.
    # See Game for notes on SLMatchGame.

    attributes = {
        "board": None,
        "gradingonly": None,
    }
    attributes.update(Game.attributes)

    def is_inconsistent(self, other, problems):
        """Add board and gradingonly to attributes checked for consistency."""
        state = False
        if self.board != other.board:
            if other.board:
                problems.add(constants.BOARD_DUP_REP)
                state = True
        if self.gradingonly != other.gradingonly:
            problems.add(constants.GRADING_ONLY)
            state = True
        i = super().is_inconsistent(other, problems)
        return i or state

    def is_game_counted_in_match_score(self):
        """Return True if game is not 'for grading only'."""
        return not self.gradingonly

    def get_print_result(self):
        """Return (<printable result>, <status comment>).

        Typically returns ('', 'unfinished') where match report includes an
        unfinished game

        """
        return (
            displayresult.get(self.result, ""),
            displayresulttag.get(
                self.result,
                "" if self.result in displayresult else "invalid result",
            ),
            _GRADE_ONLY_TAG.get(self.gradingonly, ""),
        )

    def get_game_board_and_round(self):
        """Return tuple(self.board, ""0 for game details in tabular format."""
        return (self.board, "")


class UnfinishedGame(MatchGame):
    """Detail of a completed match game originally reported unfinished."""

    # A merge of pdlcollation.UnfinishedGame and slcollation.SLMatchGame is
    # used.  The PDL version has the right superclass but the game_result
    # method is broken.  (And much later removed because it is not used.)
    # The gameresult constant is copied from slcollation to an upper case name.
    # UnfinishedGame in slcollation is not a subclass of SLMatchGame to leave
    # out the gradingonly attribute, but that attribute has been added to Game.
    # (Also removed when game_result method removed.)

    attributes = {
        "source": None,
        "section": None,
        "competition": None,
        "hometeam": None,
        "awayteam": None,
    }
    attributes.update(MatchGame.attributes)

    def is_inconsistent(self, other, problems):
        """Extend to compare PDL attributes. Return True if inconsistent."""
        state = False
        if self.source != other.source:
            problems.add(constants.SOURCE_DUP_REP)
            state = True
        if self.section != other.section:
            problems.add(constants.SECTION)
            state = True
        if self.competition != other.competition:
            problems.add(constants.COMPETITION_DUP_REP)
            state = True
        if self.hometeam != other.hometeam:
            problems.add(constants.HOME_TEAM_NAME)
            state = True
        if self.awayteam != other.awayteam:
            problems.add(constants.AWAY_TEAM_NAME)
            state = True

        # The MatchGame notion for consistency of board may not be reliable for
        # unfinished game reports if the board has been calculated from it's
        # position in the report.
        # In other words, the problem is what we are told about the game, not
        # whether UnfinishedGame should be a subclass of MatchGame.
        # Actually the best name for this class is UnfinishedMatchGame because
        # it is possible for individual games to be unfinished.  Such games are
        # almost always not reported at all until they are finished.
        # Better would be a separate class for defaulted games, as it seems to
        # be use of UnfinishedGame for those which first caused the problem.
        if self.homeplayer.is_inconsistent(other.homeplayer, problems):
            problems.add(constants.HOME_PLAYER)
            state = True
        if self.awayplayer.is_inconsistent(other.awayplayer, problems):
            problems.add(constants.AWAY_PLAYER)
            state = True

        # Surely wrong to do this now, or in pre problems argument code.
        # if (self.homeplayerwhite == other.homeplayerwhite and
        #    self.result == other.result and
        #    self.gradingonly == other.gradingonly):
        #    return state

        for game in (self, other):
            for player in (game.homeplayer, game.awayplayer):
                if not isinstance(player, Null):
                    if self.result != other.result:
                        if other.result:
                            problems.add(constants.RESULT_DUP_REP)
                            state = True
        return state


class SwissGame(Game):
    """Detail of a game result extracted from a file of swiss reports.

    SwissGame.attributes is Game.attributes plus round

    """

    attributes = {
        "round": None,
    }
    attributes.update(Game.attributes)

    def is_inconsistent(self, other, problems):
        """Extend, add round to the attributes checked to return True."""
        state = False
        if self.round != other.round:
            if other.round:
                problems.add(constants.ROUND_DUP_REP)
                state = True
        i = super().is_inconsistent(other, problems)
        return i or state

    def get_game_board_and_round(self):
        """Return tuple("", self.round) for game details in tabular format."""
        return ("", self.round)


class SwissMatchGame(Game):
    """Detail of a game result extracted from a file of swiss match reports.

    SwissMatchGame.attributes is Game.attributes plus board and round

    """

    attributes = {
        "board": None,
        "round": None,
    }
    attributes.update(Game.attributes)

    def is_inconsistent(self, other, problems):
        """Extend, add board round to the attributes checked to return True."""
        state = False
        if self.round != other.round:
            if other.round:
                problems.add(constants.ROUND_DUP_REP)
                state = True
        if self.board != other.board:
            if other.board:
                problems.add(constants.BOARD_DUP_REP)
                state = True
        i = super().is_inconsistent(other, problems)
        return i or state

    def get_game_board_and_round(self):
        """Return tuple(self.board, self.round) for tabular format."""
        return (self.board, self.round)


class Section:
    """Detail of a result extracted from a file of event reports."""

    attributes = {
        "competition": None,
        "order": None,  # f(source) for sorting
        "source": None,  # tag to identify duplicate match reports
        "games": None,
        "date": None,
        "day": None,
        "pdate": None,
        "dateok": None,
    }

    def __init__(self, tagger=None, **kargs):
        """Override, set default values for <class>.attributes not in kargs."""
        self.__dict__["tagger"] = tagger
        for attribute in kargs:
            if attribute not in self.__class__.attributes:
                raise AttributeError(attribute)
        self.__dict__.update(self.attributes)
        self.__dict__.update(kargs)

    def __eq__(self, other):
        """Return True if self[a] == other[a] for a in Section.attributes."""
        for attribute in self.__class__.attributes:
            if self.__dict__[attribute] != other.__dict__[attribute]:
                return False
        return True

    def __ne__(self, other):
        """Return True if self[a] != other[a] for a in Section.attributes."""
        for attribute in self.__class__.attributes:
            if self.__dict__[attribute] != other.__dict__[attribute]:
                return True
        return False

    def __setattr__(self, name, value):
        """Allow self[name] = value if name is in <class>.attributes."""
        if name in self.__class__.attributes:
            self.__dict__[name] = value
        else:
            raise AttributeError(name)

    def __hash__(self):
        """Return object identity as hash value."""
        return id(self)

    def __ge__(self, other):
        """Return True if id(self) >= id(other)."""
        return id(self) >= id(other)

    def __gt__(self, other):
        """Return True if id(self) > id(other)."""
        return id(self) > id(other)

    def __le__(self, other):
        """Return True if id(self) <= id(other)."""
        return id(self) <= id(other)

    def __lt__(self, other):
        """Return True if id(self) < id(other)."""
        return id(self) < id(other)

    def get_team_details(self):
        """Return tuple of ""s for team details in tabular format."""
        return ("",) * 6


class MatchReport(Section):
    """Detail of a match result extracted from a file of match reports.

    MatchGame.attributes is Section.attributes plus round hometeam and so on

    """

    attributes = {
        "round": None,
        "hometeam": None,
        "homescore": None,
        "awayteam": None,
        "awayscore": None,
        "default": None,
    }
    attributes.update(Section.attributes)

    def get_unfinished_games_and_score_consistency(self):
        """Return (unfinished game, match and game score consistency).

        This method serves two masters: one treats an inconsistency as an error
        while the other treats it as a warning and makes use of the list of
        unfinished games in the returned tuple.

        """
        ufg = []
        difference = 0
        points = 0
        force_inconsistent = False
        for game in self.games:
            if game.result not in displayresult:
                ufg.append(game)
            if game.is_game_counted_in_match_score():
                i = match_score_difference.get(game.result)
                if i is None:
                    force_inconsistent = True
                else:
                    difference += i
                i = match_score_total.get(game.result)
                if i is None:
                    force_inconsistent = True
                else:
                    points += i
        try:
            homepoints = float(self.homescore)
        except ValueError:
            homepoints = 0
        try:
            awaypoints = float(self.awayscore)
        except ValueError:
            awaypoints = 0
        if self.default and len(ufg) == 0:
            consistent = True
        elif points != homepoints + awaypoints:
            consistent = False
        elif difference != homepoints - awaypoints:
            consistent = False
        else:
            consistent = True
        return ufg, consistent or force_inconsistent

    def get_team_details(self):
        """Return tuple of team details for tabular format."""
        return (
            self.round,
            self.hometeam,
            self.homescore,
            self.awayteam,
            self.awayscore,
            self.default,
        )


class Player:
    """A player in an event."""

    # There is a design flaw here because the attributes 'tagger', '_identity',
    # and 'reported codes', are left out of 'attributes' because they do not
    # contribute to the __eq__ and __ne__ methods.
    # These should be included for the __setattr__ and __getattr__ methods.
    attributes = {
        "name": None,
        "event": None,
        "startdate": None,
        "enddate": None,
        "section": None,  # eg. swiss tournament or league division
        "club": None,  # the club played for in league
        "pin": None,
        "affiliation": None,  # eg. club or location (ECF "club")
    }

    def __init__(self, tagger=None, reported_codes=None, **kargs):
        """Override, set default values for <class>.attributes not in kargs."""
        self.__dict__["tagger"] = tagger
        self.__dict__["reported_codes"] = reported_codes
        for attribute in kargs:
            if attribute not in self.__class__.attributes:
                raise AttributeError(attribute)
        self.__dict__.update(self.attributes)
        self.__dict__.update(kargs)
        if self.club:
            self.set_player_identity_club()
            # Comment this line to avoid pylint unused-variable report.
            # affiliation = self.club  # Should this be "self.affiliation ="?
        elif self.section:
            self.set_player_identity_section()
        else:
            self.set_player_identity()

    def __eq__(self, other):
        """Return True if self[a] == other[a] for a in Player.attributes."""
        for attribute in Player.attributes:

            # Hack because Null instance represents a defaulting player, and
            # may get compared when sorting.
            try:
                if self.__dict__[attribute] != other.__dict__[attribute]:
                    return False
            except KeyError:
                if isinstance(other, Null):
                    return False
                raise
        return True

    def __ne__(self, other):
        """Return True if self[a] != other[a] for a in Player.attributes."""
        for attribute in Player.attributes:

            # Hack because Null instance represents a defaulting player, and
            # may get compared when sorting.
            try:
                if self.__dict__[attribute] != other.__getattr__(attribute):
                    return True
            except KeyError:
                if isinstance(other, Null):
                    return False
                raise
        return False

    # introduced for compatibility with NullPlayer class
    # guardian if statement probably not needed
    def __getattr__(self, name):
        """Allow return self[name] if name is in <class>.attributes."""
        if name in self.__class__.attributes:
            return self.__dict__[name]
        raise AttributeError(name)

    def __setattr__(self, name, value):
        """Allow self[name] = value if name is in <class>.attributes."""
        if name in self.__class__.attributes:
            self.__dict__[name] = value
        else:
            raise AttributeError(name)

    def __hash__(self):
        """Return object identity as hash value."""
        return id(self)

    def get_brief_identity(self):
        """Return tuple(name, pin|club|False|None) elements of player identity.

        For use when dealing with players within a section of an event.

        """
        if self.club:
            return (self.name, self.club)
        if self.section:
            if self.pin:
                return (self.name, self.pin)
            return (self.name, False)
        return (self.name, None)

    def get_full_identity(self):
        """Return a tab separated string containing player identity."""
        if self.club:
            return "\t".join(
                (
                    self.name,
                    self.event,
                    self.startdate,
                    self.enddate,
                    self.club,
                )
            )
        if self.section:
            if self.pin:
                return "\t".join(
                    (
                        self.name,
                        self.event,
                        self.startdate,
                        self.enddate,
                        self.section,
                        str(self.pin),
                    )
                )
            return "\t".join(
                (
                    self.name,
                    self.event,
                    self.startdate,
                    self.enddate,
                    self.section,
                )
            )
        return "\t".join((self.name, self.event, self.startdate, self.enddate))

    def get_identity(self):
        """Return tuple of player identity with fillers for absent elements.

        For use as database key where known format helps a lot

        """
        if self.club:
            return (
                self.name,
                self.event,
                self.startdate,
                self.enddate,
                self.club,
                None,
            )
        if self.section:
            if self.pin:
                return (
                    self.name,
                    self.event,
                    self.startdate,
                    self.enddate,
                    self.section,
                    self.pin,
                )
            return (
                self.name,
                self.event,
                self.startdate,
                self.enddate,
                self.section,
                False,
            )
        return (
            self.name,
            self.event,
            self.startdate,
            self.enddate,
            None,
            None,
        )

    def get_player_event(self):
        """Return a tuple containing event part of player identity."""
        return (self.event, self.startdate, self.enddate)

    def get_player_identity(self):
        """Return tuple containing player identity."""
        return self._identity

    def get_player_section(self):
        """Return section part of player identity or None."""
        if self.club:
            return self.club
        if self.section:
            return self.section
        return None

    def get_short_identity(self):
        """Return tab separated string of player identity excluding event.

        Includes the section if present.

        """
        if self.club:
            return "\t\t".join((self.name, self.club))
        if self.section:
            if self.pin:
                return "".join(
                    (self.name, "\t\t", self.section, " ", str(self.pin))
                )
            return "".join((self.name, "\t\t", self.section))
        return "\t".join((self.name,))

    def is_inconsistent(self, other, problems):
        """Return True if attribute values of self and other are inconsistent.

        Used to check that duplicate reports of a game are consistent allowing
        for previously unknown detail to be added.  Such as the name of a
        player.

        """
        del problems
        # state = False
        for attribute in Player.attributes:
            if self.__dict__[attribute] != other.__dict__.get("attribute"):
                if other.__dict__.get("attribute"):

                    # Listing attribute names as problems may be too much.
                    # problems.add(attribute)

                    # state = True
                    return True
        # return state
        return False

    def add_reported_codes(self, code):
        """Add code(s) to self.reported_codes."""
        self.__dict__["reported_codes"].update(code)

    def get_reported_codes(self):
        """Return space separated string of reported codes.

        Usually a grading code, but membership numbers and grades may be
        common too.  Any element of 'name' containg a digit (0-9) will be
        treated as a code by the parser.

        """
        return " ".join(
            self.reported_codes if self.reported_codes is not None else ""
        )

    def set_player_identity(self):
        """Set player identity where club or section is not relevant."""
        self.__dict__["_identity"] = (
            self.name,
            self.event,
            self.startdate,
            self.enddate,
        )

    def set_player_identity_club(self):
        """Set player identity where club is relevant."""
        self.__dict__["_identity"] = (
            self.name,
            self.event,
            self.startdate,
            self.enddate,
            self.club,
        )

    def set_player_identity_section(self):
        """Set player identity where section is relevant."""
        self.__dict__["_identity"] = (
            self.name,
            self.event,
            self.startdate,
            self.enddate,
            self.section,
            self.pin,
        )


# GameCollation is superclass of Collation and CollationEvents, the latter used
# when importing data from another database.
class GameCollation:
    """Base class for results extracted from a file of game reports."""

    def __init__(self):
        """Define game and player dictionaries and error report list."""
        super().__init__()
        self.games = {}
        self.players = {}

    def set_games(self, key, gamelist):
        """Note gamelist in games dictionary under key."""
        self.games[key] = gamelist

    def set_player(self, player):
        """Note player in players dictionary under key if not present."""
        key = player.get_player_identity()
        if key not in self.players:
            self.players[key] = player


# The element names are in the order which gives a useful sort order.
TabularReportRow = namedtuple(
    "TabularReportRow",
    constants.TABULAR_REPORT_ROW_ORDER,
    defaults=("",) * len(constants.TABULAR_REPORT_ROW_ORDER),
)


def get_game_rows_for_csv_format(collated_games):
    """Return list of dicts representing collated games for an event.

    It is assumed sourceedit.SourceEdit._collate_unfinished_games()
    has been called if required.

    """
    rows = []

    # The event name is only available as an attribute of the Player
    # instances found.  All these instances must have the same event
    # name, except that defaulted games will produce None as the
    # event name for one or both players of a game.
    # Player represents a bundle of games reported under one name in
    # a section of an event: it does not represent the person playing
    # in an event or a game.
    # If eventname is None after processing the report either there
    # are no games or all games were double defaults.
    eventname = None

    for value in collated_games.values():
        (
            round_,
            hometeam,
            homescore,
            awayteam,
            awayscore,
            default,
        ) = value.get_team_details()
        if default:
            continue
        for game in value.games:
            if not game.gradegame:
                continue
            gameboard, gameround = game.get_game_board_and_round()
            if round_:
                if gameround and round_ != gameround:
                    raise GameObjectsError(
                        "Inconsistent round given in game and section"
                    )

            # Note re-binding of homeplayer and awayplayer in this block.
            # Allow for double default games when checking consistency of
            # event name references.
            homeplayer = game.homeplayer
            awayplayer = game.awayplayer
            if (
                homeplayer is not None
                and awayplayer is not None
                and homeplayer.event is not None
                and awayplayer.event is not None
            ):
                if homeplayer.event != awayplayer.event:
                    raise GameObjectsError(
                        "Inconsistent event names for players of game"
                    )
            game_eventname = homeplayer.event or awayplayer.event
            if eventname is None:
                eventname = game_eventname
            if (
                homeplayer.event is not None
                and awayplayer.event is not None
                and game_eventname != eventname
            ):
                raise GameObjectsError(
                    "Inconsistent event names for game in event"
                )
            if homeplayer.reported_codes is not None:
                homeplayer = " ".join(
                    (
                        " ".join(homeplayer.reported_codes),
                        homeplayer.name,
                    )
                ).strip()
            else:
                homeplayer = homeplayer.name
            if awayplayer.reported_codes is not None:
                awayplayer = " ".join(
                    (
                        awayplayer.name,
                        " ".join(awayplayer.reported_codes),
                    )
                ).strip()
            else:
                awayplayer = awayplayer.name

            # The **{} arguments are in the default order of a tabular
            # source report. (The order before conversion to namedtuple.)
            rows.append(
                TabularReportRow(
                    **{
                        constants.REPORT_SECTION: value.competition,
                        constants.REPORT_DAY: "",
                        constants.REPORT_DATE: game.date,
                        constants.REPORT_ROUND: gameround,
                        constants.REPORT_HOME_TEAM: hometeam,
                        constants.REPORT_HOME_TEAM_SCORE: homescore,
                        constants.REPORT_HOME_PLAYER: homeplayer,
                        constants.REPORT_RESULT: displayresult.get(
                            game.result, ""
                        ),
                        constants.REPORT_AWAY_PLAYER: awayplayer,
                        constants.REPORT_AWAY_TEAM_SCORE: awayscore,
                        constants.REPORT_AWAY_TEAM: awayteam,
                        constants.REPORT_BOARD: gameboard,
                        constants.REPORT_HOME_PLAYER_COLOUR: (
                            home_player_pieces[game.homeplayerwhite]
                        ),
                        constants.REPORT_EVENT: eventname,
                    }
                )
            )

    return rows
