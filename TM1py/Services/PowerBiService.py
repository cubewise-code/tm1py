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
    def get_member_properties(self, dimension_name: str = None, hierarchy_name: str = None,
                              member_selection: Iterable = None,
                              skip_consolidations: bool = True, attributes: Iterable = None,
                              skip_parents: bool = False, level_names=None,
                              parent_attribute: str = None, skip_weights=True) -> 'pd.DataFrame':
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
        if not skip_weights and skip_parents:
            raise ValueError("skip_weights must not be False if skip_parents is True")

        return self.elements.get_elements_dataframe(
            dimension_name=dimension_name, hierarchy_name=hierarchy_name, member_selection=member_selection,
            skip_consolidations=skip_consolidations, attributes=attributes, skip_parents=skip_parents,
            level_names=level_names, parent_attribute=parent_attribute, skip_weights=skip_weights)
