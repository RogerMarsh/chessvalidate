# eventparser.py
# Copyright 2014 Roger Marsh
# Licence: See LICENCE (BSD licence)

"""Event parser class."""
import re

from .emailextractor import (
    RESULTS_PREFIX,
    SECTION_PREFIX,
    SECTION_BODY,
    MATCH_BODY,
    TEAMS_BODY,
    GAMES_BODY,
    FINISHED,
    UNFINISHED,
    DEFAULT,
    MATCH_DEFAULT,
    MATCH_DATE_BODY,
    PLAYED_ON_BODY,
    TEAMS_PLAYED_ON_BODY,
    GAMES_PLAYED_ON_BODY,
    FINISHED_PLAYED_ON,
    UNFINISHED_PLAYED_ON,
    MATCH_DATE_PLAYED_ON_BODY,
    SCHEDULE_BODY,
    FIXTURE_BODY,
    MATCH_FORMATS,
    PLAYED_ON_FORMATS,
    FIXTURE_FORMATS,
    KEEP_WORD_SPLITTERS,
    SECTION_NAME,
    SOURCE,
    DROP_FORWARDED_MARKERS,
    REPORT_TABLE,
    TABLE_DELIMITER,
)

from .eventdata import (
    EventData,
    TableEventData,
)
from .found import (
    Score,
    Found,
)
from .adapteventcontext import AdaptEventContext

# The competition name used in tabular inputs if no competition name is given.
# Usually the competition 'All Sections' is but in event's conf file if needed.
_ALL_SECTIONS = "all sections"

# By default results text is split into components by newline.
# Rules supplied by _FIND_MATCHES use arbitrary criteria to split the text and
# produce newline delimited components.
_FIND_MATCHES = (
    (
        MATCH_FORMATS,
        MATCH_BODY,
        (
            MATCH_DATE_BODY,
            TEAMS_BODY,
            MATCH_DEFAULT,
        ),
        GAMES_BODY,
        (
            DEFAULT,
            UNFINISHED,
            FINISHED,
        ),
    ),
    (
        PLAYED_ON_FORMATS,
        PLAYED_ON_BODY,
        (
            MATCH_DATE_PLAYED_ON_BODY,
            TEAMS_PLAYED_ON_BODY,
        ),
        GAMES_PLAYED_ON_BODY,
        (
            UNFINISHED_PLAYED_ON,
            FINISHED_PLAYED_ON,
        ),
    ),
    (
        FIXTURE_FORMATS,
        SCHEDULE_BODY,
        (FIXTURE_BODY,),
        None,
        (),
    ),
)

# Boards look like ' 12 ', ' 1.2 ', ' 1.2.3 '.  Start and end of string is
# allowed instead of the leading and trailing space respectively.
BOARD_PATTERN = r"(?:(?<=\s)|\A)([1-9][0-9]*(?:\.[1-9][0-9]*)*)(?=\s|\Z)"
RE_BOARD = re.compile(BOARD_PATTERN, flags=re.IGNORECASE | re.DOTALL)

# Rounds look like ' 1 ', ' 12 ', ' 123 '.  Start and end of string is
# allowed instead of the leading and trailing space respectively.
ROUND_PATTERN = r"(?:(?<=\s)|\A)([1-9][0-9]*)(?=\s|\Z)"
RE_ROUND = re.compile(ROUND_PATTERN, flags=re.IGNORECASE | re.DOTALL)

# Scores look like ' 1 0 ', ' 1-0 ', ' 1 - 0 ', ' draw ', ' void ', or
# '<name> 1 <name> 0 '. End of line is allowed instead of the final space.
# The RE_SCORE_SEP regular expression accepts any word splitter as separator in
# ' 1-0 ', but '~' and '*' instead of '-' in ' 1 - 0 ' are rejected by swiss
# and all-play-all regular expressions where these characters indicate games
# not played.
# ' 1 0 ' covers the '<name> 1 0 <name>' case and so forth.
# '-' means any sequence of non-word characters excluding whitespace.
# ' ' means any sequence of whitespace excluding newline.
# These rules produce the ' 1 0 ' format from the ' 1-0 ' or ' draw ' formats.
TOTAL = r"[0-9]+(?:\.0|\.5|\xbd)?|\xbd"

# Points changed to not use TOTAL because '1.1 Smith 1 0 Jones' is a valid way
# of describing a result in a match with multiple games per board (rapidplay is
# a likely example). Neither '1.1 Smith 1-0 Jones' nor '1 Smith 1-0 Jones' work
# but '1.1 Smith draw Jones' is fine.
# Points changed to not treat '123456' in 'A Name 123456A' as a number.
# POINTS = ''.join(('(?:(?<=\s)|\A)', TOTAL, '(?=\s|\Z)'))
# POINTS = ''.join(('(?:(?<=\s)|\A)',
#                  '[0-9]+(?:\.[0-9]+|\xbd)?|\xbd',
#                  '(?=\s|\Z)'))
POINTS = r"(?:(?<=\s)|\A)(?:[0-9]+(?:\.[0-9]+|\xbd)?|\xbd)(?=\s|\Z)"

SCORE_SEP = r"(?<=[0-9\xbd])\s*[^\s\w\.]+\s*(?=[0-9\xbd])"
SCORE = "".join(
    (
        r"(?:(?<=\s)|\A)",
        "(?:(?:",
        TOTAL,
        ")",
        SCORE_SEP,
        "(?:",
        TOTAL,
        "))",
        r"(?=\s|\Z)",
    )
)
_DRAW = r"(?:(?<=\s)|\A)(?:draw|0\.5|\xbd)(?=\s|\Z)"
RE_POINTS = re.compile(POINTS, flags=re.IGNORECASE | re.DOTALL)
RE_SCORE_SEP = re.compile(SCORE_SEP, flags=re.IGNORECASE | re.DOTALL)
RE_SCORE = re.compile(SCORE, flags=re.IGNORECASE | re.DOTALL)
RE_DRAW = re.compile(_DRAW, flags=re.IGNORECASE | re.DOTALL)

# Board numbers in matches can be deduced and the match score used as a check
# on the game results if defaults are spotted.
# Defaulted games are indicated in a variety of ways.  All are assumed to say
# 'def' or 'default' either as part of the game result, ' 1-def ' for example,
# or as a player's name, 'Jones 1 0 default' for example, or at least use the
# word ' default ' in the game result, ' Toytown win by default ' for example.
# These results contribute to the match score.
# Double default does not contribute to the match score and is treated as a
# variety of _VOID.
# An unfinished game does not contribute to the match score and is treated as
# a variety of _VOID.  But a report is expected to show up eventually.
# Jones 1 def 0, and similar with the abbreviation of default, are not allowed
# because it is too tricky to determine that 'def' is not initials in a name.
_VOID = "".join(
    (
        r"(?:(?<=\s)|\A)",
        "(?:",
        "void|unfinished|",
        r"(?:1\s*-|dbl|double)?default(?:-\s*1)?|",  # includes default as a word
        r"1\s*-def|def\s*-1|(?:dbl|double)\s*def|",  # def allowed in context
        r"match\s+default",
        ")",
        r"(?=\s|\Z)",
    )
)
RE_VOID = re.compile(_VOID, flags=re.IGNORECASE | re.DOTALL)

# Lines may contain up to two dates.
# Lines with more than two dates are ignored.
DAY = "[0-9]{1,2}"
MONTH_NAMES = "".join(
    (
        "jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|",
        "jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|",
        "dec(?:ember)?",
    )
)
MONTH = "".join(
    (
        "(?:",
        "[0-9]{1,2}|",
        MONTH_NAMES.join(("(?:", ")")),
        ")",
    )
)
YEAR = r"(?:[0-9]{4}|[0-9]{2})"
DATE_SEP = r"\s*\W\s*"
DATE = "".join(
    (
        DAY,
        DATE_SEP,
        MONTH,
        DATE_SEP,
        YEAR,
        "|",
        MONTH,
        DATE_SEP,
        DAY,
        DATE_SEP,
        YEAR,
        "|",
        YEAR,
        DATE_SEP,
        MONTH,
        DATE_SEP,
        DAY,
    )
)
RE_DATE = re.compile(
    DATE.join((r"(?:(?<=\s)|\A)(?:", r")(?=\s|\Z)")),
    flags=re.IGNORECASE | re.DOTALL,
)

# Get day, date, or day and date, from fixture list.
# Day and date must be adjacent, in either order, if both are present.
DAY_NAMES = "".join(
    (
        "wednesday|thursday|saturday|tuesday|sunday|monday|friday|",
        "thurs|tues|",
        "sun|mon|tue|wed|thur|fri|sat",
    )
)
RE_DAY = re.compile(
    DAY_NAMES.join((r"(?:\s|\A)(", r")(?:\s|\Z)")),
    flags=re.IGNORECASE | re.DOTALL,
)
FIXTURE_DATE = "|".join(
    (
        "".join(("(", DAY_NAMES, r")\s+(", DATE, ")")),
        "".join(("(", DATE, r")\s+(", DAY_NAMES, ")")),
        "".join(("(", DATE, ")")),
    )
)
RE_FIXTURE_DATE = re.compile(
    FIXTURE_DATE.join((r"(?:(?<=\s)|\A)(?:", r")(?=\s|\Z)")),
    flags=re.IGNORECASE | re.DOTALL,
)

