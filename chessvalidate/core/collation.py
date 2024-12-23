# collation.py
# Copyright 2008 Roger Marsh
# Licence: See LICENCE (BSD licence)

"""Class to reconcile event schedule (fixture list) with reported results."""

import collections
from time import gmtime, mktime

from solentware_misc.core.utilities import AppSysPersonName

from .gameobjects import (
    GameCollation,
    Section,
    SwissGame,
    MatchFixture,
    MatchGame,
)
from . import constants

invert_score = {"-": "+", "=": "=", "+": "-", "1": "0", "0": "1"}
map_score = {
    "+": constants.HWIN,
    "=": constants.DRAW,
    "-": constants.AWIN,
    "1": constants.HWIN,
    "0": constants.AWIN,
}
homeplayercolour = {"w": True, "b": False}


class Collation(GameCollation):
    """Results extracted from a generic event report."""

    def __init__(self, reports, fixtures):
        """Initialise collation data."""
        super().__init__()

        self.reports = reports
        self.schedule = fixtures
        self.report_order = []  # merge report orders for schedule and results
        self.section_type = {}  # merge section types as well
        self._league_found = False

        # moved from Collation
        self.matches = {}
        self.teamplayers = {}
        self.clubplayers = {}
        self.matchesxref = {}
        self.fixturesnotplayed = []

        # moved from PDLCollationWeekly, PDLCollation, and SLCollation
        # PDLCollationWeekly has attribute unfinishedgames, but possibly only
        # because it does not have the reports attribute. (Maybe reports is
        # too wide here?)

        # Results of adjourned and adjudicated games reported later.
        self.finishedgames = {}
        # map games to unfinished games
        self.gamesxref = {}

        sectiontypes = {
            "allplayall": self._collate_allplayall,  # individuals
            "league": self._collate_league,  # team all play all
            "swiss": self._collate_swiss,  # individuals
            "fixturelist": self._collate_league,  # matches from fixture list
            "individual": self._collate_individual,  # games between players
        }

        for section in reports.er_report_order:
            process = sectiontypes.get(
                reports.er_section[section], self._section_type_unknown
            )
            if not isinstance(process, collections.abc.Callable):
                process = self._collate_not_implemented
            process(section)
            self.section_type[section] = reports.er_section[section]
            self.report_order.append(section)
        if self._league_found:
            self.collate_matches()
            self.collate_unfinished_games()
            self.collate_players()
        for section in fixtures.es_report_order:
            if section not in self.section_type:
                self.section_type[section] = fixtures.es_section[section]
                self.report_order.append(section)

    def _collate_allplayall(self, section):

        error = False
        if section not in self.schedule.es_players:
            self.reports.error.append(
                (
                    " ".join(
                        (
                            "Section",
                            section,
                            "has no information in schedule about",
                            'player "pins" and "clubs"',
                        )
                    ),
                    self.reports,
                )
            )
            error = True
        if section not in self.reports.er_swiss_table:
            self.reports.error.append(
                (
                    " ".join(
                        (
                            "Section",
                            section,
                            "has no cross table of results in reports",
                        )
                    ),
                    self.reports,
                )
            )
            error = True
        if error:
            return
        for pin in self.reports.er_swiss_table[section]:
            if pin not in self.reports.er_pins[section]:
                if pin not in self.schedule.es_pins[section]:
                    self.reports.error.append(
                        (
                            "".join(
                                (
                                    "Section ",
                                    section,
                                    " has no player name for PIN ",
                                    str(pin),
                                )
                            ),
                            self.reports,
                        )
                    )
                    error = True
                    continue
        if len(self.schedule.es_players[section]):
            for ppin, player in self.reports.er_pins[section].items():
                if ppin not in self.schedule.es_pins[section]:
                    self.reports.error.append(
                        (
                            "".join(
                                (
                                    "Section ",
                                    section,
                                    " has no information in schedule ",
                                    "for name ",
                                    player,
                                    " (PIN ",
                                    str(ppin),
                                    ")",
                                )
                            ),
                            self.reports,
                        )
                    )
                    error = True
                    continue
                if player != self.schedule.es_pins[section][ppin]:
                    self.reports.error.append(
                        (
                            "".join(
                                (
                                    "Section ",
                                    section,
                                    " has no information in schedule ",
                                    'for name "',
                                    player,
                                    " (PIN ",
                                    str(ppin),
                                    " matches on name ",
                                    self.schedule.es_pins[section][ppin],
                                    ")",
                                )
                            ),
                            self.reports,
                        )
                    )
                    error = True
                    continue
        for pin in self.schedule.es_pins[section]:
            if pin not in self.reports.er_swiss_table[section]:
                self.reports.error.append(
                    (
                        "".join(
                            (
                                "Section ",
                                section,
                                " has no results in report for name ",
                                self.schedule.es_pins[section][pin],
                                " (PIN ",
                                str(pin),
                                ")",
                            )
                        ),
                        self.reports,
                    )
                )
                error = True
                continue
        if error:
            return

        round_dates = {}
        for i in range(1, len(self.reports.er_swiss_table[section]) + 1):
            if i in self.schedule.es_round_dates[section]:
                round_dates[i] = self.schedule.es_round_dates[section][i]
            else:
                round_dates[i] = self.schedule.es_startdate
        games = []
        for pin in self.reports.er_swiss_table[section]:
            card = self.reports.er_swiss_table[section][pin]
            opponent = 0
            for game in card:
                opponent += 1
                if game["nominal_round"]:
                    if game["score"] not in map_score:
                        continue
                    colour = game["colour"]
                    if opponent > pin:
                        if colour == "b":
                            games.append(
                                (
                                    game["nominal_round"],
                                    pin,
                                    opponent,
                                    opponent,
                                    pin,
                                    map_score[invert_score[game["score"]]],
                                    colour,
                                    game["tagger"],
                                )
                            )
                        else:
                            games.append(
                                (
                                    game["nominal_round"],
                                    pin,
                                    opponent,
                                    pin,
                                    opponent,
                                    map_score[game["score"]],
                                    colour,
                                    game["tagger"],
                                )
                            )
        games.sort()
        sectiongames = Section(competition=section, games=[])
        es_pins = self.schedule.es_pins[section]
        es_players = self.schedule.es_players[section]
        for game in games:
            homeplayer = es_players[(es_pins[game[3]], game[3])]
            awayplayer = es_players[(es_pins[game[4]], game[4])]
            sectiongames.games.append(
                SwissGame(
                    tagger=game[7],
                    # Hack round for wallcharts and swiss tournaments
                    # presented in an all-play-all format, because the
                    # deduced round is wrong or irrelevant.
                    # round=str(game[0]),
                    result=game[5],
                    date=round_dates[game[0]],
                    homeplayerwhite=homeplayercolour.get(game[6]),
                    homeplayer=homeplayer,  # should be Player instance now.
                    awayplayer=awayplayer,
                )
            )  # should be the Player instance now.
            self.set_player(homeplayer)  # use existing
            self.set_player(awayplayer)  # Player instances.
        self.set_games(section, sectiongames)

    def _collate_individual(self, section):

        error = False
        if section not in self.reports.er_results:
            self.reports.error.append(
                (
                    " ".join(
                        ("Section", section, "has no results in reports")
                    ),
                    self.reports,
                )
            )
            error = True
        if error:
            return
        sectiongames = self.reports.er_results[section]
        for game in sectiongames.games:
            for player in (
                game.homeplayer,
                game.awayplayer,
            ):
                if (
                    player.event is None
                    or player.startdate is None
                    or player.enddate is None
                ):
                    self.schedule.add_event_to_player(player)

                    # The default pin=None is surely fine but False is what pin
                    # becomes in earlier versions and it does not happen here
                    # unless set so.
                    player.pin = False

            if game.date is None:
                game.date = self.schedule.es_startdate
            self.set_player(game.homeplayer)
            self.set_player(game.awayplayer)
        self.set_games(section, sectiongames)

    def _collate_league(self, section):
        del section

        # Set flag to call self.collate_matches and self.collate_players once
        # for this Generate call
        self._league_found = True

    def _collate_not_implemented(self, section):

        self.reports.error.append(("", self.reports))
        self.reports.error.append(
            (
                " ".join(("Support for", section, "format not implemented")),
                self.reports,
            )
        )
        self.reports.error.append(("", self.reports))

    def _collate_swiss(self, section):

        error = False
        if section not in self.schedule.es_players:
            self.reports.error.append(
                (
                    " ".join(
                        (
                            "Section",
                            section,
                            "has no information in schedule about",
                            'player "pins" and "clubs"',
                        )
                    ),
                    self.reports,
                )
            )
            error = True
        if section not in self.reports.er_swiss_table:
            self.reports.error.append(
                (
                    " ".join(
                        (
                            "Section",
                            section,
                            "has no swiss table of results in reports",
                        )
                    ),
                    self.reports,
                )
            )
            error = True
        if error:
            return
        for pin in self.reports.er_swiss_table[section]:
            if pin not in self.schedule.es_pins[section]:
                self.reports.error.append(
                    (
                        " ".join(
                            (
                                "Section",
                                section,
                                "has no information in schedule about pin",
                                str(pin),
                            )
                        ),
                        self.reports,
                    )
                )
                error = True
                continue
            name = self.schedule.es_pins[section][pin]
            if (name, pin) not in self.schedule.es_players[section]:
                self.reports.error.append(
                    (
                        " ".join(
                            (
                                "Section",
                                section,
                                "has no information in schedule about pin",
                                str(pin),
                                "player",
                                name,
                            )
                        ),
                        self.reports,
                    )
                )
                error = True
                continue
        for pin in self.schedule.es_pins[section]:
            if pin not in self.reports.er_swiss_table[section]:
                name = self.schedule.es_pins[section][pin]
                self.reports.error.append(
                    (
                        " ".join(
                            (
                                "Section",
                                section,
                                "has no results in report about pin",
                                str(pin),
                                "player",
                                name,
                            )
                        ),
                        self.reports,
                    )
                )
                error = True
                continue
        if error:
            return

        round_dates = {}
        for i in range(1, len(self.reports.er_swiss_table[section]) + 1):
            if i in self.schedule.es_round_dates[section]:
                round_dates[i] = self.schedule.es_round_dates[section][i]
            else:
                round_dates[i] = self.schedule.es_startdate
        games = []
        for pin in self.reports.er_swiss_table[section]:
            card = self.reports.er_swiss_table[section][pin]
            round_ = 0
            for game in card:
                round_ += 1
                opponent = game["opponent"]
                if opponent:
                    colour = game["colour"]
                    if opponent > pin:
                        if colour == "b":
                            games.append(
                                (
                                    round_,
                                    pin,
                                    opponent,
                                    opponent,
                                    pin,
                                    map_score[invert_score[game["score"]]],
                                    game["tagger"],
                                )
                            )
                        else:
                            games.append(
                                (
                                    round_,
                                    pin,
                                    opponent,
                                    pin,
                                    opponent,
                                    map_score[game["score"]],
                                    game["tagger"],
                                )
                            )
        games.sort()
        sectiongames = Section(competition=section, games=[])
        es_pins = self.schedule.es_pins[section]
        es_players = self.schedule.es_players[section]
        for game in games:
            homeplayer = es_players[(es_pins[game[3]], game[3])]
            awayplayer = es_players[(es_pins[game[4]], game[4])]
            sectiongames.games.append(
                SwissGame(
                    tagger=game[6],
                    round=str(game[0]),
                    result=game[5],
                    date=round_dates[game[0]],
                    homeplayerwhite=True,
                    homeplayer=homeplayer,  # should be the Player instance now
                    awayplayer=awayplayer,
                )
            )  # should be the Player instance now
            self.set_player(homeplayer)  # use existing
            self.set_player(awayplayer)  # Player instances
        self.set_games(section, sectiongames)

    def _section_type_unknown(self, section):

        self.reports.error.append(("", self.reports))
        self.reports.error.append(
            (" ".join((section, "type not known")), self.reports)
        )
        self.reports.error.append(("", self.reports))

    # collate_unfinished_games copied from slcollation.
    # The pdlcollation version is functionally identical, and almost identical
    # by character, differing only in one attribute name.

    def collate_unfinished_games(self):
        """Collate games played but reported unfinished."""

        def nullstring(string):
            if isinstance(string, str):
                return string
            return ""

        self.finishedgames.clear()
        self.gamesxref.clear()
        unique_game = self.finishedgames
        for game in self.reports.er_unfinishedgames:
            if game.section not in unique_game:
                unique_game[game.section] = {}

            # board is not included because it may have been calculated from
            # the position of the game in the report, and different reports
            # may have different numbers of games in different orders.
            ugkey = (
                game.hometeam,
                game.awayteam,
                game.homeplayer,
                game.awayplayer,
                game.source,
            )
            if ugkey not in unique_game[game.section]:
                unique_game[game.section][ugkey] = [game]
            else:
                unique_game[game.section][ugkey].append(game)

        for ugvalue in unique_game.values():
            for key in ugvalue:
                ugsu = ugvalue[key]
                mrg = ugsu[-1]
                game_problems = {}
                inconsistent_report = None
                for prevreport in ugsu[:-1]:
                    problems = set()
                    if mrg.is_inconsistent(prevreport, problems):
                        game_problems.setdefault(mrg, set()).update(problems)
                        inconsistent_report = prevreport

                if not game_problems:
                    self.gamesxref[mrg] = None
                    if mrg.section in self.matches:
                        for umkey in self.matches[mrg.section]:
                            if (
                                umkey[0] != mrg.hometeam
                                or umkey[1] != mrg.awayteam
                            ):
                                continue
                            match = self.matches[mrg.section][umkey][-1]
                            done = False
                            for game in match.games:
                                if game.result != constants.TOBEREPORTED:
                                    continue
                                if (
                                    game.homeplayer != mrg.homeplayer
                                    or game.awayplayer != mrg.awayplayer
                                ):
                                    continue
                                if game not in self.gamesxref:
                                    self.gamesxref[game] = mrg
                                    self.gamesxref[mrg] = game
                                    done = True
                                    break
                                self.gamesxref[mrg] = False
                            if done:
                                break
                else:
                    sect = []
                    if isinstance(mrg.section, (str, bytes)):
                        sect.append(mrg.section)
                    else:
                        for sitem in mrg.section:
                            sect.append(sitem)
                    self.reports.error.append(
                        (
                            " ".join(
                                (
                                    "Inconsistent reports for",
                                    " ".join(sect),
                                    "game.",
                                )
                            ),
                            self.reports,
                        )
                    )
                    mrg.tagger.append_generated_report(
                        self.reports.error,
                        "   Most recent report:",
                    )
                    mrg.tagger.append_generated_report(
                        self.reports.error,
                        " ".join(
                            (
                                "      ",
                                nullstring(mrg.hometeam),
                                "-",
                                nullstring(mrg.awayteam),
                                "  ",
                                nullstring(mrg.homeplayer),
                                mrg.get_print_result()[0],
                                nullstring(mrg.awayplayer),
                            )
                        ),
                    )
                    if inconsistent_report is not None:
                        inconsistent_report.tagger.append_generated_report(
                            self.reports.error, "   Earlier report:"
                        )
                        inconsistent_report.tagger.append_generated_report(
                            self.reports.error,
                            " ".join(
                                (
                                    "      ",
                                    nullstring(inconsistent_report.hometeam),
                                    "-",
                                    nullstring(inconsistent_report.awayteam),
                                    "  ",
                                    nullstring(inconsistent_report.homeplayer),
                                    inconsistent_report.get_print_result()[0],
                                    nullstring(inconsistent_report.awayplayer),
                                )
                            ),
                        )
                    self.reports.error.append(("", self.reports))

    # get_finished_games copied from slcollation.
    # The pdlcollation version is identical.

    def get_finished_games(self):
        """Return list of finished games."""
        finished = []
        for section_games in self.finishedgames.values():
            for ugkey in section_games:
                finished.append(section_games[ugkey][-1])
        return finished

    # The methods from here on are copied from Collation.
    # Added later: I think this means 'from gameobjects.Collation' which has
    # been deleted: see comment at bottom of gameobjects.py

    # Changed to populate er_results from er_matchresults
    def collate_matches(self):
        """Collate results in matchrecords with expected results in schedule.

        Match score inconsistent with game scores is reported as an error when
        the condition occurs on an earlier report: the condition is accepted on
        the most recent report and noted in the validation report.

        There are several distinct steps:
        Collect match report by teams in match taking a source dependent tag
        into account to deal with possible duplicate reports.
        Check that any duplicate reports are consistent.
        Cross-refernce reports with the schedule.
        Produce report of errors and inconsistencies that may, or may not, be
        deemed errors.

        """
        reports = self.reports
        schedule = self.schedule

        def nullstring(string):
            if isinstance(string, str):
                return string
            return ""

        matchrecords = reports.er_matchresults

        self.matches.clear()
        self.matchesxref.clear()
        unique_match = self.matches
        for match in sorted([(m.order, m.source, m) for m in matchrecords]):
            match = match[-1]
            if match.competition not in unique_match:
                unique_match[match.competition] = {}
            umkey = (match.hometeam, match.awayteam, match.source)
            if umkey not in unique_match[match.competition]:
                unique_match[match.competition][umkey] = [match]
            else:
                unique_match[match.competition][umkey].append(match)

        # Assume fixtures have a date and match reports either have a date or
        # or the matches are reported in fixture list date order.
        # MatchFixture is unorderable so decorate to sort.
        fixtures = sorted(
            [(f.date, e, f) for e, f in enumerate(schedule.es_fixtures)]
        )

        for umkey, umvalue in unique_match.items():
            teamalias = schedule.es_team_alias.get(umkey, {})
            for key in sorted(umvalue):
                umsu = umvalue[key]
                mrm = umsu[-1]
                authorizor = _MatchAuthorization(mrm)
                authorizor.authorize_match_report(mrm)
                match_problems = {}

                # This condition is reported later, as a warning, when earlier
                # reports are present.
                if len(umsu) == 1:
                    if not mrm.get_unfinished_games_and_score_consistency()[1]:
                        match_problems.setdefault(constants.ONLY_REPORT)

                for pmr in umsu[:-1]:
                    authorizor.authorize_match_report(pmr)

                    # Not really sure if this should be reported as an error
                    # for earlier reports because the consistency of each game
                    # with the most recent report is enough: but changing a
                    # match score without getting an error may be a surprise.
                    if not pmr.get_unfinished_games_and_score_consistency()[1]:
                        match_problems.setdefault(constants.MATCH_SCORE)

                    if len(pmr.games) != len(mrm.games):
                        match_problems.setdefault(constants.GAME_COUNT)
                        continue
                    for mrmg, prg in zip(mrm.games, pmr.games):
                        problems = set()
                        mrmg.is_inconsistent(prg, problems)
                        if problems:
                            match_problems.setdefault(mrmg, set()).update(
                                problems
                            )

                if not authorizor.is_match_authorized():
                    match_problems.setdefault(constants.AUTHORIZATION)
                if not match_problems:
                    self.matchesxref[mrm] = None
                    hometeam = teamalias.get(mrm.hometeam, {mrm.hometeam: {}})
                    awayteam = teamalias.get(mrm.awayteam, {mrm.awayteam: {}})
                    for fixture in fixtures:
                        fixture = fixture[-1]
                        if mrm.competition == fixture.competition:
                            if fixture.hometeam in hometeam:
                                if fixture.awayteam in awayteam:
                                    if fixture not in self.matchesxref:
                                        self.matchesxref[fixture] = mrm
                                        self.matchesxref[mrm] = fixture
                                        if not mrm.date:
                                            mrm.date = fixture.date
                                        break
                                    self.matchesxref[mrm] = False
                    self.games[(umkey, key)] = mrm

                    # Add matches which are consistent to er_results
                    reports.set_match_result(mrm)

                else:
                    rep = ["Inconsistent reports for"]
                    if isinstance(mrm.competition, str):
                        rep.append(mrm.competition)
                    else:
                        sect = []
                        for comp in mrm.competition:
                            if isinstance(comp, str):
                                sect.append(comp)
                            else:
                                for section in comp:
                                    sect.append(section)
                        rep.append(" ".join(sect))
                    rnd = nullstring(mrm.round)
                    if rnd:
                        rep.append("Round")
                        rep.append(rnd)
                    rep.append("match:")
                    reports.error.append((" ".join(rep), self.reports))
                    reports.error.append(
                        (
                            " ".join(
                                (
                                    " ",
                                    mrm.hometeam,
                                    "".join(
                                        (
                                            nullstring(mrm.homescore),
                                            "-",
                                            nullstring(mrm.awayscore),
                                        )
                                    ),
                                    mrm.awayteam,
                                    "    ",
                                    mrm.source,
                                )
                            ),
                            reports,
                        )
                    )
                    reports.error.append(("   Error detail:", reports))
                    problems = {
                        k: v
                        for k, v in match_problems.items()
                        if not isinstance(k, MatchGame)
                    }
                    if problems:
                        for k in problems:
                            match_problems.pop(k, None)
                        reports.error.append(
                            (
                                " ".join(
                                    (
                                        "      ",
                                        ", ".join(sorted(problems)),
                                    )
                                ),
                                reports,
                            )
                        )
                    for game, detail in match_problems.items():
                        reports.error.append(
                            (
                                " ".join(
                                    (
                                        "      ",
                                        nullstring(game.board),
                                        nullstring(game.homeplayer.name),
                                        game.get_print_result()[0],
                                        nullstring(game.awayplayer.name),
                                        "  **",
                                        ", ".join(sorted(detail)),
                                    )
                                ),
                                reports,
                            )
                        )
                    mrm.tagger.append_generated_report(
                        reports.error, "   Most recent report:"
                    )
                    for game in mrm.games:
                        game.tagger.append_generated_report(
                            reports.error,
                            " ".join(
                                (
                                    "      ",
                                    nullstring(game.board),
                                    nullstring(game.homeplayer.name),
                                    game.get_print_result()[0],
                                    nullstring(game.awayplayer.name),
                                )
                            ),
                        )
                    for match in umsu[:-1]:
                        games = match.games
                        match.tagger.append_generated_report(
                            reports.error, "   Earlier report:"
                        )
                        for game in games:
                            game.tagger.append_generated_report(
                                reports.error,
                                " ".join(
                                    (
                                        "      ",
                                        nullstring(game.board),
                                        nullstring(game.homeplayer.name),
                                        game.get_print_result()[0],
                                        nullstring(game.awayplayer.name),
                                    )
                                ),
                            )
                    reports.error.append(("", reports))

        fnp = [
            (
                f.competition,
                len(f.tagger.datatag),
                f.tagger.datatag,
                f.tagger.teamone,
                f.tagger.teamtwo,
                e,
                f,
            )
            for e, f in enumerate(schedule.es_fixtures)
            if f not in self.matchesxref
        ]
        self.fixturesnotplayed = [f[-1] for f in sorted(fnp)]

    def collate_players(self):
        """Unify and complete player references used in games.

        For each unique player identity there is likely to be several Player
        instances used in Game instances.  Pick one of the Player instances
        and map all Game references to it.

        Event and club details were not available when the Player instances
        were created.  Amend the instances still referenced by Game instances.
        Add each Player instance to the dictionary of player identities with
        games in this event.

        Generate data for player reports.

        """
        schedule = self.schedule
        players = {}
        teamclub = {}
        identities = {}

        # pick one of the player instances for an identity and use it in
        # all places for that identity
        for section, section_matches in self.matches.items():
            for umkey in section_matches:
                for match in section_matches[umkey]:
                    if match.hometeam not in teamclub:
                        teamclub[match.hometeam] = schedule.get_club_team(
                            section, match.hometeam
                        )
                    if match.awayteam not in teamclub:
                        teamclub[match.awayteam] = schedule.get_club_team(
                            section, match.awayteam
                        )
                    for game in match.games:
                        for player in (game.homeplayer, game.awayplayer):
                            if player:
                                identity = (
                                    player.name,
                                    player.event,
                                    schedule.es_startdate,
                                    schedule.es_enddate,
                                    teamclub[player.club],
                                )
                                if identity not in players:
                                    players[identity] = player
                                gpi = player.get_player_identity()
                                if gpi not in identities:
                                    identities[gpi] = identity
                                if player is not players[identity]:
                                    if player is game.homeplayer:
                                        game.homeplayer = players[
                                            identities[gpi]
                                        ]
                                    elif player is game.awayplayer:
                                        game.awayplayer = players[
                                            identities[gpi]
                                        ]

        # complete the player identities by adding in event and club details
        for player in players.values():
            player.startdate = schedule.es_startdate
            player.enddate = schedule.es_enddate
            player.club = teamclub[player.club]
            player.affiliation = player.club
            player.set_player_identity_club()
            self.set_player(player)

        # Generate data for player reports.
        for section, section_matches in self.matches.items():
            for umkey in section_matches:
                match = section_matches[umkey][-1]
                homet = match.hometeam
                if homet not in self.teamplayers:
                    self.teamplayers[homet] = {}
                tph = self.teamplayers[homet]
                homec = schedule.get_club_team(section, homet)
                if homec not in self.clubplayers:
                    self.clubplayers[homec] = {}
                cph = self.clubplayers[homec]
                awayt = match.awayteam
                if awayt not in self.teamplayers:
                    self.teamplayers[awayt] = {}
                tpa = self.teamplayers[awayt]
                awayc = schedule.get_club_team(section, awayt)
                if awayc not in self.clubplayers:
                    self.clubplayers[awayc] = {}
                cpa = self.clubplayers[awayc]
                for game in match.games:
                    if game.homeplayer:
                        homep = game.homeplayer.get_player_identity()
                        if homep not in tph:
                            tph[homep] = [match]
                        else:
                            tph[homep].append(match)
                        if homep not in cph:
                            cph[homep] = set(game.homeplayer.reported_codes)
                        else:
                            cph[homep].update(game.homeplayer.reported_codes)
                    if game.awayplayer:
                        awayp = game.awayplayer.get_player_identity()
                        if awayp not in tpa:
                            tpa[awayp] = [match]
                        else:
                            tpa[awayp].append(match)
                        if awayp not in cpa:
                            cpa[awayp] = set(game.awayplayer.reported_codes)
                        else:
                            cpa[awayp].update(game.awayplayer.reported_codes)

    def get_fixtures_not_played(self):
        """Return list of fixtures not played."""
        return self.fixturesnotplayed

    def get_fixtures_played(self):
        """Return list of fixtures played."""
        return [f for f in self.matchesxref if isinstance(f, MatchFixture)]

    def get_non_fixtures_played(self):
        """Return list of matches played that are not on fixture list."""
        nfp = []
        for key, value in self.matchesxref.items():
            if value is None or value is False:
                nfp.append(key)
        return [
            f[-1]
            for f in sorted(
                [
                    (
                        f.competition,
                        len(f.tagger.datatag),
                        f.tagger.datatag,
                        f.tagger.__dict__.get("teamone"),
                        f.tagger.__dict__.get("teamtwo"),
                        e,
                        f,
                    )
                    for e, f in enumerate(nfp)
                ]
            )
        ]

    def get_players_by_club(self):
        """Return dict(<club name>=[<player name>, ...], ...)."""
        players = {}
        for club, clubplayers in self.clubplayers.items():
            named = []
            for player in clubplayers:
                if player is not None:
                    named.append((AppSysPersonName(player[0]).name, player))
            named.sort()
            players[club] = [p[-1] for p in named]
        return players

    def get_reports_by_match(self):
        """Return list of matches sorted by competition and team names."""
        matches = []
        for section_matches in self.matches.values():
            for umkey in section_matches:
                match = section_matches[umkey][-1]
                matches.append(
                    (
                        match.competition,
                        match.hometeam,
                        match.awayteam,
                        match,
                    )
                )
        matches.sort()
        return [m[-1] for m in matches]

    def get_reports_by_player(self):
        """Return dict(<player name>=[(<team>, <match>), ...], ...)."""
        players = {}
        for team, teamplayers in self.teamplayers.items():
            for player in teamplayers:
                if player:
                    named = (AppSysPersonName(player[0]).name, player)
                    if named not in players:
                        players[named] = []
                    for match in teamplayers[player]:
                        players[named].append((team, match))
        for named in players.values():
            named.sort()
        return players

    def get_matches_by_source(self):
        """Return dictionary of matches collated by source email.

        Match score inconsistent with game scores is reported as a warning and
        the condition is reported only if it occurs on the most recent report
        for a match.

        """
        matches = {}
        for section_matches in self.matches.values():
            for umkey in section_matches:
                for match in section_matches[umkey]:
                    (
                        ufg,
                        con,
                    ) = match.get_unfinished_games_and_score_consistency()
                    key = (len(match.tagger.datatag), match.tagger.datatag)
                    if key not in matches:
                        matches[key] = [
                            (match.hometeam, match.awayteam, (match, ufg, con))
                        ]
                    else:
                        matches[key].append(
                            (match.hometeam, match.awayteam, (match, ufg, con))
                        )
        return matches

    def get_reports_by_source(self):
        """Return list of match reports collated by source."""
        matches = self.get_matches_by_source()
        match_list = []
        for match_key in sorted(matches):
            for reports in sorted(matches[match_key]):
                match_list.append(reports[-1])
        tags = []
        for finishedgames in self.finishedgames.values():
            for fgi in finishedgames:
                for game in finishedgames[fgi]:
                    tags.append(
                        (
                            (len(game.tagger.datatag), game.tagger.datatag),
                            len(tags),
                            game,
                        )
                    )
        return match_list, [t[-1] for t in sorted(tags)]

    def get_unfinished_games(self):
        """Return list of games with no reported result.

        1-0 0-1 draw bye void are examples of reported results.

        """
        unfinished = []
        for matches in self.matches.values():
            for umkey in matches:
                match = matches[umkey][-1]
                for game in match.games:
                    if not game.result:
                        if game.homeplayer and game.awayplayer:
                            unfinished.append(
                                (
                                    match.hometeam,
                                    match.awayteam,
                                    game.board,
                                    len(unfinished),
                                    (match, game),
                                )
                            )
        return [(u[-1]) for u in sorted(unfinished)]


class _MatchAuthorization:
    """Authorization status of match based on time since receipt.

    Relevant to match reports received by email where multiple reports
    are possible.  In particular the two match captains might be expected
    to submit independent reports.

    Not relevant to results downloaded from a database associated with a
    website.
    """

    _authorization_time = mktime(gmtime())

    def __init__(self, match):
        """Initialize authorization state of match to False."""
        self._match = match
        self._dates_ok = False

    def authorize_match_report(self, match):
        """Set authorization state of match from time since latest report."""
        headers = match.tagger.headers
        _match = self._match
        if (
            _match.hometeam != match.hometeam
            or _match.awayteam != match.awayteam
        ):
            return
        # Assume 'headers is None' implies a valid non-email source where
        # multiple sources are not required nor at least advisable.
        if headers is None:
            self._dates_ok = True
            return
        if headers.authorization_delay is None:
            self._dates_ok = True
            return
        try:
            date, delivery_date = headers.dates
            max_date = mktime(max(*date, *delivery_date))
        except (ValueError, TypeError):
            return
        self._dates_ok = (
            self._authorization_time - max_date > headers.authorization_delay
        )

    def is_match_authorized(self):
        """Return True if if match result is authorized."""
        return self._dates_ok
