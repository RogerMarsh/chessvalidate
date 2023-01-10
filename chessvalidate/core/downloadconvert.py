# downloadconvert.py
# Copyright 2022 Roger Marsh
# Licence: See LICENCE (BSD licence)

"""Convert CSV file to tabular text expected by eventdata.EventData class.

A CSV format is defined from which results can be extracted by default
processing.  Some sources of CSV files, websites, may omit some of the
data expected: perhaps because it can be assumed from the identity of the
source, or because it seems irrelevant.  Event name and match score are one
example of each.

Omitting match score forces the assumption all game results were entered
correctly.  Omitting event name is reasonable except if including multiple
events in a CSV file is required.
"""

import os
import tkinter
import urllib.parse
import urllib.request
import csv
import io
import difflib

from emailextract.core.emailextractor import EXTRACTED_CONF

# Now a badly named module and class: not an email in sight here.
# The rules needed are a subset of those supported by this class.
# (And it is possible the CSV file will be sent by email.)
from .emailextractor import (
    EmailExtractor,
    REPORT_CSV_DATA_NAME,
    REPORT_TABLE,
    TEXTENTRY,
)


class DownloadConvertError:
    """Exception class for downloadconf module."""


class DownloadConvert:
    """Extract text from CSV download containing chess game results."""

    def __init__(self, downloader, parent):
        """Initialise converter to no conversion done."""
        self.most_recent_action = None
        self.downloader = downloader
        self._parent = parent
        self._actions_done = set()

    def show_url_content(self, widget):
        """Populate widget with downloaded CSV text."""
        if self.show_url_content in self._actions_done:
            return True
        url = urllib.parse.urlparse(self.downloader.url)
        url = url._replace(path=os.path.expanduser(url.path))
        try:
            with urllib.request.urlopen(urllib.parse.urlunparse(url)) as file:
                widget.delete("1.0", tkinter.END)
                widget.insert(
                    tkinter.END, file.read().decode(self.downloader.encoding)
                )
        except urllib.request.URLError as exc:
            tkinter.messagebox.showinfo(
                parent=self._parent,
                title="Show URL Content",
                message="Problem opening URL: " + str(exc),
            )
            return False
        except ValueError as exc:
            tkinter.messagebox.showinfo(
                parent=self._parent,
                title="Show URL Content",
                message="Problem opening URL:\n\n" + str(exc),
            )
            return False
        self.most_recent_action = self.show_url_content
        self._actions_done.add(self.show_url_content)
        return True

    def show_tabular_text(self, widget, csvtext, directory):
        """Populate widget with tabular text from CSV text."""
        if self.show_tabular_text in self._actions_done:
            return True
        extractor = self._get_extractor_configuration(
            directory,
            "Show Tabular Text",
        )
        if extractor is None:
            return False
        csvdata = extractor.criteria[REPORT_CSV_DATA_NAME]
        replace_map = {}
        for item in csvdata[-1][-1].values():
            for key, value in item[-1].items():
                if value:
                    replace_map[key] = value
        expected_columns = []
        column_map = {}
        for key, value in csvdata[-1][-1].items():
            expected_columns.extend(value[0])
            for name in value[0]:
                column_map[key] = value[0]
        if extractor.home_win and extractor.away_win and extractor.draw:
            calculate_match_score = (
                extractor.home_team_score[0] not in column_map
                or extractor.away_team_score[0] not in column_map
            )
        else:
            calculate_match_score = False
        columnids = set(n.isdigit() for n in expected_columns)
        if len(columnids) != 1:
            tkinter.messagebox.showinfo(
                parent=self._parent,
                message="Column identifiers must be all names or all numbers",
                title="Show Tabular Text",
            )
            return False
        fieldnames = () if columnids.pop() else None
        if csv.Sniffer().sniff(csvtext).delimiter not in ",/t;:":
            tkinter.messagebox.showinfo(
                parent=self._parent,
                message="Text does not look like CSV format",
                title="Show Tabular Text",
            )
            return False
        tabular = []
        scores = {}
        reader = csv.DictReader(io.StringIO(csvtext), fieldnames=fieldnames)
        if fieldnames is None:
            missing = set(expected_columns).difference(reader.fieldnames)
            if missing:
                tkinter.messagebox.showinfo(
                    parent=self._parent,
                    message=" ".join(missing).join(
                        ("Expected columns\n\n", "\n\nmissing from CSV file")
                    ),
                    title="Show Tabular Text",
                )
                return False
            for row in reader:
                for value in row.items():
                    if value is None:
                        tkinter.messagebox.showinfo(
                            parent=self._parent,
                            message="Missing value",
                            title="Show Tabular Text",
                        )
                        return False
                for name, item in replace_map.items():
                    if name in row:
                        for key, value in item.items():
                            if row[name] == key:
                                row[name] = value
                                break
                tabular_row = {}
                for key, value in column_map.items():
                    tabular_row[key] = " ".join([row[i] for i in value])
                self._add_default_tabular_values(tabular_row, extractor)
                if calculate_match_score:
                    self._cumulate_match_score(tabular_row, scores, extractor)
                tabular.append(tabular_row)
        else:
            header = csv.Sniffer().has_header(csvtext)
            if header:
                tkinter.messagebox.showinfo(
                    parent=self._parent,
                    message="".join(
                        (
                            "CSV file seems to have a header row: ",
                            "consider using column names in extract ",
                            "configuration file",
                        )
                    ),
                    title="Show Tabular Text",
                )
            minfields = max(int(n) for n in expected_columns) + 1
            for row in reader:
                if header:
                    header = False
                    continue
                row = row[None]
                if len(row) < minfields:
                    missing = [
                        n for n in expected_columns if int(n) >= len(row)
                    ]
                    tkinter.messagebox.showinfo(
                        parent=self._parent,
                        message=" ".join(missing).join(
                            (
                                "Expected columns\n\n",
                                "\n\nmissing from CSV file",
                            )
                        ),
                        title="Show Tabular Text",
                    )
                    return False
                for name, item in replace_map.items():
                    name = int(name)
                    if name < len(row):
                        for key, value in item.items():
                            if row[name] == key:
                                row[name] = value
                                break
                tabular_row = {}
                for key, value in column_map.items():
                    tabular_row[key] = " ".join([row[int(i)] for i in value])
                self._add_default_tabular_values(tabular_row, extractor)
                if calculate_match_score:
                    self._cumulate_match_score(tabular_row, scores, extractor)
                tabular.append(tabular_row)
        if calculate_match_score:
            home_team = extractor.home_team[0]
            away_team = extractor.away_team[0]
            home_team_score = extractor.home_team_score[0]
            away_team_score = extractor.away_team_score[0]
            section = extractor.section[0]
            date = extractor.date[0]
            for row in tabular:
                score = scores[row[section], row[date], row[home_team]]
                if round(float(score)) == float(score):
                    score = int(score)
                row[home_team_score] = str(score)
                score = scores[row[section], row[date], row[away_team]]
                if round(float(score)) == float(score):
                    score = int(score)
                row[away_team_score] = str(score)
        widget.delete("1.0", tkinter.END)
        widget.insert(
            tkinter.END, "\n".join(self._convert_tabular_to_text(tabular))
        )
        self.most_recent_action = self.show_tabular_text
        self._actions_done.add(self.show_tabular_text)
        return True

    @staticmethod
    def _convert_tabular_to_text(table):
        """Return table, a list of dict, converted to list of str."""
        text = []
        for row in table:
            data = []
            for name in REPORT_TABLE:
                if name not in row:
                    continue
                data.append(row[name])
            text.append("\t".join(data))
        return text

    def _cumulate_match_score(self, row, score, extractor):
        """Cumulate score in match from result in row."""
        home_team = row[extractor.home_team[0]]
        away_team = row[extractor.away_team[0]]
        section = row[extractor.section[0]]
        date = row[extractor.date[0]]
        result = row[extractor.result[0]]
        for side, total in (
            (away_team, extractor.away_team_score[0]),
            (home_team, extractor.home_team_score[0]),
        ):
            row[total] = (section, date, side)
        if result == extractor.home_win:
            self._add_point(score, (section, date, home_team))
        elif result == extractor.away_win:
            self._add_point(score, (section, date, away_team))
        elif result == extractor.draw:
            self._add_half_point(score, (section, date, home_team))
            self._add_half_point(score, (section, date, away_team))

    @staticmethod
    def _add_point(score, key):
        """Add point to score of key."""
        if key not in score:
            score[key] = 0
        score[key] += 1

    @staticmethod
    def _add_half_point(score, key):
        """Add half point to score of key."""
        if key not in score:
            score[key] = 0
        score[key] += 0.5

    @staticmethod
    def _add_default_tabular_value(row, name, description):
        """Add default value for name into row."""
        del description
        if name not in row:
            row[name] = ""

    def _add_default_tabular_values(self, row, extractor):
        """Add default values into row."""
        adtv = self._add_default_tabular_value
        adtv(row, *extractor.section)
        adtv(row, *extractor.day)
        adtv(row, *extractor.date)
        adtv(row, *extractor.round)
        adtv(row, *extractor.home_team)
        adtv(row, *extractor.home_team_score)
        adtv(row, *extractor.home_player)
        adtv(row, *extractor.result)
        adtv(row, *extractor.away_team)
        adtv(row, *extractor.away_team_score)
        adtv(row, *extractor.away_player)
        adtv(row, *extractor.board)
        adtv(row, *extractor.event)
        adtv(row, *extractor.home_player_colour)

    def update_difference_files(self, tabulartextlines, directory):
        """Show the text derived from the CSV file retrieved from URL."""
        if self.update_difference_files in self._actions_done:
            return True
        extractor = self._get_extractor_configuration(
            directory,
            "Save Downloaded Results",
        )
        if extractor is None:
            return False
        textentry = os.path.join(directory, extractor.criteria[TEXTENTRY])
        if not os.path.exists(textentry):
            tkinter.messagebox.showinfo(
                parent=self._parent,
                message="".join(
                    (
                        "Expected results file\n\n",
                        textentry,
                        "\n\ndoes not exist.",
                    )
                ),
                title="Save Downloaded Results",
            )
        if (
            tkinter.messagebox.askquestion(
                parent=self._parent,
                message="".join(
                    (
                        "Confirm that results file in\n\n",
                        directory,
                        "\n\ndirectory should be overwritten.",
                    )
                ),
                title="Save Downloaded Results",
            )
            != tkinter.messagebox.YES
        ):
            return False
        with open(textentry, mode="w", encoding="utf8") as file:
            file.writelines(difflib.ndiff(tabulartextlines, tabulartextlines))
        self.most_recent_action = self.update_difference_files
        self._actions_done.add(self.update_difference_files)
        return True

    def _get_extractor_configuration(self, directory, title):
        """Return extractor configuration or None."""
        with open(
            os.path.join(directory, EXTRACTED_CONF), "r", encoding="utf8"
        ) as file:
            extractor = EmailExtractor(
                directory,
                configuration=file.read(),
                extractemail=False,
                parent=self._parent,
            )
        if not extractor.parse():
            tkinter.messagebox.showinfo(
                parent=self._parent,
                message=(
                    "Problem in configuration file\n\n"
                    + os.path.join(directory, EXTRACTED_CONF)
                ),
                title=title,
            )
            return None
        return extractor
