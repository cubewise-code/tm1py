# -*- coding: utf-8 -*-

import json
from typing import Dict, Union

from TM1py.Objects.TM1Object import TM1Object
from TM1py.Utils import case_and_space_insensitive_equals


class ElementAttribute(TM1Object):
    """ Abstraction of TM1 Element Attributes
    
    """
    valid_types = ['NUMERIC', 'STRING', 'ALIAS']

    def __init__(self, name: str, attribute_type: str):
        self.name = name
        self.attribute_type = attribute_type

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str):
        self._name = value

    @property
    def attribute_type(self) -> str:
        return self._attribute_type

    @attribute_type.setter
    def attribute_type(self, value: str):
        if not value.upper() in ElementAttribute.valid_types:
            raise ValueError("'{}' is not a valid Attribute Type".format(value))

        self._attribute_type = value.capitalize()

    @property
    def body_as_dict(self) -> Dict:
        return {"Name": self._name, "Type": self._attribute_type}

    @property
    def body(self) -> str:
        return json.dumps(self.body_as_dict, ensure_ascii=False)

    @classmethod
    def from_json(cls, element_attribute_as_json: str) -> 'ElementAttribute':
        return cls.from_dict(json.loads(element_attribute_as_json))

    @classmethod
    def from_dict(cls, element_attribute_as_dict: Dict) -> 'ElementAttribute':
        return cls(name=element_attribute_as_dict['Name'],
                   attribute_type=element_attribute_as_dict['Type'])

    def __eq__(self, other: Union[str, 'ElementAttribute']):
        if isinstance(other, str):
            return case_and_space_insensitive_equals(self.name, other)
        elif isinstance(other, ElementAttribute):
            return case_and_space_insensitive_equals(self.name, other.name)
        else:
            raise ValueError("Argument: 'other' must be of type str or ElementAttribute")
