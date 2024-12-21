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


class Names:
    """All pairs of phrases with first word in one phrase and last in other.

    The string 'a b c d e f' produces 20 pairs by removing each set, including
    the empty set, of adjacent words containing neither 'a' nor 'f' from the
    original string.  Samples are (a, f) (a b, e f) (a, d e f).  But never
    reversing word order or using a word more than once in a pair.

    """

    def __init__(self, string="", split=True):
        """Initialize namepairs attribute from string argument."""
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
            for str1, pos1, len1 in position:
                if pos1 == 0:
                    for str2, pos2, len2 in position:
                        if pos2 >= len1:
                            namepairs.append((len1 * len2, len1, (str1, str2)))
            self.namepairs = [n[-1] for n in sorted(namepairs)]

    @property
    def namephrases(self):
        """Return set of name phrases."""
        if self._namephrases is None:
            namephrases = set()
            for name in self.namepairs:
                namephrases.update(name)
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
            words = string.split()
            starts_with = " ".join(words[: (1 + len(words)) // 2])

            # pycodestyle E203 whitespace before ':'.
            # black formatting insists on the space.
            ends_with = " ".join(words[(1 + len(words)) // 2 :])

        self.namepairs = ((starts_with, ends_with),)
