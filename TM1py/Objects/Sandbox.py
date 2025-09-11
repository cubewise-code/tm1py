# -*- coding: utf-8 -*-

import collections
import json
from typing import Dict

from TM1py.Objects.TM1Object import TM1Object


class Sandbox(TM1Object):
    """Abstraction of a TM1 Sandbox"""

    def __init__(
        self,
        name: str,
        include_in_sandbox_dimension: bool = True,
        loaded: bool = False,
        active: bool = False,
        queued: bool = False,
    ):
        """

        :param name: name of the Sandbox
        :param include_in_sandbox_dimension:
        :params loaded, active, queued: leave default as false when creating sanbox
        """
        self.name = name
        self.include_in_sandbox_dimension = include_in_sandbox_dimension
        self.loaded = loaded
        self.active = active
        self.queued = queued

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str):
        self._name = value

    @property
    def include_in_sandbox_dimension(self) -> bool:
        return self._include_in_sandbox_dimension

    @include_in_sandbox_dimension.setter
    def include_in_sandbox_dimension(self, value: bool):
        self._include_in_sandbox_dimension = value

    @classmethod
    def from_json(cls, sandbox_as_json: str) -> "Sandbox":
        """Alternative constructor

        :param sandbox_as_json: user as JSON string
        :return: sandbox, an instance of this class
        """
        sandbox_as_dict = json.loads(sandbox_as_json)
        return cls.from_dict(sandbox_as_dict)

    @classmethod
    def from_dict(cls, sandbox_as_dict: Dict) -> "Sandbox":
        """Alternative constructor

        :param sandbox_as_dict: user as dict
        :return: an instance of this class
        """
        return cls(
            name=sandbox_as_dict["Name"],
            include_in_sandbox_dimension=sandbox_as_dict["IncludeInSandboxDimension"],
            loaded=sandbox_as_dict["IsLoaded"],
            active=sandbox_as_dict["IsActive"],
            queued=sandbox_as_dict["IsQueued"],
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