# '*', 'bye+', 'bye=', 'def+', 'def-', and entries like 'w34+', 'b3-', and
# 'w112=', are allowed in the swiss format.
# 11 July 2017 adjustments:
# Vega uses '+W34' format and allows '-BYE'.  Result first is a reasonable way
# of expressing things, and may be better than result last.
SWISS = "".join(
    (
        r"(?:(?<=\s)|\A)",
        "(?:",
        r"\*|bye[-=\+]|def[-\+]|[wb][0-9]+[-=\+]|",
        r"--|[-=\+]bye|[-\+]def|[-=\+][wb][0-9]+",
        ")",
        r"(?=\s|\Z)",
    )
)
RE_SWISS = re.compile(SWISS, flags=re.IGNORECASE | re.DOTALL)

# 'w+', 'w-', 'w=', 'b+', 'b-', 'b=', and '~' are allowed in the all-play-all
# format, with at least one '~' present.
# '~' is used, rather than '*', to avoid confusion with swiss layout.
# This layout is intended for club internal tournaments where an all-play-all
# chart is available for players to fill in their results when, and if, the
# game is played.  It is not intended for formal all-play-all tournaments where
# both round and colour can be determined from the table size and the game's
# place in the table.
# The colour indicator is not optional to avoid confusion between all-play-all
# rows and single game results presented as ' Jones 1 - 0 Smith '.  Otherwise
# only ' Jones 1-0 Smith ' would be acceptable (no spaces between numbers and
# '-') when a separator is used.  Preference given to single game case because
# it is more frequent.
ALL_PLAY_ALL = r"(?:(?<=\s)|\A)(?:\~|[wb][-=\+])(?=\s|\Z)"
RE_ALL_PLAY_ALL = re.compile(ALL_PLAY_ALL, flags=re.IGNORECASE | re.DOTALL)

# Player table number is common to all-play-all and swiss tables.
PIN = r"(?:(?<=\s)|\A)[0-9]+(?=\s|\Z)"
RE_PIN = re.compile(PIN, flags=re.IGNORECASE | re.DOTALL)

# Pattern of numbers and names may decide which number is board or round.
NUMBERS = "".join((r"(?:(?<=\s)|\A)", "(", TOTAL, ")", r"(?=\s|\Z)"))
RE_NUMBERS = re.compile(NUMBERS, flags=re.IGNORECASE | re.DOTALL)

# Pattern of points totals including odd number of draws.
DRAW_MARKER = r"[0-9]+(?:\.5|\xbd)+|\xbd"
DRAW_ITEMS = "".join((r"(?:(?<=\s)|\A)", "(", DRAW_MARKER, ")", r"(?=\s|\Z)"))
RE_DRAW_ITEM = re.compile(DRAW_ITEMS, flags=re.IGNORECASE | re.DOTALL)

# Colour may be specified as pieces played by first-named player.
COLOUR = "white|black|unknown"
COLOUR_ITEM = "".join((r"(?:(?<=\s)|\A)", "(", COLOUR, ")", r"(?=\s|\Z)"))
RE_COLOUR = re.compile(COLOUR_ITEM, flags=re.IGNORECASE | re.DOTALL)

# A game result may be recorded for the players but should not count toward
# totals such as match scores for validation purposes.  Sum of team scores in a
# match is expected to equal number of games played in match and similar.
RE_RESULT_ONLY = re.compile(
    r"\sresult\s+only\Z", flags=re.IGNORECASE | re.DOTALL
)

# A line may have the 'played_on' prefix.
PLAYED_ON = "played_on"
RE_PLAYED_ON = re.compile(
    PLAYED_ON.join((r"\A\s*", r"\s+")), flags=re.IGNORECASE | re.DOTALL
)

# Some regular expressions from conf file may break the re engine on some
# versions of Python, even though the re compilation succeeded.
IEIREE = "internal error in regular expression engine"

# The singleton drawn game tokens that may be used in text evaluated using
# regular expressions.  Translated to 'draw' to keep result parser happy.
_DRAW_TOKEN = frozenset(
    (
        "1/2",
        "0.5",
        "\xbd",
    )
)


class EventParserError(Exception):
    """Exception class for eventparser module."""


class EventParser:
    """Extract event schedules and results from text files.

    The outputs are used as inputs to the Schedule and Report classes and their
    subclasses.

    """

    def __init__(self, difference_items):
        """Create parser to process list of _DifferenceText instances."""
        self._difference_items = difference_items
        self.error = []

    def build_event(
        self, rules, competitions, team_name_lookup, event_identity
    ):
        """Return an instance of AdaptEventContext.

        The AdaptEventContext instance contains EventData instances arranged
        for use by the Schedule and Result classes.

        """
        competition_lookup = {c.lower(): c for c in competitions}
        sorted_competitions = sorted(
            [(len(c), c) for c in competitions], reverse=True
        )
        re_competition = re.compile(
            "|".join(
                [r"\s+".join(c[-1].split()) for c in sorted_competitions]
            ).join(("(", ")")),
            flags=re.IGNORECASE | re.DOTALL,
        )
        re_sections = []
        re_forwarded = []
        for event in rules:
            sorted_sections = sorted(
                [(len(c), c) for c in event[SECTION_NAME].values()],
                reverse=True,
            )
            re_sections.append(
                re.compile(
                    "|".join(
                        [r"\s+".join(s[-1].split()) for s in sorted_sections]
                    ).join(("(", ")")),
                    flags=re.IGNORECASE | re.DOTALL,
                )
            )
            re_forwarded.append(None)
            if event[DROP_FORWARDED_MARKERS]:
                re_forwarded[-1] = re.compile(
                    event[DROP_FORWARDED_MARKERS].join(
                        (r"(?<=\n)(?:\s*", ")+")
                    ),
                    flags=re.IGNORECASE | re.DOTALL,
                )
        selected_text = AdaptEventContext(event_identity)
        for difference_item in self._difference_items:
            found = False
            for eitem, event in enumerate(rules):
                if re_forwarded[eitem]:
                    text = "".join(
                        re_forwarded[eitem].split(difference_item.edited_text)
                    )
                else:
                    text = difference_item.edited_text
                if event[SOURCE].pattern:
                    try:
                        source = event[SOURCE].findall(text)
                        source = source[0] if source else ""
                    except RuntimeError as eee:
                        if str(eee) == IEIREE:
                            raise_re_error(SOURCE, text)
                        raise
                else:
                    source = difference_item._filename
                result_line_description = (
                    selected_text,
                    difference_item.data_tag,
                    re_sections[eitem],
                    source,
                    competition_lookup,
                    difference_item.headers,
                )
                try:
                    est = event[RESULTS_PREFIX].split(text)
                except RuntimeError as eee:
                    if str(eee) == IEIREE:
                        raise_re_error(RESULTS_PREFIX, text)
                    raise
                # tracer for fixing regular expressions
                # print(difference_item.data_tag, len(est)) # tracer
                est.pop(0)
                for rri in est:
                    kws = (
                        event[KEEP_WORD_SPLITTERS]
                        .replace("\\t", "\t")
                        .replace("\\n", "\n")
                    )
                    rri = "".join(
                        [
                            s
                            if s.isalnum() or s.isnumeric() or s in kws
                            else " "
                            for s in rri
                            if len(s)
                        ]
                    )
                    try:
                        spe = event[SECTION_PREFIX].findall(rri)
                    except RuntimeError as eee:
                        if str(eee) == IEIREE:
                            raise_re_error(SECTION_PREFIX, rri)
                        raise
                    for ski, ssi in zip(
                        spe, [r for r in event[SECTION_BODY].split(rri) if r]
                    ):
                        try:
                            ski = event[SECTION_NAME].get(
                                " ".join(ski.lower().split()), ski
                            )
                        except RuntimeError as eee:
                            if str(eee) == IEIREE:
                                raise_re_error(SECTION_NAME, ski)
                            raise
                        for mfn, mbn, mdn, gbn, grn in _FIND_MATCHES:
                            for emf in event[mfn]:
                                try:
                                    kditems = emf[mbn].findall(ssi)
                                except RuntimeError as eee:
                                    if str(eee) == IEIREE:
                                        raise_re_error(mbn, ssi)
                                    raise
                                # tracer for fixing regular expressions
                                # print(mfn, repr(ski), len(kditems), end='  ') # tracer
                                for kdi in kditems:
                                    # tracer for fixing regular expressions
                                    # print(repr(kdi[:20]), end='  ') # tracer

                                    # The competition name is included in each
                                    # fixture so is not output here.
                                    # A hack perhaps, but _select_result_line
                                    # would otherwise find it difficult to
                                    # distinguish fixture list entries and
                                    # match headers without a match score.
                                    if mfn != FIXTURE_FORMATS:
                                        _select_result_line(
                                            result_line_description,
                                            ski,
                                        )

                                    for fvi in mdn:
                                        if fvi not in emf:
                                            continue

                                        # Translate to text lines for calls
                                        # of _select_result_line.
                                        # The team and match date translations,
                                        # and their played on equivalents.
                                        # Match defaults here too.
                                        try:
                                            tle = list(emf[fvi].finditer(kdi))
                                        except RuntimeError as eee:
                                            if str(eee) == IEIREE:
                                                raise_re_error(fvi, kdi)
                                            raise
                                        # tracer for fixing regular expressions
                                        # print(fvi, len(tle), end='  ') # tracer
                                        if len(tle) != 1:
                                            continue
                                        gdi = tle[0].groupdict()

                                        # Used only by FIXTURE_BODY fvi value.
                                        if "competition" not in gdi:
                                            gdi["competition"] = ski
                                        else:
                                            gdi["competition"] = event[
                                                SECTION_NAME
                                            ].get(
                                                " ".join(
                                                    gdi["competition"]
                                                    .lower()
                                                    .split()
                                                ),
                                                ski,
                                            )

                                        _translate(
                                            result_line_description, fvi, gdi
                                        )

                                    # Fixture formats do not have game detail.
                                    if gbn is None:
                                        continue

                                    # Find the text containing game, or played
                                    # on game, results for each match report.
                                    vditems = [
                                        t.strip()
                                        if isinstance(t, str)
                                        else " ".join(t).strip()
                                        for t in emf[gbn].findall(kdi)
                                    ]
                                    # tracer for fixing regular expressions
                                    # print(gbn, len(vditems), end='  ') # tracer
                                    for vdi in vditems:
                                        if not vdi:
                                            continue
                                        # tracer for fixing regular expressions
                                        # print('.', end='') # tracer
                                        for fvi in grn:
                                            if fvi not in emf:
                                                continue

                                            # Translate to text lines for calls
                                            # of _select_result_line.
                                            # The finished, unfinished, and
                                            # default translations, and their
                                            # played on equivalents.
                                            try:
                                                tle = list(
                                                    emf[fvi].finditer(vdi)
                                                )
                                            except RuntimeError as eee:
                                                if str(eee) == IEIREE:
                                                    raise_re_error(fvi, vdi)
                                                raise
                                            if len(tle) != 1:
                                                continue
                                            # tracer for fixing regexes
                                            # print(':', end='') # tracer
                                            _translate(
                                                result_line_description,
                                                fvi,
                                                tle[0].groupdict(),
                                            )
                                            break
                                # print() # tracer for fixing regular expressions
                found |= bool(est)
                # print() # tracer for fixing regular expressions
            if not found:
                # tracer for fixing regular expressions
                # print(difference_item.data_tag, found, '\n') # tracer

                # Call _select_result_line for each line of text.
                result_line_description = (
                    selected_text,
                    difference_item.data_tag,
                    re_competition,
                    difference_item._filename,
                    competition_lookup,
                    difference_item.headers,
                )
                for tle in difference_item.edited_text.splitlines():
                    if len(tle):
                        # tracer for fixing regular expressions
                        # print('|', repr(tle)) # tracer
                        _select_result_line(result_line_description, tle)
                # tracer for fixing regular expressions
                # print('') # tracer

        # This is where next batch of future code to handle tabular input files
        # is needed. The code to populate the EventContext instance _tabular
        # attribute is already in place.
        selected_text.convert_tabular_data_to_sequence()

        # These name calculation methods can take a long time to run.
        # A few minutes compared with well under a minute for the rest.
        truncate = selected_text.fixture_list_names(team_name_lookup)
        selected_text.results_names(truncate=truncate)

        return selected_text


