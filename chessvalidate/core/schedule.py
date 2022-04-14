# schedule.py
# Copyright 2008 Roger Marsh
# Licence: See LICENCE (BSD licence)

"""Event schedule class.
"""

from solentware_misc.core import utilities

from .gameobjects import MatchFixture, Player, code_in_name


class ScheduleError(Exception):
    pass


class Schedule(object):

    """Schedule extracted from event schedule file containing one event.

    Support a free text format for leagues and events for individuals.

    Subclasses will deal with particular input formats.

    """

    def __init__(self):
        """Extend, initialise schedule data items."""
        super().__init__()
        self.textlines = None
        self.error = []
        self.es_startdate = None
        self.es_enddate = None
        self.es_rapidplay = dict()
        self.es_teams = dict()
        self.es_team_alias = dict()
        self.es_team_number = dict()
        self.es_matches = dict()  # fixtures by section
        self.es_fixtures = []
        self.es_summary = dict()
        self.rapidplay = False
        self._section = None  # latest section name found by get_section
        self.error_repeat = False
        self.es_section = dict()
        self.es_report_order = []
        self.es_name = None
        self.es_round_dates = dict()
        self.es_players = dict()  # keys are (name, pin) eg pin on swiss table
        self.es_pins = dict()  # map pin to name for es_players lookup
        self._maximum_round = None
        self._round = None

    def add_league_section(self):
        """Initialise data structures for league format."""
        self._set_league_section()

    def _set_league_section(self):
        """Initialise data structures for league format."""
        self.es_teams.setdefault(self._section, dict())
        self.es_team_number.setdefault(self._section, dict())
        self.es_team_alias.setdefault(self._section, dict())
        self.es_matches.setdefault(self._section, dict())
        self.es_rapidplay.setdefault(self._section, self.rapidplay)
        self.es_summary.setdefault(
            self._section, dict(matches=0, teams=dict())
        )

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
        c = fixture.competition
        estc = self.es_teams[c]
        essct = self.es_summary[c]["teams"]
        self.es_summary[c]["matches"] += 1
        for t in (fixture.hometeam, fixture.awayteam):
            if t not in estc:
                estc[t] = dict(club=self.default_club_for_team(t), section=c)
            if t not in essct:
                essct[t] = dict(
                    homematches=0,
                    awaymatches=0,
                    name=t,
                    division=c,
                )
            if t == fixture.hometeam:
                essct[t]["homematches"] += 1
            else:
                essct[t]["awaymatches"] += 1

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

    def build_schedule(self, textlines):
        """Populate the event schedule from textlines."""

        def get_allplayall_players(text, tagger):
            """Create Player instance from text and return state indicator."""
            pt, ct = split_text_and_pad(text, 1)
            s = pt.split()
            sl0 = s[0].lower()
            if sl0.isdigit():
                pin = s[0]
                name = " ".join(s[1:])
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
                codes = set([s.strip() for s in code_in_name.findall(name)])
                name = " ".join(
                    [s.strip() for s in code_in_name.split(name)]
                ).strip()
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
                    affiliation=" ".join(ct.split()),
                    reported_codes=codes,
                )
                self.es_players[self._section][(name, pin)] = player
                self.es_pins[self._section][pin] = name
                return get_allplayall_players
            elif sl0 in sectiontypes:
                return get_section(text, tagger)
            elif sl0 in playtypes:
                return get_section(text, tagger)
            else:
                tagger.append_generated_schedule(
                    self.error,
                    "".join(('No PIN in "', text, '"')),
                )
                self.error_repeat = False
                return get_allplayall_players

        def get_allplayall_round_dates(text, tagger):
            """Extract round date from text and return state indicator."""
            if "players" == text.lower():
                return get_allplayall_players
            s = text.split()
            s0 = s.pop(0)
            if s0.isdigit():
                rdate = utilities.AppSysDate()
                dt = " ".join(s)
                rd = rdate.parse_date(dt)
                if rd == len(dt):
                    self.es_round_dates[self._section][
                        int(s0)
                    ] = rdate.iso_format_date()
                    return get_allplayall_round_dates
            for e in s:
                if e.isdigit():
                    if s0.isdigit():
                        tagger.append_generated_schedule(
                            self.error,
                            "".join(
                                (
                                    '"',
                                    text,
                                    '" ',
                                    "assumed to be invalid date for round ",
                                    s0,
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
            dt = " ".join(text.split())
            sd = sdate.parse_date(dt)
            ed = edate.parse_date(dt[sd:])
            if sd + ed == len(dt):
                self.es_startdate = sdate.iso_format_date()
                self.es_enddate = edate.iso_format_date()
            else:
                tagger.append_generated_schedule(
                    self.error,
                    "".join(
                        ('Start or end date not recognised in "', dt, '"')
                    ),
                )
            return get_section

        def get_event_name(text, tagger):
            """Extract event name from text and return state indicator."""
            en = text.split()
            self.es_name = " ".join(en)
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
            """Module structure requires this function to exist.

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
            tm, cb, ta = split_text_and_pad(text, 2)
            t = tm.split()
            t0 = t[0].lower()
            if t0 in matchtypes:
                return get_match_specification_type(text, tagger)
            team = " ".join(tm.split())
            club = " ".join(cb.split())
            teamalias = [a for a in ta.split("\t") if len(a)]
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
            self.es_teams[self._section][team] = dict(
                club=club,
                # homematches=0, count appearances in self.es_matches?
                # awaymatches=0,
                section=self._section,
            )
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
            t = text.split()
            t0 = t[0].lower()
            if t0 in matchtypes:
                if self.error_repeat:
                    tagger.append_generated_schedule(
                        self.error,
                        "".join(
                            ('Match type "', t0, '" ', "found after errors")
                        ),
                    )
                    self.error_repeat = False
                if t0 == "rounds":
                    if len(t) != 2:
                        tagger.append_generated_schedule(
                            self.error,
                            "".join(
                                (
                                    '"',
                                    text,
                                    '"must be like "rounds 10" to specify the ',
                                    "number of rounds of matches.  If a round is ",
                                    "given for a match it must be between 1 and ",
                                    "the number.  The matches should be given in ",
                                    "a fixture list.",
                                )
                            ),
                        )
                        return get_match_specification_type
                    if not t[1].isdigit():
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
                    if int(t[1]) == 0:
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
                    self._maximum_round = str(int(t[1]))
                elif t0 == "generate":
                    if len(t) != 2:
                        tagger.append_generated_schedule(
                            self.error,
                            "".join(
                                (
                                    '"',
                                    text,
                                    '" must be like "generate 2" to specify the ',
                                    "number of times the teams play each other.  ",
                                    "The team names are reversed in odd and even ",
                                    "numbered matches assuming this may mean home ",
                                    "and away.  The generated list of matches ",
                                    "does not give dates or rounds for the ",
                                    "matches.",
                                )
                            ),
                        )
                        return get_match_specification_type
                    if not t[1].isdigit():
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
                    generate_matches(int(t[1]))
                return matchtypes[t0]
            if self.error_repeat:
                return get_match_specification_type
            tagger.append_generated_schedule(
                self.error,
                "".join(
                    (
                        'Match type "',
                        t0,
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
            r = text.split()
            r0 = r[0].lower()
            if r0 == "round":
                if len(r) != 2:
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
                if not r[1].isdigit():
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
                if int(r[1]) > int(self._maximum_round):
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
                if int(r[1]) == 0:
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
                self._round = str(int(r[1]))
                return get_matches_by_round
            rtn, match = get_match(text, tagger)
            if match:
                team1, team2, date = match
                teams = dict()
                for m in self.es_matches[self._section]:
                    if self._round == self.es_matches[self._section][m].round:
                        teams[m[0]] = None
                        teams[m[1]] = None
                if team1 not in teams:
                    if team2 not in teams:
                        self.es_matches[self._section][
                            match
                        ] = self.es_fixtures[-1]
                        return get_matches_by_round
                tagger.append_generated_schedule(
                    self.error,
                    "".join(
                        (
                            'Match "',
                            text,
                            '" involves a team in an earlier match for round "',
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
            s = text.split()
            st = s[0].lower()
            if st in playtypes:
                self.rapidplay = playtypes[st]
                return get_section
            if st not in sectiontypes:
                if self.error_repeat:
                    return get_section
                tagger.append_generated_schedule(
                    self.error,
                    "".join(
                        (
                            'Section type "',
                            st,
                            '" ',
                            "not recognised",
                            "\n\nAllowed section types are:\n\t",
                            "allplayall\t\tall play all table for individuals\n\t",
                            "league\t\ta list of matches in rounds\n\t",
                            "swiss\t\tswiss tournament table for individuals\n\t",
                            "individual\t\ta list of games between individuals\n\t",
                            "\n\nAlso allowed at this point is the type of game ",
                            "in following sections:\n\t",
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
                        ('Section type "', st, '" ', "found after errors")
                    ),
                )
                self.error_repeat = False
            self._section = " ".join(s[1:])
            if self._section in self.es_section:
                tagger.append_generated_schedule(
                    self.error,
                    "".join(('Section "', self._section, '" named earlier')),
                )
                self.error_repeat = True
                return get_section
            self.es_section[self._section] = st
            self.es_report_order.append(self._section)
            sectiondata[st]()
            return sectiontypes[st]

        def get_swiss_players(text, tagger):
            """Create Player instance from text and return state indicator."""
            pt, ct = split_text_and_pad(text, 1)
            s = pt.split()
            sl0 = s[0].lower()
            if sl0.isdigit():
                pin = s[0]
                name = " ".join(s[1:])
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
                codes = set([s.strip() for s in code_in_name.findall(name)])
                name = " ".join(
                    [s.strip() for s in code_in_name.split(name)]
                ).strip()
                pin = int(pin)
                player = Player(
                    tagger=tagger,
                    name=name,
                    event=self.es_name,
                    startdate=self.es_startdate,
                    enddate=self.es_enddate,
                    section=self._section,
                    pin=pin,
                    affiliation=" ".join(ct.split()),
                    reported_codes=codes,
                )
                self.es_players[self._section][(name, pin)] = player
                self.es_pins[self._section][pin] = name
                return get_swiss_players
            elif sl0 in sectiontypes:
                return get_section(text, tagger)
            elif sl0 in playtypes:
                return get_section(text, tagger)
            else:
                tagger.append_generated_schedule(
                    self.error,
                    "".join(('No PIN in "', text, '"')),
                )
                self.error_repeat = False
                return get_swiss_players

        def get_swiss_round_dates(text, tagger):
            """Extract round date from text and return state indicator."""
            if "players" == text.lower():
                return get_swiss_players
            s = text.split()
            s0 = s.pop(0)
            if s0.isdigit():
                rdate = utilities.AppSysDate()
                dt = " ".join(s)
                rd = rdate.parse_date(dt)
                if rd == len(dt):
                    self.es_round_dates[self._section][
                        int(s0)
                    ] = rdate.iso_format_date()
                    return get_swiss_round_dates
            for e in s:
                if e.isdigit():
                    if s0.isdigit():
                        tagger.append_generated_schedule(
                            self.error,
                            "".join(
                                (
                                    '"',
                                    text,
                                    '" ',
                                    "assumed to be invalid date for round ",
                                    s0,
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
            self.es_pins.setdefault(self._section, dict())
            self.es_players.setdefault(self._section, dict())
            self.es_rapidplay.setdefault(self._section, self.rapidplay)
            self.es_round_dates.setdefault(self._section, dict())

        def add_individual_section():
            """Initialise data structures for individual game format."""
            self.es_players.setdefault(self._section, dict())
            self.es_rapidplay.setdefault(self._section, self.rapidplay)

        def add_swiss_section():
            """Initialise data structures for swiss wall-chart format."""
            self.es_players.setdefault(self._section, dict())
            self.es_pins.setdefault(self._section, dict())
            self.es_rapidplay.setdefault(self._section, self.rapidplay)
            self.es_round_dates.setdefault(self._section, dict())

        def split_text_and_pad(text, count, separator=None):
            """Return tuple of text split maximum count times by separator."""
            if separator == None:
                separator = "\t"
            s = text.split(separator, count)
            if len(s) < count + 1:
                s.extend([""] * (count - len(s) + 1))
            return s

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
            """Create MatchFixture from text, return (state indicator, match)."""
            t1, t2 = split_text_and_pad(text, 1)
            tp = t1.split()
            tp0 = tp[0].lower()
            if tp0 in matchtypes:
                return (get_match_specification_type(text, tagger), None)
            if tp0 in sectiontypes:
                return (get_section(text, tagger), None)
            if tp0 in playtypes:
                self.rapidplay = playtypes[tp0]
                return (get_section, None)
            t1 = " ".join(tp)
            mdate = utilities.AppSysDate()
            md = mdate.parse_date(t1)
            if (
                md < 3
            ):  # not md < -1 so leading digits can be part of team name
                tdate = ""
                team1 = t1
            else:  # badly formatted dates treated as part of team name
                tdate = mdate.iso_format_date()
                team1 = " ".join(t1[md:].split())
            team2 = " ".join(t2.split())
            error = False
            for t in (team1, team2):
                if t not in self.es_teams[self._section]:
                    tagger.append_generated_schedule(
                        self.error,
                        "".join(
                            (
                                'Team name "',
                                t,
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
            pd = date_checker.parse_date(pdate)
            if date_checker.parse_date(pdate) == -1:
                dateok = False
                tagger.append_generated_schedule(self.error, text)
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
        state = None
        process = get_event_name
        for linestr, linetag in self.textlines:
            linestr = linestr.strip()
            if len(linestr) == 0:
                continue
            state = process
            process = process(linestr, linetag)

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
    # of the item in self._generated_schedule containing the text (or whatever).
    def get_schedule_tag_and_text(self, text):  # key):
        """ """
        return ("gash", text)  # self._generated_schedule[key])
