# -*- coding: utf-8 -*-

import json


from TM1py.Exceptions import TM1pyException
from TM1py.Objects.Dimension import Dimension
from TM1py.Services.ObjectService import ObjectService
from TM1py.Services.SubsetService import SubsetService
from TM1py.Services.HierarchyService import HierarchyService
from TM1py.Services.ProcessService import ProcessService

class DimensionService(ObjectService):
    """ Service to handle Object Updates for TM1 Dimensions
    
    """

    # Tuple with TM1 Versions where ElementAttributes need to be created through TI
    ATTRIBUTE_WORKAROUND_VERSIONS = ('11.0.002', '11.0.003')

    def __init__(self, rest):
        super().__init__(rest)
        self.hierarchies = HierarchyService(rest)
        self.subsets = SubsetService(rest)

    def create(self, dimension):
        """ Create a dimension

        :param dimension: instance of TM1py.Dimension
        :return: response
        """
        # If Dimension exists. throw Exception
        if self.exists(dimension.name):
            raise Exception("Dimension already exists")
        # If not all subsequent calls successfull -> undo everything that has been done in this function
        try:
            # Create Dimension, Hierarchies, Elements, Edges.
            request = "/api/v1/Dimensions"
            response = self._rest.POST(request, dimension.body)
            # Create Attributes (Can't be done in the same step as creating the dimension!)
            if self.version[0:8] in self.ATTRIBUTE_WORKAROUND_VERSIONS:
                # Create ElementAttributes through TI on certain PA/TM1 versions to avoid PATCH on Hierarchy
                # Workaround: https://www.ibm.com/developerworks/community/forums/html/topic?id=75f2b99e-6961-4c71-9364-1d5e1e083eff&ps=
                self.create_element_attributes_through_ti(dimension)
            else:
                for hierarchy in dimension:
                    if len(hierarchy.element_attributes) > 0:
                        self.hierarchies.update(hierarchy)
        except TM1pyException as e:
            # undo everything if problem in step 1 or 2
            if self.exists(dimension.name):
                self.delete(dimension.name)
            raise e
        return response

    def get(self, dimension_name):
        """ Get a Dimension

        :param dimension_name:
        :return:
        """
        request = "/api/v1/Dimensions('{}')?$expand=Hierarchies($expand=*)".format(dimension_name)
        dimension_as_json = self._rest.GET(request)
        return Dimension.from_json(dimension_as_json)

    def update(self, dimension):
        """ Update an existing dimension

        :param dimension: instance of TM1py.Dimension
        :return: None
        """
        # update Hierarchies
        for hierarchy in dimension:
            self.hierarchies.update(hierarchy)

    def delete(self, dimension_name):
        """ Delete a dimension

        :param dimension_name: Name of the dimension
        :return:
        """
        request = '/api/v1/Dimensions(\'{}\')'.format(dimension_name)
        return self._rest.DELETE(request)

    def exists(self, dimension_name):
        """ Check if dimension exists
        
        :return: 
        """
        request = "/api/v1/Dimensions('{}')".format(dimension_name)
        return super(DimensionService, self).exists(request)

    def get_all_names(self):
        """Ask TM1 Server for list with all dimension names

        :Returns:
            List of Strings
        """
        response = self._rest.GET('/api/v1/Dimensions?$select=Name', '')
        dimensions = json.loads(response)['value']
        list_dimensions = list(entry['Name'] for entry in dimensions)
        return list_dimensions

    def execute_mdx(self, dimension_name, mdx):
        """ Execute MDX against Dimension. 
        Requires }ElementAttributes_ Cube of the dimension to exist !
 
        :param dimension_name: Name of the Dimension
        :param mdx: valid Dimension-MDX Statement 
        :return: List of Element names
        """
        mdx_skeleton = "SELECT " \
                       "{} ON ROWS, " \
                       "{{ [}}ElementAttributes_{}].DefaultMember }} ON COLUMNS  " \
                       "FROM [}}ElementAttributes_{}]"
        mdx_full = mdx_skeleton.format(mdx, dimension_name, dimension_name)
        request = '/api/v1/ExecuteMDX?$expand=Axes(' \
                  '$filter=Ordinal eq 1;' \
                  '$expand=Tuples($expand=Members($select=Ordinal;$expand=Element($select=Name))))'
        payload = {"MDX": mdx_full}
        raw = self._rest.POST(request, json.dumps(payload, ensure_ascii=False))
        raw_dict = json.loads(raw)
        return [row_tuple['Members'][0]['Element']['Name'] for row_tuple in raw_dict['Axes'][0]['Tuples']]

    def create_element_attributes_through_ti(self, dimension):
        """ 
        
        :param dimension. Instance of TM1py.Objects.Dimension class
        :return: 
        """
        process_service = ProcessService(self._rest)
        for h in dimension:
            statements = ["AttrInsert('{}', '', '{}', '{}');".format(dimension.name, ea.name, ea.attribute_type[0])
                          for ea
                          in h.element_attributes]
        process_service.execute_ti_code(lines_prolog=statements)
