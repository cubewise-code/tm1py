import configparser
import copy
import json
import unittest
from pathlib import Path

from mdxpy import MdxBuilder

from Tests.Utils import (
    generate_test_uuid,
    skip_if_no_pandas,
    skip_if_version_lower_than,
)
from TM1py.Exceptions import (
    TM1pyException,
    TM1pyRestException,
    TM1pyWritePartialFailureException,
)
from TM1py.Objects import Dimension, Element, ElementAttribute, Hierarchy
from TM1py.Services import TM1Service
from TM1py.Services.ElementService import ElementService


class TestElementService(unittest.TestCase):
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

    def setUp(self):
        dimension_uuid = generate_test_uuid()
        prefix = "TM1py_unittest_element"
        pure_dimension_name = f"{prefix}_dimension_{dimension_uuid}"

        self.dimension_name = pure_dimension_name
        self.dimension_with_hierarchies_name = pure_dimension_name + "_with_hierarchies"
        self.dimension_with_same_attribute_name = pure_dimension_name + "_attribute_same_name"
        self.hierarchy_name = pure_dimension_name
        self.attribute_cube_name = "}ElementAttributes_" + pure_dimension_name
        self.dimension_does_not_exist_name = pure_dimension_name + "_does_not_exist"
        self.hierarchy_does_not_exist_name = self.dimension_does_not_exist_name

        # create dimension with a default hierarchy
        d = Dimension(self.dimension_name)
        h = Hierarchy(self.dimension_name, self.hierarchy_name)

        # add elements
        self.years = ("No Year", "1989", "1990", "1991", "1992")
        self.extra_year = "4321"

        h.add_element("Total Years", "Consolidated")
        h.add_element("All Consolidations", "Consolidated")
        h.add_edge("All Consolidations", "Total Years", 1)
        for year in self.years:
            h.add_element(year, "Numeric")
            h.add_edge("Total Years", year, 1)

        # add attributes
        self.attributes = ("Previous Year", "Next Year")
        self.alias_attributes = ("Financial Year",)

        for attribute in self.attributes:
            h.add_element_attribute(attribute, "String")
        for attribute in self.alias_attributes:
            h.add_element_attribute(attribute, "Alias")
        d.add_hierarchy(h)
        self.tm1.dimensions.update_or_create(d)

        self.added_attribute_name = "NewAttribute"

        # write attribute values
        self.tm1.cubes.cells.write_value("1988", self.attribute_cube_name, ("1989", "Previous Year"))
        self.tm1.cubes.cells.write_value("1989", self.attribute_cube_name, ("1990", "Previous Year"))
        self.tm1.cubes.cells.write_value("1990", self.attribute_cube_name, ("1991", "Previous Year"))
        self.tm1.cubes.cells.write_value("1991", self.attribute_cube_name, ("1992", "Previous Year"))

        self.tm1.cubes.cells.write_value("1988/89", self.attribute_cube_name, ("1989", "Financial Year"))
        self.tm1.cubes.cells.write_value("1989/90", self.attribute_cube_name, ("1990", "Financial Year"))
        self.tm1.cubes.cells.write_value("1990/91", self.attribute_cube_name, ("1991", "Financial Year"))
        self.tm1.cubes.cells.write_value("1991/92", self.attribute_cube_name, ("1992", "Financial Year"))
        self.tm1.cubes.cells.write_value("All Years", self.attribute_cube_name, ("Total Years", "Financial Year"))
        self.tm1.cubes.cells.write_value(
            "All Consolidations", self.attribute_cube_name, ("All Consolidations", "Financial Year")
        )

        self.create_or_update_dimension_with_hierarchies()

        d.name = self.dimension_with_same_attribute_name
        h = d.get_hierarchy(d.name)
        h.add_element_attribute(name=self.dimension_with_same_attribute_name, attribute_type="String")
        self.tm1.dimensions.update_or_create(d)

    def tearDown(self):
        self.tm1.dimensions.delete(self.dimension_name)
        self.tm1.dimensions.delete(self.dimension_with_hierarchies_name)
        self.tm1.dimensions.delete(self.dimension_with_same_attribute_name)

    def create_or_update_dimension_with_hierarchies(self):
        dimension = Dimension(self.dimension_with_hierarchies_name)
        dimension.add_hierarchy(
            Hierarchy(
                name="Hierarchy1",
                dimension_name=dimension.name,
                element_attributes=[ElementAttribute("Attr1", "String")],
                elements=[Element("Elem1", "Numeric"), Element("Elem2", "Numeric"), Element("Elem3", "Numeric")],
            )
        )
        dimension.add_hierarchy(
            Hierarchy(
                name="Hierarchy2",
                dimension_name=dimension.name,
                elements=[Element("Elem4", "Numeric"), Element("Elem6", "Numeric"), Element("Cons1", "Consolidated")],
            )
        )
        dimension.add_hierarchy(
            Hierarchy(
                name="Hierarchy3",
                dimension_name=dimension.name,
                element_attributes=[ElementAttribute("Attr2", "String")],
                elements=[
                    Element("Elem5", "Numeric"),
                    Element("Cons2", "Consolidated"),
                    Element("Cons3", "Consolidated"),
                ],
                edges={("Cons3", "Elem5"): 1},
            ),
        )
        self.tm1.dimensions.update_or_create(dimension)

    def test_create_and_delete_element(self):
        element = Element(self.extra_year, "String")
        self.tm1.dimensions.hierarchies.elements.create(self.dimension_name, self.hierarchy_name, element)

        element_returned = self.tm1.dimensions.hierarchies.elements.get(
            self.dimension_name, self.hierarchy_name, element.name
        )
        self.assertEqual(element, element_returned)

        self.tm1.dimensions.hierarchies.elements.delete(self.dimension_name, self.hierarchy_name, element.name)

    def test_get_element(self):
        for element_name in self.years:
            element = self.tm1.dimensions.hierarchies.elements.get(
                self.dimension_name, self.hierarchy_name, element_name
            )
            self.assertEqual(element.name, element_name)

    def test_update_element(self):
        element = Element(self.extra_year, Element.Types("S T R I N G"))
        self.tm1.dimensions.hierarchies.elements.create(self.dimension_name, self.hierarchy_name, element)

        element_name = self.extra_year
        element = self.tm1.dimensions.hierarchies.elements.get(self.dimension_name, self.hierarchy_name, element_name)
        element.element_type = "Numeric"
        self.tm1.dimensions.hierarchies.elements.update(self.dimension_name, self.hierarchy_name, element)

        element = self.tm1.dimensions.hierarchies.elements.get(self.dimension_name, self.hierarchy_name, element_name)
        self.assertTrue(element.element_type == Element.Types.NUMERIC)

        self.tm1.dimensions.hierarchies.elements.delete(self.dimension_name, self.hierarchy_name, element.name)

    def test_get_element_attributes(self):
        element_attributes = self.tm1.dimensions.hierarchies.elements.get_element_attributes(
            self.dimension_name, self.hierarchy_name
        )
        self.assertIn("Previous Year", element_attributes)
        self.assertIn("Next Year", element_attributes)

    def test_get_elements_filtered_by_attribute(self):
        elements = self.tm1.dimensions.hierarchies.elements.get_elements_filtered_by_attribute(
            self.dimension_name, self.hierarchy_name, "Previous Year", "1988"
        )
        self.assertIn("1989", elements)

    def test_get_element_by_attribute_without_elements(self):
        elements = self.tm1.dimensions.hierarchies.elements.get_attribute_of_elements(
            dimension_name=self.dimension_name, hierarchy_name=self.hierarchy_name, attribute="Previous Year"
        )
        self.assertEqual("1989", elements["1990"])
        self.assertEqual("1990", elements["1991"])
        self.assertNotIn(self.extra_year, elements)
        self.assertIsInstance(elements, dict)

    def test_get_element_by_attribute_with_elements(self):
        elements = self.tm1.dimensions.hierarchies.elements.get_attribute_of_elements(
            dimension_name=self.dimension_name,
            hierarchy_name=self.hierarchy_name,
            elements=["1990", "1991"],
            attribute="Previous Year",
            element_unique_names=True,
        )
        self.assertNotIn("[" + self.dimension_name + "]." + "[" + self.hierarchy_name + "]." + "[1989]", elements)
        self.assertEqual(
            "1989", elements["[" + self.dimension_name + "]." + "[" + self.hierarchy_name + "]." + "[1990]"]
        )
        self.assertIn("[" + self.dimension_name + "]." + "[" + self.hierarchy_name + "]." + "[1991]", elements)
        self.assertIsInstance(elements, dict)

    def test_create_filter_and_delete_element_attribute(self):
        attribute = ElementAttribute("Leap Year", "Numeric")
        self.tm1.dimensions.hierarchies.elements.create_element_attribute(
            self.dimension_name, self.hierarchy_name, attribute
        )
        # write one element attribute value
        self.tm1.cubes.cells.write_value(1, "}ElementAttributes_" + self.dimension_name, ("1992", "Leap Year"))
        elements = self.tm1.dimensions.hierarchies.elements.get_elements_filtered_by_attribute(
            self.dimension_name, self.hierarchy_name, "Leap Year", 1
        )
        self.assertIn("1992", elements)
        self.assertEqual(len(elements), 1)

        self.tm1.dimensions.hierarchies.elements.delete_element_attribute(
            self.dimension_name, self.hierarchy_name, "Leap Year"
        )

    def test_get_elements(self):
        elements = self.tm1.dimensions.hierarchies.elements.get_elements(self.dimension_name, self.hierarchy_name)
        element_names = [element.name for element in elements]
        for year in self.years:
            self.assertIn(year, element_names)
        self.assertNotIn(self.extra_year, element_names)

    def run_test_get_elements_dataframe(self, use_blob: bool):
        df = self.tm1.elements.get_elements_dataframe(
            dimension_name=self.dimension_name,
            hierarchy_name=self.hierarchy_name,
            elements=["1989", "1990"],
            skip_consolidations=True,
            attributes=["Next Year", "Previous Year"],
            attribute_column_prefix="Attribute ",
            skip_parents=False,
            level_names=None,
            parent_attribute=None,
            skip_weights=False,
            use_blob=use_blob,
        )

        expected_columns = (
            self.dimension_name,
            "Type",
            "Attribute Next Year",
            "Attribute Previous Year",
            "level001_Weight",
            "level000_Weight",
            "level001",
            "level000",
        )

        self.assertEqual((2, 8), df.shape)
        self.assertEqual(expected_columns, tuple(df.columns))
        row = df.loc[df[self.dimension_name] == "1989"]
        self.assertEqual(
            ("1989", "Numeric", "", "1988", "1.000000", "1.000000", "Total Years", "All Consolidations"),
            tuple(row.values[0]),
        )

    @skip_if_no_pandas
    def test_get_elements_dataframe(self):
        self.run_test_get_elements_dataframe(use_blob=False)

    @skip_if_no_pandas
    def test_get_elements_dataframe_use_blob(self):
        self.run_test_get_elements_dataframe(use_blob=True)

    def run_test_get_elements_dataframe_not_allow_empty_alias(self, use_blob):
        df = self.tm1.elements.get_elements_dataframe(
            dimension_name=self.dimension_name,
            hierarchy_name=self.hierarchy_name,
            elements=[
                "No Year",
            ],
            skip_consolidations=True,
            attributes=["Financial Year", "Previous Year"],
            skip_parents=False,
            level_names=None,
            parent_attribute=None,
            skip_weights=False,
            allow_empty_alias=False,
            use_blob=use_blob,
        )

        expected_columns = (
            self.dimension_name,
            "Type",
            "Financial Year",
            "Previous Year",
            "level001_Weight",
            "level000_Weight",
            "level001",
            "level000",
        )

        self.assertEqual((1, 8), df.shape)
        self.assertEqual(expected_columns, tuple(df.columns))

        row = df.loc[df[self.dimension_name] == "No Year"]
        self.assertEqual(
            ("No Year", "Numeric", "No Year", "", "1.000000", "1.000000", "Total Years", "All Consolidations"),
            tuple(row.values[0]),
        )

    @skip_if_no_pandas
    def test_get_elements_dataframe_not_allow_empty_alias(self):
        self.run_test_get_elements_dataframe_not_allow_empty_alias(use_blob=False)

    @skip_if_no_pandas
    def test_get_elements_dataframe_not_allow_empty_alias_use_blob(self):
        self.run_test_get_elements_dataframe_not_allow_empty_alias(use_blob=True)

    def run_test_get_elements_dataframe_allow_empty_alias(self, use_blob):
        df = self.tm1.elements.get_elements_dataframe(
            dimension_name=self.dimension_name,
            hierarchy_name=self.hierarchy_name,
            elements=[
                "No Year",
            ],
            skip_consolidations=True,
            attributes=["Financial Year", "Previous Year"],
            skip_parents=False,
            level_names=None,
            parent_attribute=None,
            skip_weights=False,
            allow_empty_alias=True,
            use_blob=use_blob,
        )

        expected_columns = (
            self.dimension_name,
            "Type",
            "Financial Year",
            "Previous Year",
            "level001_Weight",
            "level000_Weight",
            "level001",
            "level000",
        )

        self.assertEqual((1, 8), df.shape)
        self.assertEqual(expected_columns, tuple(df.columns))

        row = df.loc[df[self.dimension_name] == "No Year"]
        self.assertEqual(
            ("No Year", "Numeric", "", "", "1.000000", "1.000000", "Total Years", "All Consolidations"),
            tuple(row.values[0]),
        )

    @skip_if_no_pandas
    def test_get_elements_dataframe_allow_empty_alias(self):
        self.run_test_get_elements_dataframe_allow_empty_alias(use_blob=False)

    @skip_if_no_pandas
    def test_get_elements_dataframe_allow_empty_alias_use_blob(self):
        self.run_test_get_elements_dataframe_allow_empty_alias(use_blob=True)

    def run_test_get_elements_dataframe_not_allow_empty_alias_mixed_source(self, use_blob):
        df = self.tm1.elements.get_elements_dataframe(
            dimension_name=self.dimension_name,
            hierarchy_name=self.hierarchy_name,
            elements=["No Year", "1990"],
            skip_consolidations=True,
            attributes=["Financial Year", "Previous Year"],
            skip_parents=False,
            level_names=None,
            parent_attribute=None,
            skip_weights=False,
            allow_empty_alias=False,
            use_blob=use_blob,
        )

        expected_columns = (
            self.dimension_name,
            "Type",
            "Financial Year",
            "Previous Year",
            "level001_Weight",
            "level000_Weight",
            "level001",
            "level000",
        )

        self.assertEqual((2, 8), df.shape)
        self.assertEqual(expected_columns, tuple(df.columns))

        row = df.loc[df[self.dimension_name] == "No Year"]
        self.assertEqual(
            ("No Year", "Numeric", "No Year", "", "1.000000", "1.000000", "Total Years", "All Consolidations"),
            tuple(row.values[0]),
        )

        row = df.loc[df[self.dimension_name] == "1990"]
        self.assertEqual(
            ("1990", "Numeric", "1989/90", "1989", "1.000000", "1.000000", "Total Years", "All Consolidations"),
            tuple(row.values[0]),
        )

    @skip_if_no_pandas
    def test_get_elements_dataframe_not_allow_empty_alias_mixed_source(self):
        self.run_test_get_elements_dataframe_not_allow_empty_alias_mixed_source(False)

    @skip_if_no_pandas
    def test_get_elements_dataframe_not_allow_empty_alias_mixed_source_use_blob(self):
        self.run_test_get_elements_dataframe_not_allow_empty_alias_mixed_source(True)

    def run_test_get_elements_dataframe_alternate_hierarchy(self, use_blob):
        df = self.tm1.elements.get_elements_dataframe(
            dimension_name=self.dimension_with_hierarchies_name,
            hierarchy_name="Hierarchy3",
            elements=["Elem5"],
            skip_consolidations=True,
            attributes=[],
            skip_parents=False,
            level_names=None,
            parent_attribute=None,
            skip_weights=False,
            use_blob=use_blob,
        )

        expected_columns = (
            self.dimension_with_hierarchies_name,
            "Type",
            "level000_Weight",
            "level000",
        )

        self.assertEqual((1, 4), df.shape)
        self.assertEqual(expected_columns, tuple(df.columns))
        row = df.loc[df[self.dimension_with_hierarchies_name] == "Elem5"]
        self.assertEqual(("Elem5", "Numeric", "1.000000", "Cons3"), tuple(row.values[0]))

    @skip_if_no_pandas
    def test_get_elements_dataframe_alternate_hierarchy(self):
        self.run_test_get_elements_dataframe_alternate_hierarchy(use_blob=False)

    @skip_if_no_pandas
    def test_get_elements_dataframe_alternate_hierarchy_use_blob(self):
        self.run_test_get_elements_dataframe_alternate_hierarchy(use_blob=True)

    def run_test_get_elements_dataframe_attribute_suffix(self, use_blob):
        df = self.tm1.elements.get_elements_dataframe(
            dimension_name=self.dimension_name,
            hierarchy_name=self.hierarchy_name,
            elements=["1989", "1990"],
            skip_consolidations=True,
            attributes=["Next Year", "Previous Year"],
            attribute_suffix=True,
            skip_parents=False,
            level_names=None,
            parent_attribute=None,
            skip_weights=False,
            use_blob=use_blob,
        )

        expected_columns = (
            self.dimension_name,
            "Type",
            "Next Year:s",
            "Previous Year:s",
            "level001_Weight",
            "level000_Weight",
            "level001",
            "level000",
        )

        self.assertEqual((2, 8), df.shape)
        self.assertEqual(expected_columns, tuple(df.columns))
        row = df.loc[df[self.dimension_name] == "1989"]
        self.assertEqual(
            ("1989", "Numeric", "", "1988", "1.000000", "1.000000", "Total Years", "All Consolidations"),
            tuple(row.values[0]),
        )

    @skip_if_no_pandas
    def test_get_elements_dataframe_attribute_suffix(self):
        self.run_test_get_elements_dataframe_attribute_suffix(False)

    @skip_if_no_pandas
    def test_get_elements_dataframe_attribute_suffix_use_blob(self):
        self.run_test_get_elements_dataframe_attribute_suffix(True)

    def run_test_get_elements_dataframe_attribute_prefix_and_suffix(self, use_blob):
        df = self.tm1.elements.get_elements_dataframe(
            dimension_name=self.dimension_name,
            hierarchy_name=self.hierarchy_name,
            elements=["1989", "1990"],
            skip_consolidations=True,
            attributes=["Next Year", "Previous Year"],
            attribute_column_prefix="A_",
            attribute_suffix=True,
            skip_parents=False,
            level_names=None,
            parent_attribute=None,
            skip_weights=False,
            use_blob=use_blob,
        )

        expected_columns = (
            self.dimension_name,
            "Type",
            "A_Next Year:s",
            "A_Previous Year:s",
            "level001_Weight",
            "level000_Weight",
            "level001",
            "level000",
        )

        self.assertEqual((2, 8), df.shape)
        self.assertEqual(expected_columns, tuple(df.columns))
        row = df.loc[df[self.dimension_name] == "1989"]
        self.assertEqual(
            ("1989", "Numeric", "", "1988", "1.000000", "1.000000", "Total Years", "All Consolidations"),
            tuple(row.values[0]),
        )

    @skip_if_no_pandas
    def test_get_elements_dataframe_attribute_prefix_and_suffix(self):
        self.run_test_get_elements_dataframe_attribute_prefix_and_suffix(False)

    @skip_if_no_pandas
    def test_get_elements_dataframe_attribute_prefix_and_suffix_use_blob(self):
        self.run_test_get_elements_dataframe_attribute_prefix_and_suffix(True)

    def run_test_get_elements_dataframe_element_type_column(self, use_blob):
        df = self.tm1.elements.get_elements_dataframe(
            dimension_name=self.dimension_name,
            hierarchy_name=self.hierarchy_name,
            elements=["1989", "1990"],
            skip_consolidations=True,
            attributes=["Next Year", "Previous Year"],
            element_type_column="ElementType",
            skip_parents=False,
            level_names=None,
            parent_attribute=None,
            skip_weights=False,
            use_blob=use_blob,
        )

        expected_columns = (
            self.dimension_name,
            "ElementType",
            "Next Year",
            "Previous Year",
            "level001_Weight",
            "level000_Weight",
            "level001",
            "level000",
        )

        self.assertEqual((2, 8), df.shape)
        self.assertEqual(expected_columns, tuple(df.columns))
        row = df.loc[df[self.dimension_name] == "1989"]
        self.assertEqual(
            ("1989", "Numeric", "", "1988", "1.000000", "1.000000", "Total Years", "All Consolidations"),
            tuple(row.values[0]),
        )

    @skip_if_no_pandas
    def test_get_elements_dataframe_element_type_column(self):
        self.run_test_get_elements_dataframe_element_type_column(False)

    @skip_if_no_pandas
    def test_get_elements_dataframe_element_type_column_use_blob(self):
        self.run_test_get_elements_dataframe_element_type_column(True)

    def run_test_get_elements_dataframe_parent_attribute(self, use_blob):
        df = self.tm1.elements.get_elements_dataframe(
            dimension_name=self.dimension_name,
            hierarchy_name=self.hierarchy_name,
            elements=["1989", "1990"],
            skip_consolidations=True,
            attributes=["Next Year", "Previous Year"],
            attribute_column_prefix="Attribute ",
            skip_parents=False,
            level_names=None,
            parent_attribute="Financial Year",
            skip_weights=False,
            use_blob=use_blob,
        )

        expected_columns = (
            self.dimension_name,
            "Type",
            "Attribute Next Year",
            "Attribute Previous Year",
            "level001_Weight",
            "level000_Weight",
            "level001",
            "level000",
        )

        self.assertEqual((2, 8), df.shape)
        self.assertEqual(expected_columns, tuple(df.columns))
        row = df.loc[df[self.dimension_name] == "1989"]
        self.assertEqual(
            ("1989", "Numeric", "", "1988", "1.000000", "1.000000", "All Years", "All Consolidations"),
            tuple(row.values[0]),
        )

    @skip_if_no_pandas
    def test_get_elements_dataframe_parent_attribute(self):
        self.run_test_get_elements_dataframe_parent_attribute(False)

    @skip_if_no_pandas
    def test_get_elements_dataframe_parent_attribute_use_blob(self):
        self.run_test_get_elements_dataframe_parent_attribute(True)

    def run_test_get_elements_dataframe_not_elements(self, use_blob: bool):
        df = self.tm1.elements.get_elements_dataframe(
            dimension_name=self.dimension_name,
            hierarchy_name=self.hierarchy_name,
            skip_consolidations=True,
            attributes=["Next Year", "Previous Year"],
            attribute_column_prefix="Attribute ",
            skip_parents=False,
            level_names=None,
            parent_attribute=None,
            skip_weights=False,
            use_blob=use_blob,
        )

        reference_df = self.tm1.elements.get_elements_dataframe(
            dimension_name=self.dimension_name,
            hierarchy_name=self.hierarchy_name,
            elements=f"{{ [{self.dimension_name}].[{self.hierarchy_name}].Members }}",
            skip_consolidations=True,
            attributes=["Next Year", "Previous Year"],
            attribute_column_prefix="Attribute ",
            skip_parents=False,
            level_names=None,
            parent_attribute=None,
            skip_weights=False,
            use_blob=use_blob,
        )

        self.assertTrue(df.equals(reference_df))

    @skip_if_no_pandas
    def test_get_elements_dataframe_not_elements(self):
        self.run_test_get_elements_dataframe_not_elements(use_blob=False)

    @skip_if_no_pandas
    def test_get_elements_dataframe_use_blob_not_elements(self):
        self.run_test_get_elements_dataframe_not_elements(use_blob=True)

    @skip_if_no_pandas
    def test_get_elements_dataframe_attribute_same_name(self):
        self.run_test_get_elements_dataframe_attribute_same_name(False)

    @skip_if_no_pandas
    def test_get_elements_dataframe_attribute_same_name_use_blob(self):
        self.run_test_get_elements_dataframe_attribute_same_name(True)

    def run_test_get_elements_dataframe_attribute_same_name(self, use_blob: bool):
        df = self.tm1.elements.get_elements_dataframe(
            dimension_name=self.dimension_with_same_attribute_name,
            hierarchy_name=self.dimension_with_same_attribute_name,
            skip_consolidations=True,
            attributes=None,
            attribute_column_prefix="Attribute ",
            skip_parents=True,
            level_names=None,
            parent_attribute=None,
            skip_weights=False,
            use_blob=use_blob,
        )

        expected_columns = (
            self.dimension_with_same_attribute_name,
            "Type",
            "Attribute Previous Year",
            "Attribute Next Year",
            "Attribute Financial Year",
            "Attribute " + self.dimension_with_same_attribute_name,
        )

        self.assertEqual((5, 6), df.shape)
        self.assertEqual(expected_columns, tuple(df.columns))

    def run_test_get_elements_dataframe_elements_via_mdx(self, use_blob: bool):
        element_names = self.tm1.elements.get_element_names(self.dimension_name, self.hierarchy_name)
        df = self.tm1.elements.get_elements_dataframe(
            dimension_name=self.dimension_name,
            hierarchy_name=self.hierarchy_name,
            elements=element_names,
            skip_consolidations=True,
            attributes=["Next Year", "Previous Year"],
            attribute_column_prefix="Attribute ",
            skip_parents=False,
            level_names=None,
            parent_attribute=None,
            skip_weights=False,
            use_blob=use_blob,
        )

        elements = (
            "{"
            + ",".join(f"[{self.dimension_name}].[{self.hierarchy_name}].[{member}]" for member in element_names)
            + "}"
        )
        reference_df = self.tm1.elements.get_elements_dataframe(
            dimension_name=self.dimension_name,
            hierarchy_name=self.hierarchy_name,
            elements=elements,
            skip_consolidations=True,
            attributes=["Next Year", "Previous Year"],
            attribute_column_prefix="Attribute ",
            skip_parents=False,
            level_names=None,
            parent_attribute=None,
            skip_weights=False,
            use_blob=use_blob,
        )

        self.assertTrue(df.equals(reference_df))

    def test_get_element_names(self):
        element_names = self.tm1.dimensions.hierarchies.elements.get_element_names(
            self.dimension_name, self.hierarchy_name
        )
        for year in self.years:
            self.assertIn(year, element_names)

    def test_get_leaf_element_names(self):
        leaf_element_names = self.tm1.dimensions.hierarchies.elements.get_leaf_element_names(
            self.dimension_name, self.hierarchy_name
        )
        for leaf in leaf_element_names:
            self.assertIn(leaf, self.years)
        self.assertNotIn(self.extra_year, leaf_element_names)
        self.assertNotIn("Total Years", leaf_element_names)

    def test_get_consolidated_element_names(self):
        consol_element_names = self.tm1.dimensions.hierarchies.elements.get_consolidated_element_names(
            self.dimension_name, self.hierarchy_name
        )
        for consol in consol_element_names:
            self.assertNotIn(consol, self.years)
        self.assertIn("Total Years", consol_element_names)

    def test_get_numeric_element_names(self):
        numeric_element_names = self.tm1.dimensions.hierarchies.elements.get_numeric_element_names(
            self.dimension_name, self.hierarchy_name
        )
        for elem in numeric_element_names:
            self.assertIn(elem, self.years)
        self.assertNotIn(self.extra_year, numeric_element_names)
        self.assertNotIn("Total Years", numeric_element_names)

    def test_get_leaf_elements(self):
        leaf_elements = self.tm1.dimensions.hierarchies.elements.get_leaf_elements(
            self.dimension_name, self.hierarchy_name
        )
        for leaf in leaf_elements:
            self.assertIn(leaf.name, self.years)
            self.assertNotEqual(leaf.element_type, "Consolidated")
        leaf_element_names = [element.name for element in leaf_elements]
        self.assertNotIn(self.extra_year, leaf_element_names)
        self.assertNotIn("Total Year", leaf_element_names)

    def test_get_numeric_elements(self):
        numeric_elements = self.tm1.dimensions.hierarchies.elements.get_numeric_elements(
            self.dimension_name, self.hierarchy_name
        )
        for elem in numeric_elements:
            self.assertIn(elem.name, self.years)
            self.assertNotEqual(elem.element_type, "Consolidated")
        numeric_element_names = [element.name for element in numeric_elements]
        self.assertNotIn(self.extra_year, numeric_element_names)
        self.assertNotIn("Total Year", numeric_element_names)

    def test_get_consolidated_elements(self):
        consol_elements = self.tm1.dimensions.hierarchies.elements.get_consolidated_elements(
            self.dimension_name, self.hierarchy_name
        )
        for consol in consol_elements:
            self.assertNotIn(consol.name, self.years)
            self.assertNotEqual(consol.element_type, "Numeric")
        consol_element_names = [element.name for element in consol_elements]
        self.assertIn("Total Years", consol_element_names)

    def test_element_exists(self):
        for year in self.years:
            self.assertTrue(
                self.tm1.dimensions.hierarchies.elements.exists(self.dimension_name, self.hierarchy_name, year)
            )

    def test_get_leaves_under_consolidation(self):
        leaves = self.tm1.dimensions.hierarchies.elements.get_leaves_under_consolidation(
            self.dimension_name, self.hierarchy_name, "All Consolidations"
        )
        self.assertNotIn("Total Years", leaves)
        for year in self.years:
            self.assertIn(year, leaves)

    def test_get_edges_under_consolidation(self):
        edges = self.tm1.dimensions.hierarchies.elements.get_edges_under_consolidation(
            self.dimension_name, self.hierarchy_name, "All Consolidations"
        )

        self.assertEqual(len(self.years) + 1, len(edges))
        self.assertEqual(1, edges["All Consolidations", "Total Years"])
        for year in self.years:
            self.assertEqual(1, edges["Total Years", year])

    def test_get_edges_under_consolidation_max_depth_1(self):
        edges = self.tm1.dimensions.hierarchies.elements.get_edges_under_consolidation(
            self.dimension_name, self.hierarchy_name, "All Consolidations", max_depth=1
        )

        self.assertEqual(1, len(edges))
        self.assertEqual(1, edges["All Consolidations", "Total Years"])

    def test_get_edges_under_consolidation_max_depth_1_with_n_components(self):
        edges = self.tm1.dimensions.hierarchies.elements.get_edges_under_consolidation(
            self.dimension_name, self.hierarchy_name, "Total Years", max_depth=1
        )

        self.assertEqual(len(self.years), len(edges))
        for year in self.years:
            self.assertEqual(1, edges["Total Years", year])

    def test_get_edges_under_consolidation_not_existing_consolidation(self):
        with self.assertRaises(TM1pyRestException) as _:
            self.tm1.dimensions.hierarchies.elements.get_edges_under_consolidation(
                self.dimension_name, self.hierarchy_name, "NotExistingConsolidation"
            )

    def test_get_edges_under_consolidation_remove_read(self):
        edges = self.tm1.dimensions.hierarchies.elements.get_edges_under_consolidation(
            self.dimension_name, self.hierarchy_name, "All Consolidations", max_depth=99
        )
        h = self.tm1.hierarchies.get(self.dimension_name, self.hierarchy_name)
        h_original = copy.deepcopy(h)

        h.remove_all_edges()
        for edge, weight in edges.items():
            h.add_edge(edge[0], edge[1], weight=weight)

        self.assertEqual(h_original.edges, h.edges)

    def test_get_members_under_consolidation(self):
        leaves = self.tm1.dimensions.hierarchies.elements.get_members_under_consolidation(
            self.dimension_name, self.hierarchy_name, "All Consolidations", leaves_only=True
        )
        self.assertNotIn("Total Years", leaves)
        for year in self.years:
            self.assertIn(year, leaves)

        members = self.tm1.dimensions.hierarchies.elements.get_members_under_consolidation(
            self.dimension_name, self.hierarchy_name, "All Consolidations", leaves_only=False
        )
        self.assertIn("Total Years", members)
        for year in self.years:
            self.assertIn(year, members)

    def test_get_element_identifiers_with_iterable(self):
        expected_identifiers = {"1988/89", "1989/90", "1990/91", "1991/92", *self.years}
        elements = self.years
        identifiers = self.tm1.dimensions.hierarchies.elements.get_element_identifiers(
            dimension_name=self.dimension_name, hierarchy_name=self.hierarchy_name, elements=elements
        )
        self.assertEqual(expected_identifiers, set(identifiers))

    def test_get_element_identifiers_with_string(self):
        expected_identifiers = {"1988/89", "1989/90", "1990/91", "1991/92", *self.years}
        elements = "{" + ",".join(["[" + self.dimension_name + "].[" + year + "]" for year in self.years]) + "}"
        identifiers = self.tm1.dimensions.hierarchies.elements.get_element_identifiers(
            dimension_name=self.dimension_name, hierarchy_name=self.hierarchy_name, elements=elements
        )
        self.assertEqual(expected_identifiers, set(identifiers))

    def test_get_all_element_identifiers(self):
        expected_identifiers = {
            "1988/89",
            "1989/90",
            "1990/91",
            "1991/92",
            "All Years",
            "Total Years",
            "All Consolidations",
            *self.years,
        }
        identifiers = self.tm1.dimensions.hierarchies.elements.get_all_element_identifiers(
            self.dimension_name, self.hierarchy_name
        )
        self.assertEqual(expected_identifiers, set(identifiers))

    def test_get_all_element_identifiers_no_attributes(self):
        expected_identifiers = {"Elem1", "Elem2", "Elem3"}
        identifiers = self.tm1.dimensions.hierarchies.elements.get_all_element_identifiers(
            self.dimension_with_hierarchies_name, "Hierarchy1"
        )
        self.assertEqual(expected_identifiers, set(identifiers))

    def test_get_all_leaf_element_identifiers(self):
        expected_identifiers = {"1988/89", "1989/90", "1990/91", "1991/92", *self.years}
        identifiers = self.tm1.dimensions.hierarchies.elements.get_all_leaf_element_identifiers(
            self.dimension_name, self.hierarchy_name
        )
        self.assertEqual(expected_identifiers, set(identifiers))

    def test_get_elements_by_level(self):
        expected_elements = ["No Year", "1989", "1990", "1991", "1992"]
        elements = self.tm1.dimensions.hierarchies.elements.get_elements_by_level(
            self.dimension_name, self.hierarchy_name, 0
        )

        self.assertEqual(elements, expected_elements)

        expected_elements = ["Total Years"]
        elements = self.tm1.dimensions.hierarchies.elements.get_elements_by_level(
            self.dimension_name, self.hierarchy_name, 1
        )
        self.assertEqual(elements, expected_elements)

    def test_get_elements_by_wildcard(self):
        expected_elements = ["Total Years", "No Year"]
        elements = self.tm1.dimensions.hierarchies.elements.get_elements_filtered_by_wildcard(
            self.dimension_name, self.hierarchy_name, "year"
        )
        self.assertEqual(elements, expected_elements)

        expected_elements = ["Total Years"]
        elements = self.tm1.dimensions.hierarchies.elements.get_elements_filtered_by_wildcard(
            self.dimension_name, self.hierarchy_name, "talyear", 1
        )
        self.assertEqual(elements, expected_elements)

        expected_elements = ["1989", "1990", "1991", "1992"]
        elements = self.tm1.dimensions.hierarchies.elements.get_elements_filtered_by_wildcard(
            self.dimension_name, self.hierarchy_name, "19", 0
        )
        self.assertEqual(elements, expected_elements)

        expected_elements = ["1990", "1991", "1992"]
        elements = self.tm1.dimensions.hierarchies.elements.get_elements_filtered_by_wildcard(
            self.dimension_name, self.hierarchy_name, "99", 0
        )
        self.assertEqual(elements, expected_elements)

    def test_get_number_of_elements(self):
        number_of_elements = self.tm1.dimensions.hierarchies.elements.get_number_of_elements(
            self.dimension_name, self.hierarchy_name
        )
        self.assertEqual(number_of_elements, 7)

    def test_get_number_of_leaf_elements(self):
        number_of_elements = self.tm1.dimensions.hierarchies.elements.get_number_of_leaf_elements(
            self.dimension_name, self.hierarchy_name
        )

        self.assertEqual(number_of_elements, 5)

    def test_get_number_of_consolidated_elements(self):
        number_of_elements = self.tm1.dimensions.hierarchies.elements.get_number_of_consolidated_elements(
            self.dimension_name, self.hierarchy_name
        )

        self.assertEqual(number_of_elements, 2)

    def test_get_number_of_numeric_elements(self):
        number_of_elements = self.tm1.dimensions.hierarchies.elements.get_number_of_numeric_elements(
            self.dimension_name, self.hierarchy_name
        )

        self.assertEqual(number_of_elements, 5)

    def test_string_element_functions(self):
        string_elem = "string_element"
        element = Element(string_elem, "String")
        self.tm1.dimensions.hierarchies.elements.create(self.dimension_name, self.hierarchy_name, element)

        number_of_elements = self.tm1.dimensions.hierarchies.elements.get_number_of_string_elements(
            self.dimension_name, self.hierarchy_name
        )
        self.assertEqual(number_of_elements, 1)

        string_element_names = self.tm1.dimensions.hierarchies.elements.get_string_element_names(
            self.dimension_name, self.hierarchy_name
        )
        for elem in string_element_names:
            self.assertIn(elem, [string_elem])
        self.assertNotIn("Total Years", string_element_names)
        self.assertNotIn("1989", string_element_names)

        string_elements = self.tm1.dimensions.hierarchies.elements.get_string_elements(
            self.dimension_name, self.hierarchy_name
        )
        for elem in string_elements:
            self.assertIn(elem.name, [string_elem])
            self.assertNotEqual(elem.element_type, "Consolidated")
            self.assertNotEqual(elem.element_type, "Numeric")
        string_element_names = [element.name for element in string_elements]
        self.assertNotIn("1989", string_element_names)
        self.assertNotIn("Total Year", string_element_names)

        self.tm1.dimensions.hierarchies.elements.delete(self.dimension_name, self.hierarchy_name, element.name)

    def test_create_element_attribute(self):
        element_attribute = ElementAttribute("NewAttribute", "String")
        self.tm1.dimensions.hierarchies.elements.create_element_attribute(
            self.dimension_name, self.dimension_name, element_attribute
        )

        element_attributes = self.tm1.dimensions.hierarchies.elements.get_element_attributes(
            self.dimension_name, self.dimension_name
        )

        self.assertIn(element_attribute, element_attributes)

    def test_delete_elements(self):
        self.assertIn("1989", self.tm1.elements.get_element_names(self.dimension_name, self.hierarchy_name))

        self.assertIn("1990", self.tm1.elements.get_element_names(self.dimension_name, self.hierarchy_name))

        element_names = ["1989", "1990"]
        self.tm1.elements.delete_elements(
            dimension_name=self.dimension_name,
            hierarchy_name=self.hierarchy_name,
            element_names=element_names,
            use_ti=False,
        )
        self.assertNotIn("1989", self.tm1.elements.get_element_names(self.dimension_name, self.hierarchy_name))

        self.assertNotIn("1990", self.tm1.elements.get_element_names(self.dimension_name, self.hierarchy_name))

    def test_delete_elements_use_ti(self):
        self.assertIn("1989", self.tm1.elements.get_element_names(self.dimension_name, self.hierarchy_name))

        self.assertIn("1990", self.tm1.elements.get_element_names(self.dimension_name, self.hierarchy_name))

        element_names = ["1989", "1990"]
        self.tm1.elements.delete_elements(
            dimension_name=self.dimension_name,
            hierarchy_name=self.hierarchy_name,
            element_names=element_names,
            use_ti=True,
        )
        self.assertNotIn("1989", self.tm1.elements.get_element_names(self.dimension_name, self.hierarchy_name))

        self.assertNotIn("1990", self.tm1.elements.get_element_names(self.dimension_name, self.hierarchy_name))

    def test_delete_elements_use_blob(self):
        self.assertIn("1989", self.tm1.elements.get_element_names(self.dimension_name, self.hierarchy_name))

        self.assertIn("1990", self.tm1.elements.get_element_names(self.dimension_name, self.hierarchy_name))

        element_names = ["1989", "1990"]
        self.tm1.elements.delete_elements(
            dimension_name=self.dimension_name,
            hierarchy_name=self.hierarchy_name,
            element_names=element_names,
            use_blob=True,
        )
        self.assertNotIn("1989", self.tm1.elements.get_element_names(self.dimension_name, self.hierarchy_name))

        self.assertNotIn("1990", self.tm1.elements.get_element_names(self.dimension_name, self.hierarchy_name))

    def test_delete_element_attribute(self):
        element_attribute = ElementAttribute("NewAttribute", "String")
        self.tm1.dimensions.hierarchies.elements.create_element_attribute(
            self.dimension_name, self.dimension_name, element_attribute
        )

        self.tm1.dimensions.hierarchies.elements.delete_element_attribute(
            self.dimension_name, self.dimension_name, element_attribute.name
        )

        element_attributes = self.tm1.dimensions.hierarchies.elements.get_element_attributes(
            self.dimension_name, self.dimension_name
        )

        self.assertNotIn(element_attribute, element_attributes)

    def test_add_edge_single(self):
        consolidation = Element(name="Consolidation", element_type="Consolidated")
        element = Element(name="Element", element_type="Numeric")
        self.tm1.elements.add_elements(self.dimension_name, self.dimension_name, [consolidation, element])

        edge = {(consolidation.name, element.name): 2}
        self.tm1.elements.add_edges(self.dimension_name, self.hierarchy_name, edge)

        all_edges = self.tm1.elements.get_edges(self.dimension_name, self.dimension_name)
        self.assertIn((consolidation.name, element.name), all_edges)
        self.assertEqual(2, all_edges[consolidation.name, element.name])

    def test_add_edge_multi(self):
        consolidation = Element(name="Consolidation", element_type="Consolidated")
        element1 = Element(name="Element1", element_type="Numeric")
        element2 = Element(name="Element2", element_type="Numeric")
        self.tm1.elements.add_elements(self.dimension_name, self.dimension_name, [consolidation, element1, element2])

        edges = {(consolidation.name, element1.name): 2, (consolidation.name, element2.name): 3}
        self.tm1.elements.add_edges(self.dimension_name, self.hierarchy_name, edges)

        all_edges = self.tm1.elements.get_edges(self.dimension_name, self.dimension_name)
        self.assertIn((consolidation.name, element1.name), all_edges)
        self.assertIn((consolidation.name, element2.name), all_edges)
        self.assertEqual(2, all_edges[consolidation.name, element1.name])
        self.assertEqual(3, all_edges[consolidation.name, element2.name])

    def test_add_edge_fail(self):
        with self.assertRaises(TM1pyRestException) as _:
            edges = {("NotExisting1", "NotExisting2"): 1}
            self.tm1.elements.add_edges(self.dimension_name, self.dimension_name, edges)

    def test_add_elements_single(self):
        element = Element(name="Element0", element_type="Numeric")
        self.tm1.elements.add_elements(self.dimension_name, self.dimension_name, [element])

        self.assertEqual(element, self.tm1.elements.get(self.dimension_name, self.dimension_name, element.name))

    def test_add_elements_multi(self):
        element1 = Element(name="Element1", element_type="Numeric")
        element2 = Element(name="Element2", element_type="Numeric")
        self.tm1.elements.add_elements(self.dimension_name, self.dimension_name, [element1, element2])

        self.assertEqual(element1, self.tm1.elements.get(self.dimension_name, self.dimension_name, element1.name))
        self.assertEqual(element2, self.tm1.elements.get(self.dimension_name, self.dimension_name, element2.name))

    def test_add_elements_fail(self):
        with self.assertRaises(TM1pyRestException) as _:
            element = Element(self.years[0], "Numeric")
            self.tm1.elements.add_elements(self.dimension_name, self.dimension_name, [element])

    @skip_if_version_lower_than(version="11.4")
    def test_add_elements_use_blob(self):
        elements = [Element("Element1", "Numeric"), Element("Element2", "String")]
        self.tm1.elements.add_elements(self.dimension_name, self.hierarchy_name, elements, use_blob=True)

        for element in elements:
            self.assertEqual(element, self.tm1.elements.get(self.dimension_name, self.hierarchy_name, element.name))

    @skip_if_version_lower_than(version="11.4")
    def test_add_elements_use_blob_with_consolidations(self):
        elements = [
            Element("Leaf1", "Numeric"),
            Element("Leaf2", "Numeric"),
            Element("Cons A", "Consolidated"),
            Element("Cons B", "Consolidated"),
        ]
        self.tm1.elements.add_elements(self.dimension_name, self.hierarchy_name, elements, use_blob=True)

        for element in elements:
            self.assertEqual(element, self.tm1.elements.get(self.dimension_name, self.hierarchy_name, element.name))

    @skip_if_version_lower_than(version="11.4")
    def test_add_edges_use_blob(self):
        # add new leaves first, then wire them under an existing consolidation via blob
        self.tm1.elements.add_elements(
            self.dimension_name,
            self.hierarchy_name,
            [Element("2050", "Numeric"), Element("2051", "Numeric")],
            use_blob=True,
        )
        self.tm1.elements.add_edges(
            dimension_name=self.dimension_name,
            hierarchy_name=self.hierarchy_name,
            edges={("Total Years", "2050"): 1, ("Total Years", "2051"): 1},
            use_blob=True,
        )

        edges = self.tm1.elements.get_edges(self.dimension_name, self.hierarchy_name)
        self.assertEqual(edges[("Total Years", "2050")], 1)
        self.assertEqual(edges[("Total Years", "2051")], 1)

    @skip_if_version_lower_than(version="11.4")
    def test_add_elements_and_edges_use_blob_build_consolidation(self):
        # build a fresh consolidation with leaves entirely via blob (elements first, then edges)
        self.tm1.elements.add_elements(
            self.dimension_name,
            self.hierarchy_name,
            [Element("New Cons", "Consolidated"), Element("Child A", "Numeric"), Element("Child B", "Numeric")],
            use_blob=True,
        )
        self.tm1.elements.add_edges(
            dimension_name=self.dimension_name,
            hierarchy_name=self.hierarchy_name,
            edges={("New Cons", "Child A"): 1, ("New Cons", "Child B"): 2},
            use_blob=True,
        )

        self.assertEqual(
            Element.Types.CONSOLIDATED,
            self.tm1.elements.get(self.dimension_name, self.hierarchy_name, "New Cons").element_type,
        )
        edges = self.tm1.elements.get_edges(self.dimension_name, self.hierarchy_name)
        self.assertEqual(edges[("New Cons", "Child A")], 1)
        self.assertEqual(edges[("New Cons", "Child B")], 2)

    def test_add_element_attributes_single(self):
        element_attribute = ElementAttribute(name="Attribute1", attribute_type="String")
        self.tm1.elements.add_element_attributes(self.dimension_name, self.dimension_name, [element_attribute])

        self.assertIn(
            element_attribute, self.tm1.elements.get_element_attributes(self.dimension_name, self.dimension_name)
        )

    def test_add_element_attributes_multi(self):
        element_attribute1 = ElementAttribute(name="Attribute1", attribute_type="String")
        element_attribute2 = ElementAttribute(name="Attribute2", attribute_type="String")
        self.tm1.elements.add_element_attributes(
            self.dimension_name, self.dimension_name, [element_attribute1, element_attribute2]
        )

        self.assertIn(
            element_attribute1, self.tm1.elements.get_element_attributes(self.dimension_name, self.dimension_name)
        )
        self.assertIn(
            element_attribute2, self.tm1.elements.get_element_attributes(self.dimension_name, self.dimension_name)
        )

    def test_add_element_attributes_fail(self):
        with self.assertRaises(TM1pyRestException) as _:
            element_attribute = ElementAttribute(name=self.attributes[0], attribute_type="String")

            self.tm1.elements.add_element_attributes(self.dimension_name, self.dimension_name, [element_attribute])

    def test_execute_set_mdx_element_names(self):
        mdx = f"{{[{self.dimension_name}].[1990]}}"
        members = self.tm1.elements.execute_set_mdx_element_names(mdx=mdx)
        self.assertEqual(members, ["1990"])

    def test_execute_set_mdx(self):
        mdx = f"{{[{self.dimension_name}].[1990]}}"
        members = self.tm1.elements.execute_set_mdx(
            mdx=mdx, member_properties=["Name"], element_properties=None, parent_properties=None
        )

        self.assertEqual(members, [[{"Name": "1990"}]])

    def test_execute_set_mdx_return_async_id(self):
        mdx = f"{{[{self.dimension_name}].[1990]}}"
        async_id = self.tm1.elements.execute_set_mdx(
            mdx=mdx, member_properties=["Name"], element_properties=None, parent_properties=None, return_async_id=True
        )

        self.assertGreater(len(async_id), 5)

    def test_execute_set_mdx_attribute_with_space(self):
        mdx = f"{{[{self.dimension_name}].[1990]}}"
        members = self.tm1.elements.execute_set_mdx(
            mdx=mdx,
            member_properties=["Name", "Attributes/Previous Year"],
            element_properties=None,
            parent_properties=None,
        )

        self.assertEqual(members, [[{"Name": "1990", "Attributes": {"Previous Year": "1989"}}]])

    def test_get_element_types(self):
        element_types = self.tm1.elements.get_element_types(self.dimension_name, self.hierarchy_name)
        expected = {
            "No Year": "Numeric",
            "1989": "Numeric",
            "1990": "Numeric",
            "1991": "Numeric",
            "1992": "Numeric",
            "Total Years": "Consolidated",
            "All Consolidations": "Consolidated",
        }
        self.assertEqual(expected, element_types)

    @skip_if_version_lower_than(version="11.8.023")
    def test_element_lock_and_unlock(self):
        self.tm1.elements.element_lock(
            dimension_name=self.dimension_name, hierarchy_name=self.hierarchy_name, element_name="1991"
        )

        query = MdxBuilder.from_cube(self.attribute_cube_name)
        query.add_member_tuple_to_columns(
            f"[{self.dimension_name}].[1991]", f"[{self.attribute_cube_name}].[Previous Year]"
        )

        with self.assertRaises(TM1pyException):
            self.tm1.cubes.cells.write_value("3000", self.attribute_cube_name, ("1991", "Previous Year"))
        self.assertEqual(self.tm1.cells.execute_mdx_values(mdx=query.to_mdx()), ["1990"])

        self.tm1.elements.element_unlock(
            dimension_name=self.dimension_name, hierarchy_name=self.hierarchy_name, element_name="1991"
        )
        self.tm1.cubes.cells.write_value("4000", self.attribute_cube_name, ("1991", "Previous Year"))
        self.assertEqual(self.tm1.cells.execute_mdx_values(mdx=query.to_mdx()), ["4000"])

    def test_get_element_types_from_all_hierarchies_with_single_hierarchy(self):
        expected = {
            "No Year": "Numeric",
            "1989": "Numeric",
            "1990": "Numeric",
            "1991": "Numeric",
            "1992": "Numeric",
            "Total Years": "Consolidated",
            "All Consolidations": "Consolidated",
        }
        element_types = self.tm1.elements.get_element_types_from_all_hierarchies(self.dimension_name)
        self.assertEqual(expected, element_types)

    def test_get_element_types_from_all_hierarchies(self):
        expected = {
            "Elem1": "Numeric",
            "Elem2": "Numeric",
            "Elem3": "Numeric",
            "Elem4": "Numeric",
            "Elem5": "Numeric",
            "Elem6": "Numeric",
            "Cons1": "Consolidated",
            "Cons2": "Consolidated",
            "Cons3": "Consolidated",
        }
        element_types = self.tm1.elements.get_element_types_from_all_hierarchies(self.dimension_with_hierarchies_name)

        self.assertEqual(expected, element_types)

    def test_get_element_types_from_all_hierarchies_skip_consolidations(self):

        expected = {
            "Elem1": "Numeric",
            "Elem2": "Numeric",
            "Elem3": "Numeric",
            "Elem4": "Numeric",
            "Elem5": "Numeric",
            "Elem6": "Numeric",
        }
        element_types = self.tm1.elements.get_element_types_from_all_hierarchies(
            dimension_name=self.dimension_with_hierarchies_name, skip_consolidations=True
        )

        self.assertEqual(expected, element_types)

    def test_remove_edge_happy_case(self):
        self.tm1.elements.remove_edge(
            dimension_name=self.dimension_name,
            hierarchy_name=self.hierarchy_name,
            parent="Total Years",
            component="1989",
        )

        edges = self.tm1.elements.get_edges(self.dimension_name, self.dimension_name)
        self.assertNotIn(("Total Years", "1989"), edges)

    @skip_if_version_lower_than(version="11.4")
    def test_delete_edges(self):
        self.tm1.elements.delete_edges(
            dimension_name=self.dimension_name,
            hierarchy_name=self.hierarchy_name,
            edges=[("Total Years", "1989"), ("Total Years", "1990")],
        )

        edges = self.tm1.elements.get_edges(self.dimension_name, self.dimension_name)
        self.assertNotIn(("Total Years", "1989"), edges)
        self.assertNotIn(("Total Years", "1990"), edges)

    @skip_if_version_lower_than(version="11.4")
    def test_delete_edges_skip_invalid_edges_true(self):
        self.tm1.elements.delete_edges(
            dimension_name=self.dimension_name,
            hierarchy_name=self.hierarchy_name,
            edges=[("Every Year", "1989"), ("Total Years", "1989"), ("Total Years", "1990")],
            skip_invalid_edges=True,
        )

        edges = self.tm1.elements.get_edges(self.dimension_name, self.dimension_name)
        self.assertNotIn(("Total Years", "1989"), edges)
        self.assertNotIn(("Total Years", "1990"), edges)

    @skip_if_version_lower_than(version="11.4")
    def test_delete_edges_skip_invalid_edges_false(self):
        with self.assertRaises(TM1pyException):
            self.tm1.elements.delete_edges(
                dimension_name=self.dimension_name,
                hierarchy_name=self.hierarchy_name,
                edges=[("Every Year", "1989")],
                skip_invalid_edges=False,
            )

    @skip_if_version_lower_than(version="11.4")
    def test_delete_edges_use_blob(self):
        self.tm1.elements.delete_edges(
            dimension_name=self.dimension_name,
            hierarchy_name=self.hierarchy_name,
            edges=[("Total Years", "1989"), ("Total Years", "1990")],
            use_blob=True,
        )

        edges = self.tm1.elements.get_edges(self.dimension_name, self.dimension_name)
        self.assertNotIn(("Total Years", "1989"), edges)
        self.assertNotIn(("Total Years", "1990"), edges)

    @skip_if_version_lower_than(version="11.4")
    def test_delete_edges_use_blob_skip_invalid_edges_true(self):
        self.tm1.elements.delete_edges(
            dimension_name=self.dimension_name,
            hierarchy_name=self.hierarchy_name,
            edges=[("Every Year", "1989"), ("Total Years", "1989"), ("Total Years", "1990")],
            use_blob=True,
            skip_invalid_edges=True,
        )

        edges = self.tm1.elements.get_edges(self.dimension_name, self.dimension_name)
        self.assertNotIn(("Total Years", "1989"), edges)
        self.assertNotIn(("Total Years", "1990"), edges)

    @skip_if_version_lower_than(version="11.4")
    def test_delete_edges_use_blob_skip_invalid_edges_false(self):
        with self.assertRaises(TM1pyWritePartialFailureException):
            self.tm1.elements.delete_edges(
                dimension_name=self.dimension_name,
                hierarchy_name=self.hierarchy_name,
                edges=[("Every Year", "1989")],
                use_blob=True,
                skip_invalid_edges=False,
            )

    @skip_if_version_lower_than(version="11.4")
    def test_delete_edges_use_ti_and_skip_invalid_edges_true(self):
        self.tm1.elements.delete_edges(
            dimension_name=self.dimension_name,
            hierarchy_name=self.hierarchy_name,
            edges=[("Every Year", "1989"), ("Total Years", "1989"), ("Total Years", "1990")],
            use_ti=True,
            skip_invalid_edges=True,
        )

        edges = self.tm1.elements.get_edges(self.dimension_name, self.dimension_name)
        self.assertNotIn(("Total Years", "1989"), edges)
        self.assertNotIn(("Total Years", "1990"), edges)

    @skip_if_version_lower_than(version="11.4")
    def test_delete_edges_use_ti_skip_invalid_edges_false(self):
        with self.assertRaises(TM1pyException):
            self.tm1.elements.delete_edges(
                dimension_name=self.dimension_name,
                hierarchy_name=self.hierarchy_name,
                edges=[("Every Year", "1989")],
                use_ti=True,
                skip_invalid_edges=False,
            )

    def test_remove_edge_parent_not_existing(self):
        with self.assertRaises(TM1pyRestException):
            self.tm1.elements.remove_edge(
                dimension_name=self.dimension_name,
                hierarchy_name=self.hierarchy_name,
                parent="Not Existing Consolidation",
                component="1989",
            )

    def test_remove_edge_child_not_existing(self):
        with self.assertRaises(TM1pyRestException):
            self.tm1.elements.remove_edge(
                dimension_name=self.dimension_name,
                hierarchy_name=self.hierarchy_name,
                parent="Total Years",
                component="Not Existing Element",
            )

    def test_get_parents_happy_case(self):
        parents = self.tm1.elements.get_parents(
            dimension_name=self.dimension_name, hierarchy_name=self.hierarchy_name, element_name="1989"
        )

        self.assertEqual(["Total Years"], parents)

    def test_get_parents_case_and_space_insensitive(self):
        parents = self.tm1.elements.get_parents(
            dimension_name=self.dimension_name, hierarchy_name=self.hierarchy_name, element_name="TOTALYEARS"
        )

        self.assertEqual(["All Consolidations"], parents)

    def test_get_parents_no_parents(self):
        parents = self.tm1.elements.get_parents(
            dimension_name=self.dimension_name, hierarchy_name=self.hierarchy_name, element_name="All Consolidations"
        )

        self.assertEqual([], parents)

    def test_get_parents_not_existing(self):
        with self.assertRaises(TM1pyRestException):
            self.tm1.elements.get_parents(
                dimension_name=self.dimension_name,
                hierarchy_name=self.hierarchy_name,
                element_name="Not Existing Element",
            )

    def test_get_parents_of_all_elements_happy_case(self):
        parents = self.tm1.elements.get_parents_of_all_elements(
            dimension_name=self.dimension_name, hierarchy_name=self.hierarchy_name
        )

        self.assertEqual(len(parents), 7)

    def test_element_is_parent_dim_not_exist(self):
        with self.assertRaises(TM1pyRestException):
            self.tm1.elements.element_is_parent(
                dimension_name=self.dimension_does_not_exist_name,
                hierarchy_name=self.hierarchy_name,
                parent_name="All Consolidations",
                element_name="Total Years",
            )

    def test_element_is_parent(self):
        result = self.tm1.elements.element_is_parent(
            dimension_name=self.dimension_name,
            hierarchy_name=self.hierarchy_name,
            parent_name="All Consolidations",
            element_name="Total Years",
        )
        self.assertEqual(True, result)

    def test_element_is_not_parent(self):
        result = self.tm1.elements.element_is_parent(
            dimension_name=self.dimension_name,
            hierarchy_name=self.hierarchy_name,
            parent_name="All Consolidations",
            element_name="1992",
        )
        self.assertEqual(False, result)

    def test_element_is_ancestor(self):
        result = self.tm1.elements.element_is_ancestor(
            dimension_name=self.dimension_name,
            hierarchy_name=self.hierarchy_name,
            ancestor_name="All Consolidations",
            element_name="1992",
        )
        self.assertEqual(True, result)

    def test_element_is_ancestor_tm1drilldownmember_false(self):
        result = self.tm1.elements.element_is_ancestor(
            dimension_name=self.dimension_name,
            hierarchy_name=self.hierarchy_name,
            ancestor_name="1992",
            element_name="1991",
            method="TM1DrillDownMember",
        )
        self.assertEqual(False, result)

    def test_element_is_ancestor_tm1drilldownmember_not_existing_element(self):
        result = self.tm1.elements.element_is_ancestor(
            dimension_name=self.dimension_name,
            hierarchy_name=self.hierarchy_name,
            ancestor_name="1992",
            element_name="NotExisting",
            method="TM1DrillDownMember",
        )
        self.assertEqual(False, result)

    def test_element_is_ancestor_tm1drilldownmember_not_existing_dimension(self):
        with self.assertRaises(TM1pyException):
            self.tm1.elements.element_is_ancestor(
                dimension_name=self.dimension_does_not_exist_name,
                hierarchy_name=self.hierarchy_name,
                ancestor_name="All Consolidations",
                element_name="1992",
                method="TM1DrillDownMember",
            )

    def test_element_is_ancestor_not_existing_hierarchy(self):
        with self.assertRaises(TM1pyException):
            self.tm1.elements.element_is_ancestor(
                dimension_name=self.dimension_name,
                hierarchy_name=self.hierarchy_does_not_exist_name,
                ancestor_name="All Consolidations",
                element_name="Total Years",
            )

    def test_element_is_ancestor_descendants_method(self):
        result = self.tm1.elements.element_is_ancestor(
            dimension_name=self.dimension_name,
            hierarchy_name=self.hierarchy_name,
            ancestor_name="All Consolidations",
            element_name="1992",
            method="Descendants",
        )
        self.assertEqual(True, result)

    def test_element_is_ancestor_descendants_method_false(self):
        result = self.tm1.elements.element_is_ancestor(
            dimension_name=self.dimension_name,
            hierarchy_name=self.hierarchy_name,
            ancestor_name="1992",
            element_name="1991",
            method="Descendants",
        )
        self.assertEqual(False, result)

    def test_element_is_ancestor_descendants_method_not_existing_element(self):
        result = self.tm1.elements.element_is_ancestor(
            dimension_name=self.dimension_name,
            hierarchy_name=self.hierarchy_name,
            ancestor_name="1992",
            element_name="Not Existing",
            method="descendants",
        )
        self.assertEqual(False, result)

    def test_element_is_ancestor_descendants_method_not_existing_dimension(self):
        with self.assertRaises(TM1pyException):
            self.tm1.elements.element_is_ancestor(
                dimension_name=self.dimension_does_not_exist_name,
                hierarchy_name=self.hierarchy_name,
                ancestor_name="All Consolidations",
                element_name="1992",
                method="descendants",
            )

    def test_element_is_ancestor_descendants_method_not_existing_hierarchy(self):
        with self.assertRaises(TM1pyException):
            self.tm1.elements.element_is_ancestor(
                dimension_name=self.dimension_name,
                hierarchy_name=self.hierarchy_does_not_exist_name,
                ancestor_name="All Consolidations",
                element_name="1992",
                method="descendants",
            )

    def test_element_is_ancestor_ti_method(self):
        result = self.tm1.elements.element_is_ancestor(
            dimension_name=self.dimension_name,
            hierarchy_name=self.hierarchy_name,
            ancestor_name="All Consolidations",
            element_name="1992",
            method="TI",
        )
        self.assertEqual(True, result)

    def test_element_is_ancestor_ti_method_false(self):
        result = self.tm1.elements.element_is_ancestor(
            dimension_name=self.dimension_name,
            hierarchy_name=self.hierarchy_name,
            ancestor_name="1992",
            element_name="1991",
            method="TI",
        )
        self.assertEqual(False, result)

    def test_element_is_ancestor_ti_method_not_existing(self):
        result = self.tm1.elements.element_is_ancestor(
            dimension_name=self.dimension_name,
            hierarchy_name=self.hierarchy_name,
            ancestor_name="1992",
            element_name="Not Existing",
            method="TI",
        )
        self.assertEqual(False, result)

    def test_element_is_ancestor_ti_method_not_existing_dimension(self):
        with self.assertRaises(TM1pyException):
            self.tm1.elements.element_is_ancestor(
                dimension_name=self.dimension_does_not_exist_name,
                hierarchy_name=self.hierarchy_name,
                ancestor_name="All Consolidations",
                element_name="1992",
                method="TI",
            )

    def test_element_is_ancestor_ti_method_not_existing_hierarchy(self):
        with self.assertRaises(TM1pyException):
            self.tm1.elements.element_is_ancestor(
                dimension_name=self.dimension_name,
                hierarchy_name=self.hierarchy_does_not_exist_name,
                ancestor_name="All Consolidations",
                element_name="1992",
                method="TI",
            )

    def test_get_parents_of_all_elements_with_closing_brace_in_dimension_name(self):
        # regression: control dimensions (names starting with "}", e.g.
        # "}APQ Time Second") must not break URL construction in
        # get_parents_of_all_elements (formerly raised
        # "Single '}' encountered in format string").
        dimension_name = "}TM1py_unittest_close_brace_" + generate_test_uuid()
        hierarchy_name = dimension_name

        dimension = Dimension(dimension_name)
        hierarchy = Hierarchy(dimension_name, hierarchy_name)
        hierarchy.add_element("Total", "Consolidated")
        hierarchy.add_element("Child1", "Numeric")
        hierarchy.add_element("Child2", "Numeric")
        hierarchy.add_edge("Total", "Child1", 1)
        hierarchy.add_edge("Total", "Child2", 1)
        dimension.add_hierarchy(hierarchy)
        self.tm1.dimensions.update_or_create(dimension)

        try:
            parents = self.tm1.elements.get_parents_of_all_elements(
                dimension_name=dimension_name, hierarchy_name=hierarchy_name
            )
        finally:
            self.tm1.dimensions.delete(dimension_name)

        self.assertEqual(["Total"], parents["Child1"])
        self.assertEqual(["Total"], parents["Child2"])
        self.assertEqual([], parents["Total"])

    @classmethod
    def tearDownClass(cls):
        cls.tm1.logout()


