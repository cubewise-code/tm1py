# -*- coding: utf-8 -*-

import collections
import json
from typing import List, Dict, Optional, Iterable

from TM1py.Objects.TM1Object import TM1Object
from TM1py.Utils import format_url


class Subset(TM1Object):
    """ Abstraction of the TM1 Subset (dynamic and static)

    """

    def __init__(self, subset_name: str, dimension_name: str, hierarchy_name: str = None, alias: str = None,
                 expression: str = None, elements: Iterable[str] = None):
        """

        :param subset_name: String
        :param dimension_name: String
        :param hierarchy_name: String
        :param alias: String, alias that is active in this subset.
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
    def dimension_name(self) -> str:
        return self._dimension_name

    @dimension_name.setter
    def dimension_name(self, value: str):
        self._dimension_name = value

    @property
    def hierarchy_name(self) -> str:
        return self._hierarchy_name

    @hierarchy_name.setter
    def hierarchy_name(self, value: str):
        self._hierarchy_name = value

    @property
    def name(self) -> str:
        return self._subset_name

    @property
    def alias(self) -> str:
        return self._alias

    @alias.setter
    def alias(self, value: str):
        self._alias = value

    @property
    def expression(self) -> str:
        return self._expression

    @expression.setter
    def expression(self, value: str):
        self._expression = value

    @property
    def elements(self) -> List[str]:
        return self._elements

    @elements.setter
    def elements(self, value: List[str]):
        self._elements = value

    @property
    def type(self) -> str:
        if self.expression:
            return 'dynamic'
        return 'static'

    @property
    def is_dynamic(self) -> bool:
        return bool(self.expression)

    @property
    def is_static(self) -> bool:
        return not self.is_dynamic

    @classmethod
    def from_json(cls, subset_as_json: str) -> 'Subset':
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
    def from_dict(cls, subset_as_dict: Dict) -> 'Subset':
        return cls(dimension_name=subset_as_dict["UniqueName"][1:subset_as_dict["UniqueName"].find('].[')],
                   hierarchy_name=subset_as_dict.get("Hierarchy", {}).get("Name"),
                   subset_name=subset_as_dict['Name'],
                   alias=subset_as_dict.get('Alias'),
                   expression=subset_as_dict.get('Expression'),
                   elements=[element['Name'] for element in subset_as_dict.get('Elements', [])]
                   if not subset_as_dict.get('Expression') else None)

    @property
    def body(self) -> str:
        """ same logic here as in TM1 : when subset has expression its dynamic, otherwise static
        """
        return json.dumps(self.body_as_dict, ensure_ascii=False)

    @property
    def body_as_dict(self) -> Dict:
        """ same logic here as in TM1 : when subset has expression its dynamic, otherwise static
        """
        if self._expression:
            return self._construct_body_dynamic()
        else:
            return self._construct_body_static()

    def add_elements(self, elements: Iterable[str]):
        """ add Elements to static subsets
            :Parameters:
                `elements` : list of element names
        """
        self._elements = self._elements + list(elements)

    def _construct_body_dynamic(self) -> Dict:
        body_as_dict = collections.OrderedDict()
        body_as_dict['Name'] = self._subset_name
        if self.alias:
            body_as_dict['Alias'] = self._alias
        body_as_dict['Hierarchy@odata.bind'] = format_url(
            "Dimensions('{}')/Hierarchies('{}')",
            self._dimension_name,
            self._hierarchy_name)
        body_as_dict['Expression'] = self._expression
        return body_as_dict

    def _construct_body_static(self) -> Dict:
        body_as_dict = collections.OrderedDict()
        body_as_dict['Name'] = self._subset_name
        if self.alias:
            body_as_dict['Alias'] = self._alias
        body_as_dict['Hierarchy@odata.bind'] = format_url(
            "Dimensions('{}')/Hierarchies('{}')",
            self._dimension_name,
            self.hierarchy_name)
        if self.elements and len(self.elements) > 0:
            body_as_dict['Elements@odata.bind'] = [
                format_url("Dimensions('{}')/Hierarchies('{}')/Elements('{}')",
                           self.dimension_name, self.hierarchy_name, element)
                for element
                in self.elements]
        return body_as_dict


class AnonymousSubset(Subset):
    """ Abstraction of unregistered Subsets used in NativeViews (Check TM1py.ViewAxisSelection)

    """

    def __init__(self, dimension_name: str, hierarchy_name: Optional[str] = None, alias: str = '',
                 expression: Optional[str] = None, elements: Optional[Iterable[str]] = None):
        Subset.__init__(self,
                        dimension_name=dimension_name,
                        hierarchy_name=hierarchy_name if hierarchy_name else dimension_name,
                        subset_name='',
                        alias=alias,
                        expression=expression,
                        elements=elements)

    @classmethod
    def from_json(cls, subset_as_json: str) -> 'Subset':
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
    def from_dict(cls, subset_as_dict: Dict) -> 'Subset':
        """Alternative constructor
        
        :param subset_as_dict: dictionary, representation of Subset as specified in CSDL
        :return: an instance of this class
        """
        return cls(dimension_name=subset_as_dict["Hierarchy"]["Dimension"]["Name"],
                   hierarchy_name=subset_as_dict["Hierarchy"]["Name"],
                   expression=subset_as_dict['Expression'],
                   alias=subset_as_dict['Alias'],
                   elements=[element['Name'] for element in subset_as_dict['Elements']]
                   if not subset_as_dict['Expression'] else None)

    def _construct_body_dynamic(self) -> Dict:
        body_as_dict = collections.OrderedDict()
        body_as_dict['Hierarchy@odata.bind'] = format_url(
            "Dimensions('{}')/Hierarchies('{}')",
            self._dimension_name,
            self.hierarchy_name)
        if self.alias:
            body_as_dict['Alias'] = self._alias
        body_as_dict['Expression'] = self._expression
        return body_as_dict

    def _construct_body_static(self) -> Dict:
        body_as_dict = collections.OrderedDict()
        body_as_dict['Hierarchy@odata.bind'] = format_url(
            "Dimensions('{}')/Hierarchies('{}')",
            self._dimension_name,
            self.hierarchy_name)
        if self.alias:
            body_as_dict['Alias'] = self._alias
        body_as_dict['Elements@odata.bind'] = [
            format_url(
                "Dimensions('{}')/Hierarchies('{}')/Elements('{}')",
                self.dimension_name,
                self.hierarchy_name,
                element)
            for element in self.elements]
        return body_as_dict
