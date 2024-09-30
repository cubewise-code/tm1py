# -*- coding: utf-8 -*-

try:
    import pandas as pd

    _has_pandas = True
except ImportError:
    _has_pandas = False

import json
import math
from typing import Dict, Tuple, List, Optional

import networkx as nx
from requests import Response

from TM1py.Exceptions import TM1pyRestException
from TM1py.Objects import Hierarchy, Element, ElementAttribute, Dimension
from TM1py.Services.ElementService import ElementService
from TM1py.Services.ObjectService import ObjectService
from TM1py.Services.RestService import RestService
from TM1py.Services.SubsetService import SubsetService
from TM1py.Utils.Utils import case_and_space_insensitive_equals, format_url, CaseAndSpaceInsensitiveDict, \
    CaseAndSpaceInsensitiveSet, CaseAndSpaceInsensitiveTuplesDict, require_pandas, require_data_admin, \
    require_ops_admin, verify_version


class HierarchyService(ObjectService):
    """ Service to handle Object Updates for TM1 Hierarchies

    """

    # Tuple with TM1 Versions where Edges need to be created through TI, due to bug:
    # https://www.ibm.com/developerworks/community/forums/html/topic?id=75f2b99e-6961-4c71-9364-1d5e1e083eff
    EDGES_WORKAROUND_VERSIONS = ('11.0.002', '11.0.003', '11.1.000')

    def __init__(self, rest: RestService):
        super().__init__(rest)
        self.subsets = SubsetService(rest)
        self.elements = ElementService(rest)

    @staticmethod
    def _validate_edges(df: 'pd.DataFrame'):
        graph = nx.DiGraph()
        for _, *record in df.itertuples():
            child = record[0]
            for parent in record[1:]:
                if not parent:
                    continue
                if isinstance(parent, float) and math.isnan(parent):
                    continue
                graph.add_edge(child, parent)
                child = parent

        cycles = list(nx.simple_cycles(graph))
        if cycles:
            raise ValueError(f"Circular reference{'s' if len(cycles) > 1 else ''} found in edges: {cycles}")

    @staticmethod
    def _validate_alias_uniqueness(df: 'pd.DataFrame'):
        # map alias values against their principal element name
        seen_values = CaseAndSpaceInsensitiveDict()

        for row in df.itertuples(index=False):
            normalized_row = tuple(col.strip().lower() for col in row)
            element_name, *alias_values = normalized_row
            # Register e.g. 'Deutschand' -> 'Deutschand'
            seen_values[element_name] = element_name

            for value in alias_values:
                if not value:
                    continue

                if value in seen_values:
                    # Duplicate entries
                    if case_and_space_insensitive_equals(element_name, seen_values[value]):
                        continue

                    raise ValueError(f"Invalid alias value found in record {tuple(row)}")
                # Register e.g. 'Deutschand' -> 'Germany'
                seen_values[value] = element_name

    def create(self, hierarchy: Hierarchy, **kwargs):
        """ Create a hierarchy in an existing dimension

        :param hierarchy:
        :return:
        """
        url = format_url("/Dimensions('{}')/Hierarchies", hierarchy.dimension_name)
        response = self._rest.POST(url, hierarchy.body, **kwargs)

        self.update_element_attributes(hierarchy, **kwargs)

        return response

    def get(self, dimension_name: str, hierarchy_name: str, **kwargs) -> Hierarchy:
        """ get hierarchy

        :param dimension_name: name of the dimension
        :param hierarchy_name: name of the hierarchy
        :return:
        """
        url = format_url(
            "/Dimensions('{}')/Hierarchies('{}')?$expand=Edges,Elements,ElementAttributes,Subsets,DefaultMember",
            dimension_name,
            hierarchy_name)
        response = self._rest.GET(url, **kwargs)
        return Hierarchy.from_dict(response.json())

    def get_all_names(self, dimension_name: str, **kwargs) -> List[str]:
        """ get all names of existing Hierarchies in a dimension

        :param dimension_name:
        :return:
        """
        url = format_url("/Dimensions('{}')/Hierarchies?$select=Name", dimension_name)
        response = self._rest.GET(url, **kwargs)
        return [hierarchy["Name"] for hierarchy in response.json()["value"]]

    def update(self, hierarchy: Hierarchy, keep_existing_attributes=False, **kwargs) -> List[Response]:
        """ update a hierarchy. It's a two step process:
        1. Update Hierarchy
        2. Update Element-Attributes

        Function caters for Bug with Edge Creation:
        https://www.ibm.com/developerworks/community/forums/html/topic?id=75f2b99e-6961-4c71-9364-1d5e1e083eff

        :param hierarchy: instance of TM1py.Hierarchy
        :param keep_existing_attributes: True to make sure existing attributes are not removed
        :return: list of responses
        """
        # functions returns multiple responses
        responses = list()
        # 1. Update Hierarchy
        url = format_url("/Dimensions('{}')/Hierarchies('{}')", hierarchy.dimension_name, hierarchy.name)
        # Workaround EDGES: Handle Issue, that Edges cant be created in one batch with the Hierarchy in certain versions
        hierarchy_body = hierarchy.body_as_dict
        if self.version[0:8] in self.EDGES_WORKAROUND_VERSIONS:
            del hierarchy_body["Edges"]
        responses.append(self._rest.PATCH(url, json.dumps(hierarchy_body), **kwargs))

        # 2. Update Attributes
        responses.append(self.update_element_attributes(
            hierarchy=hierarchy,
            keep_existing_attributes=keep_existing_attributes,
            **kwargs))

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
            responses.append(process_service.execute_ti_code(lines_prolog=ti_statements, **kwargs))

        return responses

    def update_or_create(self, hierarchy: Hierarchy, **kwargs):
        """ update if exists else create

        :param hierarchy:
        :return:
        """
        if self.exists(dimension_name=hierarchy.dimension_name, hierarchy_name=hierarchy.name, **kwargs):
            self.update(hierarchy=hierarchy, **kwargs)
        else:
            self.create(hierarchy=hierarchy, **kwargs)

    def exists(self, dimension_name: str, hierarchy_name: str, **kwargs) -> bool:
        """

        :param dimension_name:
        :param hierarchy_name:
        :return:
        """
        url = format_url("/Dimensions('{}')/Hierarchies?$select=Name", dimension_name)

        try:
            response = self._rest.GET(url, **kwargs)
        except TM1pyRestException as e:
            if e.status_code == 404:
                return False
            raise e

        existing_hierarchies = CaseAndSpaceInsensitiveSet([
            hierarchy["Name"]
            for hierarchy
            in response.json()["value"]])
        return hierarchy_name in existing_hierarchies

    def delete(self, dimension_name: str, hierarchy_name: str, **kwargs) -> Response:
        url = format_url("/Dimensions('{}')/Hierarchies('{}')", dimension_name, hierarchy_name)
        return self._rest.DELETE(url, **kwargs)

    def get_hierarchy_summary(self, dimension_name: str, hierarchy_name: str, **kwargs) -> Dict[str, int]:
        hierarchy_properties = ("Elements", "Edges", "ElementAttributes", "Members", "Levels")
        url = format_url(
            "/Dimensions('{}')/Hierarchies('{}')?$expand=Edges/$count,Elements/$count,"
            "ElementAttributes/$count,Members/$count,Levels/$count&$select=Cardinality",
            dimension_name,
            hierarchy_name)
        hierary_summary_raw = self._rest.GET(url, **kwargs).json()

        return {hierarchy_property: hierary_summary_raw[hierarchy_property + "@odata.count"]
                for hierarchy_property
                in hierarchy_properties}

    def update_element_attributes(self, hierarchy: Hierarchy, keep_existing_attributes=False, **kwargs):
        """ Update the elementattributes of a hierarchy

        :param hierarchy: Instance of TM1py.Hierarchy
        :param keep_existing_attributes: True to make sure existing attributes are not removed
        :return:
        """
        # get existing attributes first
        existing_element_attributes = self.elements.get_element_attributes(
            dimension_name=hierarchy.dimension_name,
            hierarchy_name=hierarchy.name,
            **kwargs)
        existing_element_attributes = CaseAndSpaceInsensitiveDict({ea.name: ea for ea in existing_element_attributes})

        attributes_to_create = list()
        attributes_to_delete = list()
        attributes_to_update = list()

        for element_attribute in hierarchy.element_attributes:
            if element_attribute.name not in existing_element_attributes:
                attributes_to_create.append(element_attribute)
                continue

            existing_element_attribute = existing_element_attributes[element_attribute.name]
            if not existing_element_attribute.attribute_type == element_attribute.attribute_type:
                attributes_to_update.append(element_attribute)
                continue

        if not keep_existing_attributes:
            for existing_element_attribute in existing_element_attributes:
                if existing_element_attribute not in CaseAndSpaceInsensitiveSet(
                        [ea.name for ea in hierarchy.element_attributes]):
                    attributes_to_delete.append(existing_element_attribute)

        for element_attribute in attributes_to_create:
            self.elements.create_element_attribute(
                dimension_name=hierarchy.dimension_name,
                hierarchy_name=hierarchy.name,
                element_attribute=element_attribute,
                **kwargs)

        for element_attribute in attributes_to_delete:
            self.elements.delete_element_attribute(
                dimension_name=hierarchy.dimension_name,
                hierarchy_name=hierarchy.name,
                element_attribute=element_attribute,
                **kwargs)

        for element_attribute in attributes_to_update:
            self.elements.delete_element_attribute(
                dimension_name=hierarchy.dimension_name,
                hierarchy_name=hierarchy.name,
                element_attribute=element_attribute.name,
                **kwargs)
            self.elements.create_element_attribute(
                dimension_name=hierarchy.dimension_name,
                hierarchy_name=hierarchy.name,
                element_attribute=element_attribute,
                **kwargs)

    def get_default_member(self, dimension_name: str, hierarchy_name: str = None, **kwargs) -> Optional[str]:
        """ Get the defined default_member for a Hierarchy.
        Will return the element with index 1, if default member is not specified explicitly in }HierarchyProperty Cube

        :param dimension_name:
        :param hierarchy_name:
        :return: String, name of Member
        """
        url = format_url(
            "/Dimensions('{dimension}')/Hierarchies('{hierarchy}')/DefaultMember",
            dimension=dimension_name,
            hierarchy=hierarchy_name if hierarchy_name else dimension_name)
        response = self._rest.GET(url=url, **kwargs)

        if not response.text:
            return None
        return response.json()["Name"]

    def _update_default_member_via_props_cube(self, dimension_name: str, hierarchy_name: str = None,
                                              member_name: str = "",
                                              **kwargs) -> Response:
        from TM1py import ProcessService, CellService
        if hierarchy_name and not case_and_space_insensitive_equals(dimension_name, hierarchy_name):
            dimension = "{}:{}".format(dimension_name, hierarchy_name)
        else:
            dimension = dimension_name
        cells = {(dimension, 'hierarchy0', 'defaultMember'): member_name}

        CellService(self._rest).write_values(
            cube_name="}HierarchyProperties",
            cellset_as_dict=cells,
            dimensions=('}Dimensions', '}Hierarchies', '}HierarchyProperties'),
            **kwargs)

        return ProcessService(self._rest).execute_ti_code(
            lines_prolog=format_url("RefreshMdxHierarchy('{}');", dimension_name),
            **kwargs)

    def _update_default_member_via_api(self, dimension_name: str, hierarchy_name: str = None, member_name: str = "",
                                       **kwargs) -> Response:

        url = format_url("/Dimensions('{dimension}')/Hierarchies('{hierarchy}')",
                         dimension=dimension_name,
                         hierarchy=hierarchy_name if hierarchy_name else dimension_name)

        payload = {"DefaultMemberName": member_name}

        return self._rest.PATCH(url=url, data=json.dumps(payload))

    def update_default_member(self, dimension_name: str, hierarchy_name: str = None, member_name: str = "",
                              **kwargs) -> Response:
        """ Update the default member of a hierarchy.

        :param dimension_name:
        :param hierarchy_name:
        :param member_name:
        :return:
        """
        if verify_version(required_version='12', version=self.version):
            return self._update_default_member_via_api(dimension_name, hierarchy_name, member_name)
        else:
            return self._update_default_member_via_props_cube(dimension_name, hierarchy_name, member_name)

    def remove_all_edges(self, dimension_name: str, hierarchy_name: str = None, **kwargs) -> Response:
        if not hierarchy_name:
            hierarchy_name = dimension_name
        url = format_url("/Dimensions('{}')/Hierarchies('{}')", dimension_name, hierarchy_name)
        body = {
            "Edges": []
        }
        return self._rest.PATCH(url=url, data=json.dumps(body), **kwargs)

    def remove_edges_under_consolidation(self, dimension_name: str, hierarchy_name: str,
                                         consolidation_element: str, **kwargs) -> List[Response]:
        """
        :param dimension_name: Name of the dimension
        :param hierarchy_name: Name of the hierarchy
        :param consolidation_element: Name of the Consolidated element
        :return: response
        """
        hierarchy = self.get(dimension_name, hierarchy_name)
        from TM1py.Services import ElementService
        element_service = ElementService(self._rest)
        elements_under_consolidations = element_service.get_members_under_consolidation(dimension_name, hierarchy_name,
                                                                                        consolidation_element)
        elements_under_consolidations.append(consolidation_element)
        remove_edges = []
        for (parent, component) in hierarchy.edges:
            if parent in elements_under_consolidations and component in elements_under_consolidations:
                remove_edges.append((parent, component))
        hierarchy.remove_edges(remove_edges)
        return self.update(hierarchy, **kwargs)

    def add_edges(self, dimension_name: str, hierarchy_name: str = None, edges: Dict[Tuple[str, str], int] = None,
                  **kwargs) -> Response:
        """ Add Edges to hierarchy. Fails if one edge already exists.

        :param dimension_name:
        :param hierarchy_name:
        :param edges:
        :return:
        """
        return self.elements.add_edges(dimension_name, hierarchy_name, edges, **kwargs)

    def add_elements(self, dimension_name: str, hierarchy_name: str, elements: List[Element], **kwargs):
        """ Add elements to hierarchy. Fails if one element already exists.

        :param dimension_name:
        :param hierarchy_name:
        :param elements:
        :return:
        """
        return self.elements.add_elements(dimension_name, hierarchy_name, elements, **kwargs)

    def add_element_attributes(self, dimension_name: str, hierarchy_name: str,
                               element_attributes: List[ElementAttribute], **kwargs):
        """ Add element attributes to hierarchy. Fails if one element attribute already exists.

        :param dimension_name:
        :param hierarchy_name:
        :param element_attributes:
        :return:
        """
        return self.elements.add_element_attributes(dimension_name, hierarchy_name, element_attributes, **kwargs)

    def is_balanced(self, dimension_name: str, hierarchy_name: str, **kwargs):
        """ Check if hierarchy is balanced

        :param dimension_name:
        :param hierarchy_name:
        :return:
        """
        url = format_url(
            "/Dimensions('{}')/Hierarchies('{}')/Structure/$value",
            dimension_name,
            hierarchy_name)
        structure = int(self._rest.GET(url, **kwargs).text)
        # 0 = balanced, 2 = unbalanced
        if structure == 0:
            return True
        elif structure == 2:
            return False
        else:
            raise RuntimeError(f"Unexpected return value from TM1 API request: {str(structure)}")

    @require_pandas
    @require_data_admin
    @require_ops_admin
    def update_or_create_hierarchy_from_dataframe(
            self,
            dimension_name: str,
            hierarchy_name: str,
            df: 'pd.DataFrame',
            element_column: str = None,
            verify_unique_elements: bool = False,
            verify_edges: bool = True,
            element_type_column: str = 'ElementType',
            unwind: bool = False):
        """ Update or Create a hierarchy based on a dataframe, while never deleting existing elements.

        :param dimension_name:
            Name of the dimension
        :param hierarchy_name:
            Name of the hierarchy
        :param df: pd.DataFrame the data frame. Example:
            |    | Region  | ElementType | Alias:a     | Currency:s | population:n | level001 | level000 | level001_weight | level000_weight |
            |---:|:--------|:------------|:------------|:-----------|-------------:|:---------|:---------|----------------:|----------------:|
            |  0 | France  | Numeric     | Frankreich  | EUR        |     60000000 | Europe   | World    |               1 |               1 |
            |  1 | Belgium | Numeric     | Schweiz     | CHF        |      9000000 | Europe   | World    |               1 |               1 |
            |  2 | Germany | Numeric     | Deutschland | EUR        |     84000000 | Europe   | World    |               1 |               1 |

            Names for the parent columns (level001, level000) are not configurable and `level000` is the top node.
            All columns except for the element_column, element_type_colums and parent columns are attribute columns.
            On attribute columns, you specify the type as a suffix. If no type is provided string attributes are created

        :param element_type_column: str
            The column name in the df which specifies which element is which type.
            If None, all will be considered N level.
        :param element_column: str
            The column name of the element ID. If None, assumes first column is the element ID.
        :param verify_unique_elements:
            Abort early if element names are not unique
        :param verify_edges:
            Abort early if edges have circular reference
        :param unwind: bool
            Unwind hierarch before creating new edges
        :return:

        """
        df = df.copy()

        # element ID is in first column if not specified.
        element_column = df.columns[0] if not element_column else element_column
        df[element_column] = df[element_column].astype(str)

        # assume all Numeric if no type is provided
        if element_type_column not in df.columns:
            df[element_type_column] = "Numeric"

        # verify uniqueness of element names
        if verify_unique_elements:
            unique_element_names = len(set(df[element_column].str.lower().str.replace(' ', '')))
            if df.shape[0] != unique_element_names:
                raise ValueError("There must be no duplicates in the element column")

        # verify alias uniqueness
        alias_columns = tuple([col for col in df.columns if col.lower().endswith((":a", ":alias"))])
        if len(alias_columns) > 0:
            self._validate_alias_uniqueness(df=df[[element_column, *alias_columns]])

        # identify level columns
        level_columns = []
        level_weight_columns = []
        # sort to assure right order of levels
        for column in sorted(df.columns, reverse=True):
            if column.lower().startswith('level') and column[5:8].isdigit():
                if len(column) == 8:
                    level_columns.append(column)
                elif len(column) == 15 and column.lower().endswith('_weight'):
                    level_weight_columns.append(column)

        # case: no level weight columns. All weights are 1
        if len(level_weight_columns) == 0:
            for level_column in level_columns:
                level_weight_column = level_column + "_weight"
                level_weight_columns.append(level_weight_column)
                df[level_weight_column] = 1

        if not len(level_columns) == len(level_weight_columns):
            raise ValueError("Number of level columns must be equal to number of level weight columns")

        if verify_edges:
            self._validate_edges(df=df[[element_column, *level_columns]])

        hierarchy_exists = self.exists(dimension_name, hierarchy_name)

        if not hierarchy_exists:
            existing_element_identifiers = CaseAndSpaceInsensitiveSet()
        else:
            existing_element_identifiers = self.elements.get_all_element_identifiers(
                dimension_name=dimension_name,
                hierarchy_name=hierarchy_name)

        if not hierarchy_exists:
            hierarchy = Hierarchy(name=hierarchy_name, dimension_name=dimension_name)
            dimension_service = self.get_dimension_service()
            if not dimension_service.exists(dimension_name):
                dimension = Dimension(name=dimension_name, hierarchies=[hierarchy])
                dimension_service.create(dimension)
            else:
                hierarchy = Hierarchy(name=hierarchy_name, dimension_name=dimension_name)
                self.create(hierarchy)

        # determine new elements based on Element Name column
        new_elements = CaseAndSpaceInsensitiveDict({
            element_name: Element.Types(element_type)
            for element_name, element_type
            in df.loc[
                ~df[element_column].isin(existing_element_identifiers),
                (element_column, element_type_column)
            ].itertuples(index=False)
        })

        # determine new consolidations based on level columns
        for element_name in df[[*level_columns]].stack().unique():
            if not element_name:
                continue
            if element_name in existing_element_identifiers:
                continue
            if element_name in new_elements and new_elements[element_name] != Element.Types.CONSOLIDATED:
                raise ValueError(f"Inconsistent Type for element: '{element_name}' in hierarchy '{hierarchy_name}'")
            new_elements[element_name] = Element.Types.CONSOLIDATED

        if new_elements:
            # add these elements to hierarchy in tm1
            self.elements.add_elements(
                dimension_name=dimension_name,
                hierarchy_name=hierarchy_name,
                elements=(
                    Element(element_name, element_type)
                    for element_name, element_type in
                    new_elements.items()))

        # define the attribute columns in df. Applies to all elements in df, not only new ones.
        attribute_columns = df.columns.drop(
            labels=[element_column] + [element_type_column] + level_columns + level_weight_columns,
            errors='ignore')

        # new attributes are created as strings if no type is provided
        try:
            existing_attributes = self.elements.get_all_element_identifiers(
                dimension_name='}ElementAttributes_' + dimension_name,
                hierarchy_name='}ElementAttributes_' + dimension_name)
        except TM1pyRestException as ex:
            if ex.status_code == 404:
                existing_attributes = set()
            else:
                raise ex

        new_attributes = []
        for attribute_column in attribute_columns:
            if ':' in attribute_column:
                attribute_name, attribute_type = attribute_column.rsplit(":", maxsplit=1)
                attribute_type = self._attribute_type_from_code(attribute_type)

            else:
                attribute_name = attribute_column
                attribute_type = ElementAttribute.Types.STRING

            if attribute_name not in existing_attributes:
                new_attributes.append(ElementAttribute(attribute_name, attribute_type))

        if new_attributes:
            self.elements.add_element_attributes(
                dimension_name=dimension_name,
                hierarchy_name=hierarchy_name,
                element_attributes=new_attributes)

        # define attributes df with ID + attribute columns.
        id_attribute_cols = [element_column] + list(attribute_columns.values)
        attributes_df: pd.DataFrame = df.loc[:, id_attribute_cols]

        # melt for write structure (ID, Attribute) : Attribute_value
        attributes_df = attributes_df.melt(
            id_vars=element_column,
            value_vars=attribute_columns,
            var_name='}ElementAttributes_' + dimension_name,
            value_name='attribute_value', )
        attributes_df.fillna('', inplace=True)

        # drop ':' suffix in attribute column
        attribute_column = '}ElementAttributes_' + dimension_name
        attributes_df[attribute_column] = attributes_df[attribute_column].apply(lambda x: x.rsplit(':', 1)[0])

        # write attributes to cube
        if not attributes_df.empty:
            cell_service = self.get_cell_service()
            # explicitly reference hierarchy if dimension_name != hierarchy_name
            if not case_and_space_insensitive_equals(dimension_name, hierarchy_name):
                attributes_df.iloc[:, 0] = hierarchy_name + ":" + attributes_df.iloc[:, 0].astype(str)
            cell_service.write_dataframe(
                cube_name='}ElementAttributes_' + dimension_name,
                data=attributes_df,
                sum_numeric_duplicates=False,
                use_blob=True)

        if unwind:
            self.remove_all_edges(dimension_name, hierarchy_name)

        edges = CaseAndSpaceInsensitiveTuplesDict()
        for element_name, *record in df[[element_column, *level_columns, *level_weight_columns]].itertuples(
                index=False):
            levels = record[:len(level_columns)]
            level_weights = record[len(level_columns):]

            previous_level = element_name
            for level, weight in zip(levels, level_weights):
                if not level:
                    continue
                if not isinstance(level, str) and math.isnan(level):
                    continue
                if level == previous_level:
                    continue

                edges[level, previous_level] = weight
                previous_level = level

        if edges:
            try:
                current_edges = self.elements.get_edges(
                    dimension_name=dimension_name,
                    hierarchy_name=hierarchy_name)
            except TM1pyRestException as ex:
                if ex.status_code == 404:
                    current_edges = CaseAndSpaceInsensitiveTuplesDict()
                else:
                    raise ex

            delete_edges = {
                (k, v): w
                for (k, v), w
                in edges.items()
                if w != current_edges.get((k, v), w)}
            if delete_edges:
                self.elements.delete_edges(
                    dimension_name=dimension_name,
                    hierarchy_name=hierarchy_name,
                    edges=delete_edges.keys(),
                    use_ti=self.is_admin)

            new_edges = {
                (k, v): w
                for (k, v), w
                in edges.items()
                if (k, v) not in current_edges or w != current_edges[(k, v)]}
            if new_edges:
                self.elements.add_edges(dimension_name=dimension_name, hierarchy_name=hierarchy_name, edges=new_edges)

    def get_dimension_service(self):
        from TM1py import DimensionService
        return DimensionService(self._rest)

    def get_cell_service(self):
        from TM1py import CellService
        return CellService(self._rest)

    @staticmethod
    def _attribute_type_from_code(attribute_type: str) -> ElementAttribute.Types:
        attribute_type = attribute_type.lower()
        if attribute_type not in ["a", "s", "n"] and attribute_type not in ElementAttribute.Types:
            raise ValueError(f"Attribute Type '{attribute_type}' is not a valid "
                             f"value: 'a', 's', 'n', 'alias', 'string', 'numeric'")

        if attribute_type == 'a':
            return ElementAttribute.Types.ALIAS

        if attribute_type == 's':
            return ElementAttribute.Types.STRING

        if attribute_type == 'n':
            return ElementAttribute.Types.NUMERIC

        else:
            return ElementAttribute.Types(attribute_type)
