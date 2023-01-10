# reportbase.py
# Copyright 2022 Roger Marsh
# Licence: See LICENCE (BSD licence)

"""Provide attributes and methods shared by Report and Schedule classes."""


class ReportBase:
    """Base class for Report and Schedule classes."""

    def __init__(self):
        """Initialise attributes shared by Report and Schedule for event."""
        super().__init__()
        self.textlines = None
        self.error = []
        # There are corresponding er_* and es_* attributes in Report and
        # Schedule classes.  No guarantee it is safe to use the prefixless
        # names in the commented lines here.
        # self.section = dict()
        # self.report_order = []
        # self.name = None
        # self.pins = dict()
        # self.players = dict()
        # self.team_number = dict()
        self._section = None  # latest section name found by get_section
        self._round = None  # round in "round" line (get_section sets to None)

    # pylint duplicate-code report prompted introduction of this class which
    # will provide motivation to get rid of er_* and es_* prefixes for
    # attributes in the Report and Schedule classes.
    # There is at least one method in the two classes identical except for
    # the preficies.
    def _process_textlines(self, process):
        """Generate report from self.textlines starting with process method."""
        for linestr, linetag in self.textlines:
            linestr = linestr.strip()
            if len(linestr) == 0:
                continue
            process = process(linestr, linetag)
