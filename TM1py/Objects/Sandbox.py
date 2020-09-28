# -*- coding: utf-8 -*-

import collections
import json
from typing import Dict
from TM1py.Objects.TM1Object import TM1Object
from TM1py.Utils import format_url


class Sandbox(TM1Object):
    """ Abstraction of a TM1 Sandbox
        
    """

    def __init__(self, name: str, include_in_sandbox_dimension: bool = True):
        """
        
        :param name: name of the Sandbox
        :param include_in_sandbox_dimension: 
        """
        self._name = name
        self._include_in_sandbox_dimension = include_in_sandbox_dimension

    @property
    def name(self) -> str:
        return self._name

    @classmethod
    def from_json(cls, sandbox_as_json: str) -> "Sandbox":
        """ Alternative constructor

        :param sandbox_as_json: user as JSON string
        :return: sandbox, an instance of this class
        """
        sandbox_as_dict = json.loads(sandbox_as_json)
        return cls.from_dict(sandbox_as_dict)

    @classmethod
    def from_dict(cls, sandbox_as_dict: Dict) -> "Sandbox":
        """ Alternative constructor

        :param sandbox_as_dict: user as dict
        :return: an instance of this class
        """
        return cls(
            name=sandbox_as_dict["Name"],
            include_in_sandbox_dimension=sandbox_as_dict["IncludeInSandboxDimension"],
        )

    @property
    def body(self) -> str:
        return self._construct_body()

    def _construct_body(self) -> str:
        """
        construct body (json) from the class attributes
        :return: String, TM1 JSON representation of a sandbox
        """
        body_as_dict = collections.OrderedDict()
        body_as_dict["Name"] = self.name
        body_as_dict["IncludeInSandboxDimension"] = self._include_in_sandbox_dimension
        return json.dumps(body_as_dict, ensure_ascii=False)
