# -*- coding: utf-8 -*-

import collections
import json

from TM1py.Objects.ElementAttribute import ElementAttribute
from TM1py.Objects.Element import Element
from TM1py.Utils.Utils import CaseAndSpaceInsensitiveDict, CaseAndSpaceInsensitiveTuplesDict

from TM1py.Objects.TM1Object import TM1Object


class Hierarchy(TM1Object):
    """ Abstraction of TM1 Hierarchy
        Requires reference to a Dimension

        Elements modeled as a Dictionary where key is the element name and value an instance of TM1py.Element
        {
            'US': instance of TM1py.Element,
            'CN': instance of TM1py.Element,
            'AU': instance of TM1py.Element
        }

        ElementAttributes of type TM1py.Objects.ElementAttribute

        Edges are represented as a TM1py.Utils.CaseAndSpaceInsensitiveTupleDict: 
        {
            (parent1, component1) : 10,
            (parent1, component2) : 30
        }

        Subsets is list of type TM1py.Subset

    """

    def __init__(self, name, dimension_name, elements=None, element_attributes=None,
                 edges=None, subsets=None, structure=None, default_member=None):
        self._name = name
        self._dimension_name = dimension_name
        self._elements = CaseAndSpaceInsensitiveDict()
        if elements:
            for elem in elements:
                self._elements[elem.name] = elem
        self._element_attributes = element_attributes if element_attributes else []
        self._edges = edges if edges else CaseAndSpaceInsensitiveTuplesDict()
        self._subsets = subsets if subsets else []
        # balanced is true, false or None (in versions < TM1 11)
        self._balanced = structure if not structure else structure == 0
        self._default_member = default_member

    @classmethod
    def from_dict(cls, hierarchy_as_dict):
        # Build the Dictionary for the edges
        edges = CaseAndSpaceInsensitiveTuplesDict({(edge['ParentName'], edge['ComponentName']): edge['Weight']
                                                   for edge
                                                   in hierarchy_as_dict['Edges']})
        return cls(name=hierarchy_as_dict['Name'],
                   dimension_name=hierarchy_as_dict['Dimension']['Name'],
                   elements=[Element.from_dict(elem) for elem in hierarchy_as_dict['Elements']],
                   element_attributes=[ElementAttribute(ea['Name'], ea['Type'])
                                       for ea in hierarchy_as_dict['ElementAttributes']],
                   edges=edges,
                   subsets=[subset['Name'] for subset in hierarchy_as_dict['Subsets']],
                   structure=hierarchy_as_dict['Structure'] if 'Structure' in hierarchy_as_dict else None,
                   default_member=hierarchy_as_dict['DefaultMember']['Name']
                   if hierarchy_as_dict['DefaultMember'] else None)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def dimension_name(self):
        return self._dimension_name

    @property
    def elements(self):
        return self._elements

    @property
    def element_attributes(self):
        return self._element_attributes

    @property
    def edges(self):
        return self._edges

    @property
    def subsets(self):
        return self._subsets

    @property
    def balanced(self):
        return self._balanced

    @property
    def default_member(self):
        return self._default_member

    @property
    def body(self):
        return json.dumps(self._construct_body())

    @property
    def body_as_dict(self):
        return self._construct_body()

    def add_element(self, element_name, element_type):
        if element_name in self._elements:
            raise Exception("Elementname has to be unqiue")
        e = Element(name=element_name, element_type=element_type)
        self._elements[element_name] = e

    def update_element(self, element_name, element_type=None):
        self._elements[element_name].element_type = element_type

    def add_edge(self, parent, component, weight):
        self._edges[(parent, component)] = weight

    def update_edge(self, parent, component, weight):
        self._edges[(parent, component)] = weight

    def remove_edge(self, parent, component):
        if (parent, component) in self.edges:
            del self.edges[(parent, component)]

    def add_element_attribute(self, name, attribute_type):
        if name not in self.element_attributes:
            self.element_attributes.append(ElementAttribute(name, attribute_type))

    def remove_element_attribute(self, name):
        if name in self.element_attributes:
            self.element_attributes.remove(name)

    def _construct_body(self, element_attributes=False):
        """ 
        With TM1 10.2.2 Hierarchy and Element Attributes can't be created in one batch
        -> https://www.ibm.com/developerworks/community/forums/html/threadTopic?id=d91f3e0e-d305-44db-ac02-2fdcbee00393
        Thus, no need to have the ElementAttribute included in the JSON

        :param element_attributes: Only include element_attributes in body if explicitly asked for
        :return:
        """

        body_as_dict = collections.OrderedDict()
        body_as_dict['Name'] = self._name
        body_as_dict['Elements'] = []
        body_as_dict['Edges'] = []

        for element in self._elements.values():
            body_as_dict['Elements'].append(element.body_as_dict)
        for edge in self._edges:
            edge_as_dict = collections.OrderedDict()
            edge_as_dict['ParentName'] = edge[0]
            edge_as_dict['ComponentName'] = edge[1]
            edge_as_dict['Weight'] = self._edges[edge]
            body_as_dict['Edges'].append(edge_as_dict)
        if element_attributes:
            body_as_dict['ElementAttributes'] = [element_attribute.body_as_dict
                                                 for element_attribute
                                                 in self._element_attributes]
        return body_as_dict

    def __iter__(self):
        return iter(self._elements.values())

    def __len__(self):
        return len(self._elements.values())
