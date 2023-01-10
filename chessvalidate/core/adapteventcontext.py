# adapteventcontext.py
# Copyright 2014 Roger Marsh
# Licence: See LICENCE (BSD licence)

"""Convert EventData items to style used by Report and Schedule classes."""
import tkinter.messagebox
from datetime import date

from solentware_misc.core import utilities

from . import constants
from .eventcontext import EventContext
from .eventdata import EventData
from .found import (
    Score,
    Found,
)

# These should go in .gameresults or .constants
ONENIL = "1-0"
NILONE = "0-1"

GAME_RESULT = {ONENIL: (1, 0), NILONE: (0, 1), constants.DRAW: (0.5, 0.5)}
NOMATCHSCORE = frozenset((("", ""),))


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
        if not self._event_identity:
            return []
        text = [(self._event_identity[0], None)]

        # Force an error from old-style processing, usually absence of event
        # name and dates.
        if self._event_identity[1] is None or self._event_identity[2] is None:
            text.append(("", None))
        else:
            text.append((" ".join(self._event_identity[1:]), None))

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
        if not self._event_identity:
            return []
        text = [(self._event_identity[0], None)]

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
                    game[2].add(row.date_played)

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
                            if rowmatchscore and i not in rowmatchscore:
                                errors.append(
                                    ((ckey, mkey, bkey), rowmatchscore)
                                )
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
                        "An inconsistency has been found in the match ",
                        "results data extracted from a CSV file.\n\n",
                        "One or more errors will be reported but it may not ",
                        "be immediately obvious what is wrong with the CSV ",
                        "file data, or where the problems are.",
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
                            result_date=game.date_played,
                            source=emailsource,
                            headers=game.headers,
                            nameone=game.nameone,
                            nametwo=game.nametwo,
                            competition=ckey if ckey else game.competition,
                            score=game.score,
                            numbers=[bkey],
                        )

    @staticmethod
    def _is_results_individual(results):
        """Return True if no EventData instances describe a match result."""
        for data in results:
            if data.is_match_result():
                return False
        return True

    @staticmethod
    def _print_text(text):
        """Print lines in text.  Intended for tracing bugs."""
        print("\n")
        for line in text:
            print(repr(line))

    @staticmethod
    def _set_source(eventdata, source, text):
        """Reurn eventdata.source after appending source command to text."""
        if eventdata.source != source:
            text.append((" ".join(("source", eventdata.source)), None))
        return eventdata.source
