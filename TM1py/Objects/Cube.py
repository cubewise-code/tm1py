# -*- coding: utf-8 -*-

import collections
import json
from typing import Dict, Iterable, List, Optional, Union

from TM1py.Objects.Rules import Rules
from TM1py.Objects.TM1Object import TM1Object
from TM1py.Utils import format_url


class Cube(TM1Object):
    """Abstraction of a TM1 Cube"""

    def __init__(self, name: str, dimensions: Iterable[str], rules: Optional[Union[str, Rules]] = None):
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
        return self._name

    @property
    def dimensions(self) -> List[str]:
        return self._dimensions

    @dimensions.setter
    def dimensions(self, value: List[str]):
        self._dimensions = value

    @property
    def has_rules(self) -> bool:
        if self._rules:
            return True
        return False

    @property
    def rules(self) -> Rules:
        return self._rules

    @rules.setter
    def rules(self, value: Union[str, Rules]):
        if value is None:
            self._rules = None
        elif isinstance(value, str):
            self._rules = Rules(rules=value)
        elif isinstance(value, Rules):
            self._rules = value
        else:
            raise ValueError("value must None or of type str or Rules")

    @property
    def skipcheck(self) -> bool:
        if self.has_rules:
            return self.rules.skipcheck
        return False

    @property
    def undefvals(self) -> bool:
        if self.has_rules:
            return self.rules.undefvals
        return False

    @property
    def feedstrings(self) -> bool:
        if self.has_rules:
            return self.rules.feedstrings
        return False

    @classmethod
    def from_json(cls, cube_as_json: str) -> "Cube":
        """Alternative constructor

        :param cube_as_json: user as JSON string
        :return: cube, an instance of this class
        """
        cube_as_dict = json.loads(cube_as_json)
        return cls.from_dict(cube_as_dict)

    @classmethod
    def from_dict(cls, cube_as_dict: Dict) -> "Cube":
        """Alternative constructor

        :param cube_as_dict: user as dict
        :return: user, an instance of this class
        """
        return cls(
            name=cube_as_dict["Name"],
            dimensions=[dimension["Name"] for dimension in cube_as_dict["Dimensions"]],
            rules=Rules(cube_as_dict["Rules"]) if cube_as_dict["Rules"] else None,
        )

    @property
    def body(self) -> str:
        return self._construct_body()

    def _construct_body(self) -> str:
        """
        construct body (json) from the class attributes
        :return: String, TM1 JSON representation of a cube
        """
        body_as_dict = collections.OrderedDict()
        body_as_dict["Name"] = self.name
        body_as_dict["Dimensions@odata.bind"] = [
            format_url("Dimensions('{}')", dimension) for dimension in self.dimensions
        ]
        if self.has_rules:
            body_as_dict["Rules"] = str(self.rules)
        return json.dumps(body_as_dict, ensure_ascii=False)