class _FakeRest:
    """Minimal stand-in for RestService exposing just the version (no server connection)."""

    def __init__(self, version: str):
        self.version = version


class TestElementServiceBlobProcessBuilders(unittest.TestCase):
    """Unit tests for the blob-based element/edge helpers (no server connection)."""

    @staticmethod
    def _element_service(version: str = "12.0.0") -> ElementService:
        service = object.__new__(ElementService)
        service._rest = _FakeRest(version)
        return service

    def test_blob_datasource_process_sets_utf8_and_variables(self):
        service = self._element_service("12.0.0")
        process = service._build_blob_datasource_process(
            process_name="p", blob_filename="f.csv", variables=[("vA", "String"), ("vN", "Numeric")]
        )
        self.assertIn("SetInputCharacterSet('TM1CS_UTF8')", process.prolog_procedure)
        self.assertEqual(process.datasource_data_source_name_for_server, "f.csv")
        names_and_types = {v["Name"]: v["Type"] for v in process.variables}
        self.assertEqual(names_and_types, {"vA": "String", "vN": "Numeric"})

    def test_blob_datasource_process_appends_blb_on_v11(self):
        service = self._element_service("11.8.0")
        process = service._build_blob_datasource_process(process_name="p", blob_filename="f.csv", variables=[])
        # v11 auto-appends a .blb extension to documents created via the contents api
        self.assertEqual(process.datasource_data_source_name_for_server, "f.csv.blb")

    def test_build_add_elements_process(self):
        service = self._element_service("12.0.0")
        process = service._build_add_elements_from_blob_process("Dim", "Dim", "p", "f.csv")
        self.assertEqual([v["Name"] for v in process.variables], ["vElement", "vType"])
        self.assertTrue(all(v["Type"] == "String" for v in process.variables))
        self.assertIn("HierarchyElementInsert('Dim','Dim','',vElement,vType);", process.metadata_procedure)

    def test_build_add_edges_process_has_numeric_weight(self):
        service = self._element_service("12.0.0")
        process = service._build_add_edges_from_blob_process("Dim", "Dim", "p", "f.csv")
        names_and_types = {v["Name"]: v["Type"] for v in process.variables}
        self.assertEqual(names_and_types, {"vParent": "String", "vChild": "String", "vWeight": "Numeric"})
        self.assertIn("HierarchyElementComponentAdd('Dim','Dim',vParent,vChild,vWeight);", process.metadata_procedure)

    def test_refactored_delete_edges_process_preserves_skip_invalid_guard(self):
        service = self._element_service("12.0.0")
        process = service._build_unwind_hierarchy_edges_from_blob_process(
            dimension_name="Dim",
            hierarchy_name="Dim",
            process_name="p",
            blob_filename="f.csv",
            skip_invalid_edges=True,
        )
        self.assertEqual([v["Name"] for v in process.variables], ["vParent", "vChild"])
        self.assertIn("ElementIsParent('Dim','Dim',vParent,vChild)", process.metadata_procedure)
        self.assertIn("HierarchyElementComponentDelete('Dim','Dim',vParent,vChild);", process.metadata_procedure)

    def test_add_elements_dispatches_to_blob(self):
        service = self._element_service("12.0.0")
        captured = {}
        service.add_elements_use_blob = lambda **kwargs: captured.update(kwargs) or "BLOB"
        result = service.add_elements("Dim", "Dim", [Element("e", "Numeric")], use_blob=True)
        self.assertEqual(result, "BLOB")
        self.assertEqual(captured["dimension_name"], "Dim")
        self.assertEqual(captured["hierarchy_name"], "Dim")
        self.assertTrue(captured["remove_blob"])

    def test_add_edges_dispatches_to_blob(self):
        service = self._element_service("12.0.0")
        captured = {}
        service.add_edges_use_blob = lambda **kwargs: captured.update(kwargs) or "BLOB"
        result = service.add_edges("Dim", edges={("Total", "Child1"): 1}, use_blob=True)
        self.assertEqual(result, "BLOB")
        # hierarchy_name defaults to the dimension name before dispatch
        self.assertEqual(captured["hierarchy_name"], "Dim")
        self.assertEqual(captured["edges"], {("Total", "Child1"): 1})


