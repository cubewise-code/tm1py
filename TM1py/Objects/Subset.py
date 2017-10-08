# -*- coding: utf-8 -*-

import json
import collections

from TM1py.Objects.TM1Object import TM1Object


class Subset(TM1Object):
    """ Abstraction of the TM1 Subset (dynamic and static)

        Done and tested. unittests available.
    """
    def __init__(self, subset_name, dimension_name, hierarchy_name=None, alias=None, expression=None, elements=None):
        """

        :param subset_name: String
        :param dimension_name: String
        :param hierarchy_name: String
        :param alias: String, alias that is on in this subset.
        :param expression: String
        :param elements: List, element names
        """
        self._dimension_name = dimension_name
        self._hierarchy_name = hierarchy_name if hierarchy_name else dimension_name
        self._subset_name = subset_name
        self._alias = alias
        self._expression = expression
        self._elements = list(elements) if elements else []

    @property
    def dimension_name(self):
        return self._dimension_name

    @dimension_name.setter
    def dimension_name(self, value):
        self._dimension_name = value

    @property
    def hierarchy_name(self):
        return self._hierarchy_name

    @hierarchy_name.setter
    def hierarchy_name(self, value):
        self._hierarchy_name = value

    @property
    def name(self):
        return self._subset_name

    @property
    def alias(self):
        return self._alias

    @alias.setter
    def alias(self, value):
        self._alias = value

    @property
    def expression(self):
        return self._expression

    @expression.setter
    def expression(self, value):
        self._expression = value

    @property
    def elements(self):
        return self._elements

    @elements.setter
    def elements(self, value):
        self._elements = value

    @property
    def type(self):
        if self.expression:
            return 'dynamic'
        return 'static'

    @classmethod
    def from_json(cls, subset_as_json):
        """ Alternative constructor
                :Parameters:
                    `subset_as_json` : string, JSON
                        representation of Subset as specified in CSDL

                :Returns:
                    `Subset` : an instance of this class
        """

        subset_as_dict = json.loads(subset_as_json)
        return cls.from_dict(subset_as_dict=subset_as_dict)

    @classmethod
    def from_dict(cls, subset_as_dict):
        return cls(dimension_name= subset_as_dict["UniqueName"][1:subset_as_dict["UniqueName"].find('].[')],
                   hierarchy_name=subset_as_dict["Hierarchy"]["Name"],
                   subset_name=subset_as_dict['Name'],
                   alias=subset_as_dict['Alias'],
                   expression=subset_as_dict['Expression'],
                   elements=[element['Name'] for element in subset_as_dict['Elements']]
                   if not subset_as_dict['Expression'] else None)

    @property
    def body(self):
        """ same logic here as in TM1 : when subset has expression its dynamic, otherwise static
        """
        return json.dumps(self.body_as_dict, ensure_ascii=False)

    @property
    def body_as_dict(self):
        """ same logic here as in TM1 : when subset has expression its dynamic, otherwise static
        """
        if self._expression:
            return self._construct_body_dynamic()
        else:
            return self._construct_body_static()

    def add_elements(self, elements):
        """ add Elements to static subsets
            :Parameters:
                `elements` : list of element names
        """
        self._elements = self._elements + elements

    def _construct_body_dynamic(self):
        body_as_dict = collections.OrderedDict()
        body_as_dict['Name'] = self._subset_name
        if self.alias:
            body_as_dict['Alias'] = self._alias
        body_as_dict['Hierarchy@odata.bind'] = 'Dimensions(\'{}\')/Hierarchies(\'{}\')'\
            .format(self._dimension_name, self._hierarchy_name)
        body_as_dict['Expression'] = self._expression
        return body_as_dict

    def _construct_body_static(self):
        body_as_dict = collections.OrderedDict()
        body_as_dict['Name'] = self._subset_name
        if self.alias:
            body_as_dict['Alias'] = self._alias
        body_as_dict['Hierarchy@odata.bind'] = 'Dimensions(\'{}\')/Hierarchies(\'{}\')'\
            .format(self._dimension_name, self.hierarchy_name)
        if self.elements and len(self.elements) > 0:
            body_as_dict['Elements@odata.bind'] = ['Dimensions(\'{}\')/Hierarchies(\'{}\')/Elements(\'{}\')'
                 .format(self.dimension_name, self.hierarchy_name, element) for element in self.elements]
        return body_as_dict


class AnonymousSubset(Subset):
    """ Abstraction of unregistered Subsets used in NativeViews (Check TM1py.ViewAxisSelection)

    """
    def __init__(self, dimension_name, hierarchy_name=None, expression=None, elements=None):
        Subset.__init__(self,
                        dimension_name=dimension_name,
                        hierarchy_name=hierarchy_name if hierarchy_name else dimension_name,
                        subset_name='',
                        alias='',
                        expression=expression,
                        elements=elements)

    @classmethod
    def from_json(cls, subset_as_json):
        """ Alternative constructor
                :Parameters:
                    `subset_as_json` : string, JSON
                        representation of Subset as specified in CSDL

                :Returns:
                    `Subset` : an instance of this class
        """
        subset_as_dict = json.loads(subset_as_json)
        return cls.from_dict(subset_as_dict=subset_as_dict)

    @classmethod
    def from_dict(cls, subset_as_dict):
        """ Alternative constructor
                :Parameters:
                    `subset_as_dict` : dictionary
                        representation of Subset as specified in CSDL

                :Returns:
                    `Subset` : an instance of this class
        """
        return cls(dimension_name=subset_as_dict["Hierarchy"]["Dimension"]["Name"],
                   hierarchy_name=subset_as_dict["Hierarchy"]["Name"],
                   expression=subset_as_dict['Expression'],
                   elements=[element['Name'] for element in subset_as_dict['Elements']]
                   if not subset_as_dict['Expression'] else None)

    def _construct_body_dynamic(self):
        body_as_dict = collections.OrderedDict()
        body_as_dict['Hierarchy@odata.bind'] = 'Dimensions(\'{}\')/Hierarchies(\'{}\')'\
            .format(self._dimension_name, self.hierarchy_name)
        body_as_dict['Expression'] = self._expression
        return body_as_dict

    def _construct_body_static(self):
        body_as_dict = collections.OrderedDict()
        body_as_dict['Hierarchy@odata.bind'] = 'Dimensions(\'{}\')/Hierarchies(\'{}\')'\
            .format(self._dimension_name, self.hierarchy_name)
        body_as_dict['Elements@odata.bind'] = ['Dimensions(\'{}\')/Hierarchies(\'{}\')/Elements(\'{}\')'
                                                   .format(self.dimension_name, self.hierarchy_name, element)
                                               for element
                                               in self.elements]
        return body_as_dict
