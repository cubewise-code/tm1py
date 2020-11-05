# -*- coding: utf-8 -*-
from typing import List

from TM1py.Objects.TM1Object import TM1Object


class Rules(TM1Object):
    """
        Abstraction of Rules on a cube.

        rules_analytics
            A collection of rulestatements, where each statement is stored in uppercase without linebreaks.
            comments are not included.

    """
    KEYWORDS = ['SKIPCHECK', 'FEEDSTRINGS', 'UNDEFVALS', 'FEEDERS']

    def __init__(self, rules: str):
        """
        Initialize rules.

        Args:
            self: (todo): write your description
            rules: (str): write your description
        """
        self._text = rules
        self._rules_analytics = []
        self.init_analytics()

    # self._rules_analytics_upper serves for analysis on cube rules
    def init_analytics(self):
        """
        Parse the comments.

        Args:
            self: (todo): write your description
        """
        text_without_comments = '\n'.join(
            [rule
             for rule in self._text.split('\n')
             if len(rule.strip()) > 0 and rule.strip()[0] != '#'])
        for statement in text_without_comments.split(';'):
            if len(statement.strip()) > 0:
                self._rules_analytics.append(statement.replace('\n', '').upper())

    @property
    def text(self) -> str:
        """
        Return the text.

        Args:
            self: (todo): write your description
        """
        return self._text

    @property
    def rules_analytics(self) -> List[str]:
        """
        List : class : return :

        Args:
            self: (todo): write your description
        """
        return self._rules_analytics

    @property
    def rule_statements(self) -> List[str]:
        """
        A list of rules for this rule.

        Args:
            self: (todo): write your description
        """
        if self.has_feeders:
            return self.rules_analytics[:self._rules_analytics.index('FEEDERS')]
        return self.rules_analytics

    @property
    def feeder_statements(self) -> List[str]:
        """
        List of feeder rules.

        Args:
            self: (todo): write your description
        """
        if self.has_feeders:
            return self.rules_analytics[self._rules_analytics.index('FEEDERS') + 1:]
        return []

    @property
    def skipcheck(self) -> bool:
        """
        Determine if the rules should be skipped.

        Args:
            self: (todo): write your description
        """
        for rule in self._rules_analytics[0:5]:
            if rule == 'SKIPCHECK':
                return True
        return False

    @property
    def undefvals(self) -> bool:
        """
        Determine if the rules match.

        Args:
            self: (todo): write your description
        """
        for rule in self._rules_analytics[0:5]:
            if rule == 'UNDEFVALS':
                return True
        return False

    @property
    def feedstrings(self) -> bool:
        """
        Determine if the rules in the rules.

        Args:
            self: (todo): write your description
        """
        for rule in self._rules_analytics[0:5]:
            if rule == 'FEEDSTRINGS':
                return True
        return False

    @property
    def has_feeders(self) -> bool:
        """
        Return true if the feed has feeders.

        Args:
            self: (todo): write your description
        """
        if 'FEEDERS' in self._rules_analytics:
            # has feeders declaration
            feeders = self.rules_analytics[self._rules_analytics.index('FEEDERS'):]
            # has at least one actual feeder statements
            return len(feeders) > 1
        return False

    def __len__(self):
        """
        The number of rules in bytes.

        Args:
            self: (todo): write your description
        """
        return len(self.rules_analytics)

    # iterate through actual rule statments without linebreaks. Ignore comments.
    def __iter__(self):
        """
        Return an iterable of rules.

        Args:
            self: (todo): write your description
        """
        return iter(self.rules_analytics)

    def __str__(self):
        """
        Str : str

        Args:
            self: (todo): write your description
        """
        return self.text
