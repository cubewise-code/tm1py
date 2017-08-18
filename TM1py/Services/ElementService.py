# -*- coding: utf-8 -*-

import json

from TM1py.Objects.ElementAttribute import ElementAttribute
from TM1py.Services.ObjectService import ObjectService


class ElementService(ObjectService):
    """ Service to handle Object Updates for TM1 Dimension (resp. Hierarchy) Elements
    
    """
    def __init__(self, rest):
        super().__init__(rest)

    def get_element_attributes(self, dimension_name, hierarchy_name):
        """ Get element attributes from hierarchy
    
        :param dimension_name:
        :param hierarchy_name:
        :return:
        """
        request = '/api/v1/Dimensions(\'{}\')/Hierarchies(\'{}\')/ElementAttributes'.format(dimension_name,
                                                                                            hierarchy_name)
        response = self._rest.GET(request, '')
        element_attributes = [ElementAttribute.from_dict(ea) for ea in json.loads(response)['value']]
        return element_attributes

    def get_elements_filtered_by_attribute(self, dimension_name, hierarchy_name, attribute_name, attribute_value):
        """ Get all elements from a hierarchy with given attribute value
    
        :param dimension_name:
        :param hierarchy_name:
        :param attribute_name:
        :param attribute_value:
        :return: List of element names
        """
        attribute_name = attribute_name.replace(" ", "")
        if isinstance(attribute_value, str):
            request = "/api/v1/Dimensions('{}')/Hierarchies('{}')" \
                      "?$expand=Elements($filter = Attributes/{} eq '{}';$select=Name)" \
                .format(dimension_name, hierarchy_name, attribute_name, attribute_value)
        else:
            request = "/api/v1/Dimensions('{}')/Hierarchies('{}')" \
                      "?$expand=Elements($filter = Attributes/{} eq {};$select=Name)" \
                .format(dimension_name, hierarchy_name, attribute_name, attribute_value)
        response = self._rest.GET(request)
        response_as_dict = json.loads(response)
        return [elem['Name'] for elem in response_as_dict['Elements']]

    def create_element_attribute(self, dimension_name, hierarchy_name, element_attribute):
        """ like AttrInsert

        :param dimension_name:
        :param hierarchy_name:
        :param element_attribute: instance of TM1py.ElementAttribute
        :return:
        """
        request = "/api/v1/Dimensions('{}')/Hierarchies('{}')/ElementAttributes" \
            .format(dimension_name, hierarchy_name)
        return self._rest.POST(request, element_attribute.body)

    def delete_element_attribute(self, dimension_name, hierarchy_name, element_attribute):
        """ like AttrDelete

        :param dimension_name:
        :param hierarchy_name:
        :param element_attribute: instance of TM1py.ElementAttribute
        :return:
        """
        request = "/api/v1/Dimensions('}}ElementAttributes_{}')/Hierarchies('}}ElementAttributes_{}')/Elements('{}')" \
            .format(dimension_name, hierarchy_name, element_attribute)
        return self._rest.DELETE(request, '')
