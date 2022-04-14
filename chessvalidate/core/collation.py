# collation.py
# Copyright 2008 Roger Marsh
# Licence: See LICENCE (BSD licence)

"""Class to reconcile event schedule (eg. fixture list) with reported results.
"""

import collections
from time import gmtime, mktime

from solentware_misc.core.utilities import AppSysPersonName

from .gameobjects import (
    GameCollation,
    Section,
    SwissGame,
    Player,
    MatchFixture,
    MatchGame,
)
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
    GAME_COUNT,
    MATCH_SCORE,
    ONLY_REPORT,
    AUTHORIZATION,
)

invert_score = {"-": "+", "=": "=", "+": "-", "1": "0", "0": "1"}
map_score = {"+": hwin, "=": draw, "-": awin, "1": hwin, "0": awin}
homeplayercolour = {"w": True, "b": False}


class Collation(GameCollation):

    """Results extracted from a generic event report."""

    def __init__(self, reports, fixtures):

        super().__init__()

        self.reports = reports
        self.schedule = fixtures
        self.report_order = []  # merge report orders for schedule and results
        self.section_type = dict()  # merge section types as well
        self._league_found = False

        # moved from Collation
        self.matches = dict()
        self.teamplayers = dict()
        self.clubplayers = dict()
        self.matchesxref = dict()
        self.fixturesnotplayed = []

        # moved from PDLCollationWeekly, PDLCollation, and SLCollation
        # PDLCollationWeekly has attribute unfinishedgames, but possibly only
        # because it does not have the reports attribute. (Maybe reports is
        # too wide here?)

        # Results of adjourned and adjudicated games reported later.
        self.finishedgames = dict()
        # map games to unfinished games
        self.gamesxref = dict()

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
            if not isinstance(process, collections.Callable):
                process = self._collate_not_implemented
            process(section)
            self.section_type[section] = reports.er_section[section]
            self.report_order.append(section)
        if self._league_found:
            self.collate_matches(self.reports, self.schedule)
            self.collate_unfinished_games(self.schedule)
            self.collate_players(self.schedule)
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
                                    " has no information in schedule for name ",
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
                elif player != self.schedule.es_pins[section][ppin]:
                    self.reports.error.append(
                        (
                            "".join(
                                (
                                    "Section ",
                                    section,
                                    ' has no information in schedule for name "',
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

        round_dates = dict()
        for r in range(1, len(self.reports.er_swiss_table[section]) + 1):
            if r in self.schedule.es_round_dates[section]:
                round_dates[r] = self.schedule.es_round_dates[section][r]
            else:
                round_dates[r] = self.schedule.es_startdate
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
        for g in games:
            hp = es_players[(es_pins[g[3]], g[3])]
            ap = es_players[(es_pins[g[4]], g[4])]
            sectiongames.games.append(
                SwissGame(
                    tagger=g[7],
                    # Hack round for wallcharts and swiss tournaments presented in
                    # an all-play-all format, because the deduced round is wrong or
                    # irrelevant.
                    # round=str(g[0]),
                    result=g[5],
                    date=round_dates[g[0]],
                    homeplayerwhite=homeplayercolour.get(g[6]),
                    homeplayer=hp,  # should be the Player instance now
                    awayplayer=ap,
                )
            )  # should be the Player instance now
            self.set_player(hp)  # use existing
            self.set_player(ap)  # Player instances
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
        for g in sectiongames.games:
            for p in (
                g.homeplayer,
                g.awayplayer,
            ):
                if p.event is None or p.startdate is None or p.enddate is None:
                    p.event = self.schedule.es_name
                    p.startdate = self.schedule.es_startdate
                    p.enddate = self.schedule.es_enddate
                    p.section = self.schedule._section

                    # The default pin=None is surely fine but False is what pin
                    # becomes in earlier versions and it does not happen here
                    # unless set so.
                    p.pin = False

                    p.__dict__["_identity"] = (
                        p.name,
                        p.event,
                        p.startdate,
                        p.enddate,
                    )
            if g.date is None:
                g.date = self.schedule.es_startdate
            self.set_player(g.homeplayer)
            self.set_player(g.awayplayer)
        self.set_games(section, sectiongames)

    def _collate_league(self, section):

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

        round_dates = dict()
        for r in range(1, len(self.reports.er_swiss_table[section]) + 1):
            if r in self.schedule.es_round_dates[section]:
                round_dates[r] = self.schedule.es_round_dates[section][r]
            else:
                round_dates[r] = self.schedule.es_startdate
        games = []
        for pin in self.reports.er_swiss_table[section]:
            card = self.reports.er_swiss_table[section][pin]
            r = 0
            for game in card:
                r += 1
                opponent = game["opponent"]
                if opponent:
                    colour = game["colour"]
                    if opponent > pin:
                        if colour == "b":
                            games.append(
                                (
                                    r,
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
                                    r,
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
        for g in games:
            hp = es_players[(es_pins[g[3]], g[3])]
            ap = es_players[(es_pins[g[4]], g[4])]
            sectiongames.games.append(
                SwissGame(
                    tagger=g[6],
                    round=str(g[0]),
                    result=g[5],
                    date=round_dates[g[0]],
                    homeplayerwhite=True,
                    homeplayer=hp,  # should be the Player instance now
                    awayplayer=ap,
                )
            )  # should be the Player instance now
            self.set_player(hp)  # use existing
            self.set_player(ap)  # Player instances
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

    def collate_unfinished_games(self, schedule):
        """Collate games played but reported unfinished."""

        def nullstring(s):
            if isinstance(s, str):
                return s
            else:
                return ""

        self.finishedgames.clear()
        self.gamesxref.clear()
        unique_game = self.finishedgames
        for game in self.reports.er_unfinishedgames:
            if game.section not in unique_game:
                unique_game[game.section] = dict()

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

        for s in unique_game:
            teamalias = schedule.es_team_alias.get(s, {})
            for u in unique_game[s]:
                ugsu = unique_game[s][u]
                mrg = ugsu[-1]
                game_problems = {}
                for prevreport in ugsu[:-1]:
                    problems = set()
                    if mrg.is_inconsistent(prevreport, problems):
                        game_problems.setdefault(mrg, set()).update(problems)

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
                                if game.result != tobereported:
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
                        for w in mrg.section:
                            sect.append(w)
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
                    prevreport.tagger.append_generated_report(
                        self.reports.error, "   Earlier report:"
                    )
                    prevreport.tagger.append_generated_report(
                        self.reports.error,
                        " ".join(
                            (
                                "      ",
                                nullstring(prevreport.hometeam),
                                "-",
                                nullstring(prevreport.awayteam),
                                "  ",
                                nullstring(prevreport.homeplayer),
                                prevreport.get_print_result()[0],
                                nullstring(prevreport.awayplayer),
                            )
                        ),
                    )
                    self.reports.error.append(("", self.reports))

    # get_finished_games copied from slcollation.
    # The pdlcollation version is identical.

    def get_finished_games(self):
        """Return list of finished games"""
        finished = []
        for section in self.finishedgames:
            for ugkey in self.finishedgames[section]:
                finished.append(self.finishedgames[section][ugkey][-1])
        return finished

    # The methods from here on are copied from Collation.
    # Added later: I think this means 'from gameobjects.Collation' which has
    # been deleted: see comment at bottom of gameobjects.py

    # Changed to populate er_results from er_matchresults
    def collate_matches(self, reports, schedule):
        """Collate results in matchrecords with expected results in schedule

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

        def nullstring(s):
            if isinstance(s, str):
                return s
            else:
                return ""

        matchrecords = reports.er_matchresults

        self.matches.clear()
        self.matchesxref.clear()
        unique_match = self.matches
        for e, f, match in sorted(
            [(m.order, m.source, m) for m in matchrecords]
        ):
            if match.competition not in unique_match:
                unique_match[match.competition] = dict()
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

        for s in unique_match:
            teamalias = schedule.es_team_alias.get(s, {})
            for u in sorted(unique_match[s]):
                umsu = unique_match[s][u]
                mrm = umsu[-1]
                authorizor = _MatchAuthorization(mrm)
                authorizor.authorize_match_report(mrm)
                match_problems = {}

                # This condition is reported later, as a warning, when earlier
                # reports are present.
                if len(umsu) == 1:
                    if not mrm.get_unfinished_games_and_score_consistency()[1]:
                        match_problems.setdefault(ONLY_REPORT)

                for pmr in umsu[:-1]:
                    authorizor.authorize_match_report(pmr)

                    # Not really sure if this should be reported as an error
                    # for earlier reports because the consistency of each game
                    # with the most recent report is enough: but changing a
                    # match score without getting an error may be a surprise.
                    if not pmr.get_unfinished_games_and_score_consistency()[1]:
                        match_problems.setdefault(MATCH_SCORE)

                    if len(pmr.games) != len(mrm.games):
                        match_problems.setdefault(GAME_COUNT)
                        continue
                    for mrmg, prg in zip(mrm.games, pmr.games):
                        problems = set()
                        mrmg.is_inconsistent(prg, problems)
                        if problems:
                            match_problems.setdefault(mrmg, set()).update(
                                problems
                            )

                if not authorizor.is_match_authorized():
                    match_problems.setdefault(AUTHORIZATION)
                if not match_problems:
                    self.matchesxref[mrm] = None
                    hometeam = teamalias.get(mrm.hometeam, {mrm.hometeam: {}})
                    awayteam = teamalias.get(mrm.awayteam, {mrm.awayteam: {}})
                    for df, ef, fixture in fixtures:
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
                    self.games[(s, u)] = mrm

                    # Add matches which are consistent to er_results
                    reports.set_match_result(mrm)

                else:
                    rep = ["Inconsistent reports for"]
                    if isinstance(mrm.competition, str):
                        rep.append(mrm.competition)
                    else:
                        sect = []
                        for e in mrm.competition:
                            if isinstance(e, str):
                                sect.append(e)
                            else:
                                for w in e:
                                    sect.append(w)
                        rep.append(" ".join(sect))
                    rnd = nullstring(mrm.round)
                    if rnd:
                        rep.append("Round")
                        rep.append(rnd)
                    rep.append("match:")
                    self.reports.error.append((" ".join(rep), self.reports))
                    self.reports.error.append(
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
                            self.reports,
                        )
                    )
                    self.reports.error.append(
                        ("   Error detail:", self.reports)
                    )
                    mp = {
                        k: v
                        for k, v in match_problems.items()
                        if not isinstance(k, MatchGame)
                    }
                    if mp:
                        for k in mp:
                            match_problems.pop(k, None)
                        self.reports.error.append(
                            (
                                " ".join(
                                    (
                                        "      ",
                                        ", ".join([e for e in sorted(mp)]),
                                    )
                                ),
                                self.reports,
                            )
                        )
                    for g, d in match_problems.items():
                        self.reports.error.append(
                            (
                                " ".join(
                                    (
                                        "      ",
                                        nullstring(g.board),
                                        nullstring(g.homeplayer.name),
                                        g.get_print_result()[0],
                                        nullstring(g.awayplayer.name),
                                        "  **",
                                        ", ".join([e for e in sorted(d)]),
                                    )
                                ),
                                self.reports,
                            )
                        )
                    mrm.tagger.append_generated_report(
                        self.reports.error, "   Most recent report:"
                    )
                    for g in mrm.games:
                        g.tagger.append_generated_report(
                            self.reports.error,
                            " ".join(
                                (
                                    "      ",
                                    nullstring(g.board),
                                    nullstring(g.homeplayer.name),
                                    g.get_print_result()[0],
                                    nullstring(g.awayplayer.name),
                                )
                            ),
                        )
                    for m in umsu[:-1]:
                        games = m.games
                        m.tagger.append_generated_report(
                            self.reports.error, "   Earlier report:"
                        )
                        for g in games:
                            g.tagger.append_generated_report(
                                self.reports.error,
                                " ".join(
                                    (
                                        "      ",
                                        nullstring(g.board),
                                        nullstring(g.homeplayer.name),
                                        g.get_print_result()[0],
                                        nullstring(g.awayplayer.name),
                                    )
                                ),
                            )
                    self.reports.error.append(("", self.reports))

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

    def collate_players(self, schedule):
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

        players = dict()
        teamclub = dict()
        identities = dict()

        # pick one of the player instances for an identity and use it in
        # all places for that identity
        for section in self.matches:
            for umkey in self.matches[section]:
                for match in self.matches[section][umkey]:
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
        for p in players:
            player = players[p]
            player.startdate = schedule.es_startdate
            player.enddate = schedule.es_enddate
            player.club = teamclub[player.club]
            player.affiliation = player.club
            player.__dict__["_identity"] = (
                player.name,
                player.event,
                player.startdate,
                player.enddate,
                player.club,
            )
            self.set_player(player)

        # Generate data for player reports.
        for section in self.matches:
            for umkey in self.matches[section]:
                match = self.matches[section][umkey][-1]
                homet = match.hometeam
                if homet not in self.teamplayers:
                    self.teamplayers[homet] = dict()
                tph = self.teamplayers[homet]
                homec = schedule.get_club_team(section, homet)
                if homec not in self.clubplayers:
                    self.clubplayers[homec] = dict()
                cph = self.clubplayers[homec]
                awayt = match.awayteam
                if awayt not in self.teamplayers:
                    self.teamplayers[awayt] = dict()
                tpa = self.teamplayers[awayt]
                awayc = schedule.get_club_team(section, awayt)
                if awayc not in self.clubplayers:
                    self.clubplayers[awayc] = dict()
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
        """Return list of fixtures not played"""
        return self.fixturesnotplayed

    def get_fixtures_played(self):
        """Return list of fixtures played"""
        return [f for f in self.matchesxref if isinstance(f, MatchFixture)]

    def get_non_fixtures_played(self):
        """Return list of matches played that are not on fixture list"""
        xref = self.matchesxref
        nfp = [f for f in xref if (xref[f] is None or xref[f] is False)]
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

    def get_players_by_club(self, separator=None):
        """Return dict(<club name>=[<player name>, ...], ...)"""
        cp = dict()
        for club in self.clubplayers:
            clubplayers = self.clubplayers[club]
            ps = []
            for player in clubplayers:
                if player != None:
                    ps.append((AppSysPersonName(player[0]).name, player))
            ps.sort()
            cp[club] = [p[-1] for p in ps]
        return cp

    def get_reports_by_match(self):
        """Return list of matches sorted by competition and team names"""
        rm = []
        for section in self.matches:
            for umkey in self.matches[section]:
                match = self.matches[section][umkey][-1]
                rm.append(
                    (
                        match.competition,
                        match.hometeam,
                        match.awayteam,
                        match,
                    )
                )
        rm.sort()
        return [m[-1] for m in rm]

    def get_reports_by_player(self, separator=None):
        """Return dict(<player name>=[(<team>, <match>), ...], ...)"""
        players = dict()
        for team in self.teamplayers:
            for player in self.teamplayers[team]:
                if player:
                    ps = (AppSysPersonName(player[0]).name, player)
                    if ps not in players:
                        players[ps] = []
                    for match in self.teamplayers[team][player]:
                        players[ps].append((team, match))
        for p in players:
            players[p].sort()
        return players

    def get_matches_by_source(self):
        """Return dictionary of matches collated by source email.

        Match score inconsistent with game scores is reported as a warning and
        the condition is reported only if it occurs on the most recent report
        for a match.

        """
        tm = dict()
        for section in self.matches:
            for umkey in self.matches[section]:
                for match in self.matches[section][umkey]:
                    ufg, c = match.get_unfinished_games_and_score_consistency()
                    key = (len(match.tagger.datatag), match.tagger.datatag)
                    if key not in tm:
                        tm[key] = [
                            (match.hometeam, match.awayteam, (match, ufg, c))
                        ]
                    else:
                        tm[key].append(
                            (match.hometeam, match.awayteam, (match, ufg, c))
                        )
        return tm

    def get_reports_by_source(self):
        """Return list of match reports collated by source"""
        tm = self.get_matches_by_source()
        ta = []
        for ms in sorted(tm):
            for m in sorted(tm[ms]):
                ta.append(m[-1])
        tg = []
        for fg in self.finishedgames:
            for fgi in self.finishedgames[fg]:
                for g in self.finishedgames[fg][fgi]:
                    tg.append(
                        ((len(g.tagger.datatag), g.tagger.datatag), len(tg), g)
                    )
        return ta, [t[-1] for t in sorted(tg)]

    def get_unfinished_games(self):
        """Return list of games with no reported result.

        1-0 0-1 draw bye void are examples of reported results.

        """
        unfinished = []
        for division in self.matches:
            for umkey in self.matches[division]:
                match = self.matches[division][umkey][-1]
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


class _MatchAuthorization(object):
    """Authorization status of match based on time since receipt."""

    _authorization_time = mktime(gmtime())

    def __init__(self, match):
        """ """
        self._match = match
        self._dates_ok = False

    def authorize_match_report(self, match):
        """ """
        a = match.tagger.headers
        m = self._match
        if m.hometeam != match.hometeam or m.awayteam != match.awayteam:
            return
        if a.authorization_delay is None:
            self._dates_ok = True
            return
        try:
            date, delivery_date = a.dates
            max_date = mktime(max(max(date), max(delivery_date)))
        except (ValueError, TypeError):
            return
        self._dates_ok = (
            self._authorization_time - max_date > a.authorization_delay
        )

    def is_match_authorized(self):
        """ """
        return self._dates_ok