def _is_name_and_number_set_a_score(names, numbers):
    """Return True if numbers can be interpreted and a match or game result.

    ' 1 0 ', '2 0', '0.5 0.5', '0.5 3.5'. and similar, can mean game or match
    scores.  Add in a third number and it must mean a board number and a game
    or match score, if it has meaning at all.

    A single ' 0.5 ' must mean a drawn game, being a short form of ' 0.5 0.5 ',
    like ' 1-0 ' meaning ' 1 0 ' and so forth.  ' draw ' fits with ' 1-0 ' in
    more reasonable way.  But ' 1 ' meaning ' 1-0 ' is not allowed.

    ' 2 0.5 ', '2.1 0.5 ', ' 0.5 3.6 ', and similar, must be a board number and
    drawn game, if the combination has meaning at all.

    """
    if not len(names) in {1, 2}:
        return False
    if len(numbers) == 3:
        return True
    if len(numbers) != 2:
        return False
    if len([n for n in numbers if n.endswith(".5")]) == 1:
        return False
    return True


def _board_round_indicator(text):
    """Return index of board in list of three numbers extracted from text.

    It is assumed three numbers and two names were extracted from t, and that
    other hints such as numbers starting '0' or ending '.5' did not help.

    """
    number_list = [
        e + 1
        for e, m in enumerate(
            [n for n in RE_NUMBERS.split(text) if len(n.strip())]
        )
        if not RE_NUMBERS.match(m)
    ]
    gauge = number_list[0] * number_list[-1]
    return 0 if gauge > 5 else 2 if gauge < 5 else 1


