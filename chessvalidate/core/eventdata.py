# eventdata.py
# Copyright 2014 Roger Marsh
# Licence: See LICENCE (BSD licence)

"""Source data class chess results extracted from collection of emails.

An instance of EventData is created by the EventParser class for each extracted
data item, usually but not always one item per line.  The event configuration
file must contain regular expressions to drive the extraction from non-default
data formats.

"""
from solentware_misc.core import utilities

from .eventcontext import EventContext
from .found import (
    Score,
    Found,
)


class EventData:
    """Detail of a data item extracted from a collection of emails."""

    _attributes = (
        "eventname",
        "startdate",
        "enddate",
        "swiss",
        "person",
        "pin",
        "allplayall",
        "competition",
        "competition_round",
        "teamone",
        "teamtwo",
        "teams",
        "fixture_date",
        "fixture_day",
        "result_date",
        "nameone",
        "nametwo",
        "names",
        "score",
        "result_only",
        "numbers",
        "rounddates",
        "colour",
        "played_on",
        "source",
    )
    _inheritable = (
        ("eventname", "startdate", "enddate"),
        ("competition", "result_date", "competition_round"),
    )

    def __init__(
        self,
        datatag=None,
        context=None,
        found=None,
        raw=None,
        headers=None,
        **kargs
    ):
        """Initialiase EventData instance."""
        self.datatag = datatag
        self.found = found
        self.raw = raw
        self.headers = headers
        for attribute in self.__class__._attributes:
            if attribute in kargs:
                self.__dict__[attribute] = kargs[attribute]
        if isinstance(context, EventContext):
            for i, j in zip(
                self.__class__._inheritable,
                (context.event_identity, context.competition),
            ):
                for i_attr, j_attr in zip(i, j):
                    if j_attr is not None:
                        if i_attr not in self.__dict__:
                            self.__dict__[i_attr] = j_attr
                        elif not self.__dict__[i_attr]:
                            self.__dict__[i_attr] = j_attr

            # AttributeError is assumed to be absence of eventname, usually
            # because event name and date not given at top of input data.
            try:
                context.process(self)
            except AttributeError:
                self._ignore = found
                self.found = Found.IGNORE

        # The text generated for display in the schedule and report widgets.
        # The idea is tagging information can be picked from the containing
        # EventData instance when filling the widget provided the text is
        # picked by (EventData instance, serial number) where serial number,
        # indicating production order, is a key of the appropriate dictionary.
        # Though tagging has not percolated down this far yet!
        self._generated_schedule = {}
        self._generated_report = {}
        # tracer for fixing regular expressions
        # print(self.__dict__) # tracer
        # print() #tracer

    def is_game_result(self):
        """Return True if self represents a game result.

        The score text is tested againt conventional representations of
        game results in Score class to assist the decision.

        """
        if not self.is_result():
            return False
        if self.score in Score.conventional_match_game_results:
            return False
        return not self.is_match_result()

    def is_match_result(self):
        r"""Return True if self repesents a match result.

        If the score text is exactly '\xbd' self is assumed a game result.

        If the score text ends with '\xbd' self is assumed a match result.

        If the total score is 1 self is assumed a game result.

        Otherwise a match result.

        """
        if not self.is_result():
            return False
        # if self.score in Score.conventional_match_game_results:
        #    return True
        score = []
        for text in self.score.split():
            if text == "\xbd":
                score.append(0.5)
            elif text.endswith("\xbd"):
                return True
            else:
                try:
                    score.append(float(text))
                except ValueError:
                    return False
        return sum(float(text) for text in score) != 1

    def is_match_and_game_result(self):
        """Return True if self represents a tabular result."""
        return self.found == Found.CSV_TABULAR

    def is_result(self):
        """Return True if self represents a ratable result."""
        return self.found in Found.real_result

    def append_generated_schedule(self, schedule, text):
        """Append generation reference for text to schedule."""
        self._generated_schedule[len(schedule)] = text
        schedule.append((len(schedule), self))

    def append_generated_report(self, report, text):
        """Append generation reference for text to report."""
        self._generated_report[len(report)] = text
        report.append((len(report), self))

    def get_report_tag_and_text(self, key):
        """Return (tag, text) for self._generated_report[key].

        Intended for tagging text with tag when inserted into a Text widget.

        """
        return (self.datatag, self._generated_report[key])

    def get_schedule_tag_and_text(self, key):
        """Return (tag, text) for self._generated_schedule[key].

        Intended for tagging text with tag when inserted into a Text widget.

        """
        return (self.datatag, self._generated_schedule[key])

    def print_(self):
        """Print trace when fixing problems."""
        print(self.__dict__)

    def is_match_defaulted(self):
        """Return True if match defaulted."""
        if self.found == Found.RESULT:
            return self.score == Score.match_defaulted
        return False

    def is_defaulting_side_known(self):
        """Return True if defaulting side can be decided."""
        if self.found == Found.RESULT:
            return self.score in Score.included_in_team_score
        return False

    def is_default_counted(self):
        """Return True if default counts to match result."""
        if self.found == Found.RESULT:
            return self.score == Score.default
        return False

    def is_default_not_counted(self):
        """Return True if default doed not count to match result."""
        if self.found == Found.RESULT:
            return self.score in Score.excluded_from_match_score
        return False


class TableEventData(EventData):
    """Add partial comparison to EventData."""

    _attributes = EventData._attributes + (
        "teamonescore",
        "teamtwoscore",
    )

    gdate = utilities.AppSysDate()

    def __init__(self, context=None, **kargs):
        """Initialiase TableEventData instance."""
        super().__init__(context=context, **kargs)
        self.context = context
        result_date = self.result_date
        if TableEventData.gdate.parse_date(result_date) == len(result_date):
            self.date_played = TableEventData.gdate.iso_format_date()
        else:
            self.date_played = ""

    def __eq__(self, other):
        """Return True if self equals other."""
        if self.competition != other.competition:
            return False
        if self.date_played != other.date_played:
            return False
        if self.competition_round != other.competition_round:
            return False
        if self.teamone != other.teamone:
            return False
        if self.teamtwo != other.teamtwo:
            return False
        if self.numbers[0] != other.numbers[0]:
            return False
        return True

    def __lt__(self, other):
        """Return True if self less than other."""
        if self.competition < other.competition:
            return True
        if self.date_played < other.date_played:
            return True

        # Adopt numeric string convention
        if len(self.competition_round) < len(other.competition_round):
            return True

        if self.competition_round < other.competition_round:
            return True
        if self.teamone < other.teamone:
            return True
        if self.teamtwo < other.teamtwo:
            return True

        # Adopt numeric string convention
        if len(self.numbers[0]) < len(other.numbers[0]):
            return True

        if self.numbers[0] < other.numbers[0]:
            return True
        return False
