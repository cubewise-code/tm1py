import collections
import csv
import functools
import http.client as http_client
import json
import math
import re
import ssl
import urllib.parse as urlparse
from enum import Enum, unique
from io import StringIO
from typing import Any, Dict, List, Tuple, Iterable, Optional, Generator, Union, Callable
from urllib.parse import unquote

import pytz
import requests
from mdxpy import MdxBuilder, Member
from requests.adapters import HTTPAdapter

from TM1py.Exceptions.Exceptions import (
    TM1pyVersionException,
    TM1pyNotAdminException,
    TM1pyNotDataAdminException,
    TM1pyNotSecurityAdminException,
    TM1pyNotOpsAdminException,
    TM1pyVersionDeprecationException,
)

try:
    import pandas as pd
    import numpy as np

    _has_pandas = True
except ImportError:
    _has_pandas = False


def decohints(decorator: Callable) -> Callable:
    """
    Decorator for decorators to see parameters of decorated functions in PyCharm

    Implementation of https://github.com/gri-gus/decohints
    """
    return decorator


@decohints
def odata_track_changes_header(func):
    """Higher Order function to handle addition and removal of odata.track-changes HTTP Header

    :param func:
    :return:
    """

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        # Add header
        self._rest.add_http_header("Prefer", "odata.track-changes")
        # Do stuff
        response = func(self, *args, **kwargs)
        # Remove Header
        self._rest.remove_http_header("Prefer")
        return response

    return wrapper


