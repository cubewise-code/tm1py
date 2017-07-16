
class Rules:
    """
        Abstraction of Rules on a cube.

        rules_analytics
            A collection of rulestatements, where each statement is stored without linebreaks.
            comments are not included.

        Currently rules object is not meant not be edited. To be written!

    """
    keywords = ['SKIPCHECK', 'FEEDSTRINGS', 'UNDEFVALS', 'FEEDERS']

    def __init__(self, rules):
        self._text = rules
        self._rules_analytics = []
        self._rules_analytics_upper = []
        self.init_analytics()

    def init_analytics(self):
        text_without_comments = '\n'.join(
            [rule for rule in self._text.split('\n') if len(rule) > 0 and rule.strip()[0] != '#'])
        for statement in text_without_comments.split(';'):
            if len(statement.strip()) > 0:
                self._rules_analytics.append(statement.replace('\n', ''))
        # self._rules_analytics_upper serves for analysis on cube rules
        self._rules_analytics_upper = [rule.upper() for rule in self._rules_analytics]

    @property
    def text(self):
        return self._text

    @property
    def rules_analytics(self):
        return self._rules_analytics

    @property
    def rule_statements(self):
        if self.has_feeders:
            return self.rules_analytics[:self._rules_analytics_upper.index('FEEDERS')]
        return self.rules_analytics

    @property
    def feeder_statements(self):
        if self.has_feeders:
            return self.rules_analytics[self._rules_analytics_upper.index('FEEDERS')+1:]
        return []

    @property
    def skipcheck(self):
        for rule in self._rules_analytics_upper[0:5]:
            if rule == 'SKIPCHECK':
                return True
        return False

    @property
    def undefvals(self):
        for rule in self._rules_analytics_upper[0:5]:
            if rule == 'UNDEFVALS':
                return True
        return False

    @property
    def feedstrings(self):
        for rule in self._rules_analytics_upper[0:5]:
            if rule == 'FEEDSTRINGS':
                return True
        return False

    @property
    def has_feeders(self):
        if 'FEEDERS' in self._rules_analytics_upper:
            # has feeders declaration
            feeders = self.rules_analytics[self._rules_analytics_upper.index('FEEDERS'):]
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