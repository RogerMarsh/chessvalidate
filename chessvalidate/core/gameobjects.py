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

from solentware_misc.core.null import Null

from .gameresults import (
    displayresult,
    displayresulttag,
    resultmap,
    match_score_difference,
    match_score_total,
    hwin,
    awin,
    draw,
    tobereported,
    notaresult,
    tbrstring,
    HOME_PLAYER_WHITE,
    RESULT,
    BOARD,
    GRADING_ONLY,
    SOURCE,
    SECTION,
    COMPETITION,
    HOME_TEAM_NAME,
    AWAY_TEAM_NAME,
    HOME_PLAYER,
    AWAY_PLAYER,
    ROUND,
)

# May need displayresulttag constant from slcollation too.
# Probably add this to gameresults.resultmap.
_GAME_RESULT = {
    ("1", "0"): hwin,
    ("0", "1"): awin,
    ("0.5", "0.5"): draw,
    (None, None): tobereported,
}

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
code_in_name = re.compile("\([^0-9]*[0-9].*?\)|\s*[^\s]*[0-9]{3}[^\s]*\s*")


class MatchFixture(object):
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
        for a in kargs:
            if a not in self.__class__.attributes:
                raise AttributeError(a)
        self.__dict__.update(self.attributes)
        self.__dict__.update(kargs)

    def __eq__(self, other):
        """Return True if self[a]==other[a] for a in MatchFixture.attributes."""
        for a in MatchFixture.attributes:
            if self.__dict__[a] != other.__dict__[a]:
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


class Game(object):
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
        for a in kargs:
            if a not in self.__class__.attributes:
                raise AttributeError(a)
        self.__dict__.update(self.attributes)
        self.__dict__.update(kargs)

    def __eq__(self, other):
        """Return True if self[a] == other[a] for a in Game.attributes."""
        for a in self.__class__.attributes:
            if self.__dict__[a] != other.__dict__[a]:
                return False
        return True

    def __ne__(self, other):
        """Return True if self[a] != other[a] for a in Game.attributes."""
        for a in self.__class__.attributes:
            if self.__dict__[a] != other.__dict__[a]:
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
    def game_result(result):
        """Return value representing game result such as 'h' for '1-0'."""
        return resultmap.get(result, notaresult)

    @staticmethod
    def game_result_exists(result):
        """Return True if game result is allowed"""
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
            problems.add(HOME_PLAYER)
            state = True
        if self.awayplayer.is_inconsistent(other.awayplayer, problems):
            problems.add(AWAY_PLAYER)
            state = True
        if self.homeplayerwhite != other.homeplayerwhite:
            if other.homeplayer:
                problems.add(HOME_PLAYER_WHITE)
                state = True
        if self.result != other.result:
            if other.result:
                problems.add(RESULT)
                state = True
        return state


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
                problems.add(BOARD)
                state = True
        if self.gradingonly != other.gradingonly:
            problems.add(GRADING_ONLY)
            state = True
        s = super(MatchGame, self).is_inconsistent(other, problems)
        return s or state

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


class UnfinishedGame(MatchGame):
    """Detail of completed match game that was originally reported unfinished."""

    # A merge of pdlcollation.UnfinishedGame and slcollation.SLMatchGame is
    # used.  The PDL version has the right superclass but the game_result
    # method is broken.
    # The gameresult constant is copied from slcollation to an upper case name.
    # UnfinishedGame in slcollation is not a subclass of SLMatchGame to leave
    # out the gradingonly attribute, but that attribute has been added to Game.

    attributes = {
        "source": None,
        "section": None,
        "competition": None,
        "hometeam": None,
        "awayteam": None,
    }
    attributes.update(MatchGame.attributes)

    @staticmethod
    def game_result(homeplayerscore, awayplayerscore):
        """Override, return value representing result such as 'h' for '1-0'."""
        return _GAME_RESULT.get((homeplayerscore, awayplayerscore), "")

    def is_inconsistent(self, other, problems):
        """Extend to compare PDL attributes. Return True if inconsistent."""
        state = False
        if self.source != other.source:
            problems.add(SOURCE)
            state = True
        if self.section != other.section:
            problems.add(SECTION)
            state = True
        if self.competition != other.competition:
            problems.add(COMPETITION)
            state = True
        if self.hometeam != other.hometeam:
            problems.add(HOME_TEAM_NAME)
            state = True
        if self.awayteam != other.awayteam:
            problems.add(AWAY_TEAM_NAME)
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
        # be the use of UnfinishedGame for those which first caused the problem.
        if self.homeplayer.is_inconsistent(other.homeplayer, problems):
            problems.add(HOME_PLAYER)
            state = True
        if self.awayplayer.is_inconsistent(other.awayplayer, problems):
            problems.add(AWAY_PLAYER)
            state = True

        # Surely wrong to do this now, or in pre problems argument code.
        # if (self.homeplayerwhite == other.homeplayerwhite and
        #    self.result == other.result and
        #    self.gradingonly == other.gradingonly):
        #    return state

        for g in (self, other):
            for p in (g.homeplayer, g.awayplayer):
                if not isinstance(p, Null):
                    if self.result != other.result:
                        if other.result:
                            problems.add(RESULT)
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
                problems.add(ROUND)
                state = True
        s = super(SwissGame, self).is_inconsistent(other, problems)
        return s or state


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
                problems.add(ROUND)
                state = True
        if self.board != other.board:
            if other.board:
                problems.add(BOARD)
                state = True
        s = super(SwissMatchGame, self).is_inconsistent(other, problems)
        return s or state


