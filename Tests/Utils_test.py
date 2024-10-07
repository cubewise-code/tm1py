import configparser
import unittest
from pathlib import Path

try:
    import numpy as np
    import pandas as pd
except ImportError:
    pass

from TM1py.Services import TM1Service
from TM1py.Utils import (
    Utils,
    get_dimensions_from_where_clause,
    integerize_version,
    verify_version, get_cube, resembles_mdx, format_url, add_url_parameters, extract_cell_updateable_property,
    CellUpdateableProperty, cell_is_updateable, extract_cell_properties_from_odata_context,
    map_cell_properties_to_compact_json_response, frame_to_significant_digits, drop_dimension_properties,
    build_dataframe_from_csv
)
from .Utils import skip_if_version_higher_or_equal_than, skip_if_paoc


class TestUtilsMethods(unittest.TestCase):
    tm1: TM1Service

    @classmethod
    def setUpClass(cls):
        """
        Establishes a connection to TM1 and creates TM1 objects to use across all tests
        """

        # Connection to TM1
        cls.config = configparser.ConfigParser()
        cls.config.read(Path(__file__).parent.joinpath("config.ini"))
        cls.tm1 = TM1Service(**cls.config["tm1srv01"])

    @skip_if_paoc
    @skip_if_version_higher_or_equal_than(version="12")
    def test_get_instances_from_adminhost(self):
        servers = Utils.get_all_servers_from_adminhost(
            self.config["tm1srv01"]["address"]
        )
        self.assertGreater(len(servers), 0)

    def test_integerize_version(self):
        version = "11.0.00000.918"
        integerized_version = integerize_version(version)
        self.assertEqual(1100, integerized_version)

        version = "11.0.00100.927-0"
        integerized_version = integerize_version(version)
        self.assertEqual(1100, integerized_version)

        version = "11.1.00004.2"
        integerized_version = integerize_version(version)
        self.assertEqual(1110, integerized_version)

        version = "11.2.00000.27"
        integerized_version = integerize_version(version)
        self.assertEqual(1120, integerized_version)

        version = "11.3.00003.1"
        integerized_version = integerize_version(version)
        self.assertEqual(1130, integerized_version)

        version = "11.4.00003.8"
        integerized_version = integerize_version(version)
        self.assertEqual(1140, integerized_version)

        version = "11.7.00002.1"
        integerized_version = integerize_version(version)
        self.assertEqual(1170, integerized_version)

        version = "11.8.00000.33"
        integerized_version = integerize_version(version)
        self.assertEqual(1180, integerized_version)

    def test_verify_version_true(self):
        required_version = "11.7.00002.1"
        version = "11.8.00000.33"

        result = verify_version(required_version=required_version, version=version)
        self.assertEqual(True, result)

    def test_verify_version_false(self):
        required_version = "11.7.00002.1"
        version = "11.2.00000.27"

        result = verify_version(required_version=required_version, version=version)
        self.assertEqual(False, result)

    def test_verify_version_equal(self):
        required_version = "11.7.00002.1"
        version = "11.7.00002.1"

        result = verify_version(required_version=required_version, version=version)
        self.assertEqual(True, result)

    def test_verify_version_long(self):
        required_version = "11.8.015"
        version = "11.8.00100.13"

        result = verify_version(required_version=required_version, version=version)
        self.assertEqual(False, result)

    def test_get_dimensions_from_where_clause_happy_case(self):
        mdx = """
        SELECT {[dim3].[e2]} ON COLUMNS, {[dim4].[e5]} ON ROWS FROM [cube] WHERE ([dim2].[e1], [dim1].[e4])
        """
        dimensions = get_dimensions_from_where_clause(mdx)
        self.assertEqual(["DIM2", "DIM1"], dimensions)

    def test_build_dataframe_from_csv(self):
        raw_csv = (
            "d1~d2~Value\r\n"
            "e1~e1~1.0\r\n"
            "e1~e2~2.0\r\n"
            "e2~e1~3.0\r\n"
            "e2~e2~4.0"
        )
        df = build_dataframe_from_csv(raw_csv)

        expected_df = pd.DataFrame({
            'd1': ["e1", "e1", "e2", "e2"],
            'd2': ["e1", "e2", "e1", "e2"],
            'Value': [1.0, 2.0, 3.0, 4.0],
        })

        pd._testing.assert_frame_equal(expected_df, df, check_column_type=False)

    def test_build_dataframe_from_csv_with_none_element_and_none_value(self):
        raw_csv = (
            "d1~d2~Value\r\n"
            "e1~e1~None\r\n"
            "e1~e2~2.0\r\n"
            "None~e1~3.0\r\n"
            "None~e2~4.0"
        )
        df = build_dataframe_from_csv(raw_csv)

        expected_df = pd.DataFrame({
            'd1': ["e1", "e1", "None", "None"],
            'd2': ["e1", "e2", "e1", "e2"],
            'Value': [np.nan, 2.0, 3.0, 4.0],
        }).astype(object)

        pd._testing.assert_frame_equal(expected_df, df, check_column_type=False, check_dtype=False, check_exact=False)

    def test_build_dataframe_from_csv_with_none_and_empty_string_value(self):
        raw_csv = (
            "d1~d2~Value\r\n"
            "e1~e1~None\r\n"
            "e1~e2~\"\"\r\n"
            "None~e1~3.0\r\n"
            "None~e2~4.0"
        )
        df = build_dataframe_from_csv(raw_csv)

        expected_df = pd.DataFrame({
            'd1': ["e1", "e1", "None", "None"],
            'd2': ["e1", "e2", "e1", "e2"],
            'Value': [np.nan, "", "3.0", "4.0"],
        }).astype(object)

        pd._testing.assert_frame_equal(expected_df, df, check_column_type=False, check_dtype=False, check_exact=False)


    def test_get_dimensions_from_where_clause_no_where(self):
        mdx = """
        SELECT {[dim3].[e2]} ON COLUMNS, {[dim4].[e5]} ON ROWS FROM [cube]
        """
        dimensions = get_dimensions_from_where_clause(mdx)
        self.assertEqual([], dimensions)

    def test_get_dimensions_from_where_clause_casing(self):
        mdx = """
        SELECT {[dim3].[e2]} ON COLUMNS, {[dim4].[e5]} ON ROWS FROM [cube] WhEre ([dim1].[e4])
        """
        dimensions = get_dimensions_from_where_clause(mdx)
        self.assertEqual(["DIM1"], dimensions)

    def test_get_dimensions_from_where_clause_spacing(self):
        mdx = """
        SELECT {[dim3].[e2]} ON COLUMNS, {[dim4].[e5]} ON ROWS FROM [cube] WHERE([dim5]. [e4] )
        """
        dimensions = get_dimensions_from_where_clause(mdx)
        self.assertEqual(["DIM5"], dimensions)

    def test_get_cube(self):
        mdx = """
        SELECT {[dim3].[e2]} ON COLUMNS, {[dim4].[e5]} ON ROWS FROM [cube] WHERE([dim5]. [e4] )
        """
        cube_name = get_cube(mdx)
        self.assertEqual(cube_name, "cube")

    def test_get_cube_without_brackets(self):
        mdx = """
        SELECT {[dim3].[e2]} ON COLUMNS, {[dim4].[e5]} ON ROWS FROM cube WHERE([dim5]. [e4] )
        """
        cube_name = get_cube(mdx)
        self.assertEqual(cube_name, "cube")

    def test_get_cube_without_brackets_multi_from_where(self):
        mdx = """
        SELECT {[dim3from].[e2where]} ON COLUMNS, {[dim4from].[wheree5]} ON ROWS FROM cube WHERE([dim5]. [e4] )
        """
        cube_name = get_cube(mdx)
        self.assertEqual(cube_name, "cube")

    def test_get_cube_without_rows(self):
        mdx = """
        SELECT {[dim3].[e2]} ON COLUMNS FROM [cube] WHERE([dim5]. [e4] )
        """
        cube_name = get_cube(mdx)
        self.assertEqual(cube_name, "cube")

    def test_get_cube_without_where(self):
        mdx = """
        SELECT {[dim3].[e2]} ON COLUMNS, {[dim4].[e5]} ON ROWS FROM [cube]
        """
        cube_name = get_cube(mdx)
        self.assertEqual(cube_name, "cube")

    def test_get_cube_with_tabs_and_linebreaks(self):
        mdx = """
        SELECT 
        {[dim3].[e2]} ON      COLUMNS, 
        {[dim4].[e5]} 
        ON 
        ROWS 
            FROM    [cube ]
        """
        cube_name = get_cube(mdx)
        self.assertEqual(cube_name, "cube")

    def test_get_cube_without_brackets_without_where(self):
        mdx = """
        SELECT {[dim3].[e2]} ON COLUMNS, {[dim4].[e5]} ON ROWS FROM [cube]
        """
        cube_name = get_cube(mdx)
        self.assertEqual(cube_name, "cube")

    def test_get_cube_from_and_where_in_dimension_names(self):
        mdx = """
        SELECT {[dim3from].[e2]} ON COLUMNS, {[dim4where].[e5]} ON ROWS FROM [cube]
        """
        cube_name = get_cube(mdx)
        self.assertEqual(cube_name, "cube")

    def test_resemble_mdx_happy_case_true(self):
        mdx = """
        SELECT {[dim3].[e2]} ON COLUMNS, {[dim4].[e5]} ON ROWS FROM [cube]
        """
        self.assertTrue(resembles_mdx(mdx))

    def test_resemble_mdx_happy_case_false(self):
        mdx = """
        not mdx
        """
        self.assertFalse(resembles_mdx(mdx))

    def test_resemble_mdx_lower_case(self):
        mdx = """
        SELECT {[dim3].[e2]} ON COLUMNS, {[dim4].[e5]} ON ROWS FROM [cube]
        """.lower()

        self.assertTrue(resembles_mdx(mdx))

    def test_resemble_mdx_with_line_breaks(self):
        mdx = """
        SELECT
        {[dim3].[e2]} ON 
        COLUMNS,
        {[dim4].[e5]} 
        ON ROWS FROM
        [cube]
        """
        self.assertTrue(resembles_mdx(mdx))

    def test_resemble_mdx_no_rows(self):
        mdx = """
        SELECT {[dim3].[e2]} ON COLUMNS FROM [cube]
        """

        self.assertTrue(resembles_mdx(mdx))

    def test_resemble_mdx_with_member(self):
        mdx = """
        WITH MEMBER [dim3].[e3] AS 1
        SELECT {[dim3].[e2], [dim3].[e3]} ON COLUMNS FROM [cube]
        """

        self.assertTrue(resembles_mdx(mdx))

    def test_format_url_args_no_single_quote(self):
        url = "/Processes('{}')/tm1.ExecuteWithReturn?$expand=*"
        process_name = "process"
        escaped_url = format_url(url, process_name)
        self.assertEqual(
            "/Processes('process')/tm1.ExecuteWithReturn?$expand=*", escaped_url
        )

    def test_format_url_args_one_single_quote(self):
        url = "/Processes('{}')/tm1.ExecuteWithReturn?$expand=*"
        process_name = "pro'cess"
        escaped_url = format_url(url, process_name)
        self.assertEqual(
            "/Processes('pro''cess')/tm1.ExecuteWithReturn?$expand=*",
            escaped_url,
        )

    def test_format_url_args_multi_single_quote(self):
        url = "/Processes('{}')/tm1.ExecuteWithReturn?$expand=*"
        process_name = "pro'ces's"
        escaped_url = format_url(url, process_name)
        self.assertEqual(
            "/Processes('pro''ces''s')/tm1.ExecuteWithReturn?$expand=*",
            escaped_url,
        )

    def test_format_url_kwargs_no_single_quote(self):
        url = "/Processes('{process_name}')/tm1.ExecuteWithReturn?$expand=*"
        process_name = "process"
        escaped_url = format_url(url, process_name=process_name)
        self.assertEqual(
            "/Processes('process')/tm1.ExecuteWithReturn?$expand=*", escaped_url
        )

    def test_format_url_kwargs_one_single_quote(self):
        url = "/Processes('{process_name}')/tm1.ExecuteWithReturn?$expand=*"
        process_name = "pro'cess"
        escaped_url = format_url(url, process_name=process_name)
        self.assertEqual(
            "/Processes('pro''cess')/tm1.ExecuteWithReturn?$expand=*",
            escaped_url,
        )

    def test_format_url_kwargs_multi_single_quote(self):
        url = "/Processes('{process_name}')/tm1.ExecuteWithReturn?$expand=*"
        process_name = "pro'ces's"
        escaped_url = format_url(url, process_name=process_name)
        self.assertEqual(
            "/Processes('pro''ces''s')/tm1.ExecuteWithReturn?$expand=*",
            escaped_url,
        )

    def test_url_parameters_add(self):
        url = "/Cubes('cube')/tm1.Update"
        url = add_url_parameters(url, **{"!sandbox": "sandbox1"})

        self.assertEqual(
            "/Cubes('cube')/tm1.Update?!sandbox=sandbox1",
            url)

    def test_url_parameters_add_with_query_options(self):
        url = "/Cellsets('abcd')?$expand=Cells($select=Value)"
        url = add_url_parameters(url, **{"!sandbox": "sandbox1"})

        self.assertEqual(
            "/Cellsets('abcd')?$expand=Cells($select=Value)&!sandbox=sandbox1",
            url)

    def test_get_seconds_from_duration(self):
        elapsed_time = "P0DT00H04M02S"
        seconds = Utils.get_seconds_from_duration(elapsed_time)
        self.assertEqual(242, seconds)

    def test_get_tm1_time_value_now(self):
        current_time_from_excel_serial_date = Utils.get_tm1_time_value_now(use_excel_serial_date=True)
        current_time_from_tm1_serial_date = Utils.get_tm1_time_value_now(use_excel_serial_date=False)

        self.assertIsInstance(current_time_from_excel_serial_date, float)
        self.assertIsInstance(current_time_from_tm1_serial_date, float)
        self.assertGreater(current_time_from_excel_serial_date, current_time_from_tm1_serial_date)

    def test_extract_cell_updateable_property_rule_is_applied_true(self):
        value = 268435716
        self.assertTrue(extract_cell_updateable_property(
            decimal_value=value,
            cell_property=CellUpdateableProperty.RULE_IS_APPLIED))

    def test_extract_cell_updateable_property_rule_is_applied_false(self):
        value = 258
        self.assertFalse(extract_cell_updateable_property(
            decimal_value=value,
            cell_property=CellUpdateableProperty.RULE_IS_APPLIED))

    def test_extract_cell_updateable_property_cell_is_not_updateable_true(self):
        value = 268435716
        self.assertTrue(extract_cell_updateable_property(
            decimal_value=value,
            cell_property=CellUpdateableProperty.CELL_IS_NOT_UPDATEABLE))

    def test_extract_cell_updateable_property_cell_is_not_updateable_false(self):
        value = 258
        self.assertFalse(extract_cell_updateable_property(
            decimal_value=value,
            cell_property=CellUpdateableProperty.CELL_IS_NOT_UPDATEABLE))

    def test_cell_is_updateable_true(self):
        cell = {'Updateable': 258}
        self.assertTrue(cell_is_updateable(cell))

    def test_cell_is_updateable_false(self):
        cell = {'Updateable': 268435716}
        self.assertFalse(cell_is_updateable(cell))

    def test_extract_cell_properties_from_odata_context_cell_properties(self):
        context = "$metadata#Cellsets(Cells(Ordinal,Value,RuleDerived))/$entity"
        cell_properties = extract_cell_properties_from_odata_context(context)

        self.assertEqual(['Ordinal', 'Value', 'RuleDerived'], cell_properties)

    def test_extract_cell_properties_from_odata_context_only_value(self):
        context = "$metadata#Cellsets(Cells(Value))/$entity"
        cell_properties = extract_cell_properties_from_odata_context(context)

        self.assertEqual(['Value'], cell_properties)

    def test_map_cell_properties_to_compact_json_response_ordinal_value(self):
        properties = ['Ordinal', 'Value']
        compact_cells_response = [[1, 200], [2, 350], [3, 100]]
        actual = map_cell_properties_to_compact_json_response(properties, compact_cells_response)

        expected = {'Cells': [
            {'Ordinal': 1, 'Value': 200},
            {'Ordinal': 2, 'Value': 350},
            {'Ordinal': 3, 'Value': 100},
        ]}

        self.assertEqual(expected, actual)

    def test_map_cell_properties_to_compact_json_response_value(self):
        properties = ['Value']
        compact_cells_response = [[200], [350], [100]]
        actual = map_cell_properties_to_compact_json_response(properties, compact_cells_response)

        expected = {'Cells': [
            {'Value': 200},
            {'Value': 350},
            {'Value': 100},
        ]}

        self.assertEqual(expected, actual)

    def test_frame_to_significant_digits_happy_case(self):
        framed_value = frame_to_significant_digits(1000, 4)
        self.assertEqual('1000', framed_value)

    def test_frame_to_significant_digits_too_many_decimals(self):
        framed_value = frame_to_significant_digits(1000.1234, 6)
        self.assertEqual('1000.12', framed_value)

    def test_frame_to_significant_digits_too_many_digits(self):
        framed_value = frame_to_significant_digits(1234, 2)
        self.assertEqual('1200', framed_value)

    def test_frame_to_significant_digits_scientific_too_many_digits(self):
        framed_value = frame_to_significant_digits(1.2345E-1, 2)
        self.assertEqual('0.12', framed_value)

    def test_frame_to_significant_digits_scientific_too_many_digits_large(self):
        framed_value = frame_to_significant_digits(1.2345E3, 2)
        self.assertEqual('1200.0', framed_value)

    def test_element_name_from_element_unique_name_happy_case(self):
        element_name = Utils.element_name_from_element_unique_name("[d1].[e1]")
        self.assertEqual("e1", element_name)

    def test_element_name_from_element_unique_name_with_double_closing_square_bracket(self):
        element_name = Utils.element_name_from_element_unique_name("[d1].[other [please specify]]]")
        self.assertEqual("other [please specify]", element_name)

    def test_drop_dimension_properties_member_name(self):
        mdx = """
        SELECT
        {[d1].[e1]} DIMENSION PROPERTIES MEMBER_NAME ON 0,
        {[d2].[e1]} DIMENSION PROPERTIES MEMBER_NAME ON 1
        FROM [c1]
        """
        expected_mdx = """
        SELECT
        {[d1].[e1]} ON 0,
        {[d2].[e1]} ON 1
        FROM [c1]
        """
        self.assertEqual(
            expected_mdx,
            drop_dimension_properties(mdx))

    def test_drop_dimension_properties_member_name_lower_case(self):
        mdx = """
        SELECT
        {[d1].[e1]} dimension properties member_name ON 0,
        {[d2].[e1]} dimension properties member_name ON 1
        FROM [c1]
        """
        expected_mdx = """
        SELECT
        {[d1].[e1]} ON 0,
        {[d2].[e1]} ON 1
        FROM [c1]
        """
        self.assertEqual(
            expected_mdx,
            drop_dimension_properties(mdx))

    def test_drop_dimension_properties_one_axis(self):
        mdx = """
        SELECT
        {[d1].[e1]} * {[d2].[e1]} dimension properties member_name ON 0
        FROM [c1]
        """
        expected_mdx = """
        SELECT
        {[d1].[e1]} * {[d2].[e1]} ON 0
        FROM [c1]
        """
        self.assertEqual(
            expected_mdx,
            drop_dimension_properties(mdx))

    def test_drop_dimension_properties_attributes(self):
        mdx = """
            SELECT
            NON EMPTY {[dim2].[dim2].[elem2]} DIMENSION PROPERTIES [dim2].[dim2].[name] ON 0,
            NON EMPTY {TM1FILTERBYLEVEL({TM1SUBSETALL([dim1].[dim1])},0)} DIMENSION PROPERTIES [dim1].[dim1].[codeandname] ON 1
            FROM [cube]
            WHERE ([dim3].[dim3].[elem3],[dim4].[dim4].[elem4])
        """
        expected_mdx = """
            SELECT
            NON EMPTY {[dim2].[dim2].[elem2]}  ON 0,
            NON EMPTY {TM1FILTERBYLEVEL({TM1SUBSETALL([dim1].[dim1])},0)}  ON 1
            FROM [cube]
            WHERE ([dim3].[dim3].[elem3],[dim4].[dim4].[elem4])
        """
        self.assertEqual(
            expected_mdx,
            drop_dimension_properties(mdx))

    def test_drop_dimension_properties_member_name(self):
        mdx = """
        SELECT
        {[d1].[e1]} PROPERTIES MEMBER_NAME ON 0,
        {[d2].[e1]} PROPERTIES MEMBER_NAME ON 1
        FROM [c1]
        """
        expected_mdx = """
        SELECT
        {[d1].[e1]} ON 0,
        {[d2].[e1]} ON 1
        FROM [c1]
        """
        self.assertEqual(
            expected_mdx,
            drop_dimension_properties(mdx))

    def test_drop_dimension_properties_member_name_lower_case(self):
        mdx = """
        SELECT
        {[d1].[e1]} properties member_name ON 0,
        {[d2].[e1]} properties member_name ON 1
        FROM [c1]
        """
        expected_mdx = """
        SELECT
        {[d1].[e1]} ON 0,
        {[d2].[e1]} ON 1
        FROM [c1]
        """
        self.assertEqual(
            expected_mdx,
            drop_dimension_properties(mdx))

    def test_drop_dimension_properties_one_axis(self):
        mdx = """
        SELECT
        {[d1].[e1]} * {[d2].[e1]} properties member_name ON 0
        FROM [c1]
        """
        expected_mdx = """
        SELECT
        {[d1].[e1]} * {[d2].[e1]} ON 0
        FROM [c1]
        """
        self.assertEqual(
            expected_mdx,
            drop_dimension_properties(mdx))

    def test_drop_properties_attributes(self):
        mdx = """
            SELECT
            NON EMPTY {[dim2].[dim2].[elem2]} PROPERTIES [dim2].[dim2].[name] ON 0,
            NON EMPTY {TM1FILTERBYLEVEL({TM1SUBSETALL([dim1].[dim1])},0)} PROPERTIES [dim1].[dim1].[codeandname] ON 1
            FROM [cube]
            WHERE ([dim3].[dim3].[elem3],[dim4].[dim4].[elem4])
        """
        expected_mdx = """
            SELECT
            NON EMPTY {[dim2].[dim2].[elem2]} ON 0,
            NON EMPTY {TM1FILTERBYLEVEL({TM1SUBSETALL([dim1].[dim1])},0)} ON 1
            FROM [cube]
            WHERE ([dim3].[dim3].[elem3],[dim4].[dim4].[elem4])
        """
        self.assertEqual(
            expected_mdx,
            drop_dimension_properties(mdx))

    @classmethod
    def tearDownClass(cls):
        cls.tm1.logout()


if __name__ == "__main__":
    unittest.main()
