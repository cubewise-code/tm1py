# -*- coding: utf-8 -*-

import collections
import json

from TM1py.Objects.Hierarchy import Hierarchy
from TM1py.Objects.TM1Object import TM1Object


class Dimension(TM1Object):
    """ Abstraction of TM1 Dimension
        
        A Dimension is a container for hierarchies.
    """
    def __init__(self, name, hierarchies=None):
        """ Abstraction of TM1 Dimension
        
         
        :param name: Name of the dimension
        :param hierarchies: List of TM1py.Objects.Hierarchy instances
        """
        self._name = name
        self._hierarchies = list(hierarchies) if hierarchies else []
        self._attributes = {'Caption': name}

    @classmethod
    def from_json(cls, dimension_as_json):
        dimension_as_dict = json.loads(dimension_as_json)
        return cls.from_dict(dimension_as_dict)

    @classmethod
    def from_dict(cls, dimension_as_dict):
        return cls(name=dimension_as_dict['Name'],
                   hierarchies=[Hierarchy.from_dict(hierarchy)
                                for hierarchy
                                in dimension_as_dict['Hierarchies']])

    @property
    def name(self):
        return self._name

    @property
    def unique_name(self):
        return '[' + self._name + ']'

    @property
    def hierarchies(self):
        return self._hierarchies

    @property
    def default_hierarchy(self):
        return self._hierarchies[0]

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def body(self):
        return json.dumps(self._construct_body())

    @property
    def body_as_dict(self):
        return self._construct_body()

    def __iter__(self):
        return iter(self._hierarchies)

    def __len__(self):
        return len(self.hierarchies)

    def add_hierarchy(self, hierarchy):
        self._hierarchies.append(hierarchy)

    def remove_hierarchy(self, name):
        self._hierarchies = list(filter(lambda h: h.name != name, self._hierarchies))

    def _construct_body(self):
        body_as_dict = collections.OrderedDict()
        # self.body_as_dict["@odata.type"] = "ibm.tm1.api.v1.Dimension"
        body_as_dict["Name"] = self._name
        body_as_dict["UniqueName"] = self.unique_name
        body_as_dict["Attributes"] = self._attributes
        body_as_dict["Hierarchies"] = [hierarchy.body_as_dict for hierarchy in self.hierarchies]
        return body_as_dict
