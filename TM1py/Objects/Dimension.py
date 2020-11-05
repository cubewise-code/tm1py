# -*- coding: utf-8 -*-

import collections
import json
from typing import Optional, Iterable, Dict, List

from TM1py.Objects.Hierarchy import Hierarchy
from TM1py.Objects.TM1Object import TM1Object
from TM1py.Utils.Utils import case_and_space_insensitive_equals


class Dimension(TM1Object):
    """ Abstraction of TM1 Dimension
        
        A Dimension is a container for hierarchies.
    """

    def __init__(self, name: str, hierarchies: Optional[Iterable[Hierarchy]] = None):
        """ Abstraction of TM1 Dimension
        
         
        :param name: Name of the dimension
        :param hierarchies: List of TM1py.Objects.Hierarchy instances
        """
        self._name = name
        self._hierarchies = list(hierarchies) if hierarchies else []
        self._attributes = {'Caption': name}

    @classmethod
    def from_json(cls, dimension_as_json: str) -> 'Dimension':
        """
        Create a : class from a json.

        Args:
            cls: (todo): write your description
            dimension_as_json: (int): write your description
        """
        dimension_as_dict = json.loads(dimension_as_json)
        return cls.from_dict(dimension_as_dict)

    @classmethod
    def from_dict(cls, dimension_as_dict: Dict) -> 'Dimension':
        """
        Create a : class from a dictionary.

        Args:
            cls: (todo): write your description
            dimension_as_dict: (dict): write your description
        """
        return cls(name=dimension_as_dict['Name'],
                   hierarchies=[Hierarchy.from_dict(hierarchy)
                                for hierarchy
                                in dimension_as_dict['Hierarchies']])

    @property
    def name(self) -> str:
        """
        Returns the name of this node.

        Args:
            self: (todo): write your description
        """
        return self._name

    @property
    def unique_name(self) -> str:
        """
        Generate unique name.

        Args:
            self: (todo): write your description
        """
        return '[' + self._name + ']'

    @property
    def hierarchies(self) -> List[Hierarchy]:
        """
        List [ hierarchies.

        Args:
            self: (todo): write your description
        """
        return self._hierarchies

    @property
    def hierarchy_names(self) -> List[str]:
        """
        Returns a list of all hierarchy.

        Args:
            self: (todo): write your description
        """
        return [hierarchy.name for hierarchy in self._hierarchies]

    @property
    def default_hierarchy(self) -> Hierarchy:
        """
        Default hierarchy hierarchy.

        Args:
            self: (todo): write your description
        """
        return self._hierarchies[0]

    @name.setter
    def name(self, value: str):
        """
        Set the name of the dimension.

        Args:
            self: (todo): write your description
            value: (str): write your description
        """
        for hierarchy in self.hierarchies:
            hierarchy._dimension_name = value
            if hierarchy.name == self._name:
                hierarchy.name = value
        self._name = value

    @property
    def body(self) -> str:
        """
        Returns the body of the request.

        Args:
            self: (todo): write your description
        """
        return json.dumps(self._construct_body())

    @property
    def body_as_dict(self) -> Dict:
        """
        Return the body as a dictionary.

        Args:
            self: (todo): write your description
        """
        return self._construct_body()

    def __iter__(self):
        """
        Iterate iterator over all iterables.

        Args:
            self: (todo): write your description
        """
        return iter(self._hierarchies)

    def __len__(self):
        """
        Returns the length of the tree.

        Args:
            self: (todo): write your description
        """
        return len(self.hierarchies)

    def __contains__(self, item):
        """
        Return true if item is contained item.

        Args:
            self: (todo): write your description
            item: (str): write your description
        """
        return self.contains_hierarchy(item)

    def __getitem__(self, item):
        """
        Returns the item associated with the given item.

        Args:
            self: (todo): write your description
            item: (str): write your description
        """
        return self.get_hierarchy(item)

    def contains_hierarchy(self, hierarchy_name: str) -> bool:
        """
        Returns true if the given hierarchy contains a hierarchy hierarchy.

        Args:
            self: (todo): write your description
            hierarchy_name: (str): write your description
        """
        for hierarchy in self._hierarchies:
            if case_and_space_insensitive_equals(hierarchy.name, hierarchy_name):
                return True
        return False

    def get_hierarchy(self, hierarchy_name: str) -> Hierarchy:
        """
        Return hierarchy hierarchy with given hierarchy.

        Args:
            self: (todo): write your description
            hierarchy_name: (str): write your description
        """
        for hierarchy in self._hierarchies:
            if case_and_space_insensitive_equals(hierarchy.name, hierarchy_name):
                return hierarchy
        raise ValueError("Hierarchy: {} not found in dimension: {}".format(hierarchy_name, self.name))

    def add_hierarchy(self, hierarchy: Hierarchy):
        """
        Add hierarchy.

        Args:
            self: (todo): write your description
            hierarchy: (todo): write your description
        """
        if self.contains_hierarchy(hierarchy.name):
            raise ValueError("Hierarchy: {} already exists in dimension: {}".format(hierarchy.name, self.name))
        self._hierarchies.append(hierarchy)

    def remove_hierarchy(self, hierarchy_name: str):
        """
        Remove hierarchy from the hierarchy.

        Args:
            self: (todo): write your description
            hierarchy_name: (str): write your description
        """
        if case_and_space_insensitive_equals(hierarchy_name, "leaves"):
            raise ValueError("'Leaves' hierarchy must not be removed from dimension")

        for num, hierarchy in enumerate(self._hierarchies):
            if case_and_space_insensitive_equals(hierarchy.name, hierarchy_name):
                del self._hierarchies[num]
                return

    def _construct_body(self, include_leaves_hierarchy=False) -> Dict:
        """
        Construct the body body. body.

        Args:
            self: (todo): write your description
            include_leaves_hierarchy: (bool): write your description
        """
        body_as_dict = collections.OrderedDict()
        body_as_dict["Name"] = self._name
        body_as_dict["UniqueName"] = self.unique_name
        body_as_dict["Attributes"] = self._attributes
        body_as_dict["Hierarchies"] = [
            hierarchy.body_as_dict
            for hierarchy
            in self.hierarchies if
            not case_and_space_insensitive_equals(hierarchy.name, "Leaves") or include_leaves_hierarchy]
        return body_as_dict
