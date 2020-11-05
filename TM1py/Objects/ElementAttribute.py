# -*- coding: utf-8 -*-

import json
from enum import Enum
from typing import Dict, Union

from TM1py.Objects.TM1Object import TM1Object
from TM1py.Utils import case_and_space_insensitive_equals


class ElementAttribute(TM1Object):
    """ Abstraction of TM1 Element Attributes
    
    """

    class Types(Enum):
        NUMERIC = 1
        STRING = 2
        ALIAS = 3

        def __str__(self):
            """
            Return a string representation of this object.

            Args:
                self: (todo): write your description
            """
            return self.name.capitalize()

        @classmethod
        def _missing_(cls, value: str):
            """
            Returns true if any missing value.

            Args:
                cls: (todo): write your description
                value: (str): write your description
            """
            for member in cls:
                if member.name.lower() == value.replace(" ", "").lower():
                    return member
            # default
            raise ValueError(f"Invalid attribute type: '{value}'")

    def __init__(self, name: str, attribute_type: Union[Types, str]):
        """
        Initialize an attribute.

        Args:
            self: (todo): write your description
            name: (str): write your description
            attribute_type: (dict): write your description
        """
        self.name = name
        self.attribute_type = attribute_type

    @property
    def name(self) -> str:
        """
        Returns the name of this node.

        Args:
            self: (todo): write your description
        """
        return self._name

    @name.setter
    def name(self, value: str):
        """
        Set the name of the message

        Args:
            self: (todo): write your description
            value: (str): write your description
        """
        self._name = value

    @property
    def attribute_type(self) -> str:
        """
        Returns the type of the attribute.

        Args:
            self: (todo): write your description
        """
        return str(self._attribute_type)

    @attribute_type.setter
    def attribute_type(self, value: Union[Types, str]):
        """
        Set the attribute of the given attribute.

        Args:
            self: (todo): write your description
            value: (todo): write your description
        """
        self._attribute_type = ElementAttribute.Types(value)

    @property
    def body_as_dict(self) -> Dict:
        """
        Return the body as a dict.

        Args:
            self: (todo): write your description
        """
        return {"Name": self._name, "Type": self.attribute_type}

    @property
    def body(self) -> str:
        """
        Return the body as a dictionary.

        Args:
            self: (todo): write your description
        """
        return json.dumps(self.body_as_dict, ensure_ascii=False)

    @classmethod
    def from_json(cls, element_attribute_as_json: str) -> 'ElementAttribute':
        """
        Create an element from a json string.

        Args:
            cls: (todo): write your description
            element_attribute_as_json: (todo): write your description
        """
        return cls.from_dict(json.loads(element_attribute_as_json))

    @classmethod
    def from_dict(cls, element_attribute_as_dict: Dict) -> 'ElementAttribute':
        """
        Create an element from a dictionary.

        Args:
            cls: (todo): write your description
            element_attribute_as_dict: (dict): write your description
        """
        return cls(name=element_attribute_as_dict['Name'],
                   attribute_type=element_attribute_as_dict['Type'])

    def __eq__(self, other: Union[str, 'ElementAttribute']):
        """
        Compares two strings.

        Args:
            self: (todo): write your description
            other: (todo): write your description
        """
        if isinstance(other, str):
            return case_and_space_insensitive_equals(self.name, other)
        elif isinstance(other, ElementAttribute):
            return case_and_space_insensitive_equals(self.name, other.name)
        else:
            raise ValueError("Argument: 'other' must be of type str or ElementAttribute")
