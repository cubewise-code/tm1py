# -*- coding: utf-8 -*-

import json

from TM1py.Objects.TM1Object import TM1Object


class ElementAttribute(TM1Object):
    """ Abstraction of TM1 Element Attributes
    
    """
    valid_types = ['NUMERIC', 'STRING', 'ALIAS']

    def __init__(self, name, attribute_type):
        self.name = name
        self.attribute_type = attribute_type

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def attribute_type(self):
        return self._attribute_type

    @attribute_type.setter
    def attribute_type(self, value):
        if value.upper() in ElementAttribute.valid_types:
            self._attribute_type = value
        else:
            raise Exception('{} not a valid Attribute Type.'.format(value))

    @property
    def body_as_dict(self):
        return {"Name": self._name, "Type": self._attribute_type}

    @property
    def body(self):
        return json.dumps(self.body_as_dict, ensure_ascii=False)

    @classmethod
    def from_json(cls, element_attribute_as_json):
        return cls.from_dict(json.loads(element_attribute_as_json))

    @classmethod
    def from_dict(cls, element_attribute_as_dict):
        return cls(name=element_attribute_as_dict['Name'],
                   attribute_type=element_attribute_as_dict['Type'])

    def __eq__(self, other):
        return self.name == other.name
