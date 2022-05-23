# -*- coding: utf-8 -*-
import json
import warnings
from typing import List

from requests import Response

from TM1py.Exceptions.Exceptions import TM1pyException
from TM1py.Objects.Dimension import Dimension
from TM1py.Services.HierarchyService import HierarchyService
from TM1py.Services.ObjectService import ObjectService
from TM1py.Services.ProcessService import ProcessService
from TM1py.Services.RestService import RestService
from TM1py.Services.SubsetService import SubsetService
from TM1py.Utils.Utils import case_and_space_insensitive_equals, format_url, CaseAndSpaceInsensitiveSet


class DimensionService(ObjectService):
    """ Service to handle Object Updates for TM1 Dimensions
    
    """

    def __init__(self, rest: RestService):
        super().__init__(rest)
        self.hierarchies = HierarchyService(rest)
        self.subsets = SubsetService(rest)

    def create(self, dimension: Dimension, **kwargs) -> Response:
        """ Create a dimension

        :param dimension: instance of TM1py.Dimension
        :return: response
        """
        # If Dimension exists. throw Exception
        if self.exists(dimension.name):
            raise RuntimeError("Dimension '{}' already exists".format(dimension.name))
        # If not all subsequent calls successful -> undo everything that has been done in this function
        try:
            # Create Dimension, Hierarchies, Elements, Edges.
            url = "/api/v1/Dimensions"
            response = self._rest.POST(url, dimension.body, **kwargs)
            # Create ElementAttributes
            for hierarchy in dimension:
                if not case_and_space_insensitive_equals(hierarchy.name, "Leaves"):
                    self.hierarchies.update_element_attributes(hierarchy, **kwargs)
        except TM1pyException as e:
            # undo everything if problem in step 1 or 2
            if self.exists(dimension.name, **kwargs):
                self.delete(dimension.name)
            raise e
        return response

    def get(self, dimension_name: str, **kwargs) -> Dimension:
        """ Get a Dimension

        :param dimension_name:
        :return:
        """
        url = format_url("/api/v1/Dimensions('{}')?$expand=Hierarchies($expand=*)", dimension_name)
        response = self._rest.GET(url, **kwargs)
        return Dimension.from_json(response.text)

    def update(self, dimension: Dimension, **kwargs):
        """ Update an existing dimension

        :param dimension: instance of TM1py.Dimension
        :return: None
        """
        # delete hierarchies that have been removed from the dimension object
        hierarchies_to_be_removed = CaseAndSpaceInsensitiveSet(
            *self.hierarchies.get_all_names(dimension.name, **kwargs))
        for hierarchy in dimension.hierarchy_names:
            hierarchies_to_be_removed.discard(hierarchy)

        # update all Hierarchies except for the implicitly maintained 'Leaves' Hierarchy
        for hierarchy in dimension:
            if not case_and_space_insensitive_equals(hierarchy.name, "Leaves"):
                if self.hierarchies.exists(hierarchy.dimension_name, hierarchy.name, **kwargs):
                    self.hierarchies.update(hierarchy, **kwargs)
                else:
                    self.hierarchies.create(hierarchy, **kwargs)

        # Edge case: elements in leaves hierarchy that do not exist in other hierarchies
        if "Leaves" in dimension:
            existing_leaves = CaseAndSpaceInsensitiveSet(
                self.hierarchies.elements.get_leaf_element_names(dimension.name, "Leaves"))

            leaves_to_create = list()
            for leaf in dimension.get_hierarchy("Leaves"):
                if leaf.name not in existing_leaves:
                    leaves_to_create.append(leaf)

            if leaves_to_create:
                self.hierarchies.elements.add_elements(
                    dimension_name=dimension.name,
                    hierarchy_name="Leaves",
                    elements=leaves_to_create)

        for hierarchy_name in hierarchies_to_be_removed:
            if not case_and_space_insensitive_equals(hierarchy_name, "Leaves"):
                self.hierarchies.delete(dimension_name=dimension.name, hierarchy_name=hierarchy_name, **kwargs)

    def update_or_create(self, dimension: Dimension, **kwargs):
        """ update if exists else create

        :param dimension:
        :return:
        """
        if self.exists(dimension_name=dimension.name, **kwargs):
            self.update(dimension=dimension, **kwargs)
        else:
            self.create(dimension=dimension, **kwargs)

    def delete(self, dimension_name: str, **kwargs) -> Response:
        """ Delete a dimension

        :param dimension_name: Name of the dimension
        :return:
        """
        url = format_url("/api/v1/Dimensions('{}')", dimension_name)
        return self._rest.DELETE(url, **kwargs)

    def exists(self, dimension_name: str, **kwargs) -> bool:
        """ Check if dimension exists
        
        :return: 
        """
        url = format_url("/api/v1/Dimensions('{}')", dimension_name)
        return self._exists(url, **kwargs)

    def get_all_names(self, skip_control_dims: bool = False, **kwargs) -> List[str]:
        """Ask TM1 Server for list of all dimension names

        :skip_control_dims: bool, True to skip control dims
        :Returns:
            List of Strings
        """
        url = format_url(
            "/api/v1/{}?$select=Name",
            'ModelDimensions()' if skip_control_dims else 'Dimensions'
        )

        response = self._rest.GET(url, **kwargs)

        dimension_names = list(entry['Name'] for entry in response.json()['value'])
        return dimension_names

    def get_number_of_dimensions(self, skip_control_dims: bool = False, **kwargs) -> int:
        """Ask TM1 Server for number of dimensions

        :skip_control_dims: bool, True to exclude control dims from count
        :return: Number of dimensions
        """

        if skip_control_dims:
            response = int(self._rest.GET("/api/v1/ModelDimensions()?$select=Name&$count", **kwargs).json()['@odata.count'])
        else:
            response = int(self._rest.GET("/api/v1/Dimensions/$count", **kwargs).text)
        
        return response

    def execute_mdx(self, dimension_name: str, mdx: str, **kwargs) -> List:
        """ Execute MDX against Dimension. 
        Requires }ElementAttributes_ Cube of the dimension to exist !
 
        :param dimension_name: Name of the Dimension
        :param mdx: valid Dimension-MDX Statement 
        :return: List of Element names
        """

        warnings.warn("execute_mdx() will be deprecated; use ElementService execute_set_mdx.", DeprecationWarning,
                      stacklevel=2)

        mdx_skeleton = "SELECT " \
                       "{} ON ROWS, " \
                       "{{ [}}ElementAttributes_{}].DefaultMember }} ON COLUMNS  " \
                       "FROM [}}ElementAttributes_{}]"
        mdx_full = mdx_skeleton.format(mdx, dimension_name, dimension_name)
        request = '/api/v1/ExecuteMDX?$expand=Axes(' \
                  '$filter=Ordinal eq 1;' \
                  '$expand=Tuples($expand=Members($select=Ordinal;$expand=Element($select=Name))))'
        payload = {"MDX": mdx_full}
        response = self._rest.POST(request, json.dumps(payload, ensure_ascii=False), **kwargs)
        raw_dict = response.json()
        return [row_tuple['Members'][0]['Element']['Name'] for row_tuple in raw_dict['Axes'][0]['Tuples']]

    def create_element_attributes_through_ti(self, dimension: Dimension, **kwargs):
        """ 
        
        :param dimension. Instance of TM1py.Objects.Dimension class
        :return: 
        """
        process_service = ProcessService(self._rest)
        for h in dimension:
            statements = ["AttrInsert('{}', '', '{}', '{}');".format(dimension.name, ea.name, ea.attribute_type[0])
                          for ea
                          in h.element_attributes]
            process_service.execute_ti_code(lines_prolog=statements, **kwargs)
