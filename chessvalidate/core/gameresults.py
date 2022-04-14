# gameresults.py
# Copyright 2008 Roger Marsh
# Licence: See LICENCE (BSD licence)

"""Constants used in the results of games.
"""

# Game score identifiers.
# h... refers to first-named player usually the home player in team context.
# a... refers to second-named player usually the away player in team context.
# No assumption is made about which player has the white or black pieces.
hwin = "h"
awin = "a"
draw = "d"
hdefault = "hd"
adefault = "ad"
doubledefault = "dd"
drawdefault = "=d"
hbye = "hb"
abye = "ab"
hbyehalf = "hbh"
abyehalf = "abh"
tobereported = None
void = "v"
notaresult = "not a result"
defaulted = "gd"

# Commentary on printed results
tbrstring = "to be reported"

# ECF score identifiers.
# Results are reported to ECF as '10' '01' or '55'.
# Only hwin awin and draw are reported.
ecfresult = {hwin: "10", awin: "01", draw: "55"}

# Particular data entry modules may wish to use their own versions
# of the following maps.
# But all must use the definitions above.

# Display score strings.
# Results are displayed as '1-0' '0-1' etc.
# Use is "A Player 1-0 A N Other".
displayresult = {
    hwin: "1-0",
    awin: "0-1",
    draw: "draw",
    hdefault: "1-def",
    adefault: "def-1",
    doubledefault: "dbldef",
    hbye: "bye+",
    abye: "bye+",
    hbyehalf: "bye=",
    abyehalf: "bye=",
    void: "void",
    drawdefault: "drawdef",
    defaulted: "defaulted",
}

# Score tags.  Comments displayed after a game result.
# Use is "A Player  A N Other   to be reported".
displayresulttag = {
    tobereported: tbrstring,
    notaresult: notaresult,
}

# Map of all strings representing a result to result.
# Where the context implies that a string is a result treat as "void"
# if no map exists i.e. resultmap.get(resultstring, resultmap['void']).
# resultstring may have been initialised to None and not been set.
# Thus the extra entry None:tobereported.
resultmap = {
    "1-0": hwin,
    "0-1": awin,
    "draw": draw,
    "void": void,
    "tbr": tobereported,
    "": tobereported,
    None: tobereported,
    "def+": hdefault,
    "def-": adefault,
    "dbld": doubledefault,
    "def=": drawdefault,
    "default": defaulted,
}

# Map game results to the difference created in the match score
match_score_difference = {
    hwin: 1,
    awin: -1,
    draw: 0,
    hdefault: 1,
    adefault: -1,
    doubledefault: 0,
    drawdefault: 0,
    hbye: 1,
    abye: -1,
    hbyehalf: 0.5,
    abyehalf: -0.5,
    tobereported: 0,
    void: 0,
    notaresult: 0,
}

# Map game results to the contribution to the total match score
match_score_total = {
    hwin: 1,
    awin: 1,
    draw: 1,
    hdefault: 1,
    adefault: 1,
    doubledefault: 0,
    drawdefault: 0.5,
    hbye: 1,
    abye: 1,
    hbyehalf: 0.5,
    abyehalf: 0.5,
    tobereported: 0,
    void: 0,
    notaresult: 0,
}

# Games with following results are stored on database
# Maybe move to gameresults
# Not sure if the mapping is needed
_loss = "0-1"
_draw = "draw"
_win = "1-0"
_storeresults = {awin: _loss, draw: _draw, hwin: _win}

# Duplicate game report inconsistency flags
NULL_PLAYER = "null"
HOME_PLAYER_WHITE = "home player white"
RESULT = "result"
BOARD = "board"
GRADING_ONLY = "grading only"
SOURCE = "source"
SECTION = "section"
COMPETITION = "competition"
HOME_TEAM_NAME = "home team name"
AWAY_TEAM_NAME = "away team name"
HOME_PLAYER = "home player"
AWAY_PLAYER = "away player"
ROUND = "round"
GAME_COUNT = "game count"
MATCH_SCORE = "match and game scores in earlier reports"
ONLY_REPORT = "match and game scores in only report"
AUTHORIZATION = "authorization"
