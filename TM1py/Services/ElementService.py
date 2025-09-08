# -*- coding: utf-8 -*-
import csv
import json
from enum import Enum
from io import StringIO
from typing import List, Union, Iterable, Optional, Dict, Tuple


from TM1py import Subset, Process

try:
    import pandas as pd
    import numpy as np

    _has_pandas = True
except ImportError:
    _has_pandas = False

from mdxpy import MdxHierarchySet, Member, MdxLevelExpression
from requests import Response

from TM1py.Exceptions.Exceptions import TM1pyException, TM1pyWritePartialFailureException, TM1pyWriteFailureException, \
    TM1pyRestException
from TM1py.Objects import ElementAttribute, Element
from TM1py.Services.FileService import FileService
from TM1py.Services.ObjectService import ObjectService
from TM1py.Services.ProcessService import ProcessService
from TM1py.Services.RestService import RestService
from TM1py.Utils import CaseAndSpaceInsensitiveDict, format_url, CaseAndSpaceInsensitiveSet, require_data_admin, \
     require_ops_admin, dimension_hierarchy_element_tuple_from_unique_name, require_pandas, require_version
from TM1py.Utils import build_element_unique_names, CaseAndSpaceInsensitiveTuplesDict, verify_version
from itertools import islice
from collections import OrderedDict

class MDXDrillMethod(Enum):
    TM1DRILLDOWNMEMBER = 1
    DESCENDANTS = 2


