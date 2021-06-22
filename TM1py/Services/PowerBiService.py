from collections.abc import Iterable

from TM1py.Services import CellService
from TM1py.Services import ElementService
from TM1py.Utils import require_pandas

try:
    import pandas as pd

    _has_pandas = True
except ImportError:
    _has_pandas = False


class PowerBiService:
    def __init__(self, tm1_rest):
        """

        :param tm1_rest: instance of RestService
        """
        self._tm1_rest = tm1_rest
        self.cells = CellService(tm1_rest)
        self.elements = ElementService(tm1_rest)

    @require_pandas
    def execute_mdx(self, mdx, **kwargs) -> 'pd.DataFrame':
        return self.cells.execute_mdx_dataframe_shaped(mdx, **kwargs)

    @require_pandas
    def execute_view(self, cube_name, view_name, private, **kwargs) -> 'pd.DataFrame':
        return self.cells.execute_view_dataframe_shaped(cube_name, view_name, private, **kwargs)

    @require_pandas
    def get_member_properties(self, dimension_name: str, hierarchy_name: str, member_selection: Iterable = None,
                              skip_consolidations: bool = True, attributes: Iterable = None,
                              skip_parents: bool = False, level_names=None,
                              parent_attribute: str = None) -> 'pd.DataFrame':
        """

        :param dimension_name: Name of the dimension
        :param hierarchy_name: Name of the hierarchy in the dimension
        :param member_selection: Selection of members. Iterable or valid MDX string
        :param skip_consolidations: Boolean flag to skip consolidations
        :param attributes: Selection of attributes. Iterable. If None retrieve all.
        :param level_names: List of labels for parent columns. If None use level names from TM1.
        :param skip_parents: Boolean Flag to skip parent columns.
        :param parent_attribute: Attribute to be displayed in parent columns. If None, parent name is used.
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
                level_names = self.elements.get_level_names(dimension_name, hierarchy_name, descending=True)

            for parent in range(1, levels, 1):
                name_or_attribute = f"Properties('{parent_attribute}')" if parent_attribute else "Name"
                member = f"""
                    MEMBER [{self.elements.ELEMENT_ATTRIBUTES_PREFIX + dimension_name}].[{level_names[parent]}] 
                    AS [{dimension_name}].CurrentMember.{'Parent.' * parent}{name_or_attribute}
                    """
                calculated_members_definition.append(member)

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

        # override hierarchy name
        df_data.rename(columns={hierarchy_name:dimension_name},inplace=True)
        
        # shift levels to right hand side
        if not skip_parents:
            # skip max level (= leaves)
            level_names = level_names[1:]
            # iterative approach
            for _ in level_names:
                rows_to_shift = df_data[df_data[level_names[-1]] == ''].index
                if rows_to_shift.empty:
                    break
                df_data.iloc[rows_to_shift, -len(level_names):] = df_data.iloc[rows_to_shift, -len(level_names):].shift(
                    1, axis=1)

            df_data.iloc[:, -len(level_names):] = df_data.iloc[:, -len(level_names):].fillna('')

        return pd.merge(df, df_data, on=dimension_name).drop_duplicates()
