from collections.abc import Iterable

import pandas as pd

from TM1py.Services import CellService
from TM1py.Services import ElementService


class PowerBiService:
    def __init__(self, tm1_rest):
        """

        :param tm1_rest: instance of RestService
        """
        self._tm1_rest = tm1_rest
        self.cells = CellService(tm1_rest)
        self.elements = ElementService(tm1_rest)

    def execute_mdx(self, mdx, **kwargs):
        cellset_id = self.cells.create_cellset(mdx)
        return self.cells.extract_cellset_power_bi(cellset_id, **kwargs)

    def execute_view(self, cube_name, view_name, private, **kwargs):
        cellset_id = self.cells.create_cellset_from_view(cube_name, view_name, private)
        return self.cells.extract_cellset_power_bi(cellset_id, **kwargs)

    def get_member_properties(self, dimension_name, hierarchy_name, member_selection=None,
                              skip_consolidations=True, attributes=None, skip_parents=False,
                              level_names=None):
        """

        :param dimension_name: Name of the dimension
        :param hierarchy_name: Name of the hierarchy in the dimension
        :param member_selection: Selection of members. Iterable or valid MDX string
        :param skip_consolidations: Boolean flag to skip consolidations
        :param attributes: Selection of attributes. Iterable. If None retrieve all.
        :param level_names: List of labels for parent columns. If None use level names from TM1.
        :param skip_parents: Boolean Flag to skip parent columns.
        :return: pandas DataFrame
        """
        if not member_selection:
            member_selection = f"{{ [{dimension_name}].[{hierarchy_name}].Members }}"
            if skip_consolidations:
                member_selection = f"{{ Tm1FilterByLevel({member_selection}, 0) }}"

        if not isinstance(member_selection, str):
            if isinstance(member_selection, Iterable):
                member_selection = "{" + ",".join(f"[{dimension_name}].[{member}]" for member in member_selection) + "}"
            else:
                raise ValueError("Argument 'element_selection' must be None or str")

        if not self.elements.attribute_cube_exists(dimension_name):
            raise RuntimeError(self.elements.ELEMENT_ATTRIBUTES_PREFIX + dimension_name + " cube must exist")

        members = [tupl[0] for tupl in self.elements.execute_set_mdx(
            mdx=member_selection,
            element_properties=None,
            member_properties=("Name", "UniqueName"),
            parent_properties=None)]

        element_types = self.elements.get_element_types(
            dimension_name=dimension_name,
            hierarchy_name=hierarchy_name,
            skip_consolidations=skip_consolidations)

        df = pd.DataFrame(
            data=[(member["Name"], element_types[member["Name"]])
                  for member
                  in members
                  if member["Name"] in element_types],
            dtype=str,
            columns=[dimension_name, 'Type'])

        calculated_members_definition = list()
        calculated_members_selection = list()
        if not skip_parents:
            levels = self.elements.get_levels_count(dimension_name, hierarchy_name)

            # potential custom parent names
            if not level_names:
                level_names = self.elements.get_level_names(dimension_name, hierarchy_name)

            for parent in range(1, levels, 1):
                calculated_members_definition.append(
                    f"""
                    MEMBER [{self.elements.ELEMENT_ATTRIBUTES_PREFIX + dimension_name}].[{level_names[parent]}] 
                    AS [{dimension_name}].CurrentMember.{'Parent.' * parent}Name
                    """)

                calculated_members_selection.append(
                    f"[{self.elements.ELEMENT_ATTRIBUTES_PREFIX + dimension_name}].[{level_names[parent]}]")

        if attributes is None:
            column_selection = "{Tm1SubsetAll([" + self.elements.ELEMENT_ATTRIBUTES_PREFIX + dimension_name + "])}"
        else:
            column_selection = "{" + ",".join(
                "[" + self.elements.ELEMENT_ATTRIBUTES_PREFIX + dimension_name + "].[" + attribute + "]"
                for attribute
                in attributes) + "}"

        if calculated_members_selection:
            column_selection = column_selection + " + {" + ",".join(calculated_members_selection) + "}"
        member_selection = ",".join(
            member["UniqueName"]
            for member
            in members)

        mdx_with_block = ""
        if calculated_members_definition:
            mdx_with_block = "WITH " + " ".join(calculated_members_definition)

        mdx = f"""
        {mdx_with_block}
        SELECT
        {{ {member_selection} }} ON ROWS,
        {{ {column_selection} }} ON COLUMNS
        FROM [{self.elements.ELEMENT_ATTRIBUTES_PREFIX + dimension_name}]  
        """

        df_data = self.execute_mdx(mdx)

        return pd.merge(df, df_data, on=dimension_name).drop_duplicates()