def _select_result_line(result_line_description, text):
    """Return normalized line of event data."""
    (
        context,
        data_tag,
        re_competition,
        source,
        competition_lookup,
        headers,
    ) = result_line_description

    # Some lines may have the prefix indicating results of games played-on or
    # adjudicated, both getting rare now, after an initial report saying this
    # is happening.  This possibility is ignored until the csv, swiss, and
    # all-play-all formats have been tried.

    # text may have game results derived from a csv file where each line also
    # contains the match details.  The data was arranged in a specific order,
    # slightly odd when eyeballed, to simplify, or perhaps make possible, the
    # processing done here.  Still, it is probably easier to eyeball than the
    # raw csv data.
    # '+2' because REPORT_TABLE defines one data item which does not appear in
    # the TABLE_DELIMITER delimited text.
    if text.count(TABLE_DELIMITER) + 2 == len(REPORT_TABLE):
        tsc = [t.strip() for t in text.split(TABLE_DELIMITER)]
        try:
            return TableEventData(
                datatag=data_tag,
                context=context,
                found=Found.CSV_TABULAR,
                teamone=tsc[4],
                competition=_lookup_competition(
                    competition_lookup,
                    tsc[0].lower() if tsc[0] else _ALL_SECTIONS,
                ),
                competition_round=tsc[3],
                result_date=tsc[2],
                teamonescore=tsc[5],
                nameone=tsc[6],
                score=tsc[7],
                nametwo=tsc[8],
                teamtwoscore=tsc[9],
                teamtwo=tsc[10],
                numbers=[tsc[11]],
                colour=tsc[12],
                source=source,
                headers=headers,
            )
        except:
            return EventData(
                datatag=data_tag,
                found=Found.TABLE_FORMAT,
                raw=text,
                headers=headers,
            )

    # text may have results either in all-play-all or in swiss table style.
    # Exactly one number must be present: the player's number in the table.
    # text must produce exactly one item containining none-whitespace when
    # split by the other items, which is assumed to be the player's name.

    # Check for swiss implying absence of all-play-all
    split_text = RE_SWISS.split(text)
    swiss = [s for s in split_text if len(s.strip())]
    if len(split_text) > 1 and len(swiss):
        if len(swiss) > 1:
            return EventData(
                datatag=data_tag,
                found=Found.SPLIT_SWISS_DATA,
                raw=text,
                headers=headers,
            )
        if len(RE_ALL_PLAY_ALL.findall(swiss[0])):
            return EventData(
                datatag=data_tag,
                found=Found.APA_IN_SWISS_DATA,
                raw=text,
                headers=headers,
            )
        pin = RE_PIN.findall(swiss[0])
        if len(pin) == 0:
            return EventData(
                datatag=data_tag,
                found=Found.NO_PIN_SWISS,
                raw=text,
                headers=headers,
            )
        tssw = RE_PIN.split(swiss[0])
        if len(tssw) != 2:
            return EventData(
                datatag=data_tag,
                found=Found.EXTRA_PIN_SWISS_DATA,
                raw=text,
                headers=headers,
            )
        if len([s for s in tssw if len(s.strip())]) != 1:
            return EventData(
                datatag=data_tag,
                found=Found.NAME_SPLIT_BY_PIN_SWISS,
                raw=text,
                headers=headers,
            )
        return EventData(
            datatag=data_tag,
            context=context,
            found=Found.SWISS_PAIRING_CARD,
            pin=pin[0],
            person=" ".join(" ".join(tssw).split()),
            swiss=[_convert_result_first(t) for t in RE_SWISS.findall(text)],
            source=source,
            headers=headers,
        )

    # Check for all-play-all assuming absence of swiss
    split_text = RE_ALL_PLAY_ALL.split(text)
    if len(split_text) > 1:
        all_play_all = [s for s in split_text if len(s.strip())]
        if len(all_play_all) > 1:
            # print(split_text)
            # print(all_play_all)
            return EventData(
                datatag=data_tag,
                found=Found.SPLIT_APA_DATA,
                raw=text,
                headers=headers,
            )
        pin = RE_PIN.findall(all_play_all[0])
        if len(pin) == 0:
            return EventData(
                datatag=data_tag,
                found=Found.NO_PIN_APA,
                raw=text,
                headers=headers,
            )
        tsapa = RE_PIN.split(all_play_all[0])
        if len(tsapa) != 2:
            return EventData(
                datatag=data_tag,
                found=Found.EXTRA_PIN_APA_DATA,
                raw=text,
                headers=headers,
            )
        if len([s for s in tsapa if len(s.strip())]) != 1:
            return EventData(
                datatag=data_tag,
                found=Found.NAME_SPLIT_BY_PIN_APA,
                raw=text,
                headers=headers,
            )
        return EventData(
            datatag=data_tag,
            context=context,
            found=Found.APA_PLAYER_CARD,
            pin=pin[0],
            person=" ".join(" ".join(tsapa).split()),
            allplayall=RE_ALL_PLAY_ALL.findall(text),
            source=source,
            headers=headers,
        )

    # 'played_on' at the start of a line is removed and a flag set.
    # On lines reporting a match result it means the games included in this
    # report must correspond to other match reports reporting the games as
    # unfinished.
    # Same for individual games, but it is not necessary to do this for each
    # game within a 'played_on' match report.
    # This trick is needed only where the reports of adjourned or adjudicated
    # results do not include enough information to identify the game.  Often
    # the date is omitted meaning it is necessary to check there is only one
    # possible corresponding unfinished game report.
    split_text = RE_PLAYED_ON.split(text, maxsplit=1)
    played_on = len(split_text) == 2
    if played_on:
        text = split_text[1]

    # Check for round dates for all-play-all and swiss competitions
    # text must contain exactly a competition name and more than one date.
    # Pick out the competition first, noting that later scans pick dates first.
    try:
        tsc = re_competition.split(text, maxsplit=1)
    except ValueError as exc:
        if re_competition.pattern == "()":
            raise EventParserError(
                "".join(
                    (
                        "Attempt to extract competition name \n\n'",
                        re_competition.pattern[1:-1],
                        "'\n\nfailed: ",
                        "it is likely no competition is given in the ",
                        "configuration file.\n\n",
                        "The error was described:\n\n",
                        str(exc),
                    )
                )
            )
        raise

    # A swiss tournament table report is assumed to have more than one round
    # and hence more than one date in the list after the competition name.
    # With monthly rating the first round of a club championship may be
    # reported on it's own; and a dummy second round date is needed to force
    # swiss tournament table processing.
    # <word> <date> is valid in non-swiss tournament table context and
    # cannot be taken as 'swiss' because it is not yet known that the
    # context is 'swiss'.
    if len(tsc) == 3:
        if len(tsc[0].strip()) == 0:
            if len("".join(RE_DATE.split(tsc[2])).strip()) == 0:
                date = RE_DATE.findall(tsc[2])
                if len(date) > 1:
                    return EventData(
                        datatag=data_tag,
                        found=Found.COMPETITION_AND_DATES,
                        context=context,
                        competition=_lookup_competition(
                            competition_lookup, tsc[1].lower()
                        ),
                        rounddates=date,
                        source=source,
                        headers=headers,
                    )

    # text must contain less than three dates.
    # Use tsdate, not split_text, to keep for later if text turns out to be fixture.
    tsdate = RE_DATE.split(text)
    if len(tsdate) > 3:
        return EventData(
            datatag=data_tag,
            found=Found.MORE_THAN_TWO_DATES,
            raw=text,
            headers=headers,
        )

    # Two dates are the start and end dates of an event.
    # One only of the split items must contain some non-whitespace and is
    # the event.
    if len(tsdate) == 3:
        tsd = [t for t in [" ".join(s.split()) for s in tsdate] if len(t)]
        if len(tsd) > 1:
            return EventData(
                datatag=data_tag,
                found=Found.DATE_SPLITS_EVENT_NAME,
                raw=text,
                headers=headers,
            )
        start_date, end_date = RE_DATE.findall(text)
        ed_kargs = dict(
            datatag=data_tag,
            found=Found.EVENT_AND_DATES,
            context=context,
            startdate=start_date,
            enddate=end_date,
            source=source,
            headers=headers,
        )
        if len(tsd):
            ed_kargs["eventname"] = tsd[0]
        return EventData(**ed_kargs)

    # One date is the date a match or game was played, or the date in the
    # fixture list when a match is scheduled to be played.
    # Strip out the date and retain rest of text.
    # Overrule date found when looking for all-play-all and swiss round dates.
    if len(tsdate) == 2:
        date = RE_DATE.findall(text)[0]
        tsnd = "".join(tsdate)
    else:
        date = ""
        tsnd = text

    # tsnd may contain a competition name like ' Division 1 '.  The '1' is
    # a valid score or board number so take competition name out of text.
    # Overrule competition extracted when looking for all-play-all and swiss
    # round dates.
    tsc = re_competition.split(tsnd, maxsplit=1)
    if len(tsc) == 3:
        competition = _lookup_competition(
            competition_lookup, " ".join(tsc[1].split()).lower()
        )
        tsnd = " ".join((tsc[0], tsc[2]))
    else:
        competition = None

    # tsnd may end with ' result only' if the game is not included in totals
    # which may be used to validate a set of results, such as a match score.
    # The regex is assumed to match only at end of string.
    # Remove it from string to checking validity of score.
    split_text = RE_RESULT_ONLY.split(tsnd)
    result_only = len(split_text) == 2
    if result_only:
        tsnro = split_text[0]
    else:
        tsnro = tsnd

    # tsnro must contain at most two score items and at most one board item.
    # Board items cannot be distinguished from some points items, and scores
    # can be written ' 1-0 ' and ' draw ', instead of ' 1 0 ' perhaps separated
    # by a player name ot names.  So look at ' 1-0 ' and similar first.

    # First stage checks for void unfinished and defaulted games, allowing for
    # board number to be present.  If a defaulted game is found try to decide
    # who won.
    void = RE_VOID.findall(tsnro)
    if len(void) == 1:
        void = "".join(void[0].split()).lower()
        names = [
            " ".join(n)
            for n in [t.split() for t in RE_VOID.split(tsnro)]
            if len(n)
        ]
        board = ""
        ed_kargs = dict(
            datatag=data_tag,
            context=context,
            result_date=date,
            source=source,
            headers=headers,
        )
        if played_on:
            ed_kargs["played_on"] = PLAYED_ON
        if competition:
            ed_kargs["competition"] = competition

        # Interpretation of numbers depends on what matched RE_VOID.
        # Zero or one numbers make sense for matches other than 'default',
        # being the presence or absence of a board number.
        # Up to three numbers make sense when the match is 'default'.
        numbers = RE_POINTS.findall(" ".join(names))
        if len(numbers) > 3:
            return EventData(
                datatag=data_tag,
                found=Found.EXTRA_SCORE_AND_BOARD_ITEMS,
                raw=text,
                headers=headers,
            )

        # default is the awkward one.
        if void == "default":

            # number rules for setting board to be added.
            # Valid default lines when three numbers are present, ignoring
            # leading and trailing whitespace and the board number, are:
            # '0 default 1 <name>'
            # 'default 0 1 <name>'
            # 'default 0 <name> 1'
            # '1 <name> 0 default'
            # '<name> 1 0 default'
            # '<name> 1 default 0'
            # The options above are the valid lines with two numbers present.
            # 'default' must be adjacent to two of '0', '1', edge of string.
            # When two numbers are present 'default' must be adjacent to a '0'.
            # If one number is present '1' is always
            if len(numbers) == 0:

                # Position of 'default' in string decides result
                vsrc = tsnro.split()
                if len(vsrc) == 1:
                    ed_kargs["score"] = Score.default
                elif vsrc[0].lower() == void:
                    ed_kargs["score"] = Score.away_win_default
                elif vsrc[-1].lower() == void:
                    ed_kargs["score"] = Score.home_win_default
                else:
                    ed_kargs["score"] = Score.default

            elif len(numbers) == 1:

                # 'default' must be adjacent to both the number and the edge of
                # the string.
                # Allowing as many ways as possible to present a result:
                # 'Jones 1 Smith 0'
                # 'Jones 1 0 Smith'
                # 'Jones Smith 1 0'
                # 'Jones 1-0 Smith'
                # and their equivalents giving a board number, plus odd-looking
                # others like '1 0 4 Jones Smith', causes problems interpreting
                # 'Jones 1 default'.
                # The likely meaning is different if the non-default results
                # are 'Jones 1 Smith 0' rather than 'Jones 1-0 Smith'.  '1-0'
                # is a single symbol, not two delimited numbers.
                # We have to choose one meaning here.
                # '1' is part of result in 'Jones 1 default'.
                # '4' is board number in 'Jones 4 default'.
                # 'Jones 0 default' is a bad result, say something like
                # '0 Jones 1 0 default' to get '0' as board number rather than
                # the board number deduced from result position.  '1' also.
                vsrc = tsnro.split()
                if numbers[0] == "0":
                    ed_kargs["score"] = Score.bad_score
                elif vsrc[0].lower() == void and vsrc[1] == numbers[0]:
                    if numbers[0] != "1":
                        ed_kargs["numbers"] = [numbers[0]]
                    ed_kargs["score"] = Score.away_win_default
                elif vsrc[-1].lower() == void and vsrc[-2] == numbers[0]:
                    if numbers[0] != "1":
                        ed_kargs["numbers"] = [numbers[0]]
                    ed_kargs["score"] = Score.home_win_default
                else:
                    ed_kargs["score"] = Score.bad_score

            elif len(numbers) == 2:

                # 'default' must be adjacent to two numbers or one number and
                # the edge of the string.
                # A non-'0' number is board number if the other number is '1'.
                # 'Jones 4 default 1' and '1 default 4 Jones' are nonsense, but
                # all versions with 'default' at edge of string make sense, as
                # are 'Jones 1 default 4' and '4 default 1 Jones'.
                # League rules may make reports like 'Jones 4 default 1' valid.
                # Jones did not turn up and loses by default, but the other
                # player is not named because it would then count as playing
                # for the team either out of strength order or with an effect
                # on eligibility for other teams.  Use 'Jones 4 def-1' instead.
                vsrc = tsnro.split()
                vsrcwinh = [{"1-0": "1"}.get(v, v) for v in vsrc]
                vsrcwina = [{"0-1": "1"}.get(v, v) for v in vsrc]
                if "1" not in numbers and "0" in numbers:
                    ed_kargs["score"] = Score.bad_score
                elif vsrc[0].lower() == void and vsrcwina[1] in numbers:
                    ed_kargs["score"] = Score.away_win_default
                    numbers = [n for n in numbers if n != "0"]
                    if len(numbers) == 2:
                        numbers.remove("1")
                        ed_kargs["numbers"] = [numbers[0]]
                elif vsrc[-1].lower() == void and vsrcwinh[-2] in numbers:
                    ed_kargs["score"] = Score.home_win_default
                    numbers = [n for n in numbers if n != "0"]
                    if len(numbers) == 2:
                        numbers.remove("1")
                        ed_kargs["numbers"] = [numbers[0]]
                else:
                    voiditem = [v.lower() for v in vsrc].index(void)
                    if voiditem == 0 and vsrcwina[1] not in numbers:
                        ed_kargs["score"] = Score.bad_score
                    elif voiditem == len(vsrc) and vsrcwinh[-2] not in numbers:
                        ed_kargs["score"] = Score.bad_score
                    elif (
                        vsrcwina[voiditem + 1] not in numbers
                        or vsrcwinh[voiditem - 1] not in numbers
                    ):
                        ed_kargs["score"] = Score.bad_score
                    else:
                        numbers = [n for n in numbers if n != "0"]
                        if len(numbers) == 2:
                            numbers.remove("1")
                            if vsrc[-1] == numbers[0]:
                                ed_kargs["score"] = Score.home_win_default
                                ed_kargs["numbers"] = [numbers[0]]
                            elif vsrc[0] == numbers[0]:
                                ed_kargs["score"] = Score.away_win_default
                                ed_kargs["numbers"] = [numbers[0]]
                            else:
                                ed_kargs["score"] = Score.bad_score
                        elif len(numbers) == 1:
                            if numbers[0] == "1":
                                if vsrc.index("1") < vsrc.index("0"):
                                    ed_kargs["score"] = Score.home_win_default
                                else:
                                    ed_kargs["score"] = Score.away_win_default
                            else:
                                ed_kargs["score"] = Score.bad_score
                        else:
                            ed_kargs["score"] = Score.bad_score

            elif len(numbers) == 3:

                # 'default' must be adjacent to two numbers or one number and
                # the edge of the string.
                # 'default' replaces the name of the player who defaulted.
                # If someone named Default plays a game, initials or forenames
                # must be given to avoid confusion with the 'default' case.
                # It is plausible to allow abbreviations of 'default' to mean
                # a defaulted game as well.  But these run the risk of causing
                # results to be rejected by the len(RE_VOID) == 1 test, as in:
                # 'DEF Jones 1 0 default', assuming character case is ignored.
                # Use 'DE Jones 1 0 default' instead if the 'def' abbreviation
                # is allowed.
                vsrc = tsnro.split()
                if "1" not in numbers or "0" not in numbers:
                    ed_kargs["score"] = Score.bad_score
                else:
                    names = [
                        " ".join(n)
                        for n in [t.split() for t in RE_BOARD.split(tsnro)]
                    ]
                    if len([n for n in names if len(n)]) == 2:
                        names = [n for n in names if len(n)]
                        nonboard = [n for n in numbers if n in "01"]
                        if names[0].lower() == void:
                            if len(nonboard) > 1:
                                if nonboard[-1] == "1":
                                    ed_kargs["score"] = Score.away_win_default
                                    if len(nonboard) == 3:
                                        ed_kargs["numbers"] = ["1"]
                                    else:
                                        ed_kargs["numbers"] = [
                                            [
                                                n
                                                for n in numbers
                                                if n not in "01"
                                            ][0]
                                        ]
                                else:
                                    ed_kargs["score"] = Score.bad_score
                            else:
                                ed_kargs["score"] = Score.bad_score
                        elif names[-1].lower() == void:
                            if len(nonboard) > 1:
                                if nonboard[0] == "1":
                                    ed_kargs["score"] = Score.home_win_default
                                    if len(nonboard) == 3:
                                        ed_kargs["numbers"] = ["1"]
                                    else:
                                        ed_kargs["numbers"] = [
                                            [
                                                n
                                                for n in numbers
                                                if n not in "01"
                                            ][0]
                                        ]
                                else:
                                    ed_kargs["score"] = Score.bad_score
                            else:
                                ed_kargs["score"] = Score.bad_score
                        else:
                            ed_kargs["score"] = Score.bad_score
                    elif len([n for n in names if len(n)]) == 1:
                        if numbers[1] == "0" and numbers[0] == "1":
                            if names[0].lower() != void:
                                ed_kargs["score"] = Score.home_win_default
                            else:
                                ed_kargs["score"] = Score.bad_score
                            ed_kargs["numbers"] = [numbers[2]]
                        elif numbers[1] == "0" and numbers[-1] == "1":
                            if names[-1].lower() != void:
                                ed_kargs["score"] = Score.away_win_default
                            else:
                                ed_kargs["score"] = Score.bad_score
                            ed_kargs["numbers"] = [numbers[0]]
                        elif numbers[-1] == "0":
                            names = [n.lower() for n in names]
                            if void not in names:
                                ed_kargs["score"] = Score.bad_score
                            elif names.index(void) > 1:
                                ed_kargs["score"] = Score.home_win_default
                            else:
                                ed_kargs["score"] = Score.bad_score
                            if numbers[1] == "1":
                                ed_kargs["numbers"] = [numbers[0]]
                            else:
                                ed_kargs["numbers"] = [numbers[1]]
                        elif numbers[0] == "0":
                            names = [n.lower() for n in names]
                            if void not in names:
                                ed_kargs["score"] = Score.bad_score
                            elif names.index(void) < 2:
                                ed_kargs["score"] = Score.away_win_default
                            else:
                                ed_kargs["score"] = Score.bad_score
                            if numbers[1] == "1":
                                ed_kargs["numbers"] = [numbers[-1]]
                            else:
                                ed_kargs["numbers"] = [numbers[1]]
                    else:
                        ed_kargs["score"] = Score.bad_score

            ed_kargs["nameone"] = ""
            ed_kargs["nametwo"] = ""
            ed_kargs["found"] = Found.RESULT
            # print('!', end='') # tracer for fixing regular expressions
            return EventData(**ed_kargs)

        if void == "unfinished":
            if len(numbers) > 1:

                # State a bad result found rather than ignore.
                ed_kargs["score"] = Score.bad_score
                ed_kargs["nameone"] = ""  # or just not set at all?
                ed_kargs["nametwo"] = ""  # or just not set at all?
                ed_kargs["found"] = Found.RESULT
                # print('!', end='') # tracer for fixing regular expressions
                return EventData(**ed_kargs)

            nbnames = []
            for name_item in names:
                non_board_numbers = []
                for board_item in RE_BOARD.split(name_item):
                    if board:
                        non_board_numbers.append(board_item.strip())
                    elif RE_BOARD.match(board_item):
                        board = board_item
                    else:
                        non_board_numbers.append(board_item.strip())
                nbnames.append(" ".join(non_board_numbers).strip())
            names = [n for n in nbnames if len(n)]
            nbnames = " ".join(names)
            if len(names) == 2:
                ed_kargs["nameone"] = names[0]
                ed_kargs["nametwo"] = names[1]
            elif names:
                names = names[0].split()
                if len(names) > 2:
                    ed_kargs["names"] = " ".join(names)
                elif len(names) == 2:
                    ed_kargs["nameone"] = names[0]
                    ed_kargs["nametwo"] = names[1]
                else:
                    names = None
            else:
                names = None
            if names is not None:
                ed_kargs["score"] = Score.unfinished
                if result_only:
                    ed_kargs["result_only"] = True
                if board:
                    ed_kargs["numbers"] = [board]
                ed_kargs["found"] = (
                    Found.RESULT if "names" in ed_kargs else Found.RESULT_NAMES
                )
                # print('!', end='') # tracer for fixing regular expressions
                return EventData(**ed_kargs)

        elif void == "void":
            if len(numbers) > 1:

                # State a bad result found rather than ignore.
                ed_kargs["score"] = Score.bad_score
                ed_kargs["nameone"] = ""  # or just not set at all?
                ed_kargs["nametwo"] = ""  # or just not set at all?
                ed_kargs["found"] = Found.RESULT
                # print('!', end='') # tracer for fixing regular expressions
                return EventData(**ed_kargs)

            # Why does commenting these two lines make report.py work right?
            if len(numbers):
                ed_kargs["numbers"] = [numbers[0]]
            ed_kargs["score"] = Score.void
            ed_kargs["nameone"] = ""
            ed_kargs["nametwo"] = ""
            ed_kargs["found"] = Found.RESULT
            # print('!', end='') # tracer for fixing regular expressions
            return EventData(**ed_kargs)

        elif void == "matchdefault":
            if len(numbers):

                # State a bad result found rather than ignore.
                ed_kargs["score"] = Score.bad_score
                ed_kargs["nameone"] = ""  # or just not set at all?
                ed_kargs["nametwo"] = ""  # or just not set at all?
                ed_kargs["found"] = Found.RESULT
                # print('!', end='') # tracer for fixing regular expressions
                return EventData(**ed_kargs)

            ed_kargs["score"] = Score.match_defaulted
            ed_kargs["nameone"] = ""
            ed_kargs["nametwo"] = ""
            ed_kargs["found"] = Found.RESULT
            # print('!', end='') # tracer for fixing regular expressions
            return EventData(**ed_kargs)

        elif void.startswith("1"):
            if len(numbers) > 1 or void.endswith("1"):

                # State a bad result found rather than ignore.
                ed_kargs["score"] = Score.bad_score
                ed_kargs["nameone"] = ""  # or just not set at all?
                ed_kargs["nametwo"] = ""  # or just not set at all?
                ed_kargs["found"] = Found.RESULT
                # print('!', end='') # tracer for fixing regular expressions
                return EventData(**ed_kargs)

            # Why does commenting these two lines make report.py work right?
            if len(numbers):
                ed_kargs["numbers"] = [numbers[0]]
            ed_kargs["score"] = Score.home_win_default
            ed_kargs["nameone"] = ""
            ed_kargs["nametwo"] = ""
            ed_kargs["found"] = Found.RESULT
            # print('!', end='') # tracer for fixing regular expressions
            return EventData(**ed_kargs)

        elif void.startswith("double") or void.startswith("dbl"):
            if len(numbers) > 1 or void.endswith("1"):

                # State a bad result found rather than ignore.
                ed_kargs["score"] = Score.bad_score
                ed_kargs["nameone"] = ""  # or just not set at all?
                ed_kargs["nametwo"] = ""  # or just not set at all?
                ed_kargs["found"] = Found.RESULT
                # print('!', end='') # tracer for fixing regular expressions
                return EventData(**ed_kargs)

            # Why does commenting these two lines make report.py work right?
            if len(numbers):
                ed_kargs["numbers"] = [numbers[0]]
            ed_kargs["score"] = Score.double_default
            ed_kargs["nameone"] = ""
            ed_kargs["nametwo"] = ""
            ed_kargs["found"] = Found.RESULT
            # print('!', end='') # tracer for fixing regular expressions
            return EventData(**ed_kargs)

        elif void.endswith("1"):
            if len(numbers) > 1:

                # State a bad result found rather than ignore.
                ed_kargs["score"] = Score.bad_score
                ed_kargs["nameone"] = ""  # or just not set at all?
                ed_kargs["nametwo"] = ""  # or just not set at all?
                ed_kargs["found"] = Found.RESULT
                # print('!', end='') # tracer for fixing regular expressions
                return EventData(**ed_kargs)

            # Why does commenting these two lines make report.py work right?
            if len(numbers):
                ed_kargs["numbers"] = [numbers[0]]
            ed_kargs["score"] = Score.away_win_default
            ed_kargs["nameone"] = ""
            ed_kargs["nametwo"] = ""
            ed_kargs["found"] = Found.RESULT
            # print('!', end='') # tracer for fixing regular expressions
            return EventData(**ed_kargs)

        else:

            # State an error result found rather than ignore.
            ed_kargs["score"] = Score.error
            ed_kargs["nameone"] = ""
            ed_kargs["nametwo"] = ""
            ed_kargs["found"] = Found.RESULT
            # print('!', end='') # tracer for fixing regular expressions
            return EventData(**ed_kargs)

    # Second stage checks for a pair of points items like ' 1 0 ' perhaps
    # separated by one or two player names and allows one board item to be
    # present.  The first points item which could be a board item is chosen as
    # the board item. Board items do not start with '0'.
    numbers = RE_POINTS.findall(tsnro)
    names = [
        " ".join(n)
        for n in [t.split() for t in RE_POINTS.split(tsnro)]
        if len(n)
    ]
    if _is_name_and_number_set_a_score(names, numbers):
        # print('@@@@') # temporary tracer for fixing regular expressions
        # print(repr(text.replace('\xbd', '?')),
        #      names,
        #      [n.replace('\xbd', '?') for n in numbers]) # tracer
        ed_kargs = dict(
            datatag=data_tag,
            context=context,
            result_date=date,
            source=source,
            headers=headers,
        )
        if played_on:
            ed_kargs["played_on"] = PLAYED_ON
        if competition:
            ed_kargs["competition"] = competition
        if len(numbers) == 2:
            ed_kargs["score"] = " ".join((numbers[0], numbers[1]))
        elif len(names) == 2:

            # If neither all nor none of the items in numbers are draw markers
            # use the singleton item as the round or board: the total score
            # must be an integer.  If the choice is wrong the total score is
            # wrong too.
            nlist = [n for n in numbers if RE_DRAW_ITEM.findall(n)]
            if len(nlist) == 2:
                ed_kargs["score"] = " ".join(
                    (
                        numbers.pop(numbers.index(nlist[0])),
                        numbers.pop(numbers.index(nlist[1])),
                    )
                )
                ed_kargs["numbers"] = [numbers[0]]
            elif len(nlist) == 1:
                ed_kargs["numbers"] = [numbers.pop(numbers.index(nlist[0]))]
                ed_kargs["score"] = " ".join((numbers[0], numbers[1]))
            else:

                # Assumptions are made using the count of '1' and '0' items.
                # These can be overruled by expressing scores like '0-1' or
                # '4-0'.  This might be awkward to arrange for results picked
                # using regular expressions in the configuration file.
                zero = [n for n in numbers if n == "0"]
                one = [n for n in numbers if n == "1"]

                # If one item in numbers is '0' several options exists.
                if len(zero) == 1:

                    # If another item in numbers is '1' use the unpicked item
                    # as the round or board.
                    # This catches round one match results where one team wins
                    # all games, as well as decisive game results.
                    if len(one) == 1:
                        ed_kargs["score"] = " ".join(
                            [n for n in numbers if n in zero + one]
                        )
                        ed_kargs["numbers"] = [
                            n for n in numbers if n not in zero + one
                        ]

                    # If none of the items in numbers is '1' use the first item
                    # as the round or board.
                    elif len(one) == 0:
                        ed_kargs["numbers"] = [numbers.pop(0)]
                        ed_kargs["score"] = " ".join((numbers[0], numbers[1]))

                    # If two of the other items in numbers are '1' use the first
                    # '1' item as the round or board.
                    # The explicit test is used but it should be equivalent to
                    # 'anything else'.
                    elif len(one) == 2:
                        ed_kargs["numbers"] = [
                            numbers.pop(numbers.index(one[0]))
                        ]
                        ed_kargs["score"] = " ".join((numbers[0], numbers[1]))

                # If two items in numbers are '0' and the other is '1' use the
                # first '0' item as the round or board.
                # All choices are probably wrong so maybe these lines should be
                # ignored rather than picking a valid game result.
                elif len(zero) == 2 and len(one) == 1:
                    ed_kargs["numbers"] = [numbers.pop(numbers.index(zero[0]))]
                    ed_kargs["score"] = " ".join((numbers[0], numbers[1]))

                # Pick the round or board item using adjacency of name and
                # number items as defined by the _board_round_indicator()
                # function.
                # Most match results which quote a round will get to here.
                # The only game results which get to here are draws with board
                # numbers like '3.5', from a plausible way of labelling games
                # in a rapidplay match with multiple games per board.
                else:
                    ed_kargs["numbers"] = [
                        numbers.pop(_board_round_indicator(tsnro))
                    ]
                    ed_kargs["score"] = " ".join((numbers[0], numbers[1]))
        else:

            # Names are adjacent.  Middle number cannot be the board or round
            # according to _board_round_indicator() call.  Last number is board
            # or round if names in first element.
            if names[0] == RE_NUMBERS.split(tsnro)[0]:
                ed_kargs["numbers"] = [numbers.pop()]
            else:
                ed_kargs["numbers"] = [numbers.pop(0)]
            ed_kargs["score"] = " ".join((numbers[0], numbers[1]))
        if len(names) == 2:
            ed_kargs["nameone"] = names[0]
            ed_kargs["nametwo"] = names[1]
        else:
            names = names[0].split()
            if len(names) > 2:
                ed_kargs["names"] = " ".join(names)
            elif len(names) == 2:
                ed_kargs["nameone"] = names[0]
                ed_kargs["nametwo"] = names[1]
            else:
                names = None
        if names is not None:
            if result_only:
                ed_kargs["result_only"] = True
            ed_kargs["found"] = (
                Found.RESULT if "names" in ed_kargs else Found.RESULT_NAMES
            )
            # print('!', end='') # tracer for fixing regular expressions
            return EventData(**ed_kargs)

    # Third stage checks for single items like ' 1-0 ' and allows one board
    # item to be present.  Items like ' draw ' and single ' 0.5 ' meaning a
    # draw are ignored in this stage.
    score = RE_SCORE.findall(tsnro)
    if len(score) > 1:
        return EventData(
            datatag=data_tag,
            found=Found.EXTRA_SCORE_AND_BOARD_ITEMS,
            raw=text,
            headers=headers,
        )
    if len(score) == 1:
        names = [
            " ".join(n)
            for n in [t.split() for t in RE_SCORE.split(tsnro)]
            if len(n)
        ]
        board = ""
        nbnames = []
        for name_item in names:
            non_board_numbers = []
            for board_item in RE_BOARD.split(name_item):
                if board:
                    non_board_numbers.append(board_item.strip())
                elif RE_BOARD.match(board_item):
                    board = board_item
                else:
                    non_board_numbers.append(board_item.strip())
            nbnames.append(" ".join(non_board_numbers).strip())
        names = [n for n in nbnames if len(n)]
        nbnames = " ".join(names)
        if len(RE_DRAW.findall(nbnames)):
            return EventData(
                datatag=data_tag,
                found=Found.EXTRA_DRAW_ITEMS_SCORE,
                raw=text,
                headers=headers,
            )
        ed_kargs = dict(
            datatag=data_tag,
            context=context,
            result_date=date,
            source=source,
            headers=headers,
        )
        if played_on:
            ed_kargs["played_on"] = PLAYED_ON
        if competition:
            ed_kargs["competition"] = competition
        ed_kargs["score"] = " ".join(RE_SCORE_SEP.split(score[0]))
        if board:
            ed_kargs["numbers"] = [board]
        if len(names) == 2:
            ed_kargs["nameone"] = names[0]
            ed_kargs["nametwo"] = names[1]
        elif names:
            names = names[0].split()
            if len(names) > 2:
                ed_kargs["names"] = " ".join(names)
            elif len(names) == 2:
                ed_kargs["nameone"] = names[0]
                ed_kargs["nametwo"] = names[1]
            else:
                names = None
        else:
            names = None
        if names is not None:
            if result_only:
                ed_kargs["result_only"] = True
            ed_kargs["found"] = (
                Found.RESULT if "names" in ed_kargs else Found.RESULT_NAMES
            )
            # print('!', end='') # tracer for fixing regular expressions
            return EventData(**ed_kargs)

    # Fourth stage checks for single items like ' draw ' or single ' 0.5 '
    # items and allows one board item to be present.
    # 3 Smith 0.5 Jones is interpreted as a 3-0.5 result rather than a draw
    # on board 3 so match scores like Anytown 0.5 Toytown 3.5 are not seen
    # as a result on board 3.5.  Use ' draw ' instead of ' 0.5 '.
    score = RE_DRAW.findall(tsnro)
    if len(score) == 1:
        names = [
            " ".join(n)
            for n in [t.split() for t in RE_DRAW.split(tsnro)]
            if len(n)
        ]
        board = ""
        nbnames = []
        for name_item in names:
            non_board_numbers = []
            for board_item in RE_BOARD.split(name_item):
                if board:
                    non_board_numbers.append(board_item.strip())
                elif RE_BOARD.match(board_item):
                    board = board_item
                else:
                    non_board_numbers.append(board_item.strip())
            nbnames.append(" ".join(non_board_numbers).strip())
        names = [n for n in nbnames if len(n)]
        nbnames = " ".join(names)
        ed_kargs = dict(
            datatag=data_tag,
            context=context,
            result_date=date,
            source=source,
            headers=headers,
        )
        if played_on:
            ed_kargs["played_on"] = PLAYED_ON
        if competition:
            ed_kargs["competition"] = competition
        ed_kargs["score"] = "\xbd \xbd"
        if board:
            ed_kargs["numbers"] = [board]
        if len(names) == 2:
            ed_kargs["nameone"] = names[0]
            ed_kargs["nametwo"] = names[1]
        elif names:
            names = names[0].split()
            if len(names) > 2:
                ed_kargs["names"] = " ".join(names)
            elif len(names) == 2:
                ed_kargs["nameone"] = names[0]
                ed_kargs["nametwo"] = names[1]
            else:
                names = None
        else:
            names = None
        if names is not None:
            if result_only:
                ed_kargs["result_only"] = True
            ed_kargs["found"] = (
                Found.RESULT if "names" in ed_kargs else Found.RESULT_NAMES
            )
            # print('!', end='') # tracer for fixing regular expressions
            return EventData(**ed_kargs)

    # Absence of any kind of score, and presence of date and competition
    # makes line an entry in fixture list, or date of following games in
    # competition if rest of line is whitespace.
    # Presence of round adds the possibility the line is a round header for
    # following games in a competition.  The line will be treated as part of
    # a fixture list if enough extra text is present.
    # Valid rounds are a subset of valid scores so if more than one round
    # is present the line was treated as a game result earlier.
    if date and competition:

        # Fixture lists often give the day as well as the date, for example
        # 'Thur 29 Oct 2012' rather than '29 Oct 2012'.  This can be used to
        # validate the date later if desired.
        # Day must be adjacent to date, so 'Thur Final 29 Oct 2012' does not
        # count as giving the day.
        # Refer back to text because date and competition stripped out of tsnd.
        day = ""
        split_text = RE_FIXTURE_DATE.split(text)
        if len(split_text) != 1:
            if split_text[1]:
                day = split_text[1]
                tsnd = split_text[-1].replace(competition, "", 1)
            elif split_text[3]:
                day = split_text[3]
                tsnd = split_text[-1].replace(competition, "", 1)

        split_text = RE_ROUND.split(tsnd)
        if len(split_text) == 3:
            teamone, teamtwo = [
                " ".join(t.split()) for t in (split_text[0], split_text[2])
            ]
            if len(teamone) and len(teamtwo):
                return EventData(
                    datatag=data_tag,
                    found=Found.FIXTURE_TEAMS,
                    context=context,
                    teamone=teamone,
                    teamtwo=teamtwo,
                    competition_round=split_text[1],
                    competition=competition,
                    fixture_date=date,
                    fixture_day=day,
                    source=source,
                    headers=headers,
                )
            if len(teamone) or len(teamtwo):
                teams = "".join((teamone, teamtwo))
                if len(teams.split()) == 1:
                    return EventData(
                        datatag=data_tag,
                        found=Found.NOT_TWO_TEAMS,
                        raw=text,
                        headers=headers,
                    )
                return EventData(
                    datatag=data_tag,
                    found=Found.FIXTURE,
                    context=context,
                    teams=teams,
                    competition_round=split_text[1],
                    competition=competition,
                    fixture_date=date,
                    fixture_day=day,
                    source=source,
                    headers=headers,
                )
            return EventData(
                datatag=data_tag,
                found=Found.COMPETITION_ROUND_GAME_DATE,
                context=context,
                competition_round=split_text[1],
                competition=competition,
                result_date=date,
                source=source,
                headers=headers,
            )
        if len(split_text) == 1:
            teams = " ".join(split_text[0].split())
            if len(teams) > 0:
                if len(teams.split()) == 1:
                    return EventData(
                        datatag=data_tag, found=Found.NOT_TWO_TEAMS, raw=text
                    )
                return EventData(
                    datatag=data_tag,
                    found=Found.FIXTURE,
                    context=context,
                    teams=teams,
                    competition=competition,
                    fixture_date=date,
                    fixture_day=day,
                    source=source,
                    headers=headers,
                )
            return EventData(
                datatag=data_tag,
                found=Found.COMPETITION_DATE,
                context=context,
                competition=competition,
                result_date=date,
                source=source,
                headers=headers,
            )
        return EventData(
            datatag=data_tag,
            found=Found.EXTRA_ROUNDS_DATE_COMPETITION,
            raw=text,
            headers=headers,
        )

    # Absence of round and competition, but presence of date makes line the
    # date of following games in competition if rest of line is whitespace.
    if date:
        split_text = RE_ROUND.split(tsnd)
        if len(split_text) == 1:
            if len(split_text[0].strip()) == 0:
                return EventData(
                    datatag=data_tag,
                    found=Found.COMPETITION_GAME_DATE,
                    context=context,
                    result_date=date,
                    source=source,
                    headers=headers,
                )
            return EventData(
                datatag=data_tag,
                found=Found.NOT_DATE_ONLY,
                raw=text,
                headers=headers,
            )
        return EventData(
            datatag=data_tag,
            found=Found.EXTRA_ROUNDS_DATE,
            raw=text,
            headers=headers,
        )

    # Presence of competition and absence of date makes line the competition
    # name of following games, and also a round header if round is present,
    # provided rest of line is whitespace.
    if competition:
        split_text = RE_ROUND.split(tsnd)
        if len(split_text) == 3:
            if len(" ".join((split_text[0], split_text[2])).strip()) == 0:
                return EventData(
                    datatag=data_tag,
                    found=Found.COMPETITION_ROUND,
                    context=context,
                    competition_round=RE_ROUND.findall(tsnd)[0],
                    competition=competition,
                    source=source,
                    headers=headers,
                )
            return EventData(
                datatag=data_tag,
                found=Found.NOT_COMPETITION_ROUND_ONLY,
                raw=text,
                headers=headers,
            )
        if len(split_text) == 1:
            if len(split_text[0].strip()) == 0:
                return EventData(
                    datatag=data_tag,
                    found=Found.COMPETITION_NAME,
                    context=context,
                    competition=competition,
                    source=source,
                    headers=headers,
                )
            return EventData(
                datatag=data_tag,
                found=Found.NOT_COMPETITION_ONLY,
                raw=text,
                headers=headers,
            )
        return EventData(
            datatag=data_tag,
            found=Found.EXTRA_ROUNDS_COMPETITION,
            raw=text,
            headers=headers,
        )

    # Presence of board, and absence of date and competition makes line the
    # round of following games if rest of line is whitespace.
    split_text = RE_ROUND.split(tsnd)
    if len(split_text) == 3:
        if len(" ".join((split_text[0], split_text[2])).strip()) == 0:
            return EventData(
                datatag=data_tag,
                found=Found.ROUND_HEADER,
                context=context,
                competition_round=RE_ROUND.findall(tsnd)[0],
                source=source,
                headers=headers,
            )

    # Text is the event name if it is followed by line with two dates.
    event_name = " ".join(text.split())
    if len(event_name) > 0:
        return EventData(
            datatag=data_tag,
            found=Found.POSSIBLE_EVENT_NAME,
            context=context,
            eventname=event_name,
            source=source,
            headers=headers,
        )
    return EventData(
        datatag=data_tag,
        found=Found.IGNORE,
        context=context,
        headers=headers,
    )


