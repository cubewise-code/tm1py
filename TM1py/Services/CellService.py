# -*- coding: utf-8 -*-

import functools
import json
import warnings
from collections import OrderedDict
from io import StringIO

import pandas as pd

from TM1py.Utils import Utils
from TM1py.Utils.Utils import build_pandas_dataframe_from_cellset, dimension_name_from_element_unique_name, \
    CaseAndSpaceInsensitiveTuplesDict, case_and_space_insensitive_equals, odata_escape_single_quotes_in_object_names


def tidy_cellset(func):
    """ Higher Order Function to tidy up cellset after usage
    """

    @functools.wraps(func)
    def wrapper(self, cellset_id, *args, **kwargs):
        try:
            return func(self, cellset_id, *args, **kwargs)
        finally:
            if kwargs.get("delete_cellset", True):
                self.delete_cellset(cellset_id=cellset_id)

    return wrapper


class CellService:
    """ Service to handle Read and Write operations to TM1 cubes
    
    """

    SANDBOX_DIMENSION = "Sandboxes"

    def __init__(self, tm1_rest):
        """
        
        :param tm1_rest: 
        """
        self._rest = tm1_rest

    def get_value(self, cube_name, element_string, dimensions=None):
        """ Element_String describes the Dimension-Hierarchy-Element arrangement
            
        :param cube_name: Name of the cube
        :param element_string: "Hierarchy1::Element1 && Hierarchy2::Element4, Element9, Element2"
            - Dimensions are not specified! They are derived from the position.
            - The , seperates the element-selections
            - If more than one hierarchy is selected per dimension && splits the elementselections
            - If no Hierarchy is specified. Default Hierarchy will be addressed
        :param dimensions: List of dimension names in correct order
        :return: 
        """
        mdx_template = "SELECT {} ON ROWS, {} ON COLUMNS FROM [{}]"
        mdx_rows_list = []
        from TM1py.Services.CubeService import CubeService
        if not dimensions:
            dimensions = CubeService(self._rest).get(cube_name).dimensions
        element_selections = element_string.split(',')
        # Build the ON ROWS statement:
        # Loop through the comma seperated element selection, except for the last one
        for dimension_name, element_selection in zip(dimensions[:-1], element_selections[:-1]):
            if "&&" not in element_selection:
                mdx_rows_list.append("{[" + dimension_name + "].[" + dimension_name + "].[" + element_selection + "]}")
            else:
                for element_selection_part in element_selection.split('&&'):
                    hierarchy_name, element_name = element_selection_part.split('::')
                    mdx_rows_list.append("{[" + dimension_name + "].[" + hierarchy_name + "].[" + element_name + "]}")
        mdx_rows = "*".join(mdx_rows_list)
        # Build the ON COLUMNS statement from last dimension
        mdx_columns = ""
        if "&&" not in element_selections[-1]:
            mdx_columns = "{[" + dimensions[-1] + "].[" + dimensions[-1] + "].[" + element_selections[-1] + "]}"
        else:
            mdx_columns_list = []
            for element_selection_part in element_selections[-1].split('&&'):
                hierarchy_name, element_name = element_selection_part.split('::')
                mdx_columns_list.append("{[" + dimensions[-1] + "].[" + hierarchy_name + "].[" + element_name + "]}")
                mdx_columns = "*".join(mdx_columns_list)
        # Construct final MDX
        mdx = mdx_template.format(mdx_rows, mdx_columns, cube_name)
        # Execute MDX
        cellset = dict(self.execute_mdx(mdx))
        return next(iter(cellset.values()))["Value"]

    def relative_proportional_spread(
            self,
            value,
            cube,
            unique_element_names,
            reference_unique_element_names,
            reference_cube=None):
        """ Execute relative proportional spread

        :param value: value to be spread
        :param cube: name of the cube
        :param unique_element_names: target cell coordinates as unique element names (e.g. ["[d1].[c1]","[d2].[e3]"])
        :param reference_cube: name of the reference cube. Can be None
        :param reference_unique_element_names: reference cell coordinates as unique element names
        :return:
        """
        mdx = """
        SELECT
        {{ {rows} }} ON 0
        FROM [{cube}]
        """.format(rows="}*{".join(unique_element_names), cube=cube)
        cellset_id = self.create_cellset(mdx=mdx)

        payload = {
            "BeginOrdinal": 0,
            "Value": "RP" + str(value),
            "ReferenceCell@odata.bind": list(),
            "ReferenceCube@odata.bind":
                odata_escape_single_quotes_in_object_names("Cubes('{}')".format(
                    reference_cube if reference_cube else cube))}
        for unique_element_name in reference_unique_element_names:
            payload["ReferenceCell@odata.bind"].append(
                odata_escape_single_quotes_in_object_names("Dimensions('{}')/Hierarchies('{}')/Elements('{}')".format(
                    *Utils.dimension_hierarchy_element_tuple_from_unique_name(unique_element_name))))

        self._post_against_cellset(cellset_id=cellset_id, payload=payload, delete_cellset=True)

    @tidy_cellset
    def _post_against_cellset(self, cellset_id, payload, **kwargs):
        request = "/api/v1/Cellsets('{}')/tm1.Update".format(cellset_id)
        return self._rest.POST(request=request, data=json.dumps(payload))

    def get_dimension_names_for_writing(self, cube_name):
        from TM1py.Services import CubeService
        cube_service = CubeService(self._rest)
        dimensions = cube_service.get_dimension_names(cube_name)
        # do not return sandbox dimension as first dimension, as it can't be used in address tuple for writing
        if case_and_space_insensitive_equals(dimensions[0], self.SANDBOX_DIMENSION):
            return dimensions[1:]
        return dimensions

    def write_value(self, value, cube_name, element_tuple, dimensions=None):
        """ Write value into cube at specified coordinates

        :param value: the actual value
        :param cube_name: name of the target cube
        :param element_tuple: target coordinates
        :param dimensions: optional. Dimension names in their natural order. Will speed up the execution!
        :return: response
        """
        if not dimensions:
            dimensions = self.get_dimension_names_for_writing(cube_name=cube_name)
        request = "/api/v1/Cubes('{}')/tm1.Update".format(cube_name)
        body_as_dict = OrderedDict()
        body_as_dict["Cells"] = [{}]
        body_as_dict["Cells"][0]["Tuple@odata.bind"] = [
            odata_escape_single_quotes_in_object_names("Dimensions('{}')/Hierarchies('{}')/Elements('{}')".format(
                dim, dim, elem))
            for dim, elem
            in zip(dimensions, element_tuple)]
        body_as_dict["Value"] = str(value) if value else ""
        data = json.dumps(body_as_dict, ensure_ascii=False)
        return self._rest.POST(request=request, data=data)

    def write_values(self, cube_name, cellset_as_dict, dimensions=None):
        """ Write values in cube.  
        For cellsets with > 1000 cells look into "write_values_through_cellset"

        :param cube_name: name of the cube
        :param cellset_as_dict: {(elem_a, elem_b, elem_c): 243, (elem_d, elem_e, elem_f) : 109}
        :param dimensions: optional. Dimension names in their natural order. Will speed up the execution!
        :return: Response
        """
        if not dimensions:
            dimensions = self.get_dimension_names_for_writing(cube_name=cube_name)
        request = "/api/v1/Cubes('{}')/tm1.Update".format(cube_name)
        updates = []
        for element_tuple, value in cellset_as_dict.items():
            body_as_dict = OrderedDict()
            body_as_dict["Cells"] = [{}]
            body_as_dict["Cells"][0]["Tuple@odata.bind"] = [
                odata_escape_single_quotes_in_object_names("Dimensions('{}')/Hierarchies('{}')/Elements('{}')".format(
                    dim, dim, elem))
                for dim, elem
                in zip(dimensions, element_tuple)]
            body_as_dict["Value"] = str(value) if value else ""
            updates.append(json.dumps(body_as_dict, ensure_ascii=False))
        updates = '[' + ','.join(updates) + ']'
        return self._rest.POST(request=request, data=updates)

    def write_values_through_cellset(self, mdx, values):
        """ Significantly faster than write_values function
        Cellset gets created according to MDX Expression. For instance:
        [[61, 29 ,13], 
        [42, 54, 15], 
        [17, 28, 81]]
        
        Each value in the cellset can be addressed through its position: The ordinal integer value. 
        Ordinal-enumeration goes from top to bottom from left to right
        Number 61 has Ordinal 0, 29 has Ordinal 1, etc.

        The order of the iterable determines the insertion point in the cellset. 
        For instance:
        [91, 85, 72, 68, 51, 42, 35, 28, 11]

        would lead to:
        [[91, 85 ,72], 
        [68, 51, 42], 
        [35, 28, 11]]

        When writing large datasets into TM1 Cubes it can be convenient to call this function asynchronously.
        
        :param mdx: Valid MDX Expression.
        :param values: List of values. The Order of the List/ Iterable determines the insertion point in the cellset.
        :return: 
        """
        # execute mdx and create cellset at Server
        cellset_id = self.create_cellset(mdx)
        self.update_cellset(cellset_id=cellset_id, values=values)

    @tidy_cellset
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

    def execute_mdx(self, mdx, cell_properties=None, top=None, skip_contexts=False):
        """ Execute MDX and return the cells with their properties

        :param mdx: MDX Query, as string
        :param cell_properties: properties to be queried from the cell. E.g. Value, Ordinal, RuleDerived, ... 
        :param top: integer
        :param skip_contexts: skip elements from titles / contexts in response
        :return: content in sweet concise structure.
        """
        cellset_id = self.create_cellset(mdx=mdx)
        return self.extract_cellset(
            cellset_id=cellset_id,
            cell_properties=cell_properties,
            top=top,
            skip_contexts=skip_contexts,
            delete_cellset=True)

    def execute_view(self, cube_name, view_name, cell_properties=None, private=True, top=None, skip_contexts=False):
        """ get view content as dictionary with sweet and concise structure.
            Works on NativeView and MDXView !

        :param cube_name: String
        :param view_name: String
        :param cell_properties: List, cell properties: [Values, Status, HasPicklist, etc.]
        :param private: Boolean
        :param top: Int, number of cells to return (counting from top)
        :param skip_contexts: skip elements from titles / contexts in response

        :return: Dictionary : {([dim1].[elem1], [dim2][elem6]): {'Value':3127.312, 'Ordinal':12}   ....  }
        """
        cellset_id = self.create_cellset_from_view(cube_name=cube_name, view_name=view_name, private=private)
        return self.extract_cellset(
            cellset_id=cellset_id,
            cell_properties=cell_properties,
            top=top,
            skip_contexts=skip_contexts,
            delete_cellset=True)

    def execute_mdx_raw(
            self,
            mdx,
            cell_properties=None,
            elem_properties=None,
            member_properties=None,
            top=None,
            skip_contexts=False):
        """ Execute MDX and return the raw data from TM1

        :param mdx: String, a valid MDX Query
        :param cell_properties: List of properties to be queried from the cell. E.g. ['Value', 'Ordinal', 'RuleDerived', ...]
        :param elem_properties: List of properties to be queried from the elements. E.g. ['UniqueName','Attributes', ...]
        :param member_properties: List of properties to be queried from the members. E.g. ['UniqueName','Attributes', ...]
        :param top: Integer limiting the number of cells and the number or rows returned
        :param skip_contexts: skip elements from titles / contexts in response
        :return: Raw format from TM1.
        """
        cellset_id = self.create_cellset(mdx=mdx)
        return self.extract_cellset_raw(
            cellset_id=cellset_id,
            cell_properties=cell_properties,
            elem_properties=elem_properties,
            member_properties=member_properties,
            top=top,
            delete_cellset=True,
            skip_contexts=skip_contexts)

    def execute_view_raw(
            self,
            cube_name,
            view_name,
            private=True,
            cell_properties=None,
            elem_properties=None,
            member_properties=None,
            top=None,
            skip_contexts=False):
        """ Execute a cube view and return the raw data from TM1

        :param cube_name: String, name of the cube
        :param view_name: String, name of the view
        :param private: True (private) or False (public)
        :param cell_properties: List of properties to be queried from the cell. E.g. ['Value', 'Ordinal', 'RuleDerived', ...]
        :param elem_properties: List of properties to be queried from the elements. E.g. ['UniqueName','Attributes', ...]
        :param member_properties: List of properties to be queried from the members. E.g. ['UniqueName','Attributes', ...]
        :param top: Integer limiting the number of cells and the number or rows returned
        :param skip_contexts: skip elements from titles / contexts in response
        :return: Raw format from TM1.
        """
        cellset_id = self.create_cellset_from_view(cube_name=cube_name, view_name=view_name, private=private)
        return self.extract_cellset_raw(
            cellset_id=cellset_id,
            cell_properties=cell_properties,
            elem_properties=elem_properties,
            member_properties=member_properties,
            top=top,
            skip_contexts=skip_contexts,
            delete_cellset=True)

    def execute_mdx_values(self, mdx):
        """ Optimized for performance. Query only raw cell values. 
        Coordinates are omitted !

        :param mdx: a valid MDX Query
        :return: Generator of cell values
        """
        cellset_id = self.create_cellset(mdx=mdx)
        return self.extract_cellset_values(cellset_id, delete_cellset=True)

    def execute_view_values(self, cube_name, view_name, private=True):
        cellset_id = self.create_cellset_from_view(cube_name=cube_name, view_name=view_name, private=private)
        return self.extract_cellset_values(cellset_id, delete_cellset=True)

    def execute_mdx_rows_and_values(self, mdx, element_unique_names=True):
        cellset_id = self.create_cellset(mdx=mdx)
        return self.extract_cellset_rows_and_values(cellset_id, element_unique_names, delete_cellset=True)

    def execute_view_rows_and_values(self, cube_name, view_name, private=True, element_unique_names=True):
        cellset_id = self.create_cellset_from_view(cube_name=cube_name, view_name=view_name, private=private)
        return self.extract_cellset_rows_and_values(cellset_id, element_unique_names, delete_cellset=True)

    def execute_mdx_csv(self, mdx):
        """ Optimized for performance. Get csv string of coordinates and values. 
        Context dimensions are omitted !
        Cells with Zero/null are omitted !

        :param mdx: Valid MDX Query 
        :return: String
        """
        cellset_id = self.create_cellset(mdx)
        return self.extract_cellset_csv(cellset_id=cellset_id, delete_cellset=True)

    def execute_view_csv(self, cube_name, view_name, private=True):
        cellset_id = self.create_cellset_from_view(cube_name=cube_name, view_name=view_name, private=private)
        return self.extract_cellset_csv(cellset_id=cellset_id, delete_cellset=True)

    def execute_mdx_dataframe(self, mdx, **kwargs):
        """ Optimized for performance. Get Pandas DataFrame from MDX Query.

        Context dimensions are omitted in the resulting Dataframe !
        Cells with Zero/null are omitted !

        Takes all arguments from the pandas.read_csv method:
        https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.read_csv.html

        :param mdx: Valid MDX Query
        :return: Pandas Dataframe
        """
        cellset_id = self.create_cellset(mdx)
        return self.extract_cellset_dataframe(cellset_id, **kwargs)

    def execute_view_dataframe_pivot(self, cube_name, view_name, private=False, dropna=False, fill_value=None):
        """ Execute a cube view to get a pandas pivot dataframe, in the shape of the cube view

        :param cube_name:
        :param view_name:
        :param private:
        :param dropna:
        :param fill_value:
        :return:
        """
        cellset_id = self.create_cellset_from_view(cube_name=cube_name, view_name=view_name, private=private)
        return self.extract_cellset_dataframe_pivot(
            cellset_id=cellset_id,
            dropna=dropna,
            fill_value=fill_value)

    def execute_mdx_dataframe_pivot(self, mdx, dropna=False, fill_value=None):
        """ Execute MDX Query to get a pandas pivot dataframe in the shape as specified in the Query

        :param mdx:
        :param dropna:
        :param fill_value:
        :return:
        """
        cellset_id = self.create_cellset(mdx=mdx)
        return self.extract_cellset_dataframe_pivot(
            cellset_id=cellset_id,
            dropna=dropna,
            fill_value=fill_value)

    def execute_view_dataframe(self, cube_name, view_name, private=True, **kwargs):
        """ Optimized for performance. Get Pandas DataFrame from an existing Cube View 
        Context dimensions are omitted in the resulting Dataframe !
        Cells with Zero/null are omitted !

        Takes all arguments from the pandas.read_csv method:
        https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.read_csv.html

        :param cube_name: Name of the 
        :param view_name: 
        :param private: 
        :return: Pandas Dataframe
        """
        cellset_id = self.create_cellset_from_view(cube_name=cube_name, view_name=view_name, private=private)
        return self.extract_cellset_dataframe(cellset_id, **kwargs)

    def execute_mdx_cellcount(self, mdx):
        """ Execute MDX in order to understand how many cells are in a cellset.
        Only return number of cells in the cellset. FAST!

        :param mdx: MDX Query, as string
        :return: Number of Cells in the CellSet
        """
        cellset_id = self.create_cellset(mdx)
        return self.extract_cellset_cellcount(cellset_id, delete_cellset=True)

    def execute_view_cellcount(self, cube_name, view_name, private=True):
        """ Execute cube view in order to understand how many cells are in a cellset.
        Only return number of cells in the cellset. FAST!
        
        :param cube_name: cube name
        :param view_name: view name
        :param private: True (private) or False (public)
        :return: 
        """
        cellset_id = self.create_cellset_from_view(cube_name=cube_name, view_name=view_name, private=private)
        return self.extract_cellset_cellcount(cellset_id, delete_cellset=True)

    def execute_mdx_ui_dygraph(
            self,
            mdx,
            elem_properties=None,
            member_properties=None,
            value_precision=2,
            top=None):
        """ Execute MDX get dygraph dictionary
        Useful for grids or charting libraries that want an array of cell values per column
        Returns 3-dimensional cell structure for tabbed grids or multiple charts
        Example 'cells' return format:
            'cells': {
                '10100': [
                    ['Q1-2004', 28981046.50724231, 19832724.72429739],
                    ['Q2-2004', 29512482.207418434, 20365654.788303416],
                    ['Q3-2004', 29913730.038971487, 20729201.329183243],
                    ['Q4-2004', 29563345.9542385, 20480205.20121749]],
                '10200': [
                    ['Q1-2004', 13888143.710000003, 9853293.623709997],
                    ['Q2-2004', 14300216.43, 10277650.763958748],
                    ['Q3-2004', 14502421.63, 10466934.096533755],
                    ['Q4-2004', 14321501.940000001, 10333095.839474997]]
            },
        :param top:
        :param mdx: String, valid MDX Query
        :param elem_properties: List of properties to be queried from the elements. E.g. ['UniqueName','Attributes', ...]
        :param member_properties: List of properties to be queried from the members. E.g. ['UniqueName','Attributes', ...]
        :param value_precision: Integer (optional) specifying number of decimal places to return
        :return: dict : { titles: [], headers: [axis][], cells: { Page0: [  [column name, column values], [], ... ], ...} }
        """
        cellset_id = self.create_cellset(mdx)
        data = self.extract_cellset_raw(cellset_id=cellset_id,
                                        cell_properties=["Value"],
                                        elem_properties=elem_properties,
                                        member_properties=list(set(member_properties or []) | {"Name"}),
                                        top=top,
                                        delete_cellset=True)
        return Utils.build_ui_dygraph_arrays_from_cellset(raw_cellset_as_dict=data, value_precision=value_precision)

    def execute_view_ui_dygraph(
            self,
            cube_name,
            view_name,
            private=True,
            elem_properties=None,
            member_properties=None,
            value_precision=2,
            top=None):
        """ 
        Useful for grids or charting libraries that want an array of cell values per row.
        Returns 3-dimensional cell structure for tabbed grids or multiple charts.
        Rows and pages are dicts, addressable by their name. Proper order of rows can be obtained in headers[1]
        Example 'cells' return format:
            'cells': { 
                '10100': { 
                    'Net Operating Income': [ 19832724.72429739,
                                              20365654.788303416,
                                              20729201.329183243,
                                              20480205.20121749],
                    'Revenue': [ 28981046.50724231,
                                 29512482.207418434,
                                 29913730.038971487,
                                 29563345.9542385]},
                '10200': { 
                    'Net Operating Income': [ 9853293.623709997,
                                               10277650.763958748,
                                               10466934.096533755,
                                               10333095.839474997],
                    'Revenue': [ 13888143.710000003,
                                 14300216.43,
                                 14502421.63,
                                 14321501.940000001]}
            },
        
        :param top:
        :param cube_name: cube name
        :param view_name: view name
        :param private: True (private) or False (public)
        :param elem_properties: List of properties to be queried from the elements. E.g. ['UniqueName','Attributes', ...]
        :param member_properties: List of properties to be queried from the members. E.g. ['UniqueName','Attributes', ...]
        :param value_precision: number decimals
        :return: 
        """
        cellset_id = self.create_cellset_from_view(cube_name=cube_name, view_name=view_name, private=private)
        data = self.extract_cellset_raw(cellset_id=cellset_id,
                                        cell_properties=["Value"],
                                        elem_properties=elem_properties,
                                        member_properties=list(set(member_properties or []) | {"Name"}),
                                        top=top,
                                        delete_cellset=True)
        return Utils.build_ui_dygraph_arrays_from_cellset(raw_cellset_as_dict=data, value_precision=value_precision)

    def execute_mdx_ui_array(
            self,
            mdx,
            elem_properties=None,
            member_properties=None,
            value_precision=2,
            top=None):
        """
        Useful for grids or charting libraries that want an array of cell values per row.
        Returns 3-dimensional cell structure for tabbed grids or multiple charts.
        Rows and pages are dicts, addressable by their name. Proper order of rows can be obtained in headers[1]
        Example 'cells' return format:
            'cells': { 
                '10100': { 
                    'Net Operating Income': [ 19832724.72429739,
                                              20365654.788303416,
                                              20729201.329183243,
                                              20480205.20121749],
                    'Revenue': [ 28981046.50724231,
                                 29512482.207418434,
                                 29913730.038971487,
                                 29563345.9542385]},
                '10200': { 
                    'Net Operating Income': [ 9853293.623709997,
                                               10277650.763958748,
                                               10466934.096533755,
                                               10333095.839474997],
                    'Revenue': [ 13888143.710000003,
                                 14300216.43,
                                 14502421.63,
                                 14321501.940000001]}
            },

        :param top:
        :param mdx: a valid MDX Query
        :param elem_properties: List of properties to be queried from the elements. E.g. ['UniqueName','Attributes', ...]
        :param member_properties: List of properties to be queried from the members. E.g. ['UniqueName','Attributes', ...]
        :param value_precision: Integer (optional) specifying number of decimal places to return
        :return: dict : { titles: [], headers: [axis][], cells: { Page0: { Row0: { [row values], Row1: [], ...}, ...}, ...} }
        """
        cellset_id = self.create_cellset(mdx)
        data = self.extract_cellset_raw(cellset_id=cellset_id,
                                        cell_properties=["Value"],
                                        elem_properties=elem_properties,
                                        member_properties=list(set(member_properties or []) | {"Name"}),
                                        top=top,
                                        delete_cellset=True)
        return Utils.build_ui_arrays_from_cellset(raw_cellset_as_dict=data, value_precision=value_precision)

    def execute_view_ui_array(
            self,
            cube_name,
            view_name,
            private=True,
            elem_properties=None,
            member_properties=None,
            value_precision=2,
            top=None):
        """
        Useful for grids or charting libraries that want an array of cell values per row.
        Returns 3-dimensional cell structure for tabbed grids or multiple charts.
        Rows and pages are dicts, addressable by their name. Proper order of rows can be obtained in headers[1]
        Example 'cells' return format:
            'cells': { 
                '10100': { 
                    'Net Operating Income': [ 19832724.72429739,
                                              20365654.788303416,
                                              20729201.329183243,
                                              20480205.20121749],
                    'Revenue': [ 28981046.50724231,
                                 29512482.207418434,
                                 29913730.038971487,
                                 29563345.9542385]},
                '10200': { 
                    'Net Operating Income': [ 9853293.623709997,
                                               10277650.763958748,
                                               10466934.096533755,
                                               10333095.839474997],
                    'Revenue': [ 13888143.710000003,
                                 14300216.43,
                                 14502421.63,
                                 14321501.940000001]}
            },

        :param top:
        :param cube_name: cube name
        :param view_name: view name
        :param private: True (private) or False (public)
        :param elem_properties: List of properties to be queried from the elements. E.g. ['UniqueName','Attributes', ...]
        :param member_properties: List properties to be queried from the member. E.g. ['Name', 'UniqueName']
        :param value_precision: Integer (optional) specifying number of decimal places to return
        :return: dict : { titles: [], headers: [axis][], cells: { Page0: { Row0: { [row values], Row1: [], ...}, ...}, ...} }
        """
        cellset_id = self.create_cellset_from_view(cube_name=cube_name, view_name=view_name, private=private)
        data = self.extract_cellset_raw(cellset_id=cellset_id,
                                        cell_properties=["Value"],
                                        elem_properties=elem_properties,
                                        member_properties=list(set(member_properties or []) | {"Name"}),
                                        top=top,
                                        delete_cellset=True)
        return Utils.build_ui_arrays_from_cellset(raw_cellset_as_dict=data, value_precision=value_precision)

    @tidy_cellset
    def extract_cellset_raw(
            self,
            cellset_id,
            cell_properties=None,
            elem_properties=None,
            member_properties=None,
            top=None,
            skip_contexts=False,
            **kwargs):
        """ Extract full Cellset data and return the raw data from TM1

        :param skip_contexts:
        :param cellset_id: String; ID of existing cellset
        :param cell_properties: List of properties to be queried from cells. E.g. ['Value', 'RuleDerived', ...]
        :param elem_properties: List of properties to be queried from elements. E.g. ['UniqueName','Attributes', ...]
        :param member_properties: List properties to be queried from the member. E.g. ['Name', 'UniqueName']
        :param top: Integer limiting the number of cells and the number or rows returned
        :return: Raw format from TM1.
        """
        if not cell_properties:
            cell_properties = ['Value']

        # select Name property if member_properties is None or empty.
        # Necessary, as tm1 default behaviour is to return all properties if no $select is specified in the request.
        if member_properties is None or len(member_properties) == 0:
            member_properties = ["Name"]
        select_member_properties = "$select={}".format(",".join(member_properties))

        expand_elem_properties = ";$expand=Element($select={elem_properties})".format(
            elem_properties=",".join(elem_properties)) \
            if elem_properties is not None and len(elem_properties) > 0 \
            else ""

        filter_axis = "$filter=Ordinal ne 2;" if skip_contexts else ""

        request = "/api/v1/Cellsets('{cellset_id}')?$expand=" \
                  "Cube($select=Name;$expand=Dimensions($select=Name))," \
                  "Axes({filter_axis}$expand=Tuples($expand=Members({select_member_properties}{expand_elem_properties}){top_rows}))," \
                  "Cells($select={cell_properties}{top_cells})" \
            .format(cellset_id=cellset_id,
                    top_rows=";$top={}".format(top) if top else "",
                    cell_properties=",".join(cell_properties),
                    filter_axis=filter_axis,
                    select_member_properties=select_member_properties,
                    expand_elem_properties=expand_elem_properties,
                    top_cells=";$top={}".format(top) if top else "")
        response = self._rest.GET(request=request)
        return response.json()

    @tidy_cellset
    def extract_cellset_values(self, cellset_id, **kwargs):
        """ Extract Cellset data and return only the cells and values
        
        :param cellset_id: String; ID of existing cellset
        :return: Raw format from TM1.
        """
        request = "/api/v1/Cellsets('{}')?$expand=Cells($select=Value)".format(cellset_id)
        response = self._rest.GET(request=request, data='')
        return (cell["Value"] for cell in response.json()["Cells"])

    @tidy_cellset
    def extract_cellset_rows_and_values(self, cellset_id, element_unique_names=True, **kwargs):
        request = "/api/v1/Cellsets('{}')?$expand=" \
                  "Axes($filter=Ordinal eq 1;$expand=Tuples(" \
                  "$expand=Members($select=Element;$expand=Element($select={}))))," \
                  "Cells($select=Value)".format(cellset_id, "UniqueName" if element_unique_names else "Name")
        response = self._rest.GET(request=request, data='')
        response_json = response.json()
        rows = response_json["Axes"][0]["Tuples"]
        cell_values = [cell["Value"] for cell in response_json["Cells"]]

        result = CaseAndSpaceInsensitiveTuplesDict()

        number_rows = len(rows)
        # avoid division by zero
        if not number_rows:
            return result
        number_cells = len(cell_values)
        number_columns = int(number_cells / number_rows)

        cell_values_by_row = [cell_values[cell_counter:cell_counter + number_columns]
                              for cell_counter
                              in range(0, number_cells, number_columns)]
        element_names_by_row = [tuple(member["Element"]["UniqueName" if element_unique_names else "Name"]
                                      for member
                                      in tupl["Members"])
                                for tupl
                                in rows]
        for element_tuple, cells in zip(element_names_by_row, cell_values_by_row):
            result[element_tuple] = cells
        return result

    @tidy_cellset
    def extract_cellset_composition(self, cellset_id, **kwargs):
        request = "/api/v1/Cellsets('{}')?$expand=Cube($select=Name),Axes($expand=Hierarchies($select=UniqueName))".format(
            cellset_id)
        response = self._rest.GET(
            request=request,
            data='')
        response_json = response.json()
        cube = response_json["Cube"]["Name"]

        rows, titles, columns = [], [], []
        if response_json["Axes"][0]["Hierarchies"]:
            columns = [hierarchy["UniqueName"] for hierarchy in response_json["Axes"][0]["Hierarchies"]]
        if response_json["Axes"][1]["Hierarchies"]:
            rows = [hierarchy["UniqueName"] for hierarchy in response_json["Axes"][1]["Hierarchies"]]
        if len(response_json["Axes"]) > 2:
            titles = [hierarchy["UniqueName"] for hierarchy in response_json["Axes"][2]["Hierarchies"]]
        return cube, titles, rows, columns

    @tidy_cellset
    def extract_cellset_cellcount(self, cellset_id, **kwargs):
        request = "/api/v1/Cellsets('{}')/Cells/$count".format(cellset_id)
        response = self._rest.GET(request)
        return int(response.content)

    @tidy_cellset
    def extract_cellset_csv(self, cellset_id, **kwargs):
        """ Execute Cellset and return only the 'Content', in csv format
        
        :param cellset_id: String; ID of existing cellset
        :return: Raw format from TM1.
        """
        request = "/api/v1/Cellsets('{}')/Content".format(cellset_id)
        data = self._rest.GET(request)
        return data.text

    def extract_cellset_dataframe(self, cellset_id, **kwargs):
        """ Build pandas dataframe from cellset_id

        :param cellset_id:
        :param kwargs:
        :return:
        """
        raw_csv = self.extract_cellset_csv(cellset_id=cellset_id, delete_cellset=True)
        memory_file = StringIO(raw_csv)
        # make sure all element names are strings and values are objects
        if 'dtype' not in kwargs:
            kwargs['dtype'] = {'Value': object, **{col: str for col in range(999)}}
        return pd.read_csv(memory_file, sep=',', **kwargs)

    def extract_cellset_dataframe_pivot(self, cellset_id, dropna=False, fill_value=False, **kwargs):
        """ Extract a pivot table (pandas dataframe) from a cellset in TM1

        :param cellset_id:
        :param dropna:
        :param fill_value:
        :param kwargs:
        :return:
        """
        data = self.extract_cellset(
            cellset_id=cellset_id,
            delete_cellset=False)

        cube, titles, rows, columns = self.extract_cellset_composition(
            cellset_id=cellset_id,
            delete_cellset=True)

        df = build_pandas_dataframe_from_cellset(data, multiindex=False)
        return pd.pivot_table(
            data=df,
            index=[dimension_name_from_element_unique_name(hierarchy_unique_name) for hierarchy_unique_name in rows],
            columns=[dimension_name_from_element_unique_name(hierarchy_unique_name) for hierarchy_unique_name in
                     columns],
            values=["Values"],
            dropna=dropna,
            fill_value=fill_value,
            aggfunc='sum')

    def extract_cellset(
            self,
            cellset_id,
            cell_properties=None,
            top=None,
            delete_cellset=True,
            skip_contexts=False):
        """ Execute Cellset and return the cells with their properties

        :param skip_contexts:
        :param delete_cellset:
        :param cellset_id:
        :param cell_properties: properties to be queried from the cell. E.g. Value, Ordinal, RuleDerived, ...
        :param top: integer
        :return: Content in sweet consice strcuture.
        """
        if not cell_properties:
            cell_properties = ['Value']

        raw_cellset = self.extract_cellset_raw(
            cellset_id,
            cell_properties=cell_properties,
            elem_properties=['UniqueName'],
            member_properties=['UniqueName'],
            top=top,
            skip_contexts=skip_contexts,
            delete_cellset=delete_cellset)

        return Utils.build_content_from_cellset(
            raw_cellset_as_dict=raw_cellset,
            top=top)

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
        cellset_id = response.json()['ID']
        return cellset_id

    def create_cellset_from_view(self, cube_name, view_name, private):
        request = "/api/v1/Cubes('{cube_name}')/{views}('{view_name}')/tm1.Execute".format(
            cube_name=cube_name,
            views='PrivateViews' if private else 'Views', view_name=view_name)
        return self._rest.POST(request=request, data='').json()['ID']

    def delete_cellset(self, cellset_id):
        """ Delete a cellset

        :param cellset_id: 
        :return: 
        """
        request = "/api/v1/Cellsets('{}')".format(cellset_id)
        return self._rest.DELETE(request)

    def deactivate_transactionlog(self, *args):
        """ Deacctivate Transactionlog for one or many cubes

        :param args: one or many cube names
        :return: 
        """
        updates = {}
        for cube_name in args:
            updates[(cube_name, "Logging")] = "NO"
        return self.write_values(cube_name="}CubeProperties", cellset_as_dict=updates)

    def activate_transactionlog(self, *args):
        """ Activate Transactionlog for one or many cubes
        
        :param args: one or many cube names
        :return: 
        """
        updates = {}
        for cube_name in args:
            updates[(cube_name, "Logging")] = "YES"
        return self.write_values(cube_name="}CubeProperties", cellset_as_dict=updates)

    def get_cellset_cells_count(self, mdx):
        """ Execute MDX in order to understand how many cells are in a cellset

        :param mdx: MDX Query, as string
        :return: Number of Cells in the CellSet
        """
        warnings.simplefilter('always', PendingDeprecationWarning)
        warnings.warn(
            "Function deprecated. Use execute_mdx_cellcount(self, mdx) instead.",
            PendingDeprecationWarning
        )
        warnings.simplefilter('default', PendingDeprecationWarning)
        return self.execute_mdx_cellcount(mdx)

    def get_view_content(self, cube_name, view_name, cell_properties=None, private=True, top=None):
        warnings.simplefilter('always', PendingDeprecationWarning)
        warnings.warn(
            "Function deprecated. Use execute_view instead.",
            PendingDeprecationWarning
        )
        warnings.simplefilter('default', PendingDeprecationWarning)
        return self.execute_view(cube_name, view_name, cell_properties, private, top)