@decohints
def require_admin(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self.is_admin:
            raise TM1pyNotAdminException(func.__name__)
        return func(self, *args, **kwargs)

    return wrapper


@decohints
def require_data_admin(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self.is_data_admin:
            raise TM1pyNotDataAdminException(func.__name__)
        return func(self, *args, **kwargs)

    return wrapper


@decohints
def require_security_admin(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self.is_security_admin:
            raise TM1pyNotSecurityAdminException(func.__name__)
        return func(self, *args, **kwargs)

    return wrapper


@decohints
def require_ops_admin(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self.is_ops_admin:
            raise TM1pyNotOpsAdminException(func.__name__)
        return func(self, *args, **kwargs)

    return wrapper


@decohints
def require_version(version):
    """Higher order function to check required version for TM1py function"""

    def wrap(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            if not verify_version(required_version=version, version=self.version):
                raise TM1pyVersionException(func.__name__, version)
            return func(self, *args, **kwargs)

        return wrapper

    return wrap


@decohints
def deprecated_in_version(version):
    """Higher order function to check required version for TM1py function"""

    def wrap(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            if verify_version(required_version=version, version=self.version):
                raise TM1pyVersionDeprecationException(func.__name__, version)
            return func(self, *args, **kwargs)

        return wrapper

    return wrap


@decohints
def require_pandas(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            import pandas

            return func(self, *args, **kwargs)
        except ImportError:
            raise ImportError(f"Function '{func.__name__}' requires pandas")

    return wrapper


@decohints
def require_networkx(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            import networkx

            return func(*args, **kwargs)
        except ImportError:
            raise ImportError(f"Function '{func.__name__}' requires networkx")

    return wrapper


def get_all_servers_from_adminhost(adminhost="localhost", port=None, use_ssl=False) -> List:
    from TM1py.Objects import Server

    """ Ask Adminhost for TM1 Servers
    :param adminhost: IP or DNS Alias of the adminhost
    :param port: numeric port to connect to adminhost
    :param ssl: True for secure connection
    :return: List of Servers (instances of the TM1py.Server class)
    """

    if not use_ssl:
        conn = http_client.HTTPConnection(adminhost, port or 5895)
    else:
        conn = http_client.HTTPSConnection(adminhost, port or 5898, context=ssl._create_unverified_context())
    request = "/api/v1/Servers"
    conn.request("GET", request, body="")
    response = conn.getresponse().read().decode("utf-8")
    response_as_dict = json.loads(response)
    servers = []
    for server_as_dict in response_as_dict["value"]:
        server = Server(server_as_dict)
        servers.append(server)
    return servers


def create_server_on_adminhost(adminhost: str = "localhost", server_as_dict: Dict = None):
    from TM1py.Objects import Server

    """  Create new TM1 instance on Adminhost
    :param adminhost: IP or DNS Alias of the adminhost
    :param server_as_dict: 
            server_as_dict = {
                "Name":"MyModel1",
                "IPAddress":"172.20.10.10",
                "IPv6Address":None,
                "PortNumber":12345,
                "UsingSSL": True,
                "ClientMessagePortNumber":61098,
                "HTTPPortNumber":12999,
                "ClientExportSSLSvrCert":True,
                "ClientExportSSLSvrKeyID":"whateverExportSSLSvrKeyID",
                "AcceptingClients":True }
    :return: instance of TM1py.Server
    """

    if not server_as_dict:
        raise ValueError("server_as_dict must be provided")

    if not adminhost:
        adminhost = "localhost"

    url = f"http://{adminhost}:5895/Servers"
    response = requests.post(url, data=json.dumps(server_as_dict), headers={"Content-Type": "application/json"})
    response.raise_for_status()

    return Server(response.json())


def delete_server_on_adminhost(adminhost: str = None, server_name: str = None):
    if not server_name:
        raise ValueError("server_name must be provided")

    if not adminhost:
        adminhost = "localhost"

    url = f"http://{adminhost}:5895/Servers('{server_name}')"
    response = requests.delete(url, headers={"Content-Type": "application/json"})
    response.raise_for_status()


def update_server_on_adminhost(adminhost: str = "localhost", server_as_dict: Dict = None):
    from TM1py.Objects import Server

    """  Create new TM1 instance on Adminhost
    :param adminhost: IP or DNS Alias of the adminhost
    :param server_as_dict: 
            server_as_dict = {
                "Name":"MyModel1",
                "IPAddress":"172.20.10.10",
                "IPv6Address":None,
                "PortNumber":12345,
                "UsingSSL": True,
                "ClientMessagePortNumber":61098,
                "HTTPPortNumber":12999,
                "ClientExportSSLSvrCert":True,
                "ClientExportSSLSvrKeyID":"whateverExportSSLSvrKeyID",
                "AcceptingClients":True }
    :return: instance of TM1py.Server
    """

    if not server_as_dict:
        raise ValueError("server_as_dict must be provided")

    if not adminhost:
        adminhost = "localhost"

    url = f"http://{adminhost}:5895/Servers"
    response = requests.patch(url, body=json.dumps(server_as_dict), headers={"Content-Type": "application/json"})
    response.raise_for_status()

    return Server(response.json())


def build_url_friendly_object_name(object_name: str) -> str:
    return (
        object_name.replace("'", "''").replace("%", "%25").replace("#", "%23").replace("?", "%3F").replace("&", "%26")
    )


def format_url(url, *args: str, **kwargs: str) -> str:
    """build url and escape single quotes in args and kwargs
    :param url: url with {} placeholders
    :param args: arguments to placeholders
    :return:
    """
    args = [build_url_friendly_object_name(arg) if isinstance(arg, str) else arg for arg in args]

    kwargs = {
        key: build_url_friendly_object_name(value) if isinstance(value, str) else value for key, value in kwargs.items()
    }

    return url.format(*args, **kwargs)


def abbreviate_mdx(mdx: str, size=100) -> str:
    if len(mdx) < size:
        return mdx
    else:
        return mdx[:size] + "..."


def integerize_version(version: str, precision: int = 4) -> int:
    return int(version[:precision].replace(".", "").ljust(precision, "0"))


def verify_version(required_version: str, version: str) -> bool:
    expected = integerize_version(required_version, precision=len(required_version))
    actual = integerize_version(version, precision=len(required_version))
    return actual >= expected


def case_and_space_insensitive_equals(item1: str, item2: str) -> bool:
    return lower_and_drop_spaces(item1) == lower_and_drop_spaces(item2)


def extract_axes_from_cellset(raw_cellset_as_dict: Dict) -> Tuple[Any, ...]:
    raw_axes = raw_cellset_as_dict["Axes"]

    axes = list()

    for axis in raw_axes:
        if axis and "Tuples" in axis and len(axis["Tuples"]) > 0:
            axes.append(axis)

    return tuple(axes)


def extract_unique_names_from_members(members: Iterable[Dict]) -> List[str]:
    """Extract list of unique names from part of the cellset response
    in:
    [{'UniqueName': '[dim1].[dim1].[elem1]', 'Element': {'UniqueName': '[dim1].[dim1].[elem1]'}},
    {'UniqueName': '[dim2].[dim2].[elem3]', 'Element': {'UniqueName': '[dim2].[dim2].[elem3]'}}]
    out:
    ["[dim1].[dim1].[elem1]", "[dim2].[dim2].[elem3]"]
    :param members: dictionary
    :return: list of unique names
    """
    return [m["Element"]["UniqueName"] if "Element" in m and m["Element"] else m["UniqueName"] for m in members]


def extract_element_names_from_members(members: Iterable[Dict]) -> List[str]:
    """Extract list of unique names from part of the cellset response
    in:
    [{'UniqueName': '[dim1].[dim1].[elem1]', 'Element': {'UniqueName': '[dim1].[dim1].[elem1]'}},
    {'UniqueName': '[dim2].[dim2].[elem3]', 'Element': {'UniqueName': '[dim2].[dim2].[elem3]'}}]
    out:
    ["elem1", "elem3"]
    :param members: dictionary
    :return: list of unique names
    """
    return [m["Element"]["Name"] if "Element" in m and m["Element"] else m["Name"] for m in members]


def sort_coordinates(
    cube_dimensions: Iterable[str], unsorted_coordinates: Iterable[str], element_unique_names: True
) -> Tuple[str]:
    sorted_coordinates = []
    for dimension in cube_dimensions:
        # could be more than one hierarchy!
        address_elements = [item for item in unsorted_coordinates if item.startswith("[" + dimension + "].")]
        # address_elements could be ( [dim1].[hier1].[elem1], [dim1].[hier2].[elem3] )
        for address_element in address_elements:
            if element_unique_names:
                coordinate = address_element
            else:
                coordinate = element_name_from_element_unique_name(address_element)
            sorted_coordinates.append(coordinate)
    return tuple(sorted_coordinates)


def build_content_from_cellset_dict(
    raw_cellset_as_dict: Dict,
    top: Optional[int] = None,
    element_unique_names: bool = True,
    skip_cell_properties: bool = False,
    skip_sandbox_dimension: bool = False,
) -> "CaseAndSpaceInsensitiveTuplesDict":
    """transform raw cellset data into concise dictionary
    :param raw_cellset_as_dict:
    :param top: Int, number of cells to return (counting from top)
    :param element_unique_names: '[d1].[h1].[e1]' or 'e1'
    :param skip_cell_properties: cell values in result dictionary, instead of cell_properties dictionary
    :param skip_sandbox_dimension: skip sandbox dimension
    :return:
    """
    cube_dimensions = [dim["Name"] for dim in raw_cellset_as_dict["Cube"]["Dimensions"]]
    if skip_sandbox_dimension and cube_dimensions[0].lower() == "sandboxes":
        cube_dimensions = cube_dimensions[1:]

    cells = raw_cellset_as_dict["Cells"]
    axes = extract_axes_from_cellset(raw_cellset_as_dict=raw_cellset_as_dict)

    content_as_dict = CaseAndSpaceInsensitiveTuplesDict()
    for cell_ordinal, cell in enumerate(cells[: top or len(cells)]):
        # if skip is used in execution we must use the original ordinal from the cell, if not we can simply enumerate
        cell_ordinal = cell.get("Ordinal", cell_ordinal)

        coordinates = []
        for axis_ordinal, axis in enumerate(axes):

            if axis_ordinal == 0:
                index_columns = cell_ordinal % axis["Cardinality"]
                coordinate = extract_unique_names_from_members(axis["Tuples"][index_columns]["Members"])
                coordinates.extend(coordinate)

            else:
                tuple_ordinal = cell_ordinal
                for pre_axis_ordinal in range(axis_ordinal):
                    tuple_ordinal = tuple_ordinal // axes[pre_axis_ordinal]["Cardinality"]

                tuple_ordinal = tuple_ordinal % axis.get("Cardinality")
                coordinate = extract_unique_names_from_members(axis["Tuples"][tuple_ordinal]["Members"])
                coordinates.extend(coordinate)

        coordinates = sort_coordinates(cube_dimensions, coordinates, element_unique_names=element_unique_names)
        content_as_dict[coordinates] = cell["Value"] if skip_cell_properties else cell
    return content_as_dict


def _build_headers_for_csv(
    row_axis: Dict,
    column_axis: Dict,
    row_dimensions: List[str],
    column_dimensions: List[str],
    include_attributes: bool,
    mdx_headers: bool = False,
):
    if not include_attributes:
        return [
            dimension if mdx_headers else dimension_name_from_element_unique_name(dimension)
            for dimension in row_dimensions + column_dimensions
        ] + ["Value"]

    headers = list()
    if row_axis:
        members = row_axis["Tuples"][0]["Members"]
        for dimension, member in zip(row_dimensions, members):
            # headers in verbose syntax e.g. [Product].[Product]
            if mdx_headers:
                headers.append(dimension)
                for attribute in member["Attributes"]:
                    headers.append(dimension + ".[" + attribute + "]")
            # headers in concise syntax e.g. Product
            else:
                headers.append(dimension_name_from_element_unique_name(dimension))
                for attribute in member["Attributes"]:
                    headers.append(attribute)

    members = column_axis["Tuples"][0]["Members"]
    for dimension, member in zip(column_dimensions, members):
        # headers in verbose syntax e.g. [Product].[Product]
        if mdx_headers:
            headers.append(dimension)
            for attribute in member["Attributes"]:
                headers.append(dimension + ".[" + attribute + "]")
        # headers in concise syntax e.g. Product
        else:
            headers.append(dimension_name_from_element_unique_name(dimension))
            for attribute in member["Attributes"]:
                headers.append(attribute)

    return headers + ["Value"]


def build_csv_from_cellset_dict(
    row_dimensions: List[str],
    column_dimensions: List[str],
    raw_cellset_as_dict: Dict,
    top: Optional[int] = None,
    csv_dialect: "csv.Dialect" = None,
    line_separator: str = "\r\n",
    value_separator: str = ",",
    include_attributes: bool = False,
    include_headers: bool = True,
    mdx_headers: bool = False,
) -> str:
    """transform raw cellset data into concise dictionary
    :param column_dimensions:
    :param row_dimensions:
    :param raw_cellset_as_dict:
    :param top: Maximum Number of cells
    :param csv_dialect: provide all csv output settings through standard library csv.Dialect
        If not provided dialect is created based on line_separator and value_separator arguments.
    :param line_separator:
    :param value_separator:
    :param include_attributes: include attribute columns
    :param include_headers: bool
    :param mdx_headers: boolean. Fully qualified hierarchy name as header instead of simple dimension name
    :return:
    """

    cells = raw_cellset_as_dict["Cells"]
    # empty cellsets produce "" in order to be compliant with previous implementation that used `/Content` API endpoint
    if len(cells) == 0:
        return ""

    if csv_dialect is None:
        csv.register_dialect("TM1py", delimiter=value_separator, lineterminator=line_separator)
        csv_dialect = csv.get_dialect("TM1py")

    csv_content = StringIO()
    csv_writer = csv.writer(csv_content, dialect=csv_dialect)

    axes = extract_axes_from_cellset(raw_cellset_as_dict=raw_cellset_as_dict)
    column_axis = axes[0]
    if len(axes) > 1:
        row_axis = axes[1]
    else:
        row_axis = list()

    num_headers = 0
    if include_headers:
        headers = _build_headers_for_csv(
            row_axis=row_axis,
            column_axis=column_axis,
            row_dimensions=row_dimensions,
            column_dimensions=column_dimensions,
            include_attributes=include_attributes,
            mdx_headers=mdx_headers,
        )
        csv_writer.writerow(headers)
        num_headers = len(headers)

    for ordinal, cell in enumerate(cells[: top or len(cells)]):
        # if skip is used in execution we must use the original ordinal from the cell, if not we can simply enumerate
        ordinal = cell.get("Ordinal", ordinal)

        line = []
        if column_axis and row_axis:
            index_rows = ordinal // column_axis["Cardinality"] % row_axis["Cardinality"]
            index_columns = ordinal % column_axis["Cardinality"]

            line_items = _build_csv_line_items_from_axis_tuple(
                members=row_axis["Tuples"][index_rows]["Members"], include_attributes=include_attributes
            )
            line.extend(line_items)

            line_items = _build_csv_line_items_from_axis_tuple(
                members=column_axis["Tuples"][index_columns]["Members"], include_attributes=include_attributes
            )
            line.extend(line_items)

        elif column_axis:
            index_rows = ordinal % column_axis["Cardinality"]

            line_items = _build_csv_line_items_from_axis_tuple(
                members=column_axis["Tuples"][index_rows]["Members"], include_attributes=include_attributes
            )
            line.extend(line_items)

        line.append(str(cell["Value"] or ""))
        if include_attributes and include_headers and not len(line) == num_headers:
            raise ValueError(
                "Invalid response. With 'include_attributes' as True,"
                " Attributes must be requested explicitly as PROPERTIES in the MDX"
            )
        csv_writer.writerow(line)

    return csv_content.getvalue().strip()


def build_dataframe_from_csv(
    raw_csv,
    sep="~",
    shaped: bool = False,
    fillna_numeric_attributes: bool = False,
    fillna_numeric_attributes_value: Any = 0,
    fillna_string_attributes: bool = False,
    fillna_string_attributes_value: Any = "",
    attribute_types_by_dimension: Dict[str, Dict[str, str]] = None,
    **kwargs,
) -> "pd.DataFrame":
    if not raw_csv:
        return pd.DataFrame()

    # make sure all element names are strings and values column is derived from data
    if "dtype" not in kwargs:
        kwargs["dtype"] = {"Value": None, **{col: str for col in range(999)}}
    try:
        df = pd.read_csv(StringIO(raw_csv), sep=sep, na_values={"Value": ["None"]}, keep_default_na=False, **kwargs)

    except ValueError:
        # retry with dtype 'str' for results with a mixed value column
        kwargs["dtype"] = {"Value": str, **{col: str for col in range(999)}}
        df = pd.read_csv(StringIO(raw_csv), sep=sep, na_values={"Value": ["None"]}, keep_default_na=False, **kwargs)

    if fillna_numeric_attributes:
        fill_numeric_bool_list = [
            attr_type.lower() == "numeric"
            for dimension, attributes in attribute_types_by_dimension.items()
            for attr_type in [dimension] + list(attributes.values())
        ]
        fill_numeric_bool_list += [False]  # for the value column
        df = df.apply(
            lambda col: (
                col.replace(["", "None"], np.nan).fillna(fillna_numeric_attributes_value)
                if fill_numeric_bool_list[list(df.columns.values).index(col.name)]
                else col
            ),
            axis=0,
        )

    if fillna_string_attributes:
        fill_string_bool_list = [
            attr_type.lower() == "string"
            for dimension, attributes in attribute_types_by_dimension.items()
            for attr_type in [dimension] + list(attributes.values())
        ]
        fill_string_bool_list += [False]  # for the value column
        df = df.apply(
            lambda col: (
                col.replace(["", "None"], np.nan).fillna(fillna_string_attributes_value)
                if fill_string_bool_list[list(df.columns.values).index(col.name)]
                else col
            ),
            axis=0,
        )

    if not shaped:
        return df

    # due to csv creation logic, last column is bottom dimension from the column selection
    df = df.pivot_table(
        index=tuple(df.columns[:-2]),
        aggfunc="sum",
        columns=df.columns[-2],
        values=df.columns[-1],
        dropna=True,
        sort=False,
    ).reset_index()

    # drop title on index
    return df.rename_axis(None, axis=1)


def _build_csv_line_items_from_axis_tuple(members: Dict, include_attributes: bool = False) -> List[str]:
    if not include_attributes:
        return extract_element_names_from_members(members)

    else:
        line_items = list()
        for member in members:

            element_name = member["Element"]["Name"] if "Element" in member and member["Element"] else member["Name"]
            line_items.append(element_name)

            attribute_values = list(member["Attributes"].values())
            for attribute_value in attribute_values:
                line_items.append(str(attribute_value) if attribute_value else "")

        return line_items


def build_ui_arrays_from_cellset(raw_cellset_as_dict: Dict, value_precision: int, top: int = None):
    """Transform raw 1,2 or 3-dimension cellset data into concise dictionary
    * Useful for grids or charting libraries that want an array of cell values per row
    * Returns 3-dimensional cell structure for tabbed grids or multiple charts
    * Rows and pages are dicts, addressable by their name. Proper order of rows can be obtained in headers[1]
    * Example 'cells' return format:
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
    :param raw_cellset_as_dict: raw data from TM1
    :param value_precision: Integer (optional) specifying number of decimal places to return
    :param top: Int, number of cells to return (counting from top)
    :return: dict : { titles: [], headers: [axis][], cells: { Page0: { Row0: { [row values], Row1: [], ...}, ...}, ...} }
    """
    header_map = build_headers_from_cellset(raw_cellset_as_dict, force_header_dimensionality=3)
    titles = header_map["titles"]
    headers = header_map["headers"]
    cardinality = header_map["cardinality"]
    value_format_string = ""

    if value_precision:
        value_format_string = "{{0:.{}f}}".format(value_precision)

    cells = {}
    ordinal_cells = 0
    for z in range(cardinality[2]):
        z_header = headers[2][z]["name"]
        pages = {}
        for y in range(cardinality[1]):
            y_header = headers[1][y]["name"]
            row = []
            for x in range(cardinality[0]):
                if top and top <= ordinal_cells:
                    break
                raw_value = raw_cellset_as_dict["Cells"][ordinal_cells]["Value"] or 0
                if value_precision:
                    row.append(float(value_format_string.format(raw_value)))
                else:
                    row.append(raw_value)
                ordinal_cells += 1
            pages[y_header] = row
        cells[z_header] = pages
    return {"titles": titles, "headers": headers, "cells": cells}


def build_ui_dygraph_arrays_from_cellset(raw_cellset_as_dict: Dict, value_precision: int = None):
    """Transform raw 1,2 or 3-dimension cellset data into dygraph-friendly format
    * Useful for grids or charting libraries that want an array of cell values per column
    * Returns 3-dimensional cell structure for tabbed grids or multiple charts
    * Example 'cells' return format:
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

    :param raw_cellset_as_dict: raw data from TM1
    :param value_precision: Integer (optional) specifying number of decimal places to return
    :return: dict : { titles: [], headers: [axis][], cells: { Page0: [  [column name, column values], [], ... ], ...} }
    """
    header_map = build_headers_from_cellset(raw_cellset_as_dict, force_header_dimensionality=3)
    titles = header_map["titles"]
    headers = header_map["headers"]
    cardinality = header_map["cardinality"]
    value_format_string = ""

    if value_precision:
        value_format_string = "{{0:.{}f}}".format(value_precision)

    cells = {}
    for z in range(cardinality[2]):
        z_header = headers[2][z]["name"]
        page = []
        for x in range(cardinality[0]):
            x_header = headers[0][x]["name"]
            row = [x_header]
            for y in range(cardinality[1]):
                cell_addr = x + cardinality[0] * y + cardinality[0] * cardinality[1] * z
                raw_value = raw_cellset_as_dict["Cells"][cell_addr]["Value"] or 0
                if value_precision:
                    row.append(float(value_format_string.format(raw_value)))
                else:
                    row.append(raw_value)
            page.append(row)
        cells[z_header] = page

    return {"titles": titles, "headers": headers, "cells": cells}


def build_headers_from_cellset(raw_cellset_as_dict: Dict, force_header_dimensionality: int = 1) -> Dict:
    """Extract dimension headers from cellset into dictionary of titles (slicers) and headers (row,column,page)
    * Title dimensions are in a single list of dicts
    * Header dimensions are a 2-dimensional list of the element dicts
      * The first dimension in the header list is the axis
      * The second dimension is the list of elements on the axis
    * Dict format: {'name': 'element or compound name', 'members': [ {dict of dimension properties}, ... ] }
      * Stacked headers on an axis will have a compount 'name' created by joining the member's 'Name' properties with a '/'
      * Stacked headers will each be listed in the 'memebers' list; Single-element headers will only have one element in list
    :param raw_cellset_as_dict: raw data from TM1
    :param force_header_dimensionality: An optional integer (1,2 or 3) to force headers array to be at least that long
    :return: dict : { titles: [ { 'name': 'xx', 'members': {} } ], headers: [axis][ { 'name': 'xx', 'members': {} } ] }
    """
    dimensionality = len(raw_cellset_as_dict["Axes"])
    cardinality = [raw_cellset_as_dict["Axes"][axis]["Cardinality"] for axis in range(dimensionality)]

    titles = []
    headers = []
    for axis in range(dimensionality):
        members = []
        for tindex in range(cardinality[axis]):
            tuples_as_dict = raw_cellset_as_dict["Axes"][axis]["Tuples"][tindex]["Members"]
            name = " / ".join(tuple(member["Name"] for member in tuples_as_dict))
            members.append({"name": name, "members": tuples_as_dict})

        if axis == dimensionality - 1 and cardinality[axis] == 1:
            titles = members
        else:
            headers.append(members)

    dimensionality = len(headers)
    cardinality = [len(headers[axis]) for axis in range(dimensionality)]

    # Handle 1, 2 and 3-dimensional cellsets. Use dummy row/page headers when missing
    if dimensionality == 1 and force_header_dimensionality > 1:
        headers += [[{"name": "Row"}]]
        cardinality.insert(1, 1)
        dimensionality += 1
    if dimensionality == 2 and force_header_dimensionality > 2:
        headers += [[{"name": "Page"}]]
        cardinality.insert(2, 1)
        dimensionality += 1

    return {"titles": titles, "headers": headers, "dimensionality": dimensionality, "cardinality": cardinality}


def dimension_hierarchy_element_tuple_from_unique_name(element_unique_name: str) -> Tuple[str, str, str]:
    """Extract dimension name, hierarchy name and element name from element unique name.
    Works with explicit and implicit hierarchy references.
    :param element_unique_name: e.g. [d1].[e1] or [d1].[leaves].[e1]
    :return: tuple of dimension name, hierarchy name, element name
    """
    dimension = dimension_name_from_element_unique_name(element_unique_name)
    element = element_name_from_element_unique_name(element_unique_name)
    if element_unique_name.count("].[") == 1:
        return dimension, dimension, element
    hierarchy = hierarchy_name_from_element_unique_name(element_unique_name)
    return dimension, hierarchy, element


def dimension_name_from_element_unique_name(element_unique_name: str) -> str:
    return element_unique_name[1 : element_unique_name.find("].[")]


def hierarchy_name_from_element_unique_name(element_unique_name: str) -> str:
    return element_unique_name[element_unique_name.find("].[") + 3 : element_unique_name.rfind("].[")]


def element_name_from_element_unique_name(element_unique_name: str) -> str:
    return element_unique_name[element_unique_name.rfind("].[") + 3 : -1].replace("]]", "]")


def element_names_from_element_unique_names(element_unique_names: Iterable[str]) -> Tuple[str]:
    """Get tuple of simple element names from the full element unique names
    :param element_unique_names: tuple of element unique names ([dim1].[hier1].[elem1], ... )
    :return: tuple of element names: (elem1, elem2, ... )
    """
    return tuple(element_name_from_element_unique_name(unique_name) for unique_name in element_unique_names)


def dimension_names_from_element_unique_names(element_unique_names: Iterable[str]) -> Tuple[str]:
    """Get tuple of simple element names from the full element unique names
    :param element_unique_names: tuple of element unique names ([dim1].[hier1].[elem1], ... )
    :return: tuple of element names: (elem1, elem2, ... )
    """
    return tuple(dimension_name_from_element_unique_name(unique_name) for unique_name in element_unique_names)


def build_element_unique_names(
    dimension_names: Iterable[str], element_names: Iterable[str], hierarchy_names: Optional[Iterable[str]] = None
) -> Generator:
    """Create tuple of unique names from dimension, hierarchy and elements

    :param dimension_names:
    :param element_names:
    :param hierarchy_names:
    :return: Generator
    """
    if not hierarchy_names:
        return ("[{}].[{}]".format(dim, elem) for dim, elem in zip(dimension_names, element_names))
    else:
        return (
            "[{}].[{}].[{}]".format(dim, hier, elem)
            for dim, hier, elem in zip(dimension_names, hierarchy_names, element_names)
        )


@require_pandas
def build_pandas_dataframe_from_cellset(
    cellset: Dict, multiindex: bool = True, sort_values: bool = True
) -> "pd.DataFrame":
    """

    :param cellset:
    :param multiindex: True or False
    :param sort_values: Boolean to control sorting in result DataFrame
    :return:
    """
    try:
        cellset_clean = {}
        coordinates = []
        for coordinates, cell in cellset.items():
            element_names = element_names_from_element_unique_names(coordinates)
            cellset_clean[element_names] = cell["Value"] if cell else None
        dimension_names = tuple(unique_name[1 : unique_name.find("].[")] for unique_name in coordinates)

        # create index
        keylist = list(cellset_clean.keys())
        index = pd.MultiIndex.from_tuples(keylist, names=dimension_names)

        # create DataFrame
        values = list(cellset_clean.values())
        df = pd.DataFrame(values, index=index, columns=["Values"])

        if not multiindex:
            df.reset_index(inplace=True)
            if sort_values:
                df.sort_values(inplace=True, by=list(dimension_names))
        return df
    except UnboundLocalError:
        message = """
            Can't build DataFrame from empty cellset. 
            Make sure the underlying MDX / View is not fully zero suppressed.
        """
        raise ValueError(message)


@require_pandas
def build_cellset_from_pandas_dataframe(
    df: "pd.DataFrame", sum_numeric_duplicates: bool = True
) -> "CaseAndSpaceInsensitiveTuplesDict":
    """

    param sum_numeric_duplicates: Aggregate numerical values for duplicated intersections
    param df: a Pandas Dataframe, with dimension-column mapping in correct order.
    As created in build_pandas_dataframe_from_cellset

    :return: a CaseAndSpaceInsensitiveTuplesDict
    """
    if isinstance(df.index, pd.MultiIndex):
        df.reset_index(inplace=True)

    if sum_numeric_duplicates:
        value_header = df.columns[-1]
        dimension_headers = df.columns[:-1]

        if pd.api.types.is_numeric_dtype(df[value_header]):
            df = aggregate_duplicate_intersections(df, dimension_headers, value_header)
        else:
            filter_mask = df[value_header].apply(np.isreal)
            df_n = df[filter_mask]
            df_s = df[~filter_mask]
            df_n = aggregate_duplicate_intersections(df_n, dimension_headers, value_header)
            df = pd.concat([df_n, df_s])

    cellset = CaseAndSpaceInsensitiveTuplesDict(
        dict(zip(df.iloc[:, :-1].itertuples(index=False, name=None), df.iloc[:, -1].values))
    )
    return cellset


def aggregate_duplicate_intersections(df, dimension_headers, value_header):
    for col in dimension_headers:
        df[col] = df[col].str.lower().str.replace(" ", "")
    return df.groupby([*dimension_headers])[value_header].sum().reset_index()


def lower_and_drop_spaces(item: str) -> str:
    return item.replace(" ", "").lower()


def get_seconds_from_duration(time_str: str) -> int:
    """
    This function will convert the TM1 time to seconds
    :param time_str: P0DT00H01M43S
    :return: int
    """
    import re

    pattern = re.compile("\w(\d+)\w\w(\d+)\w(\d+)\w(\d+)\w")
    matches = pattern.search(time_str)
    d, h, m, s = matches.groups()
    seconds = (int(d) * 86400) + (int(h) * 3600) + (int(m) * 60) + int(s)
    return seconds


def get_tm1_time_value_now(use_excel_serial_date: bool = False) -> float:
    """
    This function can be used to replicate TM1's NOW function
    to return current date/time value in serial number format.
    :param use_excel_serial_date: Boolean
    :return: serial number
    """
    from datetime import datetime

    # timestamp according to tm1
    start_datetime = datetime(1899, 12, 30) if use_excel_serial_date else datetime(1960, 1, 1)
    current_datetime = datetime.now()
    delta = current_datetime - start_datetime
    return delta.days + (delta.seconds / 86400)


def add_url_parameters(url, **kwargs: str) -> str:
    """Append parameters to url string passed in kwargs
    :param url: str
    :param kwargs: key:value pairs of url parameters. For example, {'$select':'Name'}
    :return: str
    """
    parameters = []
    for key, value in kwargs.items():
        if value is not None:
            value = value.replace("'", "''") if isinstance(value, str) else value
            parameters.append(key + "=" + value)

    url_parts = list(urlparse.urlparse(url))
    query_part = url_parts[4]
    if query_part:
        query_part += "&"
    query_part += "&".join(parameters)

    url_parts[4] = query_part
    return urlparse.urlunparse(url_parts)


def extract_compact_json_cellset(context: str, response: Dict, return_as_dict: bool) -> Union[Dict, List]:
    """Translates odata compact response json into default dictionary response or plain list (e.g., list of values)

    :param context: The context field from the TM1 response JSON
    :param response: The JSON response
    :param return_as_dict: boolean
    :return:
    """
    props = extract_cell_properties_from_odata_context(context)

    # First element [0] is the cellset ID, second is the cellset data
    cells_data = response["value"][1]

    # return props with data if required
    if return_as_dict:
        return map_cell_properties_to_compact_json_response(props, cells_data)

    if len(props) == 1:
        return [value[0] for value in cells_data]

    if props == ["Ordinal", "Value"]:
        return [value[1] for value in cells_data]

    return cells_data


def extract_cell_properties_from_odata_context(context: str) -> List[str]:
    """Takes in an odata_context and returns a list of properties e.g
      [Ordinal, Value, RuleDerived, ...]
    :param context: A valid odata_context returned when querying cells
    :return:
    """
    pattern = re.compile("\$metadata#Cellsets\(Cells\(([A-Za-z,]+)\)\)/\$entity")
    matches = pattern.match(context)
    if not matches:
        raise ValueError("Could not extract cell properties from odata context")
    cell_properties = matches.groups()[0].split(",")
    return cell_properties


def map_cell_properties_to_compact_json_response(properties: List, compact_cells_response: List) -> Dict:
    """Map cell properties to compact json response e.g
    properties = [Ordinal, Value, RuleDerived]
    compact_cells_response = [[0, 258, 100], [1, 258, 500]]
    result: {Cells: [
        { Ordinal: 0, Value: 100, RuleDerived: 258},
        { Ordinal: 1, Value: 500, RuleDerived: 258}
    ]}


    :param properties: list of `Cell` properties e.g [Ordinal, Value, Updateable, ...]
    :param compact_cells_response: list of cells returned in compact json format
    :return: dict with properties mapped to compact json response
    """
    cells_dict = dict()
    cells = []
    for cell in compact_cells_response:
        d = dict()
        for index, prop in enumerate(properties):
            d[prop] = cell[index]
        cells.append(d)
    cells_dict["Cells"] = cells
    return cells_dict


class CaseAndSpaceInsensitiveDict(collections.abc.MutableMapping):
    """
    A case-and-space-insensitive dict-like object with string keys.

    This class implements all methods and operations of `collections.abc.MutableMapping`,
    as well as dict's `copy`. It also provides `adjusted_items` and `adjusted_keys`.
    All keys are expected to be strings.

    The structure remembers the case of the last key set, and methods like `__iter__`,
    `keys()`, `items()`, etc., will contain case-sensitive keys.

    However, querying and membership tests are case-and-space-insensitive:
        data = CaseAndSpaceInsensitiveDict()
        data['Travel Expenses'] = 100
        assert data['travelexpenses'] == 100  # True

    Entries are ordered.
    """

    def __init__(self, data=None, **kwargs):
        """Initialize the dictionary with optional initial data."""
        self._store = collections.OrderedDict()
        if data is None:
            data = {}
        self.update(data, **kwargs)

    def _adjust_key(self, key):
        """Adjust the key by lowering case and removing spaces."""
        if not isinstance(key, str):
            raise TypeError("Keys must be strings.")
        return lower_and_drop_spaces(key)

    def __setitem__(self, key, value):
        """Set the value for a key, adjusting the key as needed."""
        adjusted_key = self._adjust_key(key)
        self._store[adjusted_key] = (key, value)

    def __getitem__(self, key):
        """Retrieve the value for a key, using the adjusted key."""
        adjusted_key = self._adjust_key(key)
        try:
            return self._store[adjusted_key][1]
        except KeyError:
            raise KeyError(f"Key '{key}' not found.") from None

    def __delitem__(self, key):
        """Delete the item associated with the key."""
        adjusted_key = self._adjust_key(key)
        try:
            del self._store[adjusted_key]
        except KeyError:
            raise KeyError(f"Key '{key}' not found.") from None

    def __iter__(self):
        """Iterate over the keys in their original case."""
        return (key for key, _ in self._store.values())

    def __len__(self):
        return len(self._store)

    def __contains__(self, key):
        """Check if the key exists in the dictionary."""
        adjusted_key = self._adjust_key(key)
        return adjusted_key in self._store

    def keys(self):
        """Return a view of the keys in their original case."""
        return [key for key, _ in self._store.values()]

    def values(self):
        """Return a view of the values."""
        return [value for _, value in self._store.values()]

    def items(self):
        """Return a view of the items in their original case."""
        return [(key, value) for key, value in self._store.values()]

    def adjusted_keys(self):
        """Return a generator of the adjusted keys."""
        return (adjusted_key for adjusted_key in self._store.keys())

    def adjusted_items(self):
        """Return a generator of (adjusted_key, value) pairs."""
        return ((adjusted_key, key_value[1]) for adjusted_key, key_value in self._store.items())

    def __eq__(self, other):
        """Check equality with another dictionary."""
        if isinstance(other, collections.abc.Mapping):
            other = CaseAndSpaceInsensitiveDict(other)
        else:
            return NotImplemented
        return dict(self.adjusted_items()) == dict(other.adjusted_items())

    def copy(self):
        return CaseAndSpaceInsensitiveDict(self._store.values())

    def update(self, other=(), **kwargs):
        """
        Update the dictionary with key/value pairs from other, overwriting existing keys.

        Parameters:
            other (Mapping or Iterable): A mapping or iterable of key-value pairs.
            **kwargs: Additional key-value pairs.
        """
        if isinstance(other, collections.abc.Mapping):
            for key, value in other.items():
                self[key] = value

        elif hasattr(other, "__iter__"):
            for item in other:
                if not isinstance(item, collections.abc.Iterable):
                    raise TypeError("Items must be key-value pairs.")
                key, value = item
                self[key] = value

        elif other:
            raise TypeError("Other object is not a mapping or iterable of key-value pairs.")

        for key, value in kwargs.items():
            self[key] = value

    def get(self, key, default=None):
        """
        Return the value for key if key is in the dictionary, else default.

        Parameters:
            key (str): The key to look up.
            default: The value to return if the key is not found.
        """
        try:
            return self[key]
        except KeyError:
            return default

    def setdefault(self, key, default=None):
        """
        If key is in the dictionary, return its value.
        If not, insert key with a value of default and return default.

        Parameters:
            key (str): The key to look up or insert.
            default: The value to set if the key is not found.
        """
        if key in self:
            return self[key]
        else:
            self[key] = default
            return default

    def pop(self, key, default=None):
        """
        Remove the specified key and return the corresponding value.
        If key is not found, default is returned if provided, otherwise KeyError is raised.

        Parameters:
            key (str): The key to remove.
            default: The value to return if the key is not found.
        """
        adjusted_key = self._adjust_key(key)
        try:
            value = self._store.pop(adjusted_key)[1]
            return value
        except KeyError:
            if default is not None:
                return default
            else:
                raise KeyError(f"Key '{key}' not found.") from None

    def popitem(self):
        """
        Remove and return a (key, value) pair from the dictionary.
        Pairs are returned in LIFO order.

        Raises:
            KeyError: If the dictionary is empty.
        """
        adjusted_key, (key, value) = self._store.popitem()
        return key, value

    def clear(self):
        """Remove all items from the dictionary."""
        self._store.clear()

    def __repr__(self):
        """Return the dictionary's string representation."""
        items = ", ".join(f"{key!r}: {value!r}" for key, value in self.items())
        return f"{self.__class__.__name__}({{{items}}})"

    def __str__(self):
        """Return a user-friendly string representation."""
        return repr(self)


class CaseAndSpaceInsensitiveTuplesDict(collections.abc.MutableMapping):
    """
    A case-and-space-insensitive dict-like object with tuple of strings as keys.

    This class implements all methods and operations of `collections.abc.MutableMapping`,
    as well as dict's `copy`. It also provides `adjusted_items` and `adjusted_keys`.
    All keys are expected to be tuples of strings.

    The structure remembers the case of the last key set, and methods like `__iter__`,
    `keys()`, `items()`, etc., will contain case-sensitive keys.

    However, querying and membership tests are case-and-space-insensitive:
        data = CaseAndSpaceInsensitiveTuplesDict()
        data[('[Business Unit].[UK]', '[Scenario].[Worst Case]')] = 1000
        assert data[('[BusinessUnit].[UK]', '[Scenario].[worstcase]')] == 1000
        assert data[('[Business Unit].[UK]', '[Scenario].[Worst Case]')] == 1000

    Entries are ordered.
    """

    def __init__(self, data=None, **kwargs):
        """Initialize the dictionary with optional initial data."""
        self._store = collections.OrderedDict()
        if data is None:
            data = {}
        self.update(data, **kwargs)

    def _adjust_key(self, key):
        """Adjust the key by lowering case and removing spaces."""
        if not isinstance(key, tuple):
            raise TypeError("Keys must be tuples of strings.")
        try:
            return tuple(lower_and_drop_spaces(item) for item in key)
        except TypeError as e:
            raise TypeError("All items in the key tuple must be strings.") from e

    def __setitem__(self, key, value):
        """Set the value for a key, adjusting the key as needed."""
        adjusted_key = self._adjust_key(key)
        self._store[adjusted_key] = (key, value)

    def __getitem__(self, key):
        """Retrieve the value for a key, using the adjusted key."""
        adjusted_key = self._adjust_key(key)
        try:
            return self._store[adjusted_key][1]
        except KeyError:
            raise KeyError(f"Key {key} not found.") from None

    def __delitem__(self, key):
        """Delete the item associated with the key."""
        adjusted_key = self._adjust_key(key)
        try:
            del self._store[adjusted_key]
        except KeyError:
            raise KeyError(f"Key {key} not found.") from None

    def __iter__(self):
        """Iterate over the keys in their original case."""
        return (key for key, _ in self._store.values())

    def __len__(self):
        """Return the number of items in the dictionary."""
        return len(self._store)

    def __contains__(self, key):
        """Check if the key exists in the dictionary."""
        adjusted_key = self._adjust_key(key)
        return adjusted_key in self._store

    def keys(self):
        """Return a view of the keys in their original case."""
        return [key for key, _ in self._store.values()]

    def values(self):
        """Return a view of the values."""
        return [value for _, value in self._store.values()]

    def items(self):
        """Return a view of the items (key-value pairs)."""
        return [(key, value) for key, value in self._store.values()]

    def adjusted_keys(self):
        """Return a generator of the adjusted keys."""
        return (adjusted_key for adjusted_key in self._store.keys())

    def adjusted_items(self):
        """Return a generator of (adjusted_key, value) pairs."""
        return ((adjusted_key, key_value[1]) for adjusted_key, key_value in self._store.items())

    def __eq__(self, other):
        """Check equality with another dictionary."""
        if isinstance(other, collections.abc.Mapping):
            other = CaseAndSpaceInsensitiveTuplesDict(other)
        else:
            return NotImplemented
        return dict(self.adjusted_items()) == dict(other.adjusted_items())

    def copy(self):
        """Create a shallow copy of the dictionary."""
        new_copy = CaseAndSpaceInsensitiveTuplesDict()
        new_copy._store = self._store.copy()
        return new_copy

    def update(self, other=(), **kwargs):
        """
        Update the dictionary with key/value pairs from other, overwriting existing keys.

        Parameters:
            other (Mapping or Iterable): A mapping or iterable of key-value pairs.
            **kwargs: Additional key-value pairs.
        """
        if isinstance(other, collections.abc.Mapping):
            for key, value in other.items():
                self[key] = value

        elif hasattr(other, "__iter__"):
            for item in other:
                if not isinstance(item, collections.abc.Iterable):
                    raise TypeError("Items must be key-value pairs.")
                key, value = item
                self[key] = value

        elif other:
            raise TypeError("Other object is not a mapping or iterable of key-value pairs.")

        for key, value in kwargs.items():
            self[key] = value

    def join(self, other):
        """
        Merge another mapping or iterable of key-value pairs into this dictionary.

        Parameters:
            other (Mapping or Iterable): A mapping or iterable of key-value pairs.
        """
        self.update(other)

    def get(self, key, default=None):
        """
        Return the value for key if key is in the dictionary, else default.

        Parameters:
            key (tuple): The key to look up.
            default: The value to return if the key is not found.
        """
        try:
            return self[key]
        except KeyError:
            return default

    def setdefault(self, key, default=None):
        """
        If key is in the dictionary, return its value.
        If not, insert key with a value of default and return default.

        Parameters:
            key (tuple): The key to look up or insert.
            default: The value to set if the key is not found.
        """
        if key in self:
            return self[key]
        else:
            self[key] = default
            return default

    def pop(self, key, default=None):
        """
        Remove the specified key and return the corresponding value.
        If key is not found, default is returned if provided, otherwise KeyError is raised.

        Parameters:
            key (tuple): The key to remove.
            default: The value to return if the key is not found.
        """
        adjusted_key = self._adjust_key(key)
        try:
            value = self._store.pop(adjusted_key)[1]
            return value
        except KeyError:
            if default is not None:
                return default
            else:
                raise KeyError(f"Key {key} not found.") from None

    def popitem(self):
        """
        Remove and return a (key, value) pair from the dictionary.
        Pairs are returned in LIFO order.

        Raises:
            KeyError: If the dictionary is empty.
        """
        adjusted_key, (key, value) = self._store.popitem()
        return key, value

    def clear(self):
        """Remove all items from the dictionary."""
        self._store.clear()

    def __repr__(self):
        """Return the dictionary's string representation."""
        items = ", ".join(f"{key!r}: {value!r}" for key, value in self.items())
        return f"{self.__class__.__name__}({{{items}}})"

    def __str__(self):
        """Return a user-friendly string representation."""
        return repr(self)


class CaseAndSpaceInsensitiveSet(collections.abc.MutableSet):
    """
    A case-and-space-insensitive set-like object for strings.

    This class implements all methods and operations of `collections.abc.MutableSet`.
    All values are expected to be strings. The set remembers the case of the last
    value added, and methods like `__iter__` and `__str__` will contain case-sensitive values.

    However, membership tests are case-and-space-insensitive:
        data = CaseAndSpaceInsensitiveSet('Apple', 'Banana')
        assert 'apple' in data         # True
        assert '  BANANA ' in data     # True

    Entries are ordered based on insertion order.
    """

    def __init__(self, *values):
        self._store = {}
        for v in values:
            if isinstance(v, str):
                self.add(v)
            elif isinstance(v, Iterable):
                for item in v:
                    self.add(item)
            else:
                self.add(v)

    def _adjust_value(self, value):
        if not isinstance(value, str):
            raise TypeError("Value must be string.")
        return lower_and_drop_spaces(value)

    def __contains__(self, value):
        adjusted_value = self._adjust_value(value)
        return adjusted_value in self._store

    def __iter__(self):
        """Iterate over the values in their original case."""
        return iter(self._store.values())

    def __len__(self):
        return len(self._store)

    def add(self, value):
        adjusted_value = self._adjust_value(value)
        self._store[adjusted_value] = value

    def discard(self, value):
        adjusted_value = self._adjust_value(value)
        self._store.pop(adjusted_value, None)

    def clear(self):
        self._store.clear()

    def pop(self):
        """
        Remove and return an arbitrary element from the set.
        Raises KeyError if the set is empty.
        """
        if not self._store:
            raise KeyError("pop from an empty set")
        adjusted_value, value = self._store.popitem()
        return value

    def update(self, *others):
        """Update the set, adding elements from all others."""
        for iterable in others:
            for value in iterable:
                self.add(value)

    def __eq__(self, other):
        """Check equality with another set."""
        if not isinstance(other, collections.abc.Set):
            return NotImplemented
        return set(self._adjust_value(v) for v in self) == set(self._adjust_value(v) for v in other)

    def __ne__(self, other):
        """Check inequality with another set."""
        return not self == other

    def __sub__(self, other):
        """Return a new set with elements in the set that are not in the others."""
        result = self.copy()
        result.difference_update(other)
        return result

    def copy(self):
        """Create a shallow copy of the set."""
        return CaseAndSpaceInsensitiveSet(self)

    def __repr__(self):
        """Return the set's string representation."""
        items = ", ".join(repr(value) for value in self)
        return f"{self.__class__.__name__}([{items}])"

    def __str__(self):
        """Return a user-friendly string representation."""
        return f"{{{', '.join(map(str, self))}}}"

    def __le__(self, other):
        """Test whether every element in the set is in other."""
        return all(item in other for item in self)

    def __lt__(self, other):
        """Test whether the set is a proper subset of other."""
        return self <= other and self != other

    def __ge__(self, other):
        """Test whether every element in other is in the set."""
        return all(item in self for item in other)

    def __gt__(self, other):
        """Test whether the set is a proper superset of other."""
        return self >= other and self != other

    def __or__(self, other):
        """Return the union of the sets as a new set."""
        return self.union(other)

    def __and__(self, other):
        """Return the intersection of the sets as a new set."""
        return self.intersection(other)

    def __delitem__(self, key):
        del self._store[key.lower().replace(" ", "")]

    def difference_update(self, *others):
        """Remove all elements of another set from this set."""
        for iterable in others:
            for value in iterable:
                self.discard(value)

    def intersection(self, *others):
        """Return a new set with elements common to the set and all others."""
        new_set = CaseAndSpaceInsensitiveSet()
        for value in self:
            if all(value in other for other in others):
                new_set.add(value)
        return new_set

    def difference(self, *others):
        """Return a new set with elements in the set that are not in the others."""
        new_set = self.copy()
        new_set.difference_update(*others)
        return new_set

    def union(self, *others):
        """Return a new set with elements from the set and all others."""
        new_set = self.copy()
        new_set.update(*others)
        return new_set


def get_dimensions_from_where_clause(mdx: str) -> List[str]:
    mdx = mdx.replace(" ", "").upper()
    if "WHERE(" not in mdx:
        return []

    where = mdx[mdx.rfind("WHERE(") + 6 : -1]
    unique_names = where.split(",")
    return [dimension_name_from_element_unique_name(unique_name) for unique_name in unique_names]


def get_cube(mdx: str) -> str:
    # replace tabs, line breaks, spaces
    mdx = re.sub(r"\s+", "", mdx)

    # happy case: cube name in square brackets
    pattern = r"(?s)(?i)FROM\[(.*?)\]"
    search_result = re.search(pattern, mdx)
    if search_result:
        return search_result.group(1)

    # cut off where
    pattern = r"(?s)(?i).*SELECT.*ON.*FROM.*WHERE\(.*"
    if re.search(pattern=pattern, string=mdx):
        # part before where
        mdx = re.split(r"(?s)(?i)WHERE\(.*", mdx)[0]

    # part after from
    cube = re.split(r"(?s)(?i)FROM", mdx)[-1]

    return cube


def resembles_mdx(mdx: str) -> bool:
    pattern = r"(?s)(?i).*SELECT.*ON.*FROM.*"
    if re.search(pattern=pattern, string=mdx):
        return True
    return False


def wrap_in_curly_braces(expression: str) -> str:
    """Put curly braces around a string
    :param expression:
    :return:
    """
    return "".join(
        ["{" if not expression.startswith("{") else "", expression, "}" if not expression.endswith("}") else ""]
    )


@unique
class CellUpdateableProperty(Enum):
    SECURITY_RESTRICTED = 1
    UPDATE_CUBE_APPLICABLE = 2
    RULE_IS_APPLIED = 3
    PICKLIST_EXISTS = 4
    SANDBOX_VALUE_IS_DIFFERENT_TO_BASE = 5
    NO_SPREADING_HOLD = 9
    LEAF_HOLD = 10
    CONSOLIDATION_SPREADING_HOLD = 11
    TEMPORARY_SPREADING_HOLD = 12
    CELL_IS_NOT_UPDATEABLE = 29


def extract_cell_updateable_property(decimal_value: int, cell_property: CellUpdateableProperty) -> bool:
    """Function converts passed decimal (integer) value to binary
    and extracts specified (cell_property) bit counting from the right.
    It will return TRUE if bit is set, and FALSE if bit is not set
    Each cell has 'Updateable' property - a decimal value, which needs to be converted to binary to get information
    about the cell

    :param decimal_value: int Decimal number
    :param cell_property: CellUpdateableProperty enum property to extract from decimal value
    :return: bool

    """
    bit = (decimal_value & (1 << cell_property.value - 1)) != 0
    return bit


def cell_is_updateable(cell: dict) -> bool:
    """Function checks if the cell can be updated
    :param cell: dict cell including Updateable property
    :return: bool
    """
    if "Updateable" not in cell:
        raise ValueError("cell dictionary must contain key 'Updateable'")

    bit = extract_cell_updateable_property(cell["Updateable"], CellUpdateableProperty.CELL_IS_NOT_UPDATEABLE)
    updateable = not bit
    return updateable


def build_mdx_from_cellset(cells: Dict, cube_name: str, dimensions: Iterable[str]) -> str:
    query = MdxBuilder.from_cube(cube_name)
    for coordinates in cells:
        members = (Member.of(dimension, element) for dimension, element in zip(dimensions, coordinates))
        query.add_member_tuple_to_columns(*members)
    mdx = query.to_mdx()
    return mdx


def build_mdx_and_values_from_cellset(cells: Dict, cube_name: str, dimensions: Iterable[str]) -> Tuple[str, List]:
    values = []
    query = MdxBuilder.from_cube(cube_name)
    for coordinates, value in cells.items():
        members = (Member.of(dimension, element) for dimension, element in zip(dimensions, coordinates))
        query.add_member_tuple_to_columns(*members)
        values.append(value)
    mdx = query.to_mdx()
    return mdx, values


def frame_to_significant_digits(x, digits=15):
    if x == 0 or not math.isfinite(x):
        return str(x).replace("e+", "E")
    digits -= math.ceil(math.log10(abs(x)))
    return str(round(x, digits)).replace("e+", "E")


def drop_dimension_properties(mdx: str):
    pattern = re.compile(r"(?i)DIMENSION\s+PROPERTIES\s+.*?\s+ON")
    mdx = pattern.sub(" ON", mdx)

    pattern = re.compile(r"(?i)\s+PROPERTIES\s+.*?\s+ON")
    return pattern.sub(" ON", mdx)


def read_object_name_from_url(url: str, pattern: str) -> str:
    match = re.match(pattern, url)
    if not match:
        return None

    return unquote(match.group(1))


def utc_localize_time(timestamp):
    timestamp = pytz.utc.localize(timestamp)
    timestamp_utc = timestamp.astimezone(pytz.utc)
    return timestamp_utc


def reorder_with_priority(
    original_items: List[Any],
    priority_items: List[Any] = None,
    exclude_items: List[Any] = None,
    sort_remaining: bool = True,
    **kwargs,
) -> List[Any]:
    """
    Reorder a list of original items so that items in 'priority_items' list appear first (in specified order),
    followed by the remaining items of original items. The order of the remaining items depends on the
    'sort_remaining' parameter: if True, the original order is preserved; if False, the items
    are sorted alphabetically. Items in the 'exclude_items' list are omitted. Missing priority items
    and exclude items are ignored.

    Example case: hierarchy names
    "correct" order: first the main hierarchy name (matching the dimension name),
    then the Leaves hierarchy, then the other hierarchy names (sorted or not).
    When trying to create the Leaves hierarchy when it already exists (because of creating a different alternate hierarchy),
    an error pops up. Set exclude_items equal to ['Leaves'].
    """
    result = [s for s in priority_items if s in original_items]
    remaining = [s for s in original_items if (s not in result) and (s not in exclude_items)]
    result += sorted(remaining) if sort_remaining else remaining
    return result


class HTTPAdapterWithSocketOptions(HTTPAdapter):
    def __init__(self, *args, **kwargs):
        self.socket_options = kwargs.pop("socket_options", None)
        self.ssl_context = kwargs.pop("ssl_context", None)
        super(HTTPAdapterWithSocketOptions, self).__init__(*args, **kwargs)

    def init_poolmanager(self, *args, **kwargs):
        # must use hasattr here, as socket_options may be not-set in case TM1Service was created with restore_from_file
        if hasattr(self, "socket_options"):
            kwargs["socket_options"] = self.socket_options
        if hasattr(self, "ssl_context"):
            kwargs["ssl_context"] = self.ssl_context
        super(HTTPAdapterWithSocketOptions, self).init_poolmanager(*args, **kwargs)
