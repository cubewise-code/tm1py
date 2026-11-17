# -*- coding: utf-8 -*-

import json
from typing import Dict, Iterable, List, Optional, Union

from mdxpy import MdxBuilder, MdxHierarchySet, Member
from mdxpy.mdx import ElementsHierarchySet

from TM1py.Objects.Axis import ViewAxisSelection, ViewTitleSelection
from TM1py.Objects.DynamicPropertiesMixin import DynamicPropertiesMixin
from TM1py.Objects.Subset import AnonymousSubset, Subset
from TM1py.Objects.View import View
from TM1py.Utils import (
    case_and_space_insensitive_equals,
    lower_and_drop_spaces,
    read_object_name_from_url,
)


class NativeView(DynamicPropertiesMixin, View):
    """Abstraction of TM1 NativeView (classic cube view)

    :Notes:
        Complete, functional and tested
    """

    _DYNAMIC_PROPERTIES_EXCLUDED_KEYS = frozenset(
        {
            "@odata.type",
            "@odata.context",
            "@odata.etag",
            "Name",
            "Columns",
            "Rows",
            "Titles",
            "SuppressEmptyColumns",
            "SuppressEmptyRows",
            "FormatString",
            "Cube",
            "Attributes",
            "LocalizedAttributes",
        }
    )

    def __init__(
        self,
        cube_name: str,
        view_name: str,
        suppress_empty_columns: Optional[bool] = False,
        suppress_empty_rows: Optional[bool] = False,
        format_string: Optional[str] = "0.#########",
        titles: Optional[Iterable[ViewTitleSelection]] = None,
        columns: Optional[Iterable[ViewAxisSelection]] = None,
        rows: Optional[Iterable[ViewAxisSelection]] = None,
        dynamic_properties: Optional[Dict] = None,
    ):
        super().__init__(cube_name, view_name)
        self._suppress_empty_columns = suppress_empty_columns
        self._suppress_empty_rows = suppress_empty_rows
        self._format_string = format_string
        self._titles = list(titles) if titles else []
        self._columns = list(columns) if columns else []
        self._rows = list(rows) if rows else []
        self._dynamic_properties = {}
        self.dynamic_properties = dynamic_properties

    @property
    def body(self) -> str:
        return self._construct_body()

    @property
    def rows(self) -> List[ViewAxisSelection]:
        return self._rows

    @property
    def columns(self) -> List[ViewAxisSelection]:
        return self._columns

    @property
    def titles(self) -> List[ViewTitleSelection]:
        return self._titles

    @property
    def mdx(self):
        return self.as_MDX

    @property
    def MDX(self) -> str:
        return self.as_MDX

    @property
    def as_MDX(self) -> str:
        """Build a valid MDX Query from an Existing cubeview.
        Takes Zero suppression into account.
        Throws an Exception when no elements are place on the columns.
        Subsets are referenced in the result-MDX through the TM1SubsetToSet Function

        :return: String, the MDX Query
        """
        if not self.columns:
            raise ValueError("Column selection must not be empty")

        query = MdxBuilder.from_cube(self.cube)
        if self._suppress_empty_rows:
            query.rows_non_empty()

        if self.suppress_empty_columns:
            query.columns_non_empty()

        axes = [self.columns]
        if self.rows:
            axes.append(self.rows)

        for axis_id, axis in enumerate(axes):
            for axis_selection in axis:
                subset = axis_selection.subset

                if isinstance(subset, AnonymousSubset):
                    if subset.expression is not None:
                        mdx_hierarchy_set = MdxHierarchySet.from_str(
                            dimension=subset.dimension_name, hierarchy=subset.hierarchy_name, mdx=subset.expression
                        )

                    else:
                        members = [Member.of(subset.dimension_name, element) for element in subset.elements]
                        mdx_hierarchy_set = MdxHierarchySet.members(members)

                else:
                    mdx_hierarchy_set = MdxHierarchySet.tm1_subset_to_set(
                        dimension=axis_selection.dimension_name,
                        hierarchy=axis_selection.hierarchy_name,
                        subset=subset.name,
                    )
                query.add_hierarchy_set_to_axis(axis=axis_id, mdx_hierarchy_set=mdx_hierarchy_set)

        for title in self._titles:
            query.add_member_to_where(Member.of(title.dimension_name, title.selected))

        return query.to_mdx()

    @property
    def suppress_empty_cells(self) -> bool:
        return self._suppress_empty_columns and self._suppress_empty_rows

    @property
    def suppress_empty_columns(self) -> bool:
        return self._suppress_empty_columns

    @property
    def suppress_empty_rows(self) -> bool:
        return self._suppress_empty_rows

    @property
    def format_string(self) -> str:
        return self._format_string

    @suppress_empty_cells.setter
    def suppress_empty_cells(self, value: bool):
        self.suppress_empty_columns = value
        self.suppress_empty_rows = value

    @suppress_empty_rows.setter
    def suppress_empty_rows(self, value: bool):
        self._suppress_empty_rows = value

    @suppress_empty_columns.setter
    def suppress_empty_columns(self, value: bool):
        self._suppress_empty_columns = value

    @format_string.setter
    def format_string(self, value: str):
        self._format_string = value

    def add_column(self, dimension_name: str, subset: Union[Subset, AnonymousSubset] = None):
        """Add Dimension or Subset to the column-axis

        :param dimension_name: name of the dimension
        :param subset: instance of TM1py.Subset. Can be None
        :return:
        """
        view_axis_selection = ViewAxisSelection(dimension_name=dimension_name, subset=subset)
        self._columns.append(view_axis_selection)

    def remove_column(self, dimension_name: str):
        """remove dimension from the column axis

        :param dimension_name:
        :return:
        """
        for column in self._columns[:]:
            if case_and_space_insensitive_equals(column.dimension_name, dimension_name):
                self._columns.remove(column)

    def add_row(self, dimension_name: str, subset: Subset = None):
        """Add Dimension or Subset to the row-axis

        :param dimension_name:
        :param subset: instance of TM1py.Subset. Can be None instead.
        :return:
        """
        view_axis_selection = ViewAxisSelection(dimension_name=dimension_name, subset=subset)
        self._rows.append(view_axis_selection)

    def remove_row(self, dimension_name: str):
        """remove dimension from the row axis

        :param dimension_name:
        :return:
        """
        for row in self._rows[:]:
            if case_and_space_insensitive_equals(row.dimension_name, dimension_name):
                self._rows.remove(row)

    def add_title(self, dimension_name: str, selection: str, subset: Union[Subset, AnonymousSubset] = None):
        """Add subset and element to the titles-axis

        :param dimension_name: name of the dimension.
        :param selection: name of an element.
        :param subset:  instance of TM1py.Subset. Can be None instead.
        :return:
        """
        view_title_selection = ViewTitleSelection(dimension_name, subset, selection)
        self._titles.append(view_title_selection)

    def remove_title(self, dimension_name: str):
        """Remove dimension from the titles-axis

        :param dimension_name: name of the dimension.
        :return:
        """
        for title in self._titles[:]:
            if case_and_space_insensitive_equals(title.dimension_name, dimension_name):
                self._titles.remove(title)

    def substitute_title(self, dimension: str, element: str):
        for title in self._titles:
            if case_and_space_insensitive_equals(title.dimension_name, dimension):
                title._subset = AnonymousSubset(dimension, dimension, elements=[element])
                title._selected = element
                return

        raise ValueError(f"Dimension '{dimension}' not found in titles")

    @classmethod
    def from_mdx_builder(cls, mdx_builder: MdxBuilder, view_name: str = "") -> "NativeView":
        """Describe the cells an MdxBuilder selects as a native view

        Each set on axis 0 becomes a column and each set on axis 1 a row, as an anonymous subset: a static subset
        for a list of members, otherwise a subset holding the set's MDX expression. Each WHERE member becomes a
        title. NON EMPTY is not carried over.

        Names come from the MdxBuilder, which keeps dimension and cube names lower-cased and without spaces.

        :raises NotImplementedError: for a query a native view built in TI can't express: tuples on an axis,
        calculated members, more than two axes, a set that isn't a hierarchy set, one dimension in several places,
        or an alternate hierarchy (TI's view functions only take a dimension's same-named hierarchy)
        """
        if mdx_builder.calculated_members:
            raise NotImplementedError("A native view can't hold calculated members")
        if set(mdx_builder.axes) - {0, 1}:
            raise NotImplementedError("A native view has at most two axes (columns and rows)")

        view = cls(cube_name=cls._unescape_mdx_name(mdx_builder.cube), view_name=view_name)
        used_dimensions = set()

        def claim(dimension: str, hierarchy: str):
            key = lower_and_drop_spaces(dimension)
            if key in used_dimensions:
                raise NotImplementedError(f"Dimension '{dimension}' is used more than once in the query")
            if lower_and_drop_spaces(hierarchy) != key:
                raise NotImplementedError(f"Alternate hierarchy '{dimension}:{hierarchy}' in a native view built in TI")
            used_dimensions.add(key)

        for position in sorted(mdx_builder.axes):
            axis = mdx_builder.axes[position]
            if axis.tuples:
                raise NotImplementedError("A native view can't hold tuples on an axis")
            for mdx_set in axis.dim_sets:
                if not isinstance(mdx_set, MdxHierarchySet) or not mdx_set.dimension:
                    raise NotImplementedError(f"Set '{mdx_set.to_mdx()}' is not a set of one hierarchy")

                dimension = cls._unescape_mdx_name(mdx_set.dimension)
                claim(dimension, cls._unescape_mdx_name(mdx_set.hierarchy))
                if isinstance(mdx_set, ElementsHierarchySet):
                    subset = AnonymousSubset(dimension, dimension, elements=[m.element for m in mdx_set.members])
                else:
                    subset = AnonymousSubset(dimension, dimension, expression=mdx_set.to_mdx())

                if position == 0:
                    view.add_column(dimension, subset)
                else:
                    view.add_row(dimension, subset)

        for member in mdx_builder._where.members:
            claim(member.dimension, member.hierarchy)
            view.add_title(
                member.dimension, member.element, AnonymousSubset(member.dimension, elements=[member.element])
            )

        return view

    @staticmethod
    def _unescape_mdx_name(name: str) -> str:
        return name.replace("]]", "]")

    @classmethod
    def from_json(cls, view_as_json: str, cube_name: Optional[str] = None) -> "NativeView":
        """Alternative constructor
        :Parameters:
            `view_as_json` : string, JSON

        :Returns:
            `View` : an instance of this class
        """
        view_as_dict = json.loads(view_as_json)
        return NativeView.from_dict(view_as_dict, cube_name)

    @classmethod
    def from_dict(cls, view_as_dict: Dict, cube_name: str = None) -> "NativeView":
        titles, columns, rows = [], [], []

        for axis_selection in view_as_dict["Titles"]:
            subset = cls._build_subset_from_axis_selection(axis_selection)

            if "Selected" in axis_selection:
                selected = axis_selection["Selected"]["Name"]

            elif "Selected@odata.bind" in axis_selection:
                selected = read_object_name_from_url(
                    url=axis_selection["Selected@odata.bind"],
                    pattern=r"Dimensions\('.*?'\)/Hierarchies\('.*?'\)/Elements\('(.+?)'\)",
                )

                if not selected:
                    raise ValueError(
                        f"Unexpected value for 'Selected@odata.bind' property " f"in view title dict: '{selected}'"
                    )

            else:
                raise ValueError("View Title dict must contain 'Selected' or 'Selected@odata.bind' as key")

            titles.append(ViewTitleSelection(dimension_name=subset.dimension_name, subset=subset, selected=selected))

        for i, axis in enumerate([view_as_dict["Columns"], view_as_dict["Rows"]]):
            for axis_selection in axis:
                subset = cls._build_subset_from_axis_selection(axis_selection)

                axis_selection = ViewAxisSelection(dimension_name=subset.dimension_name, subset=subset)
                columns.append(axis_selection) if i == 0 else rows.append(axis_selection)

        if not cube_name:
            cube_name = view_as_dict["@odata.context"][20 : view_as_dict["@odata.context"].find("')/")]
        return cls(
            cube_name=cube_name,
            view_name=view_as_dict["Name"],
            suppress_empty_columns=view_as_dict["SuppressEmptyColumns"],
            suppress_empty_rows=view_as_dict["SuppressEmptyRows"],
            format_string=view_as_dict["FormatString"],
            titles=titles,
            columns=columns,
            rows=rows,
            dynamic_properties=cls._filter_dynamic_properties(view_as_dict),
        )

    @classmethod
    def _build_subset_from_axis_selection(cls, axis_selection) -> "Subset":
        if "Subset" in axis_selection:
            if not axis_selection["Subset"].get("Name", ""):
                subset = AnonymousSubset.from_dict(axis_selection["Subset"])
            else:
                subset = Subset.from_dict(axis_selection["Subset"])

        elif "Subset@odata.bind" in axis_selection:
            subset_name = read_object_name_from_url(
                url=axis_selection["Subset@odata.bind"],
                pattern=r"Dimensions\('.*?'\)/Hierarchies\('.*?'\)/Subsets\('(.+?)'\)",
            )
            dimension_name = read_object_name_from_url(
                url=axis_selection["Subset@odata.bind"], pattern=r"Dimensions\('(.*?)'\)/Hierarchies\('(.+?)'\)"
            )
            subset = Subset(
                subset_name=subset_name,
                dimension_name=dimension_name,
                # alternate hierarchies can are not supported in classic TM1 views
                hierarchy_name=dimension_name,
            )
        else:
            raise ValueError("View Axis Selection dict must contain 'Subset' or 'Subset@odata.bind' as key")
        return subset

    def _construct_body(self) -> str:
        """construct the ODATA conform JSON representation for the NativeView entity.

        :return: string, the valid JSON
        """
        body = {
            "@odata.type": "ibm.tm1.api.v1.NativeView",
            "Name": self._name,
            "Columns": [json.loads(column.body) for column in self._columns],
            "Rows": [json.loads(row.body) for row in self._rows],
            "Titles": [json.loads(title.body) for title in self._titles],
            "SuppressEmptyColumns": self._suppress_empty_columns,
            "SuppressEmptyRows": self._suppress_empty_rows,
            "FormatString": self._format_string,
        }

        dynamic_props = self._filter_dynamic_properties(self._dynamic_properties)
        if dynamic_props:
            body.update(dynamic_props)

        return json.dumps(body, ensure_ascii=False)
