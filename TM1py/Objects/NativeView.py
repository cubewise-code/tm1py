# -*- coding: utf-8 -*-

import json
from typing import Optional, Iterable, List, Union, Dict

from TM1py.Objects.Axis import ViewAxisSelection, ViewTitleSelection
from TM1py.Objects.Subset import Subset, AnonymousSubset
from TM1py.Objects.View import View
from TM1py.Utils import case_and_space_insensitive_equals


class NativeView(View):
    """ Abstraction of TM1 NativeView (classic cube view)

        :Notes:
            Complete, functional and tested
    """

    def __init__(self,
                 cube_name: str,
                 view_name: str,
                 suppress_empty_columns: Optional[bool] = False,
                 suppress_empty_rows: Optional[bool] = False,
                 format_string: Optional[str] = "0.#########",
                 titles: Optional[Iterable[ViewTitleSelection]] = None,
                 columns: Optional[Iterable[ViewAxisSelection]] = None,
                 rows: Optional[Iterable[ViewAxisSelection]] = None):
        super().__init__(cube_name, view_name)
        self._suppress_empty_columns = suppress_empty_columns
        self._suppress_empty_rows = suppress_empty_rows
        self._format_string = format_string
        self._titles = list(titles) if titles else []
        self._columns = list(columns) if columns else []
        self._rows = list(rows) if rows else []

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
    def MDX(self) -> str:
        return self.as_MDX

    @property
    def as_MDX(self) -> str:
        """ Build a valid MDX Query from an Existing cubeview. 
        Takes Zero suppression into account. 
        Throws an Exception when no elements are place on the columns.
        Subsets are referenced in the result-MDX through the TM1SubsetToSet Function

        :return: String, the MDX Query
        """
        mdx = 'SELECT '
        for i, axe in enumerate((self._rows, self._columns)):
            for j, axis_selection in enumerate(axe):
                subset = axis_selection.subset
                if isinstance(subset, AnonymousSubset):
                    if subset.expression is not None:
                        if j == 0:
                            if self.suppress_empty_rows:
                                mdx += 'NON EMPTY '
                            mdx += subset.expression
                        else:
                            mdx += '*' + subset.expression
                    else:
                        elements_as_unique_names = ['[' + axis_selection.dimension_name + '].[' + elem + ']'
                                                    for elem
                                                    in subset.elements]
                        mdx_set = '{' + ','.join(elements_as_unique_names) + '}'
                        if j == 0:
                            if self.suppress_empty_columns:
                                mdx += 'NON EMPTY '
                            mdx += mdx_set
                        else:
                            mdx += '*' + mdx_set
                else:
                    mdx_set = 'TM1SubsetToSet([{}],"{}")'.format(axis_selection.dimension_name, subset.name)
                    if j == 0:
                        if self.suppress_empty_columns:
                            mdx += 'NON EMPTY '
                        mdx += mdx_set
                    else:
                        mdx += '*' + mdx_set

            if i == 0:
                if len(self._rows) > 0:
                    mdx += ' on {}, '.format('ROWS')
            else:
                mdx += ' on {} '.format('COLUMNS')

        # append the FROM statement
        mdx += ' FROM [' + self._cube + '] '

        # itarate through titles - append the WHERE statement
        if len(self._titles) > 0:
            unique_names = []
            for title_selection in self._titles:
                dimension_name = title_selection.dimension_name
                selection = title_selection.selected
                unique_names.append('[' + dimension_name + '].[' + selection + ']')
            mdx += 'WHERE (' + ','.join(unique_names) + ') '
        return mdx

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
        """ Add Dimension or Subset to the column-axis

        :param dimension_name: name of the dimension
        :param subset: instance of TM1py.Subset. Can be None
        :return:
        """
        view_axis_selection = ViewAxisSelection(dimension_name=dimension_name, subset=subset)
        self._columns.append(view_axis_selection)

    def remove_column(self, dimension_name: str):
        """ remove dimension from the column axis

        :param dimension_name:
        :return:
        """
        for column in self._columns[:]:
            if case_and_space_insensitive_equals(column.dimension_name, dimension_name):
                self._columns.remove(column)

    def add_row(self, dimension_name: str, subset: Subset = None):
        """ Add Dimension or Subset to the row-axis

        :param dimension_name:
        :param subset: instance of TM1py.Subset. Can be None instead.
        :return:
        """
        view_axis_selection = ViewAxisSelection(dimension_name=dimension_name, subset=subset)
        self._rows.append(view_axis_selection)

    def remove_row(self, dimension_name: str):
        """ remove dimension from the row axis

        :param dimension_name:
        :return:
        """
        for row in self._rows[:]:
            if case_and_space_insensitive_equals(row.dimension_name, dimension_name):
                self._rows.remove(row)

    def add_title(self, dimension_name: str, selection: str, subset: Union[Subset, AnonymousSubset] = None):
        """ Add subset and element to the titles-axis

        :param dimension_name: name of the dimension.
        :param selection: name of an element.
        :param subset:  instance of TM1py.Subset. Can be None instead.
        :return:
        """
        view_title_selection = ViewTitleSelection(dimension_name, subset, selection)
        self._titles.append(view_title_selection)

    def remove_title(self, dimension_name: str):
        """ Reemove dimension from the titles-axis

        :param dimension_name: name of the dimension.
        :return:
        """
        for title in self._titles[:]:
            if case_and_space_insensitive_equals(title.dimension_name, dimension_name):
                self._titles.remove(title)

    @classmethod
    def from_json(cls, view_as_json: str, cube_name: Optional[str] = None) -> 'NativeView':
        """ Alternative constructor
                :Parameters:
                    `view_as_json` : string, JSON

                :Returns:
                    `View` : an instance of this class
        """
        view_as_dict = json.loads(view_as_json)
        return NativeView.from_dict(view_as_dict, cube_name)

    @classmethod
    def from_dict(cls, view_as_dict: Dict, cube_name: str = None) -> 'NativeView':
        titles, columns, rows = [], [], []

        for selection in view_as_dict['Titles']:
            if selection['Subset']['Name'] == '':
                subset = AnonymousSubset.from_dict(selection['Subset'])
            else:
                subset = Subset.from_dict(selection['Subset'])
            selected = selection['Selected']['Name']
            titles.append(ViewTitleSelection(dimension_name=subset.dimension_name,
                                             subset=subset, selected=selected))
        for i, axe in enumerate([view_as_dict['Columns'], view_as_dict['Rows']]):
            for selection in axe:
                if selection['Subset']['Name'] == '':
                    subset = AnonymousSubset.from_dict(selection['Subset'])
                else:
                    subset = Subset.from_dict(selection['Subset'])
                axis_selection = ViewAxisSelection(dimension_name=subset.dimension_name,
                                                   subset=subset)
                columns.append(axis_selection) if i == 0 else rows.append(axis_selection)

        return cls(
            cube_name=view_as_dict["@odata.context"][20:view_as_dict["@odata.context"].find("')/")]
            if not cube_name else cube_name,
            view_name=view_as_dict['Name'],
            suppress_empty_columns=view_as_dict['SuppressEmptyColumns'],
            suppress_empty_rows=view_as_dict['SuppressEmptyRows'],
            format_string=view_as_dict['FormatString'],
            titles=titles,
            columns=columns,
            rows=rows)

    def _construct_body(self) -> str:
        """ construct the ODATA conform JSON representation for the NativeView entity.

        :return: string, the valid JSON
        """
        top_json = "{\"@odata.type\": \"ibm.tm1.api.v1.NativeView\",\"Name\": \"" + self._name + "\","
        columns_json = ','.join([column.body for column in self._columns])
        rows_json = ','.join([row.body for row in self._rows])
        titles_json = ','.join([title.body for title in self._titles])
        bottom_json = "\"SuppressEmptyColumns\": " + str(self._suppress_empty_columns).lower() + \
                      ",\"SuppressEmptyRows\":" + str(self._suppress_empty_rows).lower() + \
                      ",\"FormatString\": \"" + self._format_string + "\"}"
        return "".join([
            top_json,
            '\"Columns\":[',
            columns_json,
            '],\"Rows\":[',
            rows_json,
            '],\"Titles\":[',
            titles_json,
            '],',
            bottom_json])