class ElementService(ObjectService):
    """ Service to handle Object Updates for TM1 Dimension (resp. Hierarchy) Elements

    """

    def __init__(self, rest: RestService):
        super().__init__(rest)

    def get(self, dimension_name: str, hierarchy_name: str, element_name: str, **kwargs) -> Element:
        url = format_url(
            "/Dimensions('{}')/Hierarchies('{}')/Elements('{}')?$expand=*",
            dimension_name, hierarchy_name, element_name)
        response = self._rest.GET(url, **kwargs)
        return Element.from_dict(response.json())

    def create(self, dimension_name: str, hierarchy_name: str, element: Element, **kwargs) -> Response:
        url = format_url(
            "/Dimensions('{}')/Hierarchies('{}')/Elements",
            dimension_name,
            hierarchy_name)
        return self._rest.POST(url, element.body, **kwargs)

    def update(self, dimension_name: str, hierarchy_name: str, element: Element, **kwargs) -> Response:
        url = format_url(
            "/Dimensions('{}')/Hierarchies('{}')/Elements('{}')",
            dimension_name,
            hierarchy_name,
            element.name)
        return self._rest.PATCH(url, element.body, **kwargs)

    def exists(self, dimension_name: str, hierarchy_name: str, element_name: str, **kwargs) -> bool:
        url = format_url(
            "/Dimensions('{}')/Hierarchies('{}')/Elements('{}')",
            dimension_name,
            hierarchy_name,
            element_name)
        return self._exists(url, **kwargs)

    def update_or_create(self, dimension_name: str, hierarchy_name: str, element: Element, **kwargs) -> Response:
        if self.exists(dimension_name=dimension_name, hierarchy_name=hierarchy_name, element_name=element.name, **kwargs):
            return self.update(dimension_name=dimension_name, hierarchy_name=hierarchy_name, element=element, **kwargs)

        return self.create(dimension_name=dimension_name, hierarchy_name=hierarchy_name, element=element, **kwargs)   
        
    def delete(self, dimension_name: str, hierarchy_name: str, element_name: str, **kwargs) -> Response:
        url = format_url(
            "/Dimensions('{}')/Hierarchies('{}')/Elements('{}')",
            dimension_name,
            hierarchy_name,
            element_name)
        return self._rest.DELETE(url, **kwargs)

    @require_version("11.4")
    def delete_elements(self, dimension_name: str, hierarchy_name: str, element_names: List[str] = None,
                        use_ti: bool = False, **kwargs):
        if use_ti:
            return self.delete_elements_use_ti(dimension_name, hierarchy_name, element_names, **kwargs)

        h_service = self._get_hierarchy_service()
        h = h_service.get(dimension_name, hierarchy_name, **kwargs)
        for ele in element_names:
            h.remove_element(ele)
        h_service.update(h, **kwargs)

    def delete_elements_use_ti(self, dimension_name: str, hierarchy_name: str, element_names: List[str] = None,
                               **kwargs):
        subset_service = self._get_subset_service()
        unbound_process_name = subset_name = self.suggest_unique_object_name()
        subset = Subset(subset_name, dimension_name, hierarchy_name, elements=element_names)
        subset_service.update_or_create(subset, private=False, **kwargs)
        try:
            process_service = self._get_process_service()
            process = Process(
                name=unbound_process_name,
                prolog_procedure=f"HierarchyDeleteElements('{dimension_name}', '{hierarchy_name}', '{subset_name}');")
            success, status, error_log_file = process_service.execute_process_with_return(process, **kwargs)
            if not success:
                raise TM1pyException(f"Failed to delete elements through unbound process. Error: '{error_log_file}'")

        finally:
            subset_service.delete(subset_name, dimension_name, hierarchy_name, private=False, **kwargs)

    @require_version("11.4")
    def delete_edges(self, dimension_name: str, hierarchy_name: str, edges: Iterable[Tuple[str, str]] = None,
                     use_ti: bool = False, use_blob: bool = False, remove_blob: bool = True, **kwargs):
        if use_ti:
            return self.delete_edges_use_ti(dimension_name, hierarchy_name, edges, **kwargs)
            
        if use_blob:
            return self.delete_edges_use_blob(dimension_name, hierarchy_name, edges, remove_blob, **kwargs)
            
        h_service = self._get_hierarchy_service()
        h = h_service.get(dimension_name, hierarchy_name, **kwargs)
        for edge in edges:
            h.remove_edge(parent=edge[0], component=edge[1])
        h_service.update(h, **kwargs)

    def delete_edges_use_ti(self, dimension_name: str, hierarchy_name: str, edges: List[str] = None, **kwargs):
        if not edges:
            return

        def escape_single_quote(text):
            return text.replace("'", "''")

        statements = [
            f"HierarchyElementComponentDelete('{dimension_name}', '{hierarchy_name}', "
            f"'{escape_single_quote(parent)}', '{escape_single_quote(child)}');"
            for (parent, child)
            in edges
        ]

        unbound_process_name = self.suggest_unique_object_name()

        process_service = self._get_process_service()
        process = Process(
            name=unbound_process_name,
            prolog_procedure="\r\n".join(statements))
        success, status, error_log_file = process_service.execute_process_with_return(process, **kwargs)
        if not success:
            raise TM1pyException(f"Failed to delete edges through unbound process. Error: '{error_log_file}'")

    @require_data_admin
    @require_ops_admin
    def delete_edges_use_blob(self, dimension_name: str, hierarchy_name: str, edges: List[str] = None, remove_blob: bool = True, **kwargs):
        """
        Remove edges in TM1 via an unbound TI process having an uploaded CSV as data source
        :param dimension_name as str: dimension name
        :param hierarchy_name as str: hierarchy name
        :param edges as list: 
        :remove_blob as bool: remove the parent child file after use, default True
        :param kwargs:
        :return: Success: bool, Messages: list, ChangeSet: None
        """
        if not edges:
            return
            
        process_service = ProcessService(self._rest)
        file_service = FileService(self._rest)

        unique_name = self.suggest_unique_object_name()

        # Transform cells to format that's consumable for TI
        csv_content = StringIO()
        csv_writer = csv.writer(
            csv_content,
            delimiter=",",
            quoting=csv.QUOTE_ALL)
        csv_writer.writerows(
            list(edge)
            for edge 
            in edges)

        file_name = f'{unique_name}.csv'
        file_service.create(
            file_name=file_name,
            file_content=csv_content.getvalue().encode('utf-8'),
            **kwargs)

        try:
            # Create and execute unbound TI process to delete edges using blob file
            process = self._build_unwind_hierarchy_edges_from_blob_process(
                dimension_name=dimension_name,
                hierarchy_name=hierarchy_name,
                process_name=unique_name,
                blob_filename=file_name)

            success, status, log_file = process_service.execute_process_with_return(process=process, **kwargs)
            if not success:
                if status in ['HasMinorErrors']:
                    raise TM1pyWritePartialFailureException([status], [log_file], 1)
                else:
                    raise TM1pyWriteFailureException([status], [log_file])

        finally:
            if remove_blob:
                file_service.delete(file_name=file_name)

    def _build_unwind_hierarchy_edges_from_blob_process(self, dimension_name: str, hierarchy_name: str, process_name: str, blob_filename: str) -> Process:

        # v11 automatically adds blb file extensions to documents created via the contents api
        if not verify_version(required_version="12", version=self.version):
            blob_filename += ".blb"
        hierarchyupdate_process = Process(
            name=process_name,
            datasource_type='ASCII',
            datasource_ascii_header_records=0,
            datasource_data_source_name_for_server=f"{blob_filename}",
            datasource_data_source_name_for_client=f"{blob_filename}",
            datasource_ascii_delimiter_char=',',
            datasource_ascii_decimal_separator='.',
            datasource_ascii_thousand_separator='',
            datasource_ascii_quote_character='"')

        # Define encoding in Prolog section
        hierarchyupdate_process.prolog_procedure = f"""
        SetInputCharacterSet('TM1CS_UTF8');
         """
        parent_variable="vParent"
        child_variable="vChild"
        hierarchyupdate_process.add_variable(name=parent_variable, variable_type='String')
        hierarchyupdate_process.add_variable(name=child_variable, variable_type='String')

        # Write the statement for delete component in hierarchy
        delete_component = f"\rHierarchyElementComponentDelete('{dimension_name}', '{hierarchy_name}', {parent_variable}, {child_variable});"
 
        # Define Metadata section
        metadata_statement = delete_component
        hierarchyupdate_process.metadata_procedure = metadata_statement
        return hierarchyupdate_process
    
    def get_elements(self, dimension_name: str, hierarchy_name: str, **kwargs) -> List[Element]:
        url = format_url(
            "/Dimensions('{}')/Hierarchies('{}')/Elements?select=Name,Type",
            dimension_name,
            hierarchy_name)
        response = self._rest.GET(url, **kwargs)
        return [Element.from_dict(element) for element in response.json()["value"]]

    @require_pandas
    def get_elements_dataframe(self, dimension_name: str = None, hierarchy_name: str = None,
                               elements: Union[str, Iterable[str]] = None,
                               skip_consolidations: bool = True, attributes: Iterable[str] = None,
                               attribute_column_prefix: str = "", skip_parents: bool = False,
                               level_names: List[str] = None, parent_attribute: str = None,
                               skip_weights: bool = False, use_blob: bool = False, allow_empty_alias: bool = True,
                               attribute_suffix: bool = False, element_type_column: str = 'Type',
                               **kwargs) -> 'pd.DataFrame':
        """

        :param dimension_name: Name of the dimension. Can be derived from elements MDX
        :param hierarchy_name: Name of the hierarchy in the dimension.Can be derived from elements MDX
        :param elements: Selection of members. Iterable or valid MDX string
        :param skip_consolidations: Boolean flag to skip consolidations
        :param attributes: Selection of attributes. Iterable. If None retrieve all.
        :param attribute_column_prefix: string to prefix attribute colums to avoid name conflicts
        :param level_names: List of labels for parent columns. If None use level names from TM1.
        :param skip_parents: Boolean Flag to skip parent columns.
        :param parent_attribute: Attribute to be displayed in parent columns. If None, parent name is used.
        :param skip_weights: include weight columns
        :param use_blob: Up to 40% better performance and lower memory footprint in any case. Requires admin permissions
        :param allow_empty_alias: False if empty alias values should be substituted with element names instead
        :param attribute_suffix: True if attribute columns should have ':a', ':s' or ':n' suffix
        :param element_type_column: The column name in the df which specifies which element is which type.
        :return: pandas DataFrame
        """

        if isinstance(elements, str) and not all([dimension_name, hierarchy_name]):
            record = self.execute_set_mdx(
                mdx=elements,
                top_records=1,
                member_properties=["UniqueName"],
                parent_properties=None,
                element_properties=None)

            if not record:
                raise ValueError(f"member_selection invalid: '{elements}'")

            unique_name = record[0][0]['UniqueName']
            dimension_name, hierarchy_name, _ = dimension_hierarchy_element_tuple_from_unique_name(unique_name)

        if elements is None or not any(elements):
            elements = f"{{ [{dimension_name}].[{hierarchy_name}].Members }}"
            if skip_consolidations:
                elements = f"{{ Tm1FilterByLevel({elements}, 0) }}"

        if not isinstance(elements, str):
            if isinstance(elements, Iterable):
                elements = "{" + ",".join(
                    f"[{dimension_name}].[{hierarchy_name}].[{member}]" for member in elements) + "}"
            else:
                raise ValueError("Argument 'element_selection' must be None or str")

        if not self.attribute_cube_exists(dimension_name):
            raise RuntimeError(self.ELEMENT_ATTRIBUTES_PREFIX + dimension_name + " cube must exist")

        members = [tupl[0] for tupl in self.execute_set_mdx(
            mdx=elements,
            element_properties=None,
            member_properties=("Name", "UniqueName"),
            parent_properties=None)]

        element_types = self.get_element_types(
            dimension_name=dimension_name,
            hierarchy_name=hierarchy_name,
            skip_consolidations=skip_consolidations)

        df = pd.DataFrame(
            data=[(member["Name"], element_types[member["Name"]])
                  for member
                  in members
                  if member["Name"] in element_types],
            dtype=str,
            columns=[dimension_name, element_type_column])

        calculated_members_definition = list()
        calculated_members_selection = list()
        levels_dict = {}
        if not skip_parents:
            levels = self.get_levels_count(dimension_name, hierarchy_name)

            # Generic Level names can't be used directly as a Calculated Member name as they conflict with an internal name
            # Therefore, we create a map that relates the level name to the calculated member name L000 = level000
            if not level_names:
                level_names = self.get_level_names(dimension_name, hierarchy_name, descending=True)
                level_calculated_member_names = []

                # Create a map of MDX Calculated Member Names and Desired Pandas Names
                for level in reversed(range(levels)):
                    level_calculated_member_names.append(f"L{str(level).zfill(3)}")
                all_level_dict = OrderedDict(zip(level_calculated_member_names, level_names))

            # if a specific parent names are provided the calculated member name is = to the data frame column name
            else:
                all_level_dict = OrderedDict(zip(level_names, level_names))

            # Remove the highest level (leafs) to create proper MDX calculated members
            levels_dict = {k: all_level_dict[k] for k in list(all_level_dict)[1:]}

            # iterate the map of levels to create an MDX calculation and a related column axis definition
            parent_members = list()
            weight_members = list()
            depth = 0
            for calculated_name, level_name in levels_dict.items():
                depth += 1
                name_or_attribute = f"Properties('{parent_attribute}')" if parent_attribute else "NAME"
                if not verify_version(required_version='12', version=self.version):
                    member = f"""
                    MEMBER [{self.ELEMENT_ATTRIBUTES_PREFIX + dimension_name}].[{calculated_name}] 
                    AS [{dimension_name}].[{hierarchy_name}].CurrentMember.{'Parent.' * depth}{name_or_attribute}
                    """
                else:
                    member = f"""
                    MEMBER [{self.ELEMENT_ATTRIBUTES_PREFIX + dimension_name}].[{calculated_name}] 
                    AS [{dimension_name}].[{hierarchy_name}].CurrentMember.{'Parent.' * depth}PROPERTIES('{name_or_attribute}')
                    """
                calculated_members_definition.append(member)

                parent_members.append(f"[{self.ELEMENT_ATTRIBUTES_PREFIX + dimension_name}].[{calculated_name}]")

                if not skip_weights:
                    if not verify_version(required_version='12', version=self.version):
                        member_weight = f"""
                        MEMBER [{self.ELEMENT_ATTRIBUTES_PREFIX + dimension_name}].[{level_name}_Weight] 
                        AS IIF(
                        [{dimension_name}].[{hierarchy_name}].CurrentMember.{'Parent.' * (depth - 1)}Properties('MEMBER_WEIGHT') = '',
                        0,
                        [{dimension_name}].[{hierarchy_name}].CurrentMember.{'Parent.' * (depth - 1)}Properties('MEMBER_WEIGHT'))
                        """
                    else:
                        member_weight = f"""
                        MEMBER [{self.ELEMENT_ATTRIBUTES_PREFIX + dimension_name}].[{level_name}_Weight]
                        AS IIF(
                        [{dimension_name}].[{hierarchy_name}].CurrentMember.{'Parent.' * ( depth - 1)}Properties('MEMBER_WEIGHT') = '',
                        0,
                        [{dimension_name}].[{hierarchy_name}].CurrentMember.{'Parent.' * ( depth - 1)}Properties('MEMBER_WEIGHT'))
                        """
                    calculated_members_definition.append(member_weight)

                    weight_members.append(
                        f"[{self.ELEMENT_ATTRIBUTES_PREFIX + dimension_name}].[{level_name}_Weight]")

            calculated_members_selection.extend(weight_members)
            calculated_members_selection.extend(parent_members)

        if attributes is None:
            column_selection = "{Tm1SubsetAll([" + self.ELEMENT_ATTRIBUTES_PREFIX + dimension_name + "])}"
        else:
            column_selection = "{" + ",".join(
                "[" + self.ELEMENT_ATTRIBUTES_PREFIX + dimension_name + "].[" + attribute + "]"
                for attribute
                in attributes) + "}"

        if calculated_members_selection:
            if column_selection == "{}":
                column_selection = "{" + ",".join(calculated_members_selection) + "}"
            else:
                column_selection = column_selection + " + {" + ",".join(calculated_members_selection) + "}"

        mdx_with_block = ""
        if calculated_members_definition:
            mdx_with_block = "WITH " + " ".join(calculated_members_definition)

        mdx = f"""
        {mdx_with_block}
        SELECT
        {{ {elements} }} ON ROWS,
        {{ {column_selection} }} ON COLUMNS
        FROM [{self.ELEMENT_ATTRIBUTES_PREFIX + dimension_name}]  
        """

        cell_service = self._get_cell_service()

        # override column names. hierarchy name with dimension and prefix attributes
        element_attributes = self.get_element_attributes(dimension_name, hierarchy_name)
        column_renaming = dict()
        if attribute_column_prefix or attribute_suffix:
            column_renaming = {
                ea.name: f"{attribute_column_prefix}{ea.name}" + (
                    f":{ea.attribute_type.lower()[0]}"
                    if attribute_suffix
                    else "")
                for ea
                in element_attributes}

        # responses are similar but not equivalent.
        # Therefor only use execute_mdx_dataframe when use_blob is True
        if use_blob:
            raw_csv = cell_service.execute_mdx_csv(
                mdx=mdx,
                skip_zeros=False,
                skip_consolidated_cells=False,
                skip_rule_derived_cells=False,
                line_separator="\r\n",
                value_separator="~",
                use_blob=True,
                **kwargs)

            df_data = pd.read_csv(StringIO(raw_csv), sep='~', na_filter=False, dtype={0: str})

            # Use _group to avoid aggregation of multiple members into one df record
            # example: element A is part of multiple consolidations resulting df must have multiple records for A
            unique_values_count = df_data['}ElementAttributes_' + dimension_name].nunique()
            df_data['_group'] = (df_data.index // unique_values_count) + 1

            # pivot the dataframe
            df_data = df_data.pivot_table(
                index=[dimension_name, '_group'],
                columns='}ElementAttributes_' + dimension_name,
                values='Value',
                aggfunc='first',
                sort=False)

            # override column names. hierarchy name with dimension and prefix attributes
            df_data.columns = [column_renaming.get(col, col) for col in df_data.columns]
            df_data = df_data.reset_index()

            # Drop the group key
            df_data = df_data.fillna("").drop(columns='_group')

        else:
            df_data = cell_service.execute_mdx_dataframe_shaped(mdx, **kwargs)

            # override column names. hierarchy name with dimension and prefix attributes
            df_data.columns = [df_data.columns[0]] + [column_renaming.get(col, col) for col in df_data.columns[1:]]

        if levels_dict:
            # rename level names to conform sto standard levels "1" -> "level001"
            df_data.rename(columns=levels_dict, inplace=True)

        # format weights
        # Find columns with certain names
        cols_to_format = [col for col in df_data.columns if '_Weight' in col]

        # format the columns
        df_data[cols_to_format] = df_data[cols_to_format].apply(pd.to_numeric)
        df_data[cols_to_format] = df_data[cols_to_format].applymap(lambda x: '{:.6f}'.format(x))

        # override colum types
        element_attributes = self.get_element_attributes(dimension_name, hierarchy_name)
        attribute_column_types = {
            ea.name: 'float' if ea.attribute_type == 'Numeric' else 'str'
            for ea
            in element_attributes
            if ea.name in df_data.columns}
        df_data = df_data.astype(attribute_column_types)

        # substitute empty strings with element name if empty alias is not allowed
        if not allow_empty_alias:
            alias_attributes = [
                ea.name
                for ea in element_attributes
                if ea.attribute_type == 'Alias' and ea.name in df_data.columns]

            for col in alias_attributes:
                df_data[col] = np.where(df_data[col] == '', df_data[dimension_name], df_data[col])

        # shift levels to right hand side
        if not skip_parents:
            # skip max level (= leaves)
            level_columns = level_names[1:]

            # iterative approach
            for _ in level_columns:

                rows_to_shift = df_data[df_data[level_columns[-1]].isin(['', None])].index
                if rows_to_shift.empty:
                    break
                shifted_cols = df_data.iloc[rows_to_shift, -len(level_columns):].shift(1, axis=1)
                df_data.iloc[rows_to_shift, -len(level_columns):] = shifted_cols

                # also shift weight columns
                if not skip_weights:
                    shifted_cols = df_data.iloc[
                                   rows_to_shift,
                                   -len(level_columns) * 2:-len(level_columns)].shift(1, axis=1)

                    df_data.iloc[rows_to_shift, -len(level_columns) * 2:-len(level_columns)] = shifted_cols

            df_data.iloc[:, -len(level_columns):] = df_data.iloc[:, -len(level_columns):].fillna('')
            if not skip_weights:
                df_data.iloc[:, -len(level_columns) * 2:-len(level_names)] = df_data.iloc[
                                                                             :,
                                                                             -len(level_columns) * 2:
                                                                             -len(level_names)].fillna(0)

        return pd.merge(df, df_data, on=dimension_name).drop_duplicates()

    def get_edges(self, dimension_name: str, hierarchy_name: str, **kwargs) -> Dict[Tuple[str, str], int]:
        url = format_url(
            "/Dimensions('{}')/Hierarchies('{}')/Edges?select=ParentName,ComponentName,Weight",
            dimension_name,
            hierarchy_name)
        response = self._rest.GET(url, **kwargs)

        return {(edge["ParentName"], edge["ComponentName"]): edge["Weight"] for edge in response.json()["value"]}

    def get_leaf_elements(self, dimension_name: str, hierarchy_name: str, **kwargs) -> List[Element]:
        url = format_url(
            "/Dimensions('{}')/Hierarchies('{}')/Elements?$expand=*&$filter=Type ne 3",
            dimension_name,
            hierarchy_name)
        response = self._rest.GET(url, **kwargs)
        return [Element.from_dict(element) for element in response.json()["value"]]

    def get_leaf_element_names(self, dimension_name: str, hierarchy_name: str, **kwargs) -> List[str]:
        url = format_url("/Dimensions('{}')/Hierarchies('{}')/Elements?$select=Name&$filter=Type ne 3",
                         dimension_name,
                         hierarchy_name)
        response = self._rest.GET(url, **kwargs)
        return [e["Name"] for e in response.json()['value']]

    def get_consolidated_elements(self, dimension_name: str, hierarchy_name: str, **kwargs) -> List[Element]:
        url = format_url(
            "/Dimensions('{}')/Hierarchies('{}')/Elements?$expand=*&$filter=Type eq 3",
            dimension_name,
            hierarchy_name)
        response = self._rest.GET(url, **kwargs)
        return [Element.from_dict(element) for element in response.json()["value"]]

    def get_consolidated_element_names(self, dimension_name: str, hierarchy_name: str, **kwargs) -> List[str]:
        url = format_url("/Dimensions('{}')/Hierarchies('{}')/Elements?$select=Name&$filter=Type eq 3",
                         dimension_name,
                         hierarchy_name)
        response = self._rest.GET(url, **kwargs)
        return [e["Name"] for e in response.json()['value']]

    def get_numeric_elements(self, dimension_name: str, hierarchy_name: str, **kwargs) -> List[Element]:
        url = format_url(
            "/Dimensions('{}')/Hierarchies('{}')/Elements?$expand=*&$filter=Type eq 1",
            dimension_name,
            hierarchy_name)
        response = self._rest.GET(url, **kwargs)
        return [Element.from_dict(element) for element in response.json()["value"]]

    def get_numeric_element_names(self, dimension_name: str, hierarchy_name: str, **kwargs) -> List[str]:
        url = format_url("/Dimensions('{}')/Hierarchies('{}')/Elements?$select=Name&$filter=Type eq 1",
                         dimension_name,
                         hierarchy_name)
        response = self._rest.GET(url, **kwargs)
        return [e["Name"] for e in response.json()['value']]

    def get_string_elements(self, dimension_name: str, hierarchy_name: str, **kwargs) -> List[Element]:
        url = format_url(
            "/Dimensions('{}')/Hierarchies('{}')/Elements?$expand=*&$filter=Type eq 2",
            dimension_name,
            hierarchy_name)
        response = self._rest.GET(url, **kwargs)
        return [Element.from_dict(element) for element in response.json()["value"]]

    def get_string_element_names(self, dimension_name: str, hierarchy_name: str, **kwargs) -> List[str]:
        url = format_url("/Dimensions('{}')/Hierarchies('{}')/Elements?$select=Name&$filter=Type eq 2",
                         dimension_name,
                         hierarchy_name)
        response = self._rest.GET(url, **kwargs)
        return [e["Name"] for e in response.json()['value']]

    def get_element_names(self, dimension_name: str, hierarchy_name: str, **kwargs) -> List[str]:
        """ Get all element names

        :param dimension_name:
        :param hierarchy_name:
        :return: Generator of element-names
        """
        url = format_url(
            "/Dimensions('{}')/Hierarchies('{}')/Elements?$select=Name",
            dimension_name,
            hierarchy_name)
        response = self._rest.GET(url, **kwargs)
        return [e["Name"] for e in response.json()['value']]

    def get_number_of_elements(self, dimension_name: str, hierarchy_name: str, **kwargs) -> int:
        url = format_url(
            "/Dimensions('{}')/Hierarchies('{}')/Elements/$count",
            dimension_name,
            hierarchy_name)
        response = self._rest.GET(url, **kwargs)
        return int(response.text)

    def get_number_of_consolidated_elements(self, dimension_name: str, hierarchy_name: str, **kwargs) -> int:
        url = format_url(
            "/Dimensions('{}')/Hierarchies('{}')/Elements/$count?$filter=Type eq 3",
            dimension_name,
            hierarchy_name)
        response = self._rest.GET(url, **kwargs)
        return int(response.text)

    def get_number_of_leaf_elements(self, dimension_name: str, hierarchy_name: str, **kwargs) -> int:
        url = format_url(
            "/Dimensions('{}')/Hierarchies('{}')/Elements/$count?$filter=Type ne 3",
            dimension_name,
            hierarchy_name)
        response = self._rest.GET(url, **kwargs)
        return int(response.text)

    def get_number_of_numeric_elements(self, dimension_name: str, hierarchy_name: str, **kwargs) -> int:
        url = format_url(
            "/Dimensions('{}')/Hierarchies('{}')/Elements/$count?$filter=Type eq 1",
            dimension_name,
            hierarchy_name)
        response = self._rest.GET(url, **kwargs)
        return int(response.text)

    def get_number_of_string_elements(self, dimension_name: str, hierarchy_name: str, **kwargs) -> int:
        url = format_url(
            "/Dimensions('{}')/Hierarchies('{}')/Elements/$count?$filter=Type eq 2",
            dimension_name,
            hierarchy_name)
        response = self._rest.GET(url, **kwargs)
        return int(response.text)

    def get_all_leaf_element_identifiers(self, dimension_name: str, hierarchy_name: str,
                                         **kwargs) -> CaseAndSpaceInsensitiveSet:
        """ Get all element names and alias values for leaf elements in a hierarchy

        :param dimension_name:
        :param hierarchy_name:
        :return:
        """
        mdx_elements = f"{{ Tm1FilterByLevel ( {{ Tm1SubsetAll ([{dimension_name}].[{hierarchy_name}]) }} , 0 ) }}"
        return self.get_element_identifiers(dimension_name, hierarchy_name, mdx_elements, **kwargs)

    def get_elements_by_level(self, dimension_name: str, hierarchy_name: str, level: int, **kwargs) -> List[str]:
        """ Get all element names by level in a hierarchy

        :param dimension_name: Name of the dimension
        :param hierarchy_name: Name of the hierarchy
        :param level: Level to filter
        :return: List of element names
        """
        url = format_url(
            "/Dimensions('{}')/Hierarchies('{}')/Elements?$select=Name&$filter=Level eq {}",
            dimension_name,
            hierarchy_name,
            str(level))
        response = self._rest.GET(url, **kwargs)
        return [e["Name"] for e in response.json()['value']]

    def get_elements_filtered_by_wildcard(self, dimension_name: str, hierarchy_name: str,
                                          wildcard: str, level: int = None, **kwargs) -> List[str]:
        """ Get all element names filtered by wildcard (CaseAndSpaceInsensitive) and level in a hierarchy

        :param dimension_name: Name of the dimension
        :param hierarchy_name: Name of the hierarchy
        :param wildcard: wildcard to filter
        :param level: Level to filter
        :return: List of element names
        """
        filter_elements = format_url("contains(tolower(replace(Name,' ','')),tolower(replace('{}',' ', '')))", wildcard)
        if level is not None:
            filter_elements = filter_elements + f" and Level eq {level}"
        url = format_url(
            "/Dimensions('{}')/Hierarchies('{}')/Elements?$select=Name&$filter=" + filter_elements,
            dimension_name,
            hierarchy_name)
        response = self._rest.GET(url, **kwargs)
        return [e["Name"] for e in response.json()['value']]

    def get_all_element_identifiers(self, dimension_name: str, hierarchy_name: str,
                                    **kwargs) -> CaseAndSpaceInsensitiveSet:
        """ Get all element names and alias values in a hierarchy

        :param dimension_name:
        :param hierarchy_name:
        :return:
        """

        mdx_elements = f"{{ Tm1SubsetAll ([{dimension_name}].[{hierarchy_name}]) }}"
        return self.get_element_identifiers(dimension_name, hierarchy_name, mdx_elements, **kwargs)

    def get_element_identifiers(self, dimension_name: str, hierarchy_name: str,
                                elements: Union[str, List[str]], **kwargs) -> CaseAndSpaceInsensitiveSet:
        """ Get all element names and alias values for a set of elements in a hierarchy

        :param dimension_name:
        :param hierarchy_name:
        :param elements: MDX (Set) expression or iterable of elements
        :return:
        """

        alias_attributes = self.get_alias_element_attributes(dimension_name, hierarchy_name, **kwargs)

        if isinstance(elements, str):
            mdx_element_selection = elements
        else:
            mdx_element_selection = ",".join(build_element_unique_names(
                [dimension_name] * len(elements),
                elements,
                [hierarchy_name] * len(elements)))

        if not alias_attributes:
            result = self.execute_set_mdx(
                mdx=mdx_element_selection,
                member_properties=["Name"],
                parent_properties=None,
                element_properties=None)
            return CaseAndSpaceInsensitiveSet([record[0]["Name"] for record in result])

        mdx = """
             SELECT
             {{ {elem_mdx} }} ON ROWS, 
             {{ {attr_mdx} }} ON COLUMNS
             FROM [}}ElementAttributes_{dim}]
             """.format(
            elem_mdx=mdx_element_selection,
            attr_mdx=",".join(build_element_unique_names(
                ["}ElementAttributes_" + dimension_name] * len(alias_attributes), alias_attributes)),
            dim=dimension_name)
        return self._retrieve_mdx_rows_and_cell_values_as_string_set(mdx, **kwargs)

    def get_attribute_of_elements(self, dimension_name: str, hierarchy_name: str, attribute: str,
                                  elements: Union[str, List[str]] = None, exclude_empty_cells: bool = True,
                                  element_unique_names: bool = False) -> dict:
        """
         Get element name and attribute value for a set of elements in a hierarchy

        :param dimension_name:
        :param hierarchy_name:
        :param attribute: Name of the Attribute
        :param elements:  MDX (Set) expression or iterable of elements
        :param exclude_empty_cells: Boolean
        :param element_unique_names: Boolean
        :return: Dict {'01':'Jan', '02':'Feb'}
        """
        if elements is None or not any(elements):
            elements = self.get_element_names(dimension_name=dimension_name, hierarchy_name=hierarchy_name)

        if isinstance(elements, str):
            mdx_element_selection = elements
        else:
            mdx_element_selection = ",".join(build_element_unique_names(
                [dimension_name] * len(elements),
                elements,
                [hierarchy_name] * len(elements)))
        mdx = """
             SELECT
             {{ {elem_mdx} }} ON ROWS, 
             {{ {attr_mdx} }} ON COLUMNS
             FROM [}}ElementAttributes_{dim}]
             """.format(
            elem_mdx=mdx_element_selection,
            attr_mdx="[}ElementAttributes_" + dimension_name + "].[" + attribute + "]",
            dim=dimension_name)
        rows_and_values = self._retrieve_mdx_rows_and_values(mdx, element_unique_names=element_unique_names)
        return self._extract_dict_from_rows_and_values(rows_and_values, exclude_empty_cells=exclude_empty_cells)

    @require_version("11.8.023")
    def element_lock(self, dimension_name: str, hierarchy_name: str, element_name: str, **kwargs) -> Response:
        """ Lock element
        :param dimension_name: Name of dimension.
        :param hierarchy_name: Name of hierarchy.
        :param element_name: Name of element to lock.
        :return: response
        """
        url = format_url(
            "/Dimensions('{}')/Hierarchies('{}')/Elements('{}')/tm1.Lock",
            dimension_name,
            hierarchy_name,
            element_name)
        return self._rest.POST(url, '', **kwargs)

    @require_version("11.8.023")
    def element_unlock(self, dimension_name: str, hierarchy_name: str, element_name: str, **kwargs) -> Response:
        """ Unlock element
        :param dimension_name: Name of dimension.
        :param hierarchy_name: Name of hierarchy.
        :param element_name: Name of element to unlock.
        :return: response
        """
        url = format_url(
            "/Dimensions('{}')/Hierarchies('{}')/Elements('{}')/tm1.Unlock",
            dimension_name,
            hierarchy_name,
            element_name)
        return self._rest.POST(url, '', **kwargs)
    
    @staticmethod
    def _extract_dict_from_rows_and_values(
            rows_and_values: CaseAndSpaceInsensitiveTuplesDict,
            exclude_empty_cells: bool = True) -> dict:
        """ Helper function for get_element_by_attribute method

        :param rows_and_values:
        :param exclude_empty_cells: Boolean
        :return: Dictionary of Element:Attribute_Value
        """
        result_set = dict()
        for row_elements, cell_values in rows_and_values.items():
            for row_element in row_elements:
                for cell_value in cell_values:
                    if cell_value or not exclude_empty_cells:
                        result_set[row_element] = cell_value
        return result_set

    def get_level_names(self, dimension_name: str, hierarchy_name: str, descending: bool = True, **kwargs) -> List[str]:
        url = format_url(
            "/Dimensions('{}')/Hierarchies('{}')/Levels?$select=Name",
            dimension_name,
            hierarchy_name)
        response = self._rest.GET(url, **kwargs)
        if descending:
            return [level["Name"] for level in reversed(response.json()["value"])]
        else:
            return [level["Name"] for level in response.json()["value"]]

    def get_levels_count(self, dimension_name: str, hierarchy_name: str, **kwargs) -> int:
        url = format_url("/Dimensions('{}')/Hierarchies('{}')/Levels/$count", dimension_name, hierarchy_name)
        response = self._rest.GET(url, **kwargs)
        return int(response.text)

    def get_element_types(self, dimension_name: str, hierarchy_name: str,
                          skip_consolidations: bool = False, **kwargs) -> CaseAndSpaceInsensitiveDict:
        url = format_url(
            "/Dimensions('{}')/Hierarchies('{}')/Elements?$select=Name,Type",
            dimension_name,
            hierarchy_name)
        if skip_consolidations:
            url += "&$filter=Type ne 3"
        response = self._rest.GET(url, **kwargs)

        result = CaseAndSpaceInsensitiveDict()
        for element in response.json()["value"]:
            result[element['Name']] = element["Type"]
        return result

    def get_element_types_from_all_hierarchies(
            self, dimension_name: str, skip_consolidations: bool = False, **kwargs) -> CaseAndSpaceInsensitiveDict:
        url = format_url(
            "/Dimensions('{}')?$expand=Hierarchies($select=Elements;$expand=Elements($select=Name,Type",
            dimension_name)
        url += ";$filter=Type ne 3))" if skip_consolidations else "))"
        response = self._rest.GET(url, **kwargs)

        result = CaseAndSpaceInsensitiveDict()
        for hierarchy in response.json()["Hierarchies"]:
            for element in hierarchy["Elements"]:
                result[element['Name']] = element["Type"]
        return result

    def attribute_cube_exists(self, dimension_name: str, **kwargs) -> bool:
        url = format_url("/Cubes('{}')", self.ELEMENT_ATTRIBUTES_PREFIX + dimension_name)
        return self._exists(url, **kwargs)

    def _retrieve_mdx_rows_and_cell_values_as_string_set(self, mdx: str, exclude_empty_cells=True, **kwargs):
        from TM1py import CellService
        return CellService(self._rest).execute_mdx_rows_and_values_string_set(mdx, exclude_empty_cells, **kwargs)

    def _retrieve_mdx_rows_and_values(self, mdx: str, **kwargs):
        from TM1py import CellService
        return CellService(self._rest).execute_mdx_rows_and_values(mdx, **kwargs)

    def get_alias_element_attributes(self, dimension_name: str, hierarchy_name: str, **kwargs) -> List[str]:
        """

        :param dimension_name:
        :param hierarchy_name:
        :return:
        """
        attributes = self.get_element_attributes(dimension_name, hierarchy_name, **kwargs)
        return [attr.name
                for attr
                in attributes if attr.attribute_type == 'Alias']

    def get_element_attributes(self, dimension_name: str, hierarchy_name: str, **kwargs) -> List[ElementAttribute]:
        """ Get element attributes from hierarchy

        :param dimension_name:
        :param hierarchy_name:
        :return:
        """
        url = format_url(
            "/Dimensions('{}')/Hierarchies('{}')/ElementAttributes",
            dimension_name,
            hierarchy_name)
        response = self._rest.GET(url, **kwargs)
        element_attributes = [ElementAttribute.from_dict(ea) for ea in response.json()['value']]
        return element_attributes

    def get_element_attribute_names(self, dimension_name: str, hierarchy_name: str, **kwargs) -> List[str]:
        """ Get element attributes from hierarchy

        :param dimension_name:
        :param hierarchy_name:
        :return:
        """
        url = format_url(
            "/Dimensions('{}')/Hierarchies('{}')/ElementAttributes?$select=Name",
            dimension_name,
            hierarchy_name)
        response = self._rest.GET(url, **kwargs)
        return [ea["Name"] for ea in response.json()['value']]

    def get_elements_filtered_by_attribute(self, dimension_name: str, hierarchy_name: str, attribute_name: str,
                                           attribute_value: Union[str, float], **kwargs) -> List[str]:
        """ Get all elements from a hierarchy with given attribute value

        :param dimension_name:
        :param hierarchy_name:
        :param attribute_name:
        :param attribute_value:
        :return: List of element names
        """
        if not self.exists(f"}}ElementAttributes_{dimension_name}",
                           f"}}ElementAttributes_{dimension_name}",
                           attribute_name):
            raise RuntimeError(f"Attribute '{attribute_name}' does not exist in Dimension '{dimension_name}'")

        if isinstance(attribute_value, str):
            mdx = (
                f"{{FILTER({{TM1SUBSETALL([{dimension_name}].[{hierarchy_name}])}},"
                f"[{dimension_name}].[{hierarchy_name}].CURRENTMEMBER.PROPERTIES(\"{attribute_name}\") = \"{attribute_value}\")}}")
        else:
            mdx = (
                f"{{FILTER({{TM1SUBSETALL([{dimension_name}].[{hierarchy_name}])}},"
                f"(IIF([{dimension_name}].[{hierarchy_name}].CURRENTMEMBER.PROPERTIES(\"{attribute_name}\")=\"\", 0.0," 
                f"STRTOVALUE([{dimension_name}].[{hierarchy_name}].CURRENTMEMBER.PROPERTIES(\"{attribute_name}\"))) = 1))}}"
            )

        elems = self.execute_set_mdx(
            mdx=mdx,
            member_properties=["Name"],
            parent_properties=None,
            element_properties=None)
        return [elem[0]["Name"] for elem in elems]

    def create_element_attribute(self, dimension_name: str, hierarchy_name: str, element_attribute: ElementAttribute,
                                 **kwargs) -> Response:
        """ like AttrInsert

        :param dimension_name:
        :param hierarchy_name:
        :param element_attribute: instance of TM1py.ElementAttribute
        :return:
        """
        url = format_url(
            "/Dimensions('{}')/Hierarchies('{}')/ElementAttributes",
            dimension_name,
            hierarchy_name)
        return self._rest.POST(url, element_attribute.body, **kwargs)

    def delete_element_attribute(self, dimension_name: str, hierarchy_name: str, element_attribute: str,
                                 **kwargs) -> Response:
        """ like AttrDelete

        :param dimension_name:
        :param hierarchy_name:
        :param element_attribute: instance of TM1py.ElementAttribute
        :return:
        """
        url = format_url(
            "/Dimensions('}}ElementAttributes_{}')/Hierarchies('}}ElementAttributes_{}')/Elements('{}')",
            dimension_name,
            hierarchy_name,
            element_attribute)
        try:
            return self._rest.DELETE(url, **kwargs)

        # Fail silently if attribute hierarchy or attribute doesn't exist
        except TM1pyRestException as ex:
            if not ex.status_code == 404:
                raise ex

    def get_leaves_under_consolidation(self, dimension_name: str, hierarchy_name: str, consolidation: str,
                                       max_depth: int = None, **kwargs) -> List[str]:
        """ Get all leaves under a consolidated element

        :param dimension_name: name of dimension
        :param hierarchy_name: name of hierarchy
        :param consolidation: name of consolidated Element
        :param max_depth: 99 if not passed
        :return:
        """
        return self.get_members_under_consolidation(dimension_name, hierarchy_name, consolidation, max_depth, True,
                                                    **kwargs)

    def get_edges_under_consolidation(self, dimension_name: str, hierarchy_name: str, consolidation: str,
                                      max_depth: int = None, **kwargs) -> List[str]:
        """ Get all members under a consolidated element

        :param dimension_name: name of dimension
        :param hierarchy_name: name of hierarchy
        :param consolidation: name of consolidated Element
        :param max_depth: 99 if not passed
        :return:
        """
        depth = max_depth or 99

        # edges to return
        edges = CaseAndSpaceInsensitiveTuplesDict()

        # build url
        bare_url = "/Dimensions('{}')/Hierarchies('{}')/Elements('{}')?"
        url = format_url(bare_url, dimension_name, hierarchy_name, consolidation)
        for d in range(depth):
            if d == 0:
                url += "$select=Edges&$expand=Edges($expand=Component("
            else:
                url += "$select=Edges;$expand=Edges($expand=Component("

        url = url[:-1] + ")" * (depth * 2 - 1)

        response = self._rest.GET(url, **kwargs)
        consolidation_tree = response.json()

        # recursive function to parse consolidation sub_tree
        def get_edges(sub_trees):
            for sub_tree in sub_trees:
                edges[sub_tree["ParentName"], sub_tree["ComponentName"]] = sub_tree["Weight"]

                if "Edges" not in sub_tree["Component"]:
                    continue

                get_edges(sub_trees=sub_tree["Component"]["Edges"])

        get_edges(consolidation_tree["Edges"])
        return edges

    def get_members_under_consolidation(self, dimension_name: str, hierarchy_name: str, consolidation: str,
                                        max_depth: int = None, leaves_only: bool = False, **kwargs) -> List[str]:
        """ Get all members under a consolidated element

        :param dimension_name: name of dimension
        :param hierarchy_name: name of hierarchy
        :param consolidation: name of consolidated Element
        :param max_depth: 99 if not passed
        :param leaves_only: Only Leaf Elements or all Elements
        :return:
        """
        depth = max_depth - 1 if max_depth else 99
        # members to return
        members = []
        # build url
        bare_url = "/Dimensions('{}')/Hierarchies('{}')/Elements('{}')?$select=Name,Type&$expand=Components("
        url = format_url(bare_url, dimension_name, hierarchy_name, consolidation)
        for _ in range(depth):
            url += "$select=Name,Type;$expand=Components("
        url = url[:-1] + ")" * depth

        response = self._rest.GET(url, **kwargs)
        consolidation_tree = response.json()

        # recursive function to parse consolidation_tree
        def get_members(element):
            if element["Type"] == "Numeric":
                members.append(element["Name"])
            elif element["Type"] == "Consolidated":
                if "Components" in element:
                    for component in element["Components"]:
                        if not leaves_only and component["Type"] == "Consolidated":
                            members.append(component["Name"])
                        get_members(component)

        get_members(consolidation_tree)
        return members

    def execute_set_mdx_element_names(
        self, mdx: str, top_records: Optional[int] = None, **kwargs
    ) -> List:
        """
        :method to execute an MDX statement against a dimension and get a list with element names back
        :param mdx: valid dimension mdx statement
        :param top_records: number of records to return, default: all elements no limit
        :return: list of element names
        """
        elements = self.execute_set_mdx(
            mdx,
            member_properties=["Name"],
            parent_properties=None,
            element_properties=None,
        )
        return [element[0]["Name"] for element in elements]

    def execute_set_mdx(
            self,
            mdx: str,
            top_records: Optional[int] = None,
            member_properties: Optional[Iterable[str]] = ('Name', 'Weight'),
            parent_properties: Optional[Iterable[str]] = ('Name', 'UniqueName'),
            element_properties: Optional[Iterable[str]] = ('Type', 'Level'),
            **kwargs) -> List:
        """
        :method to execute an MDX statement against a dimension
        :param mdx: valid dimension mdx statement
        :param top_records: number of records to return, default: all elements no limit
        :param member_properties: list of member properties (e.g., Name, UniqueName, Type, Weight, Attributes/Color)
        to return, will always return the Name property
        :param parent_properties: list of parent properties (e.g., Name, UniqueName, Type, Weight, Attributes/Color)
         to return, can be None or empty
        :param element_properties: list of element properties (e.g., Name, UniqueName, Type, Level, Index,
        Attributes/Color) to return, can be empty
        :return: dictionary of members, unique names, weights, types, and parents
        """

        top = f"$top={top_records};" if top_records else ""

        if not member_properties:
            member_properties = ['Name']

        # drop spaces in Attribute names
        else:
            member_properties = [
                member_property.replace(' ', '') if member_property.startswith('Attributes/') else member_property
                for member_property
                in member_properties]

        if element_properties:
            element_properties = [
                element_property.replace(' ', '') if element_property.startswith('Attributes/') else element_property
                for element_property
                in element_properties]

        if parent_properties:
            parent_properties = [
                parent_property.replace(' ', '') if parent_property.startswith('Attributes/') else parent_property
                for parent_property
                in parent_properties]

        member_properties = ",".join(member_properties)
        select_member_properties = f'$select={member_properties}'

        properties_to_expand = []
        if parent_properties:
            parent_properties = ",".join(parent_properties)
            select_parent_properties = f'Parent($select={parent_properties})'
            properties_to_expand.append(select_parent_properties)

        if element_properties:
            element_properties = ",".join(element_properties)
            select_element_properties = f'Element($select={element_properties})'
            properties_to_expand.append(select_element_properties)

        if properties_to_expand:
            expand_properties = f';$expand={",".join(properties_to_expand)}'
        else:
            expand_properties = ""

        url = f'/ExecuteMDXSetExpression?$expand=Tuples({top}' \
              f'$expand=Members({select_member_properties}' \
              f'{expand_properties}))'

        payload = {"MDX": mdx}
        response = self._rest.POST(url, json.dumps(payload, ensure_ascii=False), **kwargs)
        raw_dict = response.json()
        return [tuples['Members'] for tuples in raw_dict['Tuples']]

    def remove_edge(self, dimension_name: str, hierarchy_name: str, parent: str, component: str, **kwargs) -> Response:
        """ Remove one edge from hierarchy. Fails if parent or child element doesn't exist.

        :param dimension_name:
        :param hierarchy_name:
        :param parent:
        :param component:
        :return:
        """

        url = format_url(
            "/Dimensions('{}')/Hierarchies('{}')/Elements('{}')/Edges(ParentName='{}',ComponentName='{}')",
            dimension_name,
            hierarchy_name,
            parent,
            parent,
            component)

        return self._rest.DELETE(url=url, **kwargs)

    def add_edges(self, dimension_name: str, hierarchy_name: str = None, edges: Dict[Tuple[str, str], int] = None,
                  **kwargs) -> Response:
        """ Add Edges to hierarchy. Fails if one edge already exists.

        :param dimension_name:
        :param hierarchy_name:
        :param edges:
        :return:
        """
        if not hierarchy_name:
            hierarchy_name = dimension_name

        url = format_url("/Dimensions('{}')/Hierarchies('{}')/Edges", dimension_name, hierarchy_name)
        body = [{"ParentName": parent, "ComponentName": component, "Weight": float(weight)}
                for (parent, component), weight
                in edges.items()]

        return self._rest.POST(url=url, data=json.dumps(body), **kwargs)

    def add_elements(self, dimension_name: str, hierarchy_name: str, elements: Iterable[Element], **kwargs):
        """ Add elements to hierarchy. Fails if one element already exists.

        :param dimension_name:
        :param hierarchy_name:
        :param elements:
        :return:
        """
        url = format_url("/Dimensions('{}')/Hierarchies('{}')/Elements", dimension_name, hierarchy_name)
        body = [element.body_as_dict for element in elements]

        return self._rest.POST(url=url, data=json.dumps(body), **kwargs)

    def add_element_attributes(self, dimension_name: str, hierarchy_name: str,
                               element_attributes: List[ElementAttribute], **kwargs):
        """ Add element attributes to hierarchy. Fails if one element attribute already exists.

        :param dimension_name:
        :param hierarchy_name:
        :param element_attributes:
        :return:
        """
        url = format_url("/Dimensions('{}')/Hierarchies('{}')/ElementAttributes", dimension_name, hierarchy_name)
        body = [element_attribute.body_as_dict for element_attribute in element_attributes]

        return self._rest.POST(url=url, data=json.dumps(body), **kwargs)

    def get_parents(self, dimension_name: str, hierarchy_name: str, element_name: str, **kwargs) -> List[str]:
        url = format_url(
            "/Dimensions('{dimension_name}')/Hierarchies('{hierarchy_name}')/Elements('{element_name}')/Parents"
            f"?$select=Name",
            dimension_name=dimension_name,
            hierarchy_name=hierarchy_name,
            element_name=element_name
        )
        response = self._rest.GET(url=url, **kwargs)

        return [record["Name"] for record in response.json()["value"]]

    def get_parents_of_all_elements(self, dimension_name: str, hierarchy_name: str, **kwargs) -> Dict[str, List[str]]:
        url = format_url(
            f"/Dimensions('{dimension_name}')/Hierarchies('{hierarchy_name}')/Elements?$select=Name"
            f"&$expand=Parents($select=Name)",
        )
        response = self._rest.GET(url=url, **kwargs)

        return {child["Name"]: [parent["Name"] for parent in child["Parents"]] for child in response.json()["value"]}

    def get_element_principal_name(self, dimension_name: str, hierarchy_name: str, element_name: str, **kwargs) -> str:
        element = self.get(dimension_name, hierarchy_name, element_name, **kwargs)
        return element.name

    def _get_mdx_set_cardinality(self, mdx: str) -> int:
        url = format_url("/ExecuteMDXSetExpression?$select=Cardinality")
        payload = {"MDX": mdx}
        response = self._rest.POST(url, json.dumps(payload, ensure_ascii=False))
        return (response.json()).get('Cardinality')

    @staticmethod
    def _build_drill_intersection_mdx(dimension_name: str, hierarchy_name: str, first_element_name: str,
                                      second_element_name: str, mdx_method: str, recursive: bool) -> str:

        first_member = Member.of(dimension_name, hierarchy_name, first_element_name)
        second_member = Member.of(dimension_name, hierarchy_name, second_element_name)

        if MDXDrillMethod.TM1DRILLDOWNMEMBER.name == mdx_method.upper():
            query = MdxHierarchySet.members([first_member]).tm1_drill_down_member(recursive=recursive)

        elif MDXDrillMethod.DESCENDANTS.name == mdx_method.upper():
            query = MdxHierarchySet.descendants(
                member=first_member,
                level_or_depth=MdxLevelExpression.member_level(second_member),
                desc_flag='SELF')

        else:
            raise TM1pyException("Invalid MDX Drill Method Specified, Options: 'TM1DrillDownMember' or 'Descendants'")

        mdx = query.intersect(MdxHierarchySet.members([second_member]))
        return mdx.to_mdx()

    def element_is_parent(self, dimension_name: str, hierarchy_name: str, parent_name: str,
                          element_name: str) -> bool:
        """ Element is Parent
        :Note, unlike the related function in TM1 (ELISPAR or ElementIsParent), this function will return False
        :if an invalid element is passed;
        :but will raise an exception if an invalid dimension, or hierarchy is passed
        """
        mdx = self._build_drill_intersection_mdx(dimension_name=dimension_name,
                                                 hierarchy_name=hierarchy_name,
                                                 first_element_name=parent_name,
                                                 second_element_name=element_name,
                                                 mdx_method='TM1DrillDownMember',
                                                 recursive=False)

        cardinality = self._get_mdx_set_cardinality(mdx)
        return bool(cardinality)

    def element_is_ancestor(self, dimension_name: str, hierarchy_name: str, ancestor_name: str,
                            element_name: str, method: str = None) -> bool:
        """ Element is Ancestor

        :Note, unlike the related function in TM1 (`ELISANC` or `ElementIsAncestor`), this function will return False
        if an invalid element is passed; but will raise an exception if an invalid dimension, or hierarchy is passed

        For `method` you can pass 3 three values
        value `TI` performs best, but requires admin permissions
        Value 'TM1DrillDownMember' performs well when element is a leaf.
        Value 'Descendants' performs well when `ancestor_name` and `element_name` are Consolidations.

        If no value is passed, function defaults to 'TI' for user with admin permissions
        and 'TM1DrillDownMember' for users without admin permissions
        """
        if not method:
            method = 'TI' if self.is_admin else 'TM1DrillDownMember'

        if method.upper() == "TI":
            if self._element_is_ancestor_ti(dimension_name, hierarchy_name, element_name, ancestor_name):
                return True

            if self.hierarchy_exists(dimension_name, hierarchy_name):
                return False

            raise TM1pyException(f"Hierarchy: '{hierarchy_name}' does not exist in dimension: '{dimension_name}'")

        # make sure DESCENDANTS behaves like default TM1DrillDownMember
        if method.upper() == MDXDrillMethod.DESCENDANTS.name:
            if not self.exists(dimension_name, hierarchy_name, element_name):

                # case dimension or hierarchy doesn't exist
                if not self.hierarchy_exists(dimension_name, hierarchy_name):
                    raise TM1pyException(f"Hierarchy '{hierarchy_name}' does not exist in dimension '{dimension_name}'")

                # case element or ancestor doesn't exist
                return False

        if method.upper() == "TM1DRILLDOWNMEMBER":
            if not self.exists(dimension_name, hierarchy_name, element_name):

                # case dimension or hierarchy doesn't exist
                if not self.hierarchy_exists(dimension_name, hierarchy_name):
                    raise TM1pyException(f"Hierarchy '{hierarchy_name}' does not exist in dimension '{dimension_name}'")

                # case element or ancestor doesn't exist
                return False

        mdx = self._build_drill_intersection_mdx(
            dimension_name=dimension_name,
            hierarchy_name=hierarchy_name,
            first_element_name=ancestor_name,
            second_element_name=element_name,
            mdx_method=method,
            recursive=True)

        cardinality = self._get_mdx_set_cardinality(mdx)
        return bool(cardinality)

    def hierarchy_exists(self, dimension_name, hierarchy_name):
        hierarchy_service = self._get_hierarchy_service()
        return hierarchy_service.exists(dimension_name, hierarchy_name)

    @require_data_admin
    def _element_is_ancestor_ti(self, dimension_name: str, hierarchy_name: str, element_name: str,
                                ancestor_name: str) -> bool:
        process_service = self.get_process_service()
        code = f"ElementIsAncestor('{dimension_name}', '{hierarchy_name}', '{ancestor_name}', '{element_name}')=1"
        return process_service.evaluate_boolean_ti_expression(code)

    def get_process_service(self):
        from TM1py import ProcessService
        return ProcessService(self._rest)

    def _get_hierarchy_service(self):
        from TM1py import HierarchyService
        return HierarchyService(self._rest)

    def _get_subset_service(self):
        from TM1py import SubsetService
        return SubsetService(self._rest)

    def _get_process_service(self):
        from TM1py import ProcessService
        return ProcessService(self._rest)

    def _get_cell_service(self):
        from TM1py import CellService
        return CellService(self._rest)
