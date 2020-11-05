# -*- coding: utf-8 -*-

import collections
import json
from typing import Iterable, List, Dict, Optional

from TM1py.Objects.Rules import Rules
from TM1py.Objects.TM1Object import TM1Object
from TM1py.Utils import format_url


class Cube(TM1Object):
    """ Abstraction of a TM1 Cube
        
    """

    def __init__(self, name: str, dimensions: Iterable[str], rules: Optional[Rules] = None):
        """
        
        :param name: name of the Cube
        :param dimensions: list of (existing) dimension names
        :param rules: instance of TM1py.Objects.Rules
        """
        self._name = name
        self.dimensions = list(dimensions)
        self.rules = rules

    @property
    def name(self) -> str:
        """
        Returns the name of this node.

        Args:
            self: (todo): write your description
        """
        return self._name

    @property
    def dimensions(self) -> List[str]:
        """
        The dimension : class.

        Args:
            self: (todo): write your description
        """
        return self._dimensions

    @dimensions.setter
    def dimensions(self, value: List[str]):
        """
        Gets / sets the dimensions

        Args:
            self: (todo): write your description
            value: (str): write your description
        """
        self._dimensions = value

    @property
    def has_rules(self) -> bool:
        """
        Returns true if the rules are present.

        Args:
            self: (todo): write your description
        """
        if self._rules:
            return True
        return False

    @property
    def rules(self) -> Rules:
        """
        Return the rules. rules.

        Args:
            self: (todo): write your description
        """
        return self._rules

    @rules.setter
    def rules(self, value: Rules):
        """
        Set rules

        Args:
            self: (todo): write your description
            value: (todo): write your description
        """
        self._rules = value

    @property
    def skipcheck(self) -> bool:
        """
        Returns true if the rules should be skipped.

        Args:
            self: (todo): write your description
        """
        if self.has_rules:
            return self.rules.skipcheck
        return False

    @property
    def undefvals(self) -> bool:
        """
        Undefvals.

        Args:
            self: (todo): write your description
        """
        if self.has_rules:
            return self.rules.undefvals
        return False

    @property
    def feedstrings(self) -> bool:
        """
        Returns true if the feedstrings is feedstrings.

        Args:
            self: (todo): write your description
        """
        if self.has_rules:
            return self.rules.feedstrings
        return False

    @classmethod
    def from_json(cls, cube_as_json: str) -> 'Cube':
        """ Alternative constructor

        :param cube_as_json: user as JSON string
        :return: cube, an instance of this class
        """
        cube_as_dict = json.loads(cube_as_json)
        return cls.from_dict(cube_as_dict)

    @classmethod
    def from_dict(cls, cube_as_dict: Dict) -> 'Cube':
        """ Alternative constructor

        :param cube_as_dict: user as dict
        :return: user, an instance of this class
        """
        return cls(
            name=cube_as_dict['Name'],
            dimensions=[dimension['Name'] for dimension in cube_as_dict['Dimensions']],
            rules=Rules(cube_as_dict['Rules']) if cube_as_dict['Rules'] else None)

    @property
    def body(self) -> str:
        """
        Return the body of the request.

        Args:
            self: (todo): write your description
        """
        return self._construct_body()

    def _construct_body(self) -> str:
        """
        construct body (json) from the class attributes
        :return: String, TM1 JSON representation of a cube
        """
        body_as_dict = collections.OrderedDict()
        body_as_dict['Name'] = self.name
        body_as_dict['Dimensions@odata.bind'] = [format_url("Dimensions('{}')", dimension)
                                                 for dimension
                                                 in self.dimensions]
        if self.has_rules:
            body_as_dict['Rules'] = str(self.rules)
        return json.dumps(body_as_dict, ensure_ascii=False)