def _translate(result_line_description, re_name, finditer_list_groupdict):
    """Translate text from finditer_list and call _select_result_line.

    A sequence of _select_result_line(result_line_description, text) calls is
    done using text from the finditer_list groups generated by the re_name
    regular expression.

    """
    text = []
    if re_name == FINISHED:
        # print('f', end='') # tracer for fixing regular expressions
        if "scoretwo" in finditer_list_groupdict:
            for k in (
                "board",
                "names",
                "nameone",
                "scoreone",
                "scoretwo",
                "nametwo",
            ):
                if k in finditer_list_groupdict:
                    text.append(finditer_list_groupdict[k])
        else:
            for k in ("board", "names", "nameone"):
                if k in finditer_list_groupdict:
                    text.append(finditer_list_groupdict[k])
            if finditer_list_groupdict.get("scoreone") in _DRAW_TOKEN:
                text.append("draw")
                for k in ("nametwo",):
                    if k in finditer_list_groupdict:
                        text.append(finditer_list_groupdict[k])
            else:
                for k in ("scoreone", "nametwo"):
                    if k in finditer_list_groupdict:
                        text.append(finditer_list_groupdict[k])
        if finditer_list_groupdict.get("result_only"):
            text.append("result only")
    elif re_name == TEAMS_BODY:
        for k in ("teams", "teamone", "scoreone", "scoretwo", "teamtwo"):
            if k in finditer_list_groupdict:
                text.append(" ".join(finditer_list_groupdict[k].split()))
    elif re_name == MATCH_DATE_BODY:
        if "result_date" in finditer_list_groupdict:
            text.append(finditer_list_groupdict["result_date"])
    elif re_name == UNFINISHED:
        # print('u', end='') # tracer for fixing regular expressions
        for k in ("board", "names", "nameone"):
            if k in finditer_list_groupdict:
                text.append(finditer_list_groupdict[k])
        text.append("unfinished")
        if "nametwo" in finditer_list_groupdict:
            text.append(finditer_list_groupdict["nametwo"])
        if finditer_list_groupdict.get("result_only"):
            text.append("result only")
    elif re_name == FINISHED_PLAYED_ON:
        # print('p', end='') # tracer for fixing regular expressions
        for k in (
            "board",
            "names",
            "nameone",
            "scoreone",
            "scoretwo",
            "nametwo",
        ):
            if k in finditer_list_groupdict:
                text.append(finditer_list_groupdict[k])
        if finditer_list_groupdict.get("result_only"):
            text.append("result only")
    elif re_name == TEAMS_PLAYED_ON_BODY:
        text.append(PLAYED_ON)
        for k in ("teams", "teamone", "scoreone", "scoretwo", "teamtwo"):
            if k in finditer_list_groupdict:
                text.append(" ".join(finditer_list_groupdict[k].split()))
    elif re_name == MATCH_DATE_PLAYED_ON_BODY:
        if "result_date" in finditer_list_groupdict:
            text.append(finditer_list_groupdict["result_date"])
    elif re_name == DEFAULT:
        # print('d', end='') # tracer for fixing regular expressions
        if "teamwins" in finditer_list_groupdict:
            text.append("default")
        else:
            if "board" in finditer_list_groupdict:
                text.append(finditer_list_groupdict["board"])
            if finditer_list_groupdict.get("nameone"):
                text.append("1-default")
            elif finditer_list_groupdict.get("nametwo"):
                text.append("default-1")
            elif finditer_list_groupdict.get("names"):
                text.append("default")
            else:
                text.append("doubledefault")
    elif re_name == UNFINISHED_PLAYED_ON:
        for k in ("board", "names", "nameone"):
            if k in finditer_list_groupdict:
                text.append(finditer_list_groupdict[k])
        text.append("unfinished")
        if "nametwo" in finditer_list_groupdict:
            text.append(finditer_list_groupdict["nametwo"])
        if finditer_list_groupdict.get("result_only"):
            text.append("result only")
    elif re_name == MATCH_DEFAULT:
        # print('m', end='') # tracer for fixing regular expressions
        if "matchdefault" in finditer_list_groupdict:
            text.append("match default")
    elif re_name == FIXTURE_BODY:
        # print('s  ', end='') # tracer for fixing regular expressions
        for k in ("dayname", "day", "month", "year", "teams", "competition"):
            if k not in finditer_list_groupdict:
                break
        else:
            text.append(finditer_list_groupdict["dayname"])
            text.append(
                (
                    "/" if finditer_list_groupdict["month"].isdigit() else " "
                ).join(
                    (
                        finditer_list_groupdict["day"],
                        finditer_list_groupdict["month"],
                        finditer_list_groupdict["year"],
                    )
                )
            )
            text.append(finditer_list_groupdict["competition"])
            text.append(finditer_list_groupdict["teams"])
    if text:
        try:
            text = " ".join(text)
        except:
            print(finditer_list_groupdict)
            raise

        # Not certain that a return value other than None is useful, but
        # _select_result_line returns an EventData instance at present even
        # though the instance has been added to the EventContext instance data
        # structures.
        return _select_result_line(result_line_description, text)
    # print('X', end='') # tracer for fixing regular expressions
    return None


