# names.py
# Copyright 2014 Roger Marsh
# Licence: See LICENCE (BSD licence)

"""Pick possible names from string containing two names separated by junk.

Assumptions are:
Names are consistent between input strings.
A name appears at least once as first name in string.
A name appears at least once as second name in string.
There may be no junk.

Accurracy is essential.  Compare and contrast with the matchteams module.

"""


class Names(object):
    """All pairs of phrases with first word in one phrase and last in other.

    The string 'a b c d e f' produces 20 pairs by removing each set, including
    the empty set, of adjacent words containing neither 'a' nor 'f' from the
    original string.  Samples are (a, f) (a b, e f) (a, d e f).  But never
    reversing word order or using a word more than once in a pair.

    """

    def __init__(self, string="", split=True):
        """ """
        super().__init__()
        self._namephrases = None
        if not isinstance(string, str):
            if not isinstance(string, (list, tuple)):
                sentence = ("",)
                split = False
            else:
                sentence = tuple(string)
        else:
            sentence = string.split()
        self.string = " ".join(sentence)
        if not split:
            if not self.string:
                self.namepairs = []
            else:
                self.namepairs = [(self.string, "")]
            return
        position = set()
        for i in range(1, len(sentence)):
            position.add((" ".join(sentence[:i]), 0, i))
            for j in range(i, len(sentence)):
                position.add((" ".join(sentence[j:]), j, len(sentence) - j))
        if len(sentence) == 1:
            self.namepairs = [(self.string, "")]
        else:
            namepairs = []
            for s1, p1, len1 in position:
                if p1 == 0:
                    for s2, p2, len2 in position:
                        if p2 >= len1:
                            namepairs.append((len1 * len2, len1, (s1, s2)))
            self.namepairs = [n[-1] for n in sorted(namepairs)]

    @property
    def namephrases(self):
        """ """
        if self._namephrases is None:
            namephrases = set()
            for p in self.namepairs:
                namephrases.update(p)
            namephrases.discard("")
            self._namephrases = namephrases
        return self._namephrases

    def guess_names_from_known_names(self, known_names):
        """Set best (name1, name2) from self.string given names in known_names.

        self.namepairs holds (name1, name2) tuples ordered by the calculated
        guess of probability of extract from self.string being the names.

        Names are assumed to start and end self.string with an unknown amount
        of junk between the two names.  At least one of the names is not in
        known_names.  All junk is assumed part of other name when one name is
        in known names.  When both names are unknown the words, whitespace
        delimited, are divided equally between the two names: the first name
        gets the extra odd word if necessary.

        """
        starts_with = ""
        ends_with = ""
        string = self.string
        for k in known_names:
            if string.startswith(k):
                if len(k) > len(starts_with):
                    starts_with = k
            if string.endswith(k):
                if len(k) > len(ends_with):
                    ends_with = k
        if starts_with:
            ends_with = string.replace(starts_with, "").strip()
        elif ends_with:
            starts_with = string.replace(ends_with, "").strip()
        else:
            s = string.split()
            starts_with = " ".join(s[: (1 + len(s)) // 2])
            ends_with = " ".join(s[(1 + len(s)) // 2 :])
        self.namepairs = ((starts_with, ends_with),)