class Section(object):
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
        for a in kargs:
            if a not in self.__class__.attributes:
                raise AttributeError(a)
        self.__dict__.update(self.attributes)
        self.__dict__.update(kargs)

    def __eq__(self, other):
        """Return True if self[a] == other[a] for a in Section.attributes."""
        for a in self.__class__.attributes:
            if self.__dict__[a] != other.__dict__[a]:
                return False
        return True

    def __ne__(self, other):
        """Return True if self[a] != other[a] for a in Section.attributes."""
        for a in self.__class__.attributes:
            if self.__dict__[a] != other.__dict__[a]:
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
                d = match_score_difference.get(game.result)
                if d is None:
                    force_inconsistent = True
                else:
                    difference += d
                p = match_score_total.get(game.result)
                if p is None:
                    force_inconsistent = True
                else:
                    points += p
        try:
            homepoints = float(self.homescore)
        except:
            homepoints = 0
        try:
            awaypoints = float(self.awayscore)
        except:
            awaypoints = 0
        if self.default and not len(ufg):
            consistent = True
        elif points != homepoints + awaypoints:
            consistent = False
        elif difference != homepoints - awaypoints:
            consistent = False
        else:
            consistent = True
        return ufg, consistent or force_inconsistent


class Player(object):
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
        for a in kargs:
            if a not in self.__class__.attributes:
                raise AttributeError(a)
        self.__dict__.update(self.attributes)
        self.__dict__.update(kargs)
        if self.club:
            self.__dict__["_identity"] = (
                self.name,
                self.event,
                self.startdate,
                self.enddate,
                self.club,
            )
            affiliation = self.club
        elif self.section:
            self.__dict__["_identity"] = (
                self.name,
                self.event,
                self.startdate,
                self.enddate,
                self.section,
                self.pin,
            )
        else:
            self.__dict__["_identity"] = (
                self.name,
                self.event,
                self.startdate,
                self.enddate,
            )

    def __eq__(self, other):
        """Return True if self[a] == other[a] for a in Player.attributes."""
        for a in Player.attributes:

            # Hack because Null instance represents a defaulting player, and
            # may get compared when sorting.
            try:
                if self.__dict__[a] != other.__dict__[a]:
                    return False
            except KeyError:
                if isinstance(other, Null):
                    return False
                raise
        return True

    def __ne__(self, other):
        """Return True if self[a] != other[a] for a in Player.attributes."""
        for a in Player.attributes:

            # Hack because Null instance represents a defaulting player, and
            # may get compared when sorting.
            try:
                if self.__dict__[a] != other.__getattr__(a):
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
        else:
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
        elif self.section:
            if self.pin:
                return (self.name, self.pin)
            else:
                return (self.name, False)
        else:
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
        elif self.section:
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
            else:
                return "\t".join(
                    (
                        self.name,
                        self.event,
                        self.startdate,
                        self.enddate,
                        self.section,
                    )
                )
        else:
            return "\t".join(
                (self.name, self.event, self.startdate, self.enddate)
            )

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
        elif self.section:
            if self.pin:
                return (
                    self.name,
                    self.event,
                    self.startdate,
                    self.enddate,
                    self.section,
                    self.pin,
                )
            else:
                return (
                    self.name,
                    self.event,
                    self.startdate,
                    self.enddate,
                    self.section,
                    False,
                )
        else:
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
        elif self.section:
            return self.section
        else:
            return None

    def get_short_identity(self):
        """Return tab separated string of player identity excluding event.

        Includes the section if present.

        """
        if self.club:
            return "\t\t".join((self.name, self.club))
        elif self.section:
            if self.pin:
                return "".join(
                    (self.name, "\t\t", self.section, " ", str(self.pin))
                )
            else:
                return "".join((self.name, "\t\t", self.section))
        else:
            return "\t".join((self.name,))

    def is_inconsistent(self, other, problems):
        """Return True if attribute values of self and other are inconsistent.

        Used to check that duplicate reports of a game are consistent allowing
        for previously unknown detail to be added.  Such as the name of a
        player.

        """
        # state = False
        for a in Player.attributes:
            if self.__dict__[a] != other.__getattr__(a):
                if other.__getattr__(a):

                    # Listing attribute names as problems may be too much.
                    # problems.add(a)

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


# GameCollation is superclass of Collation and CollationEvents, the latter used
# when importing data from another database.
class GameCollation(object):

    """Base class for results extracted from a file of game reports."""

    def __init__(self):
        """Extend, define game and player dictionaries and error report list."""
        super(GameCollation, self).__init__()
        self.games = dict()
        self.players = dict()

    def set_games(self, key, gamelist):
        """Note gamelist in games dictionary under key."""
        self.games[key] = gamelist

    def set_player(self, player):
        """Note player in players dictionary under key if not present."""
        key = player.get_player_identity()
        if key not in self.players:
            self.players[key] = player


# Collation is separate from EventCollation because it provides behaviour shared
# by EventCollation, PDLCollation, PDLCollationWeekly, and SLCollation.
# The last three are being removed.
# So this class is copied into EventCollation for modification to fit other
# changes, and will be removed eventually.
# Added later: it actually went to collation.Collation.
