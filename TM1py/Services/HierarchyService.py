# -*- coding: utf-8 -*-
import json

from TM1py.Objects import Hierarchy
from TM1py.Services.ElementService import ElementService
from TM1py.Services.ObjectService import ObjectService
from TM1py.Services.SubsetService import SubsetService
from TM1py.Utils.Utils import case_and_space_insensitive_equals


class HierarchyService(ObjectService):
    """ Service to handle Object Updates for TM1 Hierarchies
    
    """

    # Tuple with TM1 Versions where Edges need to be created through TI, due to bug:
    # https://www.ibm.com/developerworks/community/forums/html/topic?id=75f2b99e-6961-4c71-9364-1d5e1e083eff
    EDGES_WORKAROUND_VERSIONS = ('11.0.002', '11.0.003', '11.1.000')

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
        request = "/api/v1/Dimensions('{}')/Hierarchies('{}')?$expand=" \
                  "Edges,Elements,ElementAttributes,Subsets,DefaultMember" \
            .format(dimension_name, hierarchy_name)
        response = self._rest.GET(request, '')
        return Hierarchy.from_dict(response.json())

    def get_all_names(self, dimension_name):
        """ get all names of existing Hierarchies in a dimension

        :param dimension_name:
        :return:
        """
        request = "/api/v1/Dimensions('{}')/Hierarchies?$select=Name".format(dimension_name)
        response = self._rest.GET(request, '')
        return [hierarchy["Name"] for hierarchy in response.json()["value"]]

    def update(self, hierarchy):
        """ update a hierarchy. It's a two step process: 
        1. Update Hierarchy
        2. Update Element-Attributes

        Function caters for Bug with Edge Creation:
        https://www.ibm.com/developerworks/community/forums/html/topic?id=75f2b99e-6961-4c71-9364-1d5e1e083eff

        :param hierarchy: instance of TM1py.Hierarchy
        :return: list of responses
        """
        # functions returns multiple responses
        responses = list()
        # 1. Update Hierarchy
        request = '/api/v1/Dimensions(\'{}\')/Hierarchies(\'{}\')'.format(hierarchy.dimension_name, hierarchy.name)
        # Workaround EDGES: Handle Issue, that Edges cant be created in one batch with the Hierarchy in certain versions
        hierarchy_body = hierarchy.body_as_dict
        if self.version[0:8] in self.EDGES_WORKAROUND_VERSIONS:
            del hierarchy_body["Edges"]
        responses.append(self._rest.PATCH(request, json.dumps(hierarchy_body)))

        # 2. Update Attributes
        responses.append(self._update_element_attributes(hierarchy=hierarchy))

        # Workaround EDGES
        if self.version[0:8] in self.EDGES_WORKAROUND_VERSIONS:
            from TM1py.Services import ProcessService
            process_service = ProcessService(self._rest)
            ti_function = "HierarchyElementComponentAdd('{}', '{}', '{}', '{}', {});"
            ti_statements = [ti_function.format(hierarchy.dimension_name, hierarchy.name,
                                                edge[0],
                                                edge[1],
                                                hierarchy.edges[(edge[0], edge[1])])
                             for edge
                             in hierarchy.edges]
            responses.append(process_service.execute_ti_code(lines_prolog=ti_statements))

        return responses

    def exists(self, dimension_name, hierarchy_name):
        """

        :param dimension_name: 
        :param hierarchy_name: 
        :return: 
        """
        request = '/api/v1/Dimensions(\'{}\')/Hierarchies(\'{}\')'.format(dimension_name, hierarchy_name)
        return self._exists(request)

    def delete(self, dimension_name, hierarchy_name):
        request = '/api/v1/Dimensions(\'{}\')/Hierarchies(\'{}\')'.format(dimension_name, hierarchy_name)
        return self._rest.DELETE(request)

    def get_hierarchy_summary(self, dimension_name, hierarchy_name):
        hierarchy_properties = ("Elements", "Edges", "ElementAttributes", "Members", "Levels")
        request = "/api/v1/Dimensions(\'{}\')/Hierarchies(\'{}\')?$expand=Edges/$count,Elements/$count," \
                  "ElementAttributes/$count,Members/$count,Levels/$count&$select=Cardinality" \
            .format(dimension_name, hierarchy_name)
        hierary_summary_raw = self._rest.GET(request).json()

        return {hierarchy_property: hierary_summary_raw[hierarchy_property + "@odata.count"]
                for hierarchy_property
                in hierarchy_properties}

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

    def get_default_member(self, dimension_name, hierarchy_name=None):
        """ Get the defined default_member for a Hierarchy.
        Will return the element with index 1, if default member is not specified explicitly in }HierarchyProperty Cube

        :param dimension_name:
        :param hierarchy_name:
        :return: String, name of Member
        """
        request = "/api/v1/Dimensions('{dimension}')/Hierarchies('{hierarchy}')/DefaultMember/Name/$value".format(
            dimension=dimension_name,
            hierarchy=hierarchy_name if hierarchy_name else dimension_name)
        response = self._rest.GET(request=request)
        return response.text

    def update_default_member(self, dimension_name, hierarchy_name=None, member_name=""):
        """ Update the default member of a hierarchy.
        Currently implemented through TI, since TM1 API does not supports default member updates yet.

        :param dimension_name:
        :param hierarchy_name:
        :param member_name:
        :return:
        """
        from TM1py import ProcessService, CellService
        if hierarchy_name and not case_and_space_insensitive_equals(dimension_name, hierarchy_name):
            dimension = "{}:{}".format(dimension_name, hierarchy_name)
        else:
            dimension = dimension_name
        cells = {(dimension, 'hierarchy0', 'defaultMember'): member_name}

        CellService(self._rest).write_values(
            cube_name="}HierarchyProperties",
            cellset_as_dict=cells,
            dimensions=('}Dimensions', '}Hierarchies', '}HierarchyProperties'))

        return ProcessService(self._rest).execute_ti_code(
            lines_prolog="RefreshMdxHierarchy('{}');".format(dimension_name))

    def remove_all_edges(self, dimension_name, hierarchy_name=None):
        if not hierarchy_name:
            hierarchy_name = dimension_name
        request = "/api/v1/Dimensions('{}')/Hierarchies('{}')".format(dimension_name, hierarchy_name)
        body = {
            "Edges": []
        }
        return self._rest.PATCH(request=request, data=json.dumps(body))
