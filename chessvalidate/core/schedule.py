# schedule.py
# Copyright 2008 Roger Marsh
# Licence: See LICENCE (BSD licence)

"""Event schedule class."""

from solentware_misc.core import utilities

from .gameobjects import MatchFixture, Player, split_codes_from_name
from . import reportbase


class ScheduleError(Exception):
    """Exception class for schedule module."""


class Schedule(reportbase.ReportBase):
    """Schedule extracted from event schedule file containing one event.

    Support a free text format for leagues and events for individuals.

    Subclasses will deal with particular input formats.

    """

    def __init__(self):
        """Extend, initialise schedule data items."""
        super().__init__()
        # self.textlines = None
        # self.error = []
        self.es_startdate = None
        self.es_enddate = None
        self.es_rapidplay = {}
        self.es_teams = {}
        self.es_team_alias = {}
        self.es_team_number = {}
        self.es_matches = {}  # fixtures by section
        self.es_fixtures = []
        self.es_summary = {}
        self.rapidplay = False
        # self._section = None  # latest section name found by get_section
        self.error_repeat = False
        self.es_section = {}
        self.es_report_order = []
        self.es_name = None
        self.es_round_dates = {}
        self.es_players = {}  # keys are (name, pin) eg pin on swiss table
        self.es_pins = {}  # map pin to name for es_players lookup
        self._maximum_round = None
        # self._round = None

    def add_league_section(self):
        """Initialise data structures for league format."""
        self._set_league_section()

    def _set_league_section(self):
        """Initialise data structures for league format."""
        self.es_teams.setdefault(self._section, {})
        self.es_team_number.setdefault(self._section, {})
        self.es_team_alias.setdefault(self._section, {})
        self.es_matches.setdefault(self._section, {})
        self.es_rapidplay.setdefault(self._section, self.rapidplay)
        self.es_summary.setdefault(self._section, {"matches": 0, "teams": {}})

    @staticmethod
    def default_club_for_team(team):
        """Return club name calculated from team name."""
        club = team.split()
        if len(club) > 1:
            if len(club[-1]) == 1:
                club = club[:-1]
        return " ".join(club)

    def get_club_team(self, section, team):
        """Return club for team."""
        try:
            return self.es_teams[section][team]["club"]
        except KeyError:
            return self.default_club_for_team(team)

    def set_league(self, section):
        """Initialise league format for section."""
        self._section = section.strip()
        self._set_league_section()

    def set_match(self, fixture):
        """Copy fixture detail to data structures for event."""
        self.es_fixtures.append(fixture)
        comp = fixture.competition
        estc = self.es_teams[comp]
        essct = self.es_summary[comp]["teams"]
        self.es_summary[comp]["matches"] += 1
        for team in (fixture.hometeam, fixture.awayteam):
            if team not in estc:
                estc[team] = {
                    "club": self.default_club_for_team(team),
                    "section": comp,
                }
            if team not in essct:
                essct[team] = {
                    "homematches": 0,
                    "awaymatches": 0,
                    "name": team,
                    "division": comp,
                }
            if team == fixture.hometeam:
                essct[team]["homematches"] += 1
            else:
                essct[team]["awaymatches"] += 1

    def set_team_aliases(self, team, aliases):
        """Copy team and alias detail to data structures for event."""
        sta = self.es_team_alias[self._section]
        if team not in sta:
            sta[team] = {team: team}
        for key in aliases:
            if key not in sta:
                sta[key] = {key: team, team: team}
            if key not in sta[team]:
                sta[team][key] = team
            for name in aliases:
                if name not in sta:
                    sta[key] = {name: team, key: team, team: team}
                if name not in sta[key]:
                    sta[key][name] = team

    # Adapted from collation.Collation._collate_individual() because of the
    # reference to _section attribute.
    # pylint protected-access report prompted action.
    def add_event_to_player(self, player):
        """Copy event identity to player."""
        player.event = self.es_name
        player.startdate = self.es_startdate
        player.enddate = self.es_enddate
        player.section = self._section
        player.set_player_identity()

    def build_schedule(self, textlines):
        """Populate the event schedule from textlines."""

        def get_allplayall_players(text, tagger):
            """Create Player instance from text and return state indicator."""
            ptext, ctext = split_text_and_pad(text, 1)
            stext = ptext.split()
            sl0 = stext[0].lower()
            if sl0.isdigit():
                pin = stext[0]
                name = " ".join(stext[1:])
                if len(name) == 0:
                    tagger.append_generated_schedule(
                        self.error,
                        "".join(('No player name in "', text, '"')),
                    )
                    self.error_repeat = False
                    return get_allplayall_players
                if not pin.isdigit():
                    tagger.append_generated_schedule(
                        self.error,
                        "".join(('PIN must be digits in "', text, '"')),
                    )
                    self.error_repeat = False
                    return get_allplayall_players
                name, codes = split_codes_from_name(name)
                pin = int(pin)
                if (name, pin) in self.es_players[self._section]:
                    tagger.append_generated_schedule(
                        self.error,
                        "".join(
                            (
                                'PIN in "',
                                text,
                                '" duplicates earlier PIN in ',
                                "section",
                            )
                        ),
                    )
                    self.error_repeat = False
                    return get_allplayall_players
                player = Player(
                    tagger=tagger,
                    name=name,
                    event=self.es_name,
                    startdate=self.es_startdate,
                    enddate=self.es_enddate,
                    section=self._section,
                    pin=pin,
                    affiliation=" ".join(ctext.split()),
                    reported_codes=codes,
                )
                self.es_players[self._section][(name, pin)] = player
                self.es_pins[self._section][pin] = name
                return get_allplayall_players
            if sl0 in sectiontypes:
                return get_section(text, tagger)
            if sl0 in playtypes:
                return get_section(text, tagger)
            tagger.append_generated_schedule(
                self.error,
                "".join(('No PIN in "', text, '"')),
            )
            self.error_repeat = False
            return get_allplayall_players

        def get_allplayall_round_dates(text, tagger):
            """Extract round date from text and return state indicator."""
            if text.lower() == "players":
                return get_allplayall_players
            stext = text.split()
            stext0 = stext.pop(0)
            if stext0.isdigit():
                rdate = utilities.AppSysDate()
                dtext = " ".join(stext)
                rdoffset = rdate.parse_date(dtext)
                if rdoffset == len(dtext):
                    self.es_round_dates[self._section][
                        int(stext0)
                    ] = rdate.iso_format_date()
                    return get_allplayall_round_dates
            for char in stext:
                if char.isdigit():
                    if stext0.isdigit():
                        tagger.append_generated_schedule(
                            self.error,
                            "".join(
                                (
                                    '"',
                                    text,
                                    '" ',
                                    "assumed to be invalid date for round ",
                                    stext0,
                                )
                            ),
                        )
                        self.error_repeat = False
                    else:
                        tagger.append_generated_schedule(
                            self.error,
                            "".join(
                                (
                                    '"',
                                    text,
                                    '" ',
                                    "assumed to start with invalid round",
                                )
                            ),
                        )
                        self.error_repeat = False
                    return get_allplayall_round_dates
            return get_allplayall_players(text, tagger)

        def get_event_date(text, tagger):
            """Extract event dates from text and return state indicator."""
            sdate = utilities.AppSysDate()
            edate = utilities.AppSysDate()
            dtxt = " ".join(text.split())
            sdtxt = sdate.parse_date(dtxt)
            edtxt = edate.parse_date(dtxt[sdtxt:])
            if sdtxt + edtxt == len(dtxt):
                self.es_startdate = sdate.iso_format_date()
                self.es_enddate = edate.iso_format_date()
            else:
                tagger.append_generated_schedule(
                    self.error,
                    "".join(
                        ('Start or end date not recognised in "', dtxt, '"')
                    ),
                )
            return get_section

        def get_event_name(text, tagger):
            """Extract event name from text and return state indicator."""
            ename = text.split()
            self.es_name = " ".join(ename)
            if self.es_name in self.es_section:
                tagger.append_generated_schedule(
                    self.error,
                    "".join(
                        (
                            'Event name "',
                            self.es_name,
                            '" in "',
                            text,
                            '" is a duplicate',
                        )
                    ),
                )
            self.es_section[self.es_name] = None
            return get_event_date

        def get_individual_players(text, tagger):
            """Raise ScheduleError.

            Module structure requires this function to exist.

            The conditions for calling it are no longer ever set up, so raise
            a ScheduleError if it is called.

            The Player objects are now created in the 'get_individual_games'
            function in the sibling 'report' module.
            """
            raise ScheduleError(
                "Function 'get_individual_players' must not be called"
            )

        def get_league_teams(text, tagger):
            """Extract team name from text and return state indicator."""
            tmtext, cbtext, tatext = split_text_and_pad(text, 2)
            txt = tmtext.split()
            txt0 = txt[0].lower()
            if txt0 in matchtypes:
                return get_match_specification_type(text, tagger)
            team = " ".join(tmtext.split())
            club = " ".join(cbtext.split())
            teamalias = [a for a in tatext.split("\t") if len(a)]
            error = False
            if len(team) == 0:
                tagger.append_generated_schedule(
                    self.error,
                    "".join(('No team name in "', text, '"')),
                )
                self.error_repeat = False
                error = True
                return get_league_teams
            if team in self.es_teams[self._section]:
                tagger.append_generated_schedule(
                    self.error,
                    "".join(
                        (
                            'Team name "',
                            team,
                            '" in "',
                            text,
                            '" is a duplicate in section "',
                            self._section,
                            '"',
                        )
                    ),
                )
                self.error_repeat = False
                error = True
            for alias in teamalias:
                if alias in self.es_teams[self._section]:
                    tagger.append_generated_schedule(
                        self.error,
                        "".join(
                            (
                                'Team name (alias) "',
                                alias,
                                '" in "',
                                text,
                                '" is a duplicate in section "',
                                self._section,
                                '"',
                            )
                        ),
                    )
                    self.error_repeat = False
                    error = True
                elif alias == team:
                    tagger.append_generated_schedule(
                        self.error,
                        "".join(
                            (
                                'Team name (alias) "',
                                alias,
                                '" in "',
                                text,
                                '" is same as team name in section "',
                                self._section,
                                '"',
                            )
                        ),
                    )
                    self.error_repeat = False
                    error = True
            if error:
                return get_league_teams
            if len(club) == 0:
                club = self.default_club_for_team(team)
            self.es_teams[self._section][team] = {
                "club": club,
                # "homematches": 0, count appearances in self.es_matches?
                # "awaymatches": 0,
                "section": self._section,
            }
            self.es_team_number[self._section][team] = (
                len(self.es_team_number[self._section]) + 1
            )
            self.set_team_aliases(team, teamalias)
            return get_league_teams

        def get_matches(text, tagger):
            """Extract match detail from text and return state indicator."""
            rtn, match = get_match(text, tagger)
            if match:
                self.es_matches[self._section][match] = self.es_fixtures[-1]
            return rtn

        def get_match_specification_type(text, tagger):
            """Generate fixtures and return state indicator."""
            txt = text.split()
            txt0 = txt[0].lower()
            if txt0 in matchtypes:
                if self.error_repeat:
                    tagger.append_generated_schedule(
                        self.error,
                        "".join(
                            ('Match type "', txt0, '" ', "found after errors")
                        ),
                    )
                    self.error_repeat = False
                if txt0 == "rounds":
                    if len(txt) != 2:
                        tagger.append_generated_schedule(
                            self.error,
                            "".join(
                                (
                                    '"',
                                    text,
                                    '"must be like "rounds 10" to specify ',
                                    "the number of rounds of matches.  If a ",
                                    "round is given for a match it must be ",
                                    "between 1 and the number.  The matches ",
                                    "should be given in a fixture list.",
                                )
                            ),
                        )
                        return get_match_specification_type
                    if not txt[1].isdigit():
                        tagger.append_generated_schedule(
                            self.error,
                            "".join(
                                (
                                    'Number of rounds in "',
                                    text,
                                    '" is not digits',
                                )
                            ),
                        )
                        return get_match_specification_type
                    if int(txt[1]) == 0:
                        tagger.append_generated_schedule(
                            self.error,
                            "".join(
                                (
                                    'Number of matches between each team in "',
                                    text,
                                    '" must not be zero',
                                )
                            ),
                        )
                        return get_match_specification_type
                    self._maximum_round = str(int(txt[1]))
                elif txt0 == "generate":
                    if len(txt) != 2:
                        tagger.append_generated_schedule(
                            self.error,
                            "".join(
                                (
                                    '"',
                                    text,
                                    '" must be like "generate 2" to specify ',
                                    "the number of times the teams play ",
                                    "each other.  The team names are ",
                                    "reversed in odd and even numbered ",
                                    "matches assuming this may mean home and ",
                                    "away.  The generated list of matches ",
                                    "does not give dates or rounds for the ",
                                    "matches.",
                                )
                            ),
                        )
                        return get_match_specification_type
                    if not txt[1].isdigit():
                        tagger.append_generated_schedule(
                            self.error,
                            "".join(
                                (
                                    'Number of rounds in "',
                                    text,
                                    '" is not digits',
                                )
                            ),
                        )
                        return get_match_specification_type
                    generate_matches(int(txt[1]))
                return matchtypes[txt0]
            if self.error_repeat:
                return get_match_specification_type
            tagger.append_generated_schedule(
                self.error,
                "".join(
                    (
                        'Match type "',
                        txt0,
                        '" ',
                        "not recognised.",
                        "\n\nAllowed match types are:\n\t",
                        "matches\t\ta list of matches\n\t",
                        "rounds\t\ta list of matches in rounds\n\t",
                        "generate\t\tgenerate a list of matches",
                    )
                ),
            )
            self.error_repeat = True
            return get_match_specification_type

        def get_matches_by_round(text, tagger):
            """Generate fixture and return state indicator."""
            rtext = text.split()
            rtext0 = rtext[0].lower()
            if rtext0 == "round":
                if len(rtext) != 2:
                    tagger.append_generated_schedule(
                        self.error,
                        "".join(
                            (
                                'Round number specification for "',
                                self._section,
                                '" in "',
                                text,
                                '" not recognised',
                            )
                        ),
                    )
                    return get_match_specification_type
                if not rtext[1].isdigit():
                    tagger.append_generated_schedule(
                        self.error,
                        "".join(
                            (
                                'Round number for "',
                                self._section,
                                '" in "',
                                text,
                                '" must be all digits',
                            )
                        ),
                    )
                    return get_match_specification_type
                if int(rtext[1]) > int(self._maximum_round):
                    tagger.append_generated_schedule(
                        self.error,
                        "".join(
                            (
                                'Round number for "',
                                self._section,
                                '" in "',
                                text,
                                '" must not be more than ',
                                self._maximum_round,
                            )
                        ),
                    )
                    return get_match_specification_type
                if int(rtext[1]) == 0:
                    tagger.append_generated_schedule(
                        self.error,
                        "".join(
                            (
                                'Round number for "',
                                self._section,
                                '" in "',
                                text,
                                '" must not be zero',
                            )
                        ),
                    )
                    return get_match_specification_type
                self._round = str(int(rtext[1]))
                return get_matches_by_round
            rtn, match = get_match(text, tagger)
            if match:
                team1, team2, date = match
                del date
                teams = {}
                for mname in self.es_matches[self._section]:
                    if (
                        self._round
                        == self.es_matches[self._section][mname].round
                    ):
                        teams[mname[0]] = None
                        teams[mname[1]] = None
                if team1 not in teams:
                    if team2 not in teams:
                        self.es_matches[self._section][match] = (
                            self.es_fixtures[-1]
                        )
                        return get_matches_by_round
                tagger.append_generated_schedule(
                    self.error,
                    "".join(
                        (
                            'Match "',
                            text,
                            '" involves a team in an earlier match for ',
                            'round "',
                            self._round,
                            '" in section "',
                            self._section,
                            '"',
                        )
                    ),
                )
                self.error_repeat = False
                return get_matches_by_round
            return rtn

        def get_section(text, tagger):
            """Extract section and type and return state indicator."""
            stext = text.split()
            st0 = stext[0].lower()
            if st0 in playtypes:
                self.rapidplay = playtypes[st0]
                return get_section
            if st0 not in sectiontypes:
                if self.error_repeat:
                    return get_section
                tagger.append_generated_schedule(
                    self.error,
                    "".join(
                        (
                            'Section type "',
                            st0,
                            '" ',
                            "not recognised",
                            "\n\nAllowed section types are:\n\t",
                            "allplayall\t\tall play all table for individuals",
                            "\n\tleague\t\ta list of matches in rounds\n\t",
                            "swiss\t\tswiss tournament table for individuals",
                            "\n\tindividual\t\ta list of games between ",
                            "individuals\n\t\n\nAlso allowed at this point ",
                            "is the type of game in following sections:\n\t",
                            "rapidplay\t\t\n\t",
                            "normalplay\t\t(the default)",
                        )
                    ),
                )
                self.error_repeat = True
                return get_section
            if self.error_repeat:
                tagger.append_generated_schedule(
                    self.error,
                    "".join(
                        ('Section type "', st0, '" ', "found after errors")
                    ),
                )
                self.error_repeat = False
            self._section = " ".join(stext[1:])
            if self._section in self.es_section:
                tagger.append_generated_schedule(
                    self.error,
                    "".join(('Section "', self._section, '" named earlier')),
                )
                self.error_repeat = True
                return get_section
            self.es_section[self._section] = st0
            self.es_report_order.append(self._section)
            sectiondata[st0]()
            return sectiontypes[st0]

        def get_swiss_players(text, tagger):
            """Create Player instance from text and return state indicator."""
            ptext, ctext = split_text_and_pad(text, 1)
            stext = ptext.split()
            sl0 = stext[0].lower()
            if sl0.isdigit():
                pin = stext[0]
                name = " ".join(stext[1:])
                if len(name) == 0:
                    tagger.append_generated_schedule(
                        self.error,
                        "".join(('No player name in "', text, '"')),
                    )
                    self.error_repeat = False
                    return get_swiss_players
                if not pin.isdigit():
                    tagger.append_generated_schedule(
                        self.error,
                        "".join(('PIN must be digits in "', text, '"')),
                    )
                    self.error_repeat = False
                    return get_swiss_players
                name, codes = split_codes_from_name(name)
                pin = int(pin)
                player = Player(
                    tagger=tagger,
                    name=name,
                    event=self.es_name,
                    startdate=self.es_startdate,
                    enddate=self.es_enddate,
                    section=self._section,
                    pin=pin,
                    affiliation=" ".join(ctext.split()),
                    reported_codes=codes,
                )
                self.es_players[self._section][(name, pin)] = player
                self.es_pins[self._section][pin] = name
                return get_swiss_players
            if sl0 in sectiontypes:
                return get_section(text, tagger)
            if sl0 in playtypes:
                return get_section(text, tagger)
            tagger.append_generated_schedule(
                self.error,
                "".join(('No PIN in "', text, '"')),
            )
            self.error_repeat = False
            return get_swiss_players

        def get_swiss_round_dates(text, tagger):
            """Extract round date from text and return state indicator."""
            if text.lower() == "players":
                return get_swiss_players
            stext = text.split()
            stext0 = stext.pop(0)
            if stext0.isdigit():
                rdate = utilities.AppSysDate()
                dtext = " ".join(stext)
                rdoffset = rdate.parse_date(dtext)
                if rdoffset == len(dtext):
                    self.es_round_dates[self._section][
                        int(stext0)
                    ] = rdate.iso_format_date()
                    return get_swiss_round_dates
            for item in stext:
                if item.isdigit():
                    if stext0.isdigit():
                        tagger.append_generated_schedule(
                            self.error,
                            "".join(
                                (
                                    '"',
                                    text,
                                    '" ',
                                    "assumed to be invalid date for round ",
                                    stext0,
                                )
                            ),
                        )
                        self.error_repeat = False
                    else:
                        tagger.append_generated_schedule(
                            self.error,
                            "".join(
                                (
                                    '"',
                                    text,
                                    '" ',
                                    "assumed to start with invalid round",
                                )
                            ),
                        )
                        self.error_repeat = False
                    return get_swiss_round_dates
            return get_swiss_players(text, tagger)

        def add_allplayall_section():
            """Initialise data structures for all-play-all format."""
            self.es_pins.setdefault(self._section, {})
            self.es_players.setdefault(self._section, {})
            self.es_rapidplay.setdefault(self._section, self.rapidplay)
            self.es_round_dates.setdefault(self._section, {})

        def add_individual_section():
            """Initialise data structures for individual game format."""
            self.es_players.setdefault(self._section, {})
            self.es_rapidplay.setdefault(self._section, self.rapidplay)

        def add_swiss_section():
            """Initialise data structures for swiss wall-chart format."""
            self.es_players.setdefault(self._section, {})
            self.es_pins.setdefault(self._section, {})
            self.es_rapidplay.setdefault(self._section, self.rapidplay)
            self.es_round_dates.setdefault(self._section, {})

        def split_text_and_pad(text, count, separator=None):
            """Return tuple of text split maximum count times by separator."""
            if separator is None:
                separator = "\t"
            tlist = text.split(separator, count)
            if len(tlist) < count + 1:
                tlist.extend([""] * (count - len(tlist) + 1))
            return tlist

        def generate_matches(cycles):
            """Generate fixtures for league with cycles number of rounds."""
            etns = self.es_team_number[self._section]
            for rnd in range(cycles):
                for tm1 in etns:
                    for tm2 in etns:
                        if etns[tm1] < etns[tm2]:
                            if rnd % 2:
                                if (etns[tm1] + etns[tm2]) % 2:
                                    key = (tm1, tm2, rnd)
                                else:
                                    key = (tm2, tm1, rnd)
                            elif (etns[tm1] + etns[tm2]) % 2:
                                key = (tm2, tm1, rnd)
                            else:
                                key = (tm1, tm2, rnd)
                            self.es_matches[self._section][key] = None
                            self.set_match(
                                MatchFixture(
                                    # date=tdate,
                                    competition=self._section,
                                    # round=rnd + 1,
                                    hometeam=key[0],
                                    awayteam=key[1],
                                )
                            )  # dateok=True))

        def get_match(text, tagger):
            """Create MatchFixture from text, return (next method, match)."""
            tp1, tp2 = split_text_and_pad(text, 1)
            tps = tp1.split()
            tp0 = tps[0].lower()
            if tp0 in matchtypes:
                return (get_match_specification_type(text, tagger), None)
            if tp0 in sectiontypes:
                return (get_section(text, tagger), None)
            if tp0 in playtypes:
                self.rapidplay = playtypes[tp0]
                return (get_section, None)
            tp1 = " ".join(tps)
            mdate = utilities.AppSysDate()
            matchdate = mdate.parse_date(tp1)
            if (
                matchdate < 3
            ):  # not matchdate < -1 so leading digits can be in team name.
                tdate = ""
                team1 = tp1
            else:  # badly formatted dates treated as part of team name.
                tdate = mdate.iso_format_date()
                team1 = " ".join(tp1[matchdate:].split())
            team2 = " ".join(tp2.split())
            error = False
            for team in (team1, team2):
                if team not in self.es_teams[self._section]:
                    tagger.append_generated_schedule(
                        self.error,
                        "".join(
                            (
                                'Team name "',
                                team,
                                '" in "',
                                text,
                                '" is not in team list for section "',
                                self._section,
                                '"',
                            )
                        ),
                    )
                    self.error_repeat = False
                    error = True
            if not error:
                match = (team1, team2, tdate)
                self.set_match(
                    MatchFixture(
                        date=tdate,
                        competition=self._section,
                        round=self._round,
                        hometeam=team1,
                        awayteam=team2,
                        dateok=True,
                        tagger=tagger,
                    )
                )
                if match in self.es_matches[self._section]:
                    tagger.append_generated_schedule(
                        self.error,
                        "".join(
                            (
                                'Match "',
                                text,
                                '" duplicates an earlier match for section "',
                                self._section,
                                '"',
                            )
                        ),
                    )
                    self.error_repeat = False
                else:
                    return (get_matches, match)
            return (get_matches, None)

        def get_match_teams(text, tagger):
            """Add match in text to event schedule."""
            match = text.split("\t")
            if len(match) < 5:
                tagger.append_generated_schedule(self.error, text)
                return get_match_teams
            dateok = True
            day = match[0].strip().title()
            pdate = " ".join(match[1].split()).title()
            date_checker = utilities.AppSysDate()
            if date_checker.parse_date(pdate) == -1:
                dateok = False
                tagger.append_generated_schedule(self.error, text)
                # pylint C0209 consider-using-f-string.  Not used at
                # Python 3.10 due to Idle colouring.
                # See github.com/python/cpython/issues/73473.
                date = "%08d" % 0
            elif len(day) > 1 and date_checker.date.strftime("%A").startswith(
                day.title()
            ):
                date = date_checker.iso_format_date()
            else:
                dateok = False
                tagger.append_generated_schedule(self.error, text)
                date = date_checker.iso_format_date()
            section = " ".join(match[2].split()).title()
            if section not in self.es_matches:
                self.set_league(section)
            else:
                self._section = section
            hometeam = " ".join(match[3].split())
            awayteam = " ".join(match[4].split())
            self.set_match(
                MatchFixture(
                    day=day,
                    pdate=pdate,
                    date=date,
                    competition=self._section,
                    hometeam=hometeam,
                    awayteam=awayteam,
                    dateok=dateok,
                    tagger=tagger,
                )
            )
            return get_match_teams

        # end of local functions.
        # build_schedule main code starts here
        matchtypes = {
            "matches": get_matches,  # list of matches
            "rounds": get_matches_by_round,  # list of matches by round
            "generate": get_section,  # generate list of matches
        }
        sectiondata = {
            "allplayall": add_allplayall_section,  # individuals
            "league": self.add_league_section,  # team all play all
            "swiss": add_swiss_section,  # individuals
            "fixturelist": lambda: None,  # matches from fixture list
            "individual": add_individual_section,  # games between players
        }
        sectiontypes = {
            "allplayall": get_allplayall_round_dates,  # individuals
            "league": get_league_teams,  # team all play all
            "swiss": get_swiss_round_dates,  # individuals
            "fixturelist": get_match_teams,  # matches from fixture list
            "individual": get_individual_players,  # games between players
        }
        playtypes = {
            "rapidplay": True,  # rapid play sections follow
            "normalplay": False,  # normal play sections follow
        }

        self.textlines = textlines
        self._process_textlines(get_event_name)

        # hack to spot empty schedule
        # Try to get rid of it so self.append_generated_schedule is not needed.
        if self.es_startdate is None or self.es_enddate is None:
            self.error.append(
                (
                    "Schedule has too few lines for event dates to be present",
                    self,
                )
            )

    # Tagging not used yet so the argument is the text from error, not the key
    # of the item in self._generated_schedule containing the text.
    @staticmethod
    def get_schedule_tag_and_text(text):  # key):
        """Return tuple(tag, text for error)."""
        return ("gash", text)  # self._generated_schedule[key])
