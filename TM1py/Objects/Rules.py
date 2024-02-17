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
        self._text = rules
        self._rules_analytics = []
        self.init_analytics()

    # self._rules_analytics_upper serves for analysis on cube rules
    def init_analytics(self):
        text_without_comments = '\n'.join(
            [rule
             for rule in self._text.split('\n')
             if len(rule.strip()) > 0 and rule.strip()[0] != '#'])
        for statement in text_without_comments.split(';'):
            if len(statement.strip()) > 0:
                self._rules_analytics.append(statement.replace('\n', '').upper())

    @property
    def text(self) -> str:
        return self._text

    @property
    def rules_analytics(self) -> List[str]:
        return self._rules_analytics

    @property
    def rule_statements(self) -> List[str]:
        if self.has_feeders:
            return self.rules_analytics[:self._rules_analytics.index('FEEDERS')]
        return self.rules_analytics

    def add_rule_statements(self, statements:Union[str, List[str]]):
        if isinstance(statements, list):
            statements = '\n'.join(statements)
        if self.has_feeders:
            text_split = self._text.split('FEEDERS;')
            self._text = f"{text_split[0]}\n{statements}\nFEEDERS;\n{text_split[1]}"
        else:
            self._text += f"\n{statements}"
        self.init_analytics()

    # This function is a little more complicated, because it avoids calling init_analytics() to optimize processing time
    def add_rule_statements(self, statements: Union[str, List[str]]):
        if isinstance(statements, str):
            statements = [statements]
        modified_statements = list(map(lambda x: x[:-1] if ';' in x else x, statements))
        if self.has_feeders:
            text_split = self._text.split('FEEDERS;')
            statements_string = "\n".join(statements)
            self._text = f"{text_split[0]}{statements_string}\nFEEDERS;{text_split[1]}"
            feeders_index = self._rules_analytics.index('FEEDERS')
            self._rules_analytics = self._rules_analytics[:feeders_index] + modified_statements + self._rules_analytics[feeders_index:]
        else:
            self._text += "\n"+"\n".join(statements)
            self._rules_analytics += modified_statements

    @property
    def feeder_statements(self) -> List[str]:
        if self.has_feeders:
            return self.rules_analytics[self._rules_analytics.index('FEEDERS') + 1:]
        return []

    @property
    def skipcheck(self) -> bool:
        for rule in self._rules_analytics[0:5]:
            if rule == 'SKIPCHECK':
                return True
        return False

    @property
    def undefvals(self) -> bool:
        for rule in self._rules_analytics[0:5]:
            if rule == 'UNDEFVALS':
                return True
        return False

    @property
    def feedstrings(self) -> bool:
        for rule in self._rules_analytics[0:5]:
            if rule == 'FEEDSTRINGS':
                return True
        return False

    @property
    def has_feeders(self) -> bool:
        if 'FEEDERS' in self._rules_analytics:
            # has feeders declaration
            feeders = self.rules_analytics[self._rules_analytics.index('FEEDERS'):]
            # has at least one actual feeder statements
            return len(feeders) > 1
        return False

    def __len__(self):
        return len(self.rules_analytics)

    # iterate through actual rule statments without linebreaks. Ignore comments.
    def __iter__(self):
        return iter(self.rules_analytics)

    def __str__(self):
        return self.text
