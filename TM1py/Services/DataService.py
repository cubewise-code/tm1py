# -*- coding: utf-8 -*-

import collections
import json

from TM1py.Services.CubeService import CubeService
from TM1py.Utils import Utils


class DataService:
    """ Service to handle Read and Write operations to TM1 cubes
    
    """
    def __init__(self, tm1_rest):
        """
        
        :param tm1_rest: 
        """
        self._rest = tm1_rest

    def write_value(self, value, cube_name, element_tuple, dimensions=None):
        """ Write value into cube at specified coordinates

        :param value: the actual value
        :param cube_name: name of the target cube
        :param element_tuple: target coordinates
        :param dimensions: optional. Dimension names in their natural order. Will speed up the request!
        :return: response
        """
        if not dimensions:
            dimensions = CubeService(self._rest).get(cube_name).dimensions
        request = "/api/v1/Cubes('{}')/tm1.Update".format(cube_name)
        body_as_dict = collections.OrderedDict()
        body_as_dict["Cells"] = [{}]
        body_as_dict["Cells"][0]["Tuple@odata.bind"] = \
            ["Dimensions('{}')/Hierarchies('{}')/Elements('{}')".format(dim, dim, elem)
             for dim, elem in zip(dimensions, element_tuple)]
        body_as_dict["Value"] = str(value)
        data = json.dumps(body_as_dict, ensure_ascii=False)
        return self._rest.POST(request=request, data=data)

    def write_values(self, cube_name, cellset_as_dict):
        """ Write values in cube.  
        Easy to use but doesnt scale. Not suitable for cellsets with > 1000 cells 

        :param cube_name: name of the cube
        :param cellset_as_dict: {(elem_a, elem_b, elem_c): 243, (elem_d, elem_e, elem_f) : 109}
        :return:
        """
        cube_service = CubeService(self._rest)
        dimension_order = cube_service.get_dimension_names(cube_name)
        request = "/api/v1/Cubes('{}')/tm1.Update".format(cube_name)
        updates = []
        for element_tuple, value in cellset_as_dict.items():
            body_as_dict = collections.OrderedDict()
            body_as_dict["Cells"] = [{}]
            body_as_dict["Cells"][0]["Tuple@odata.bind"] = \
                ["Dimensions('{}')/Hierarchies('{}')/Elements('{}')".format(dim, dim, elem)
                 for dim, elem in zip(dimension_order, element_tuple)]
            body_as_dict["Value"] = str(value)
            updates.append(json.dumps(body_as_dict, ensure_ascii=False))
        updates = '[' + ','.join(updates) + ']'
        self._rest.POST(request=request, data=updates)

    def write_values_through_cellset(self, mdx, values):
        """ Significantly faster than write_values function

            Cellset gets created according to MDX Expression. For instance:
                [  61, 29 ,13
                   42, 54, 15,
                   17, 28, 81  ]
                   
            Each value in the cellset can be addressed through its position: The ordinal integer value. 
            Ordinal-enumeration goes from top to bottom from left to right
            Number 61 has Ordinal 0, 29 has Ordinal 1, etc.
    
            The order of the iterable determines the insertion point in the cellset. 
            For instance:
                [91, 85, 72, 68, 51, 42, 35, 28, 11]
    
            would lead to:
                [  91, 85 ,72
                   68, 51, 42,
                   35, 28, 11  ]
    
            When writing large datasets into TM1 Cubes it can be convenient to call this function asynchronously.
    
            :param mdx: Valid MDX Expression.
            :param values: List of values. The Order of the List/ Iterable determines the insertion point in the cellset.
            :return: 
        """
        # execute mdx and create cellset at Server
        cellset_id = self.create_cellset(mdx)

        # write data
        self.update_cellset(cellset_id, values)

        # delete cellset (free up memory on server side)!
        self.delete_cellset(cellset_id)

    def update_cellset(self, cellset_id, values):
        """ Write values into cellset

        Number of values must match the number of cells in the cellset

        :param cellset_id: 
        :param values: iterable with Numeric and String values
        :return: 
        """
        request = "/api/v1/Cellsets('{}')/Cells".format(cellset_id)
        data = []
        for i, value in enumerate(values):
            data.append({
                "Ordinal": i,
                "Value": value
            })
        self._rest.PATCH(request, json.dumps(data, ensure_ascii=False))

    def execute_mdx(self, mdx, cell_properties=None, top=None):
        """ Execute MDX and return the cells with their properties

        :param mdx: MDX Query, as string
        :param cell_properties: properties to be queried from the cell. Like Value, Ordinal, etc as iterable
        :param top: integer
        :return: content in sweet consice strcuture.
        """
        if not cell_properties:
            cell_properties = ['Value', 'Ordinal']
        if top:
            request = '/api/v1/ExecuteMDX?$expand=Cube($select=Dimensions;$expand=Dimensions($select=Name)),' \
                      'Axes($expand=Tuples($expand=Members($select=UniqueName);$top={})),Cells($select={};$top={})' \
                .format(str(top), ','.join(cell_properties), str(top))
        else:
            request = '/api/v1/ExecuteMDX?$expand=Cube($select=Dimensions;$expand=Dimensions($select=Name)),' \
                      'Axes($expand=Tuples($expand=Members($select=UniqueName))),Cells($select={})' \
                .format(','.join(cell_properties))
        data = {
            'MDX': mdx
        }
        cellset = self._rest.POST(request=request, data=json.dumps(data, ensure_ascii=False))
        return Utils.build_content_from_cellset(raw_cellset_as_dict=json.loads(cellset),
                                                cell_properties=cell_properties,
                                                top=top)

    def get_view_content(self, cube_name, view_name, cell_properties=None, private=True, top=None):
        """ get view content as dictionary with sweet and concise structure.
            Works on NativeView and MDXView !
            Not Hierarchy aware !

        :param cube_name: String
        :param view_name: String
        :param cell_properties: List, cell properties: [Values, Status, HasPicklist, etc.]
        :param private: Boolean
        :param top: Int, number of cells

        :return: Dictionary : {([dim1].[elem1], [dim2][elem6]): {'Value':3127.312, 'Ordinal':12}   ....  }
        """
        if not cell_properties:
            cell_properties = ['Value', 'Ordinal']
        cellset_as_dict = self._get_cellset_from_view(cube_name, view_name, cell_properties, private, top)
        content_as_dict = Utils.build_content_from_cellset(cellset_as_dict, cell_properties, top)
        return content_as_dict

    def _get_cellset_from_view(self, cube_name, view_name, cell_properties=None, private=True, top=None):
        """ get view content as dictionary in its native (cellset-) structure.

        :param cube_name: String
        :param view_name: String
        :param cell_properties: List of cell properties
        :param private: Boolean
        :param top: Int, number of cells

        :return:
            `Dictionary` : {Cells : {}, 'ID' : '', 'Axes' : [{'Ordinal' : 1, Members: [], ...},
            {'Ordinal' : 2, Members: [], ...}, {'Ordinal' : 3, Members: [], ...} ] }
        """
        if not cell_properties:
            cell_properties = ['Value', 'Ordinal']
        views = 'PrivateViews' if private else 'Views'
        if top:
            request = '/api/v1/Cubes(\'{}\')/{}(\'{}\')/tm1.Execute?$expand=Cube($select=Dimensions;' \
                      '$expand=Dimensions($select=Name)),Axes($expand=Tuples($expand=Members' \
                      '($select=UniqueName);$top={})),Cells($select={};$top={})' \
                .format(cube_name, views, view_name, str(top), ','.join(cell_properties), str(top))
        else:
            request = '/api/v1/Cubes(\'{}\')/{}(\'{}\')/tm1.Execute?$expand=Cube($select=Dimensions;' \
                      '$expand=Dimensions($select=Name)),Axes($expand=Tuples($expand=Members' \
                      '($select=UniqueName))),Cells($select={})' \
                .format(cube_name, views, view_name, ','.join(cell_properties))
        response = self._rest.POST(request, '')
        return json.loads(response)

    def create_cellset(self, mdx):
        """ Execute MDX in order to create cellset at server. return the cellset-id

        :param mdx: MDX Query, as string
        :return: 
        """
        request = '/api/v1/ExecuteMDX'
        data = {
            'MDX': mdx
        }
        response = self._rest.POST(request=request, data=json.dumps(data, ensure_ascii=False))
        cellset_id = json.loads(response)['ID']
        return cellset_id

    def delete_cellset(self, cellset_id):
        """ Delete a cellset

        :param cellset_id: 
        :return: 
        """
        request = "/api/v1/Cellsets('{}')".format(cellset_id)
        return self._rest.DELETE(request)
