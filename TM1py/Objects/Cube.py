# -*- coding: utf-8 -*-

import collections
import json

from TM1py.Objects.Rules import Rules
from TM1py.Objects.TM1Object import TM1Object



class Cube(TM1Object):
    """ Abstraction of a TM1 Cube
        
    """
    def __init__(self, name, dimensions, rules=None):
        """
        
        :param name: name of the Cube
        :param dimensions: list of (existing) dimension names
        :param rules: instance of TM1py.Objects.Rules
        """
        self._name = name
        self._dimensions = dimensions
        self._rules = rules

    @property
    def name(self):
        return self._name

    @property
    def dimensions(self):
        return self._dimensions

    @dimensions.setter
    def dimensions(self, value):
        self._dimensions = value

    @property
    def has_rules(self):
        if self._rules:
            return True
        return False

    @property
    def rules(self):
        return self._rules

    @rules.setter
    def rules(self, value):
        self._rules = value

    @property
    def skipcheck(self):
        if self.has_rules:
            return self.rules.skipcheck
        return False

    @property
    def undefvals(self):
        if self.has_rules:
            return self.rules.undefvals
        return False

    @property
    def feedstrings(self):
        if self.has_rules:
            return self.rules.feedstrings
        return False

    @classmethod
    def from_json(cls, cube_as_json):
        """ Alternative constructor

        :param cube_as_json: user as JSON string
        :return: cube, an instance of this class
        """
        cube_as_dict = json.loads(cube_as_json)
        return cls.from_dict(cube_as_dict)

    @classmethod
    def from_dict(cls, cube_as_dict):
        """ Alternative constructor

        :param cube_as_dict: user as dict
        :return: user, an instance of this class
        """
        return cls(name=cube_as_dict['Name'],
                   dimensions=[dimension['Name'] for dimension in cube_as_dict['Dimensions']],
                   rules=Rules(cube_as_dict['Rules']) if cube_as_dict['Rules'] else None)

    @property
    def body(self):
        return self._construct_body()

    def _construct_body(self):
        """
        construct body (json) from the class attributes
        :return: String, TM1 JSON representation of a cube
        """
        body_as_dict = collections.OrderedDict()
        body_as_dict['Name'] = self.name
        body_as_dict['Dimensions@odata.bind'] = ['Dimensions(\'{}\')'.format(dimension)
                                                 for dimension
                                                 in self.dimensions]
        if self.rules:
            body_as_dict['Rules'] = str(self.rules)
        return json.dumps(body_as_dict, ensure_ascii=False)
