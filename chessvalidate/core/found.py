# found.py
# Copyright 2014 Roger Marsh
# Licence: See LICENCE (BSD licence)

"""Classes providing data type and unusual score identifiers.

Found provides the data type identifiers: negative numbers for valid data,
zero for ignored data, positive numbers for errors.

Score provides identifiers for unusual game results such as 'default'.

"""


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
