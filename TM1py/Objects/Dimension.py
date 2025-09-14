# -*- coding: utf-8 -*-

import collections
import json
from typing import Dict, Iterable, List, Optional

from TM1py.Objects.Hierarchy import Hierarchy
from TM1py.Objects.TM1Object import TM1Object
from TM1py.Utils.Utils import case_and_space_insensitive_equals


class Dimension(TM1Object):
    """Abstraction of TM1 Dimension

    A Dimension is a container for hierarchies.
    """

    def __init__(self, name: str, hierarchies: Optional[Iterable[Hierarchy]] = None):
        """Abstraction of TM1 Dimension


        :param name: Name of the dimension
        :param hierarchies: List of TM1py.Objects.Hierarchy instances
        """
        self._name = name
        self._hierarchies = list(hierarchies) if hierarchies else []
        self._attributes = {"Caption": name}

    @classmethod
    def from_json(cls, dimension_as_json: str) -> "Dimension":
        dimension_as_dict = json.loads(dimension_as_json)
        return cls.from_dict(dimension_as_dict)

    @classmethod
    def from_dict(cls, dimension_as_dict: Dict) -> "Dimension":
        return cls(
            name=dimension_as_dict["Name"],
            hierarchies=[
                Hierarchy.from_dict(hierarchy, dimension_name=dimension_as_dict["Name"])
                for hierarchy in dimension_as_dict["Hierarchies"]
            ],
        )

    @property
    def name(self) -> str:
        return self._name

    @property
    def unique_name(self) -> str:
        return "[" + self._name + "]"

    @property
    def hierarchies(self) -> List[Hierarchy]:
        return self._hierarchies

    @property
    def hierarchy_names(self) -> List[str]:
        return [hierarchy.name for hierarchy in self._hierarchies]

    @property
    def default_hierarchy(self) -> Hierarchy:
        return self._hierarchies[0]

    @name.setter
    def name(self, value: str):
        for hierarchy in self.hierarchies:
            hierarchy._dimension_name = value
            if hierarchy.name == self._name:
                hierarchy.name = value
        self._name = value

    @property
    def body(self) -> str:
        return json.dumps(self._construct_body())

    @property
    def body_as_dict(self) -> Dict:
        return self._construct_body()

    def __iter__(self):
        return iter(self._hierarchies)

    def __len__(self):
        return len(self.hierarchies)

    def __contains__(self, item):
        return self.contains_hierarchy(item)

    def __getitem__(self, item):
        return self.get_hierarchy(item)

    def contains_hierarchy(self, hierarchy_name: str) -> bool:
        for hierarchy in self._hierarchies:
            if case_and_space_insensitive_equals(hierarchy.name, hierarchy_name):
                return True
        return False

    def get_hierarchy(self, hierarchy_name: str) -> Hierarchy:
        for hierarchy in self._hierarchies:
            if case_and_space_insensitive_equals(hierarchy.name, hierarchy_name):
                return hierarchy
        raise ValueError("Hierarchy: {} not found in dimension: {}".format(hierarchy_name, self.name))

    def add_hierarchy(self, hierarchy: Hierarchy):
        if self.contains_hierarchy(hierarchy.name):
            raise ValueError("Hierarchy: {} already exists in dimension: {}".format(hierarchy.name, self.name))
        self._hierarchies.append(hierarchy)

    def remove_hierarchy(self, hierarchy_name: str):
        if case_and_space_insensitive_equals(hierarchy_name, "leaves"):
            raise ValueError("'Leaves' hierarchy must not be removed from dimension")

        for num, hierarchy in enumerate(self._hierarchies):
            if case_and_space_insensitive_equals(hierarchy.name, hierarchy_name):
                del self._hierarchies[num]
                return

    def _construct_body(self, include_leaves_hierarchy=False) -> Dict:
        body_as_dict = collections.OrderedDict()
        body_as_dict["Name"] = self._name
        body_as_dict["UniqueName"] = self.unique_name
        body_as_dict["Attributes"] = self._attributes
        body_as_dict["Hierarchies"] = [
            hierarchy.body_as_dict
            for hierarchy in self.hierarchies
            if not case_and_space_insensitive_equals(hierarchy.name, "Leaves") or include_leaves_hierarchy
        ]
        return body_as_dict
