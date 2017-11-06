# -*- coding: utf-8 -*-

from TM1py.Services.ElementService import ElementService
from TM1py.Services.ObjectService import ObjectService
from TM1py.Services.SubsetService import SubsetService


class HierarchyService(ObjectService):
    """ Service to handle Object Updates for TM1 Hierarchies
    
    """
    def __init__(self, rest):
        super().__init__(rest)
        self.subsets = SubsetService(rest)
        self.elements = ElementService(rest)

    def create(self, hierarchy):
        """ Create a hierarchy in an existing dimension

        :param hierarchy:
        :return:
        """
        request = '/api/v1/Dimensions(\'{}\')/Hierarchies'.format(hierarchy.dimension_name)
        response = self._rest.POST(request, hierarchy.body)
        return response

    def get(self, dimension_name, hierarchy_name):
        """ get hierarchy

        :param dimension_name: name of the dimension
        :param hierarchy_name: name of the hierarchy
        :return:
        """
        request = '/api/v1/Dimensions(\'{}\')/Hierarchies(\'{}\')'.format(dimension_name, hierarchy_name)
        response = self._rest.GET(request, '')
        return response

    def update(self, hierarchy):
        """ update a hierarchy. Is a two step process.
        1. Update Hierarchy
        2. Update Element-Attributes

        :param hierarchy: instance of TM1py.Hierarchy
        :return:
        """
        # Update Hierarchy
        request = '/api/v1/Dimensions(\'{}\')/Hierarchies(\'{}\')'.format(hierarchy.dimension_name, hierarchy.name)
        response = self._rest.PATCH(request, hierarchy.body)
        # Update Attributes
        self._update_element_attributes(hierarchy=hierarchy)
        return response

    def exists(self, dimension_name, hierarchy_name):
        """

        :param dimension_name: 
        :param hierarchy_name: 
        :return: 
        """
        request = '/api/v1/Dimensions(\'{}\')/Hierarchies(\'{}\')'.format(dimension_name, hierarchy_name)
        return super(HierarchyService, self).exists(request)

    def delete(self, dimension_name, hierarchy_name):
        request = '/api/v1/Dimensions(\'{}\')/Hierarchies(\'{}\')'.format(dimension_name, hierarchy_name)
        return self._rest.DELETE(request)

    def _update_element_attributes(self, hierarchy):
        """ Update the elementattributes of a hierarchy

        :param hierarchy: Instance of TM1py.Hierarchy
        :return:
        """
        # get existing attributes first.
        element_attributes = self.elements.get_element_attributes(dimension_name=hierarchy.dimension_name,
                                                                  hierarchy_name=hierarchy.name)
        element_attribute_names = [ea.name
                                   for ea
                                   in element_attributes]
        # write ElementAttributes that don't already exist !
        for element_attribute in hierarchy.element_attributes:
            if element_attribute not in element_attribute_names:
                self.elements.create_element_attribute(dimension_name=hierarchy.dimension_name,
                                                       hierarchy_name=hierarchy.name,
                                                       element_attribute=element_attribute)
        # delete attributes that are determined to be removed
        for element_attribute in element_attribute_names:
            if element_attribute not in hierarchy.element_attributes:
                self.elements.delete_element_attribute(dimension_name=hierarchy.dimension_name,
                                                       hierarchy_name=hierarchy.name,
                                                       element_attribute=element_attribute)