def _lookup_competition(competition_lookup, key):
    """Raise EventParserError exception if lookup fails KeyError."""
    try:
        return competition_lookup[key]
    except KeyError:
        raise EventParserError(
            "".join(
                (
                    "Lookup proper competition name for\n\n",
                    key,
                    "\n\nfailed: it is likely not listed in configuration file.",
                )
            )
        )


def raise_re_error(name, text):
    """Raise EventParserError with details of regular expression runtime error.

    Introduced because the regular expressions at the FINISHED level generate
    a RuntimeError exception under Python3.3.2, but not under Python3.3.1, for
    the Portsmouth and Southampton leagues.  It is assumed the expressions are
    valid because the re compiler does not object to the strings under either
    version of Python.

    """
    if len(text) > 300:
        text = "".join((text[:300], "..."))
    raise EventParserError(
        "".join(
            (
                "A regular expression derived from a\n\n",
                name,
                "\n\nentry in the event configuration file failed processing\n\n",
                repr(text).join(("", ".\n\n")),
                "This is known to depend on the Python version for at least one ",
                "regular expression.  Try the latest version of Python, or at ",
                "least a different version (change between 3.3.1 and 3.3.2 for ",
                "example) before blaming the event configuration file entry or ",
                "the application.",
            )
        )
    )


def _convert_result_first(round_result):
    """Return lower-case result replacing leading '-=+' with trailing '-=+'."""
    if round_result[0] in "-=+":
        return (round_result[1:] + round_result[0]).lower()
    return round_result.lower()
