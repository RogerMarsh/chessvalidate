# gameresults.py
# Copyright 2008 Roger Marsh
# Licence: See LICENCE (BSD licence)

"""Lookup tables used in the results of games."""
from . import constants

# ECF score identifiers.
# Results are reported to ECF as '10' '01' or '55'.
# Only HWIN AWIN and DRAW are reported.
ecfresult = {
    constants.HWIN: constants.RESULT_10,
    constants.AWIN: constants.RESULT_01,
    constants.DRAW: constants.RESULT_55,
}

# Particular data entry modules may wish to use their own versions
# of the following maps.
# But all must use the definitions above.

# Display score strings.
# Results are displayed as '1-0' '0-1' etc.
# Use is "A Player 1-0 A N Other".
displayresult = {
    constants.HWIN: "1-0",
    constants.AWIN: "0-1",
    constants.DRAW: "draw",
    constants.HWIN_DEFAULT: "1-def",
    constants.AWIN_DEFAULT: "def-1",
    constants.DOUBLEDEFAULT: "dbldef",
    constants.HBYE: "bye+",
    constants.ABYE: "bye+",
    constants.HBYEHALF: "bye=",
    constants.ABYEHALF: "bye=",
    constants.VOID_GAME: "void",
    constants.DRAWDEFAULT: "drawdef",
    constants.DEFAULTED: "defaulted",
}

# Score tags.  Comments displayed after a game result.
# Use is "A Player  A N Other   to be reported".
displayresulttag = {
    constants.TOBEREPORTED: constants.TBRSTRING,
    constants.NOTARESULT: constants.NOTARESULT,
}

# Map strings representing a result to database representation of result.
# Where the context implies that a string is a result treat as "void"
# if no map exists i.e. resultmap.get(resultstring, resultmap['void']).
# resultstring may have been initialised to None and not been set.
# Thus the extra entry None:TOBEREPORTED.
resultmap = {
    "1-0": constants.HWIN,
    "0-1": constants.AWIN,
    "draw": constants.DRAW,
    "void": constants.VOID_GAME,
    "tbr": constants.TOBEREPORTED,
    "": constants.TOBEREPORTED,
    None: constants.TOBEREPORTED,
    "def+": constants.HWIN_DEFAULT,
    "def-": constants.AWIN_DEFAULT,
    "dbld": constants.DOUBLEDEFAULT,
    "def=": constants.DRAWDEFAULT,
    "default": constants.DEFAULTED,
}

# Map strings representing a result to database representation of result.
resultmapecf = {
    "1-0": constants.RESULT_10,
    "0-1": constants.RESULT_01,
    "draw": constants.RESULT_55,
    "def+": constants.ECF_RESULT_1D,
    "def-": constants.ECF_RESULT_D1,
    "dbld": constants.ECF_RESULT_DD,
    "def=": constants.DRAWDEFAULT,
    "default": constants.DEFAULTED,
}

# Map game results to the difference created in the match score.
match_score_difference = {
    constants.HWIN: 1,
    constants.AWIN: -1,
    constants.DRAW: 0,
    constants.HWIN_DEFAULT: 1,
    constants.AWIN_DEFAULT: -1,
    constants.DOUBLEDEFAULT: 0,
    constants.DRAWDEFAULT: 0,
    constants.HBYE: 1,
    constants.ABYE: -1,
    constants.HBYEHALF: 0.5,
    constants.ABYEHALF: -0.5,
    constants.TOBEREPORTED: 0,
    constants.VOID_GAME: 0,
    constants.NOTARESULT: 0,
}

# Map game results to the contribution to the total match score.
match_score_total = {
    constants.HWIN: 1,
    constants.AWIN: 1,
    constants.DRAW: 1,
    constants.HWIN_DEFAULT: 1,
    constants.AWIN_DEFAULT: 1,
    constants.DOUBLEDEFAULT: 0,
    constants.DRAWDEFAULT: 0.5,
    constants.HBYE: 1,
    constants.ABYE: 1,
    constants.HBYEHALF: 0.5,
    constants.ABYEHALF: 0.5,
    constants.TOBEREPORTED: 0,
    constants.VOID_GAME: 0,
    constants.NOTARESULT: 0,
}

# Games with following results are stored on database.
# Not sure if the mapping is needed.
storeresults = {
    constants.AWIN: constants.LOSS,
    constants.DRAW: constants.DRAWN,
    constants.HWIN: constants.WIN,
}

# Pieces (or side) of first named player (home player in team matches).
# True and False used as indicators since long ago on database records.
home_player_pieces = {
    True: constants.FIRST_PLAYER_WHITE_PIECES,
    False: constants.FIRST_PLAYER_BLACK_PIECES,
}