class TestElementFiltering(unittest.TestCase):
    """Tests for the element_type / name_pattern / level kwargs on
    get_elements and get_element_names.

    Fixture cleanup is registered via self.addCleanup(...) inside setUp,
    so there is no tearDown method.
    """

    tm1: TM1Service

    @classmethod
    def setUpClass(cls):
        cls.config = configparser.ConfigParser()
        cls.config.read(Path(__file__).parent.joinpath("config.ini"))
        cls.tm1 = TM1Service(**cls.config["tm1srv01"])

    @classmethod
    def tearDownClass(cls):
        cls.tm1.logout()

    def setUp(self):
        """Create a fixture dimension with a known, predictable element set.

        Level 0 (leaves):
          Numeric:  'Numeric A', 'Numeric B', 'Numeric C', "O'Brien"
          String:   'String A', 'String B'
        Level 1 (consolidations):
          'Region North' (parent of Numeric A, Numeric B)
          'Region South' (parent of Numeric C, "O'Brien")
        Level 2 (top consolidation):
          'Total Regions' (parent of both regions)
        """
        dimension_uuid = generate_test_uuid()
        self.dimension_name = f"TM1py_unittest_filter_{dimension_uuid}"
        self.hierarchy_name = self.dimension_name

        d = Dimension(self.dimension_name)
        h = Hierarchy(self.dimension_name, self.hierarchy_name)

        h.add_element("Numeric A", "Numeric")
        h.add_element("Numeric B", "Numeric")
        h.add_element("Numeric C", "Numeric")
        h.add_element("O'Brien", "Numeric")
        h.add_element("String A", "String")
        h.add_element("String B", "String")

        h.add_element("Region North", "Consolidated")
        h.add_element("Region South", "Consolidated")
        h.add_element("Total Regions", "Consolidated")

        h.add_edge("Region North", "Numeric A", 1)
        h.add_edge("Region North", "Numeric B", 1)
        h.add_edge("Region South", "Numeric C", 1)
        h.add_edge("Region South", "O'Brien", 1)
        h.add_edge("Total Regions", "Region North", 1)
        h.add_edge("Total Regions", "Region South", 1)

        # Add a placeholder attribute so the }ElementAttributes_<dim> cube is
        # created. get_elements_dataframe requires this cube to exist.
        h.add_element_attribute("Description", "String")

        d.add_hierarchy(h)
        self.tm1.dimensions.update_or_create(d)
        self.addCleanup(self._cleanup_dimension)

    def _cleanup_dimension(self):
        if self.tm1.dimensions.exists(self.dimension_name):
            self.tm1.dimensions.delete(self.dimension_name)

    def test_fixture_creates(self):
        names = self.tm1.elements.get_element_names(self.dimension_name, self.hierarchy_name)
        self.assertEqual(
            set(names),
            {
                "Numeric A",
                "Numeric B",
                "Numeric C",
                "O'Brien",
                "String A",
                "String B",
                "Region North",
                "Region South",
                "Total Regions",
            },
        )

    # ------------------------------------------------------------------
    # get_element_names: element_type filter
    # ------------------------------------------------------------------

    def test_names_element_type_numeric(self):
        names = self.tm1.elements.get_element_names(self.dimension_name, self.hierarchy_name, element_type="numeric")
        self.assertEqual(set(names), {"Numeric A", "Numeric B", "Numeric C", "O'Brien"})

    def test_names_element_type_string(self):
        names = self.tm1.elements.get_element_names(self.dimension_name, self.hierarchy_name, element_type="string")
        self.assertEqual(set(names), {"String A", "String B"})

    def test_names_element_type_consolidated(self):
        names = self.tm1.elements.get_element_names(
            self.dimension_name, self.hierarchy_name, element_type="consolidated"
        )
        self.assertEqual(set(names), {"Region North", "Region South", "Total Regions"})

    def test_names_element_type_enum(self):
        names = self.tm1.elements.get_element_names(
            self.dimension_name, self.hierarchy_name, element_type=Element.Types.NUMERIC
        )
        self.assertEqual(set(names), {"Numeric A", "Numeric B", "Numeric C", "O'Brien"})

    def test_names_element_type_list_numeric_and_consolidated(self):
        """Stated use case: 'all non-string elements'."""
        names = self.tm1.elements.get_element_names(
            self.dimension_name,
            self.hierarchy_name,
            element_type=["numeric", "consolidated"],
        )
        self.assertEqual(
            set(names),
            {
                "Numeric A",
                "Numeric B",
                "Numeric C",
                "O'Brien",
                "Region North",
                "Region South",
                "Total Regions",
            },
        )

    # ------------------------------------------------------------------
    # get_element_names: name_pattern filter
    # ------------------------------------------------------------------

    def test_names_pattern_exact(self):
        names = self.tm1.elements.get_element_names(self.dimension_name, self.hierarchy_name, name_pattern="Numeric A")
        self.assertEqual(names, ["Numeric A"])

    def test_names_pattern_startswith(self):
        names = self.tm1.elements.get_element_names(self.dimension_name, self.hierarchy_name, name_pattern="Numeric*")
        self.assertEqual(set(names), {"Numeric A", "Numeric B", "Numeric C"})

    def test_names_pattern_endswith(self):
        names = self.tm1.elements.get_element_names(self.dimension_name, self.hierarchy_name, name_pattern="*A")
        # Numeric A, String A. Region North contains 'a' but does not endswith.
        self.assertEqual(set(names), {"Numeric A", "String A"})

    def test_names_pattern_contains(self):
        # 'Total Regions' matches because after space-stripping the normalized name 'totalregions' contains 'region'.
        names = self.tm1.elements.get_element_names(self.dimension_name, self.hierarchy_name, name_pattern="*Region*")
        self.assertEqual(set(names), {"Region North", "Region South", "Total Regions"})

    def test_names_pattern_case_insensitive(self):
        names = self.tm1.elements.get_element_names(self.dimension_name, self.hierarchy_name, name_pattern="numeric*")
        self.assertEqual(set(names), {"Numeric A", "Numeric B", "Numeric C"})

    def test_names_pattern_space_insensitive(self):
        # 'NumericA' (no space) should match 'Numeric A'
        names = self.tm1.elements.get_element_names(self.dimension_name, self.hierarchy_name, name_pattern="NumericA")
        self.assertEqual(names, ["Numeric A"])

    def test_names_pattern_with_quote(self):
        names = self.tm1.elements.get_element_names(self.dimension_name, self.hierarchy_name, name_pattern="*O'Brien*")
        self.assertEqual(names, ["O'Brien"])

    # ------------------------------------------------------------------
    # get_element_names: level filter
    # ------------------------------------------------------------------

    def test_names_level_zero(self):
        names = self.tm1.elements.get_element_names(self.dimension_name, self.hierarchy_name, level=0)
        self.assertEqual(
            set(names),
            {"Numeric A", "Numeric B", "Numeric C", "O'Brien", "String A", "String B"},
        )

    def test_names_level_one(self):
        names = self.tm1.elements.get_element_names(self.dimension_name, self.hierarchy_name, level=1)
        self.assertEqual(set(names), {"Region North", "Region South"})

    def test_names_level_two(self):
        names = self.tm1.elements.get_element_names(self.dimension_name, self.hierarchy_name, level=2)
        self.assertEqual(names, ["Total Regions"])

    # ------------------------------------------------------------------
    # get_element_names: composed (AND)
    # ------------------------------------------------------------------

    def test_names_type_and_pattern(self):
        # Numeric elements containing 'A'
        names = self.tm1.elements.get_element_names(
            self.dimension_name,
            self.hierarchy_name,
            element_type="numeric",
            name_pattern="*A*",
        )
        self.assertEqual(set(names), {"Numeric A"})

    def test_names_type_and_level(self):
        # Consolidated at level 1
        names = self.tm1.elements.get_element_names(
            self.dimension_name,
            self.hierarchy_name,
            element_type="consolidated",
            level=1,
        )
        self.assertEqual(set(names), {"Region North", "Region South"})

    def test_names_all_three_composed(self):
        # Numeric leaves whose normalized name ends in 'c'. After space-stripping
        # and lowercasing, only "Numeric C" qualifies. ("Numeric A"/"Numeric B"
        # also contain the letter 'c' from "numeric" so a *C* pattern would
        # match all three; use endswith to single out "Numeric C".)
        names = self.tm1.elements.get_element_names(
            self.dimension_name,
            self.hierarchy_name,
            element_type="numeric",
            name_pattern="*C",
            level=0,
        )
        self.assertEqual(names, ["Numeric C"])

    # ------------------------------------------------------------------
    # get_element_names: no filter sanity check
    # ------------------------------------------------------------------

    def test_names_no_filter_returns_all(self):
        names = self.tm1.elements.get_element_names(self.dimension_name, self.hierarchy_name)
        # 4 numeric + 2 string + 3 consolidated
        self.assertEqual(len(names), 9)

    # ------------------------------------------------------------------
    # get_element_names: validation passthrough
    # ------------------------------------------------------------------

    def test_names_invalid_type_raises(self):
        with self.assertRaises(ValueError):
            self.tm1.elements.get_element_names(self.dimension_name, self.hierarchy_name, element_type="bogus")

    def test_names_question_mark_raises(self):
        with self.assertRaises(ValueError):
            self.tm1.elements.get_element_names(self.dimension_name, self.hierarchy_name, name_pattern="foo?bar")

    # ------------------------------------------------------------------
    # get_elements (returns List[Element])
    # ------------------------------------------------------------------

    def test_elements_type_numeric(self):
        elements = self.tm1.elements.get_elements(self.dimension_name, self.hierarchy_name, element_type="numeric")
        self.assertEqual(
            {e.name for e in elements},
            {"Numeric A", "Numeric B", "Numeric C", "O'Brien"},
        )
        self.assertTrue(all(e.element_type == Element.Types.NUMERIC for e in elements))

    def test_elements_pattern_and_level(self):
        elements = self.tm1.elements.get_elements(
            self.dimension_name,
            self.hierarchy_name,
            name_pattern="Region*",
            level=1,
        )
        self.assertEqual(
            {e.name for e in elements},
            {"Region North", "Region South"},
        )

    def test_elements_no_filter_returns_all_with_types(self):
        elements = self.tm1.elements.get_elements(self.dimension_name, self.hierarchy_name)
        self.assertEqual(len(elements), 9)
        # Confirm we get the Type attribute populated (existing behavior preserved)
        types = {e.element_type for e in elements}
        self.assertEqual(
            types,
            {Element.Types.NUMERIC, Element.Types.STRING, Element.Types.CONSOLIDATED},
        )

    def test_elements_quote_escape(self):
        elements = self.tm1.elements.get_elements(self.dimension_name, self.hierarchy_name, name_pattern="*O'Brien*")
        self.assertEqual([e.name for e in elements], ["O'Brien"])
        self.assertEqual(elements[0].element_type, Element.Types.NUMERIC)

    # ------------------------------------------------------------------
    # Regression: verify behavior of typed methods is preserved after they
    # are refactored to delegate to get_element_names. Snapshots in
    # Tests/fixtures/element_filtering_snapshots/ were generated against
    # master before the refactor.
    # ------------------------------------------------------------------

    SNAPSHOT_DIR = Path(__file__).parent / "fixtures" / "element_filtering_snapshots"

    def _load_snapshot(self, name):
        path = self.SNAPSHOT_DIR / name
        if not path.exists():
            self.fail(
                f"Snapshot '{name}' not found at {self.SNAPSHOT_DIR}. "
                f"Regenerate by re-running the snapshot generator from the plan's "
                f"Phase 3 / Task 3.1."
            )
        with open(path) as f:
            return json.load(f)

    def test_regression_by_level_0(self):
        actual = self.tm1.elements.get_elements_by_level(self.dimension_name, self.hierarchy_name, level=0)
        expected = self._load_snapshot("by_level_0.json")
        self.assertEqual(sorted(actual), expected)

    def test_regression_by_level_1(self):
        actual = self.tm1.elements.get_elements_by_level(self.dimension_name, self.hierarchy_name, level=1)
        expected = self._load_snapshot("by_level_1.json")
        self.assertEqual(sorted(actual), expected)

    def test_regression_by_level_2(self):
        actual = self.tm1.elements.get_elements_by_level(self.dimension_name, self.hierarchy_name, level=2)
        expected = self._load_snapshot("by_level_2.json")
        self.assertEqual(sorted(actual), expected)

    def test_regression_wildcard_cases(self):
        """Verify get_elements_filtered_by_wildcard preserves case+space-insensitive contains."""
        for i in range(5):
            snap = self._load_snapshot(f"wildcard_{i}.json")
            actual = self.tm1.elements.get_elements_filtered_by_wildcard(
                self.dimension_name,
                self.hierarchy_name,
                wildcard=snap["wildcard"],
                level=snap["level"],
            )
            self.assertEqual(
                sorted(actual),
                snap["result"],
                msg=(
                    f"wildcard_{i}: wildcard={snap['wildcard']!r} level={snap['level']}, "
                    f"got {sorted(actual)!r}, expected {snap['result']!r}"
                ),
            )

    # ------------------------------------------------------------------
    # get_elements_dataframe with trio kwargs
    # ------------------------------------------------------------------

    @skip_if_no_pandas
    def test_dataframe_element_type_numeric(self):
        df = self.tm1.elements.get_elements_dataframe(
            self.dimension_name,
            self.hierarchy_name,
            element_type="numeric",
            skip_consolidations=False,
        )
        names = set(df[self.dimension_name].tolist())
        self.assertEqual(names, {"Numeric A", "Numeric B", "Numeric C", "O'Brien"})

    @skip_if_no_pandas
    def test_dataframe_pattern(self):
        df = self.tm1.elements.get_elements_dataframe(
            self.dimension_name,
            self.hierarchy_name,
            name_pattern="Region*",
        )
        names = set(df[self.dimension_name].tolist())
        self.assertEqual(names, {"Region North", "Region South"})

    @skip_if_no_pandas
    def test_dataframe_level(self):
        df = self.tm1.elements.get_elements_dataframe(
            self.dimension_name,
            self.hierarchy_name,
            level=0,
            skip_consolidations=False,
        )
        names = set(df[self.dimension_name].tolist())
        self.assertEqual(
            names,
            {"Numeric A", "Numeric B", "Numeric C", "O'Brien", "String A", "String B"},
        )

    @skip_if_no_pandas
    def test_dataframe_trio_composed(self):
        df = self.tm1.elements.get_elements_dataframe(
            self.dimension_name,
            self.hierarchy_name,
            element_type="numeric",
            name_pattern="*A*",
            level=0,
        )
        names = set(df[self.dimension_name].tolist())
        self.assertEqual(names, {"Numeric A"})

    @skip_if_no_pandas
    def test_dataframe_element_type_overrides_skip_consolidations(self):
        """When element_type is explicitly set, skip_consolidations is ignored
        (documented in docstring)."""
        df = self.tm1.elements.get_elements_dataframe(
            self.dimension_name,
            self.hierarchy_name,
            element_type=["numeric", "consolidated"],
            skip_consolidations=True,  # would normally drop consolidations
        )
        names = set(df[self.dimension_name].tolist())
        # Consolidations should be present despite skip_consolidations=True
        self.assertIn("Region North", names)
        self.assertIn("Region South", names)
        self.assertIn("Total Regions", names)

    @skip_if_no_pandas
    def test_dataframe_regression_no_filter(self):
        """Without trio kwargs, get_elements_dataframe matches the snapshot from master."""
        import pandas as pd

        snapshot = pd.read_csv(self.SNAPSHOT_DIR / "dataframe_default.csv")
        df = self.tm1.elements.get_elements_dataframe(self.dimension_name, self.hierarchy_name)
        # Snapshot's first column is the snapshot's dimension name; the test's
        # df uses a different dimension name. Compare row sets on element name + type.
        snap_first = snapshot.columns[0]
        df_first = df.columns[0]
        snap_rows = sorted(zip(snapshot[snap_first].tolist(), snapshot["Type"].tolist()))
        df_rows = sorted(zip(df[df_first].tolist(), df["Type"].tolist()))
        self.assertEqual(snap_rows, df_rows)

    @skip_if_no_pandas
    def test_dataframe_trio_empty_match_preserves_schema(self):
        """When the trio filter matches zero elements, the returned DataFrame must
        still carry the full column schema (attributes, levels, parents) so callers
        relying on df['<attr>'] don't see KeyError."""
        df_full = self.tm1.elements.get_elements_dataframe(self.dimension_name, self.hierarchy_name)
        df_empty = self.tm1.elements.get_elements_dataframe(
            self.dimension_name,
            self.hierarchy_name,
            name_pattern="NonExistentNameThatMatchesNothing*",
        )
        self.assertEqual(list(df_full.columns), list(df_empty.columns))
        self.assertEqual(len(df_empty), 0)


if __name__ == "__main__":
    unittest.main()
