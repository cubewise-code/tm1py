import configparser
import copy
import unittest
from pathlib import Path

from TM1py.Exceptions import TM1pyRestException, TM1pyException
from TM1py.Objects import Dimension, Hierarchy, Element, ElementAttribute
from TM1py.Services import TM1Service
from Tests.Utils import skip_if_no_pandas


class TestElementService(unittest.TestCase):
    tm1: TM1Service

    prefix = 'TM1py_unittest_element'
    dimension_name = f"{prefix}_dimension"
    dimension_with_hierarchies_name = f"{prefix}_dimension_with_hierarchies"
    hierarchy_name = dimension_name
    attribute_cube_name = '}ElementAttributes_' + dimension_name
    dimension_does_not_exist_name = f"{prefix}_dimension_does_not_exist"
    hierarchy_does_not_exist_name = dimension_does_not_exist_name

    @classmethod
    def setUpClass(cls):
        """
        Establishes a connection to TM1 and creates TM1 objects to use across all tests
        """

        # Connection to TM1
        cls.config = configparser.ConfigParser()
        cls.config.read(Path(__file__).parent.joinpath('config.ini'))
        cls.tm1 = TM1Service(**cls.config['tm1srv01'])

    def setUp(self):
        # create dimension with a default hierarchy
        d = Dimension(self.dimension_name)
        h = Hierarchy(self.dimension_name, self.hierarchy_name)

        # add elements
        self.years = ("No Year", "1989", "1990", "1991", "1992")
        self.extra_year = "4321"

        h.add_element('Total Years', 'Consolidated')
        h.add_element('All Consolidations', 'Consolidated')
        h.add_edge("All Consolidations", "Total Years", 1)
        for year in self.years:
            h.add_element(year, 'Numeric')
            h.add_edge('Total Years', year, 1)

        # add attributes
        self.attributes = ('Previous Year', 'Next Year')
        self.alias_attributes = ("Financial Year",)

        for attribute in self.attributes:
            h.add_element_attribute(attribute, "String")
        for attribute in self.alias_attributes:
            h.add_element_attribute(attribute, "Alias")
        d.add_hierarchy(h)
        self.tm1.dimensions.update_or_create(d)

        self.added_attribute_name = "NewAttribute"

        # write attribute values
        self.tm1.cubes.cells.write_value('1988', self.attribute_cube_name, ('1989', 'Previous Year'))
        self.tm1.cubes.cells.write_value('1989', self.attribute_cube_name, ('1990', 'Previous Year'))
        self.tm1.cubes.cells.write_value('1990', self.attribute_cube_name, ('1991', 'Previous Year'))
        self.tm1.cubes.cells.write_value('1991', self.attribute_cube_name, ('1992', 'Previous Year'))

        self.tm1.cubes.cells.write_value('1988/89', self.attribute_cube_name, ('1989', 'Financial Year'))
        self.tm1.cubes.cells.write_value('1989/90', self.attribute_cube_name, ('1990', 'Financial Year'))
        self.tm1.cubes.cells.write_value('1990/91', self.attribute_cube_name, ('1991', 'Financial Year'))
        self.tm1.cubes.cells.write_value('1991/92', self.attribute_cube_name, ('1992', 'Financial Year'))

        self.create_or_update_dimension_with_hierarchies()

    def tearDown(self):
        self.tm1.dimensions.delete(self.dimension_name)
        self.tm1.dimensions.delete(self.dimension_with_hierarchies_name)

    @classmethod
    def create_or_update_dimension_with_hierarchies(cls):
        dimension = Dimension(cls.dimension_with_hierarchies_name)
        dimension.add_hierarchy(
            Hierarchy(
                name="Hierarchy1",
                dimension_name=dimension.name,
                element_attributes=[ElementAttribute("Attr1", "String")],
                elements=[Element("Elem1", "Numeric"), Element("Elem2", "Numeric"), Element("Elem3", "Numeric")]))
        dimension.add_hierarchy(
            Hierarchy(
                name="Hierarchy2",
                dimension_name=dimension.name,
                elements=[Element("Elem4", "Numeric"), Element("Elem6", "Numeric"), Element("Cons1", "Consolidated")]))
        dimension.add_hierarchy(
            Hierarchy(
                name="Hierarchy3",
                dimension_name=dimension.name,
                element_attributes=[ElementAttribute("Attr2", "String")],
                elements=[Element("Elem5", "Numeric"), Element("Cons2", "Consolidated"),
                          Element("Cons3", "Consolidated")],
                edges={("Cons3", "Elem5"): 1}),
        )
        cls.tm1.dimensions.update_or_create(dimension)

    def test_create_and_delete_element(self):
        element = Element(self.extra_year, "String")
        self.tm1.dimensions.hierarchies.elements.create(
            self.dimension_name,
            self.hierarchy_name,
            element)

        element_returned = self.tm1.dimensions.hierarchies.elements.get(
            self.dimension_name,
            self.hierarchy_name,
            element.name)
        self.assertEqual(element, element_returned)

        self.tm1.dimensions.hierarchies.elements.delete(
            self.dimension_name,
            self.hierarchy_name,
            element.name)

    def test_get_element(self):
        for element_name in self.years:
            element = self.tm1.dimensions.hierarchies.elements.get(
                self.dimension_name,
                self.hierarchy_name,
                element_name)
            self.assertEqual(element.name, element_name)

    def test_update_element(self):
        element = Element(self.extra_year, Element.Types("S T R I N G"))
        self.tm1.dimensions.hierarchies.elements.create(
            self.dimension_name,
            self.hierarchy_name,
            element)

        element_name = self.extra_year
        element = self.tm1.dimensions.hierarchies.elements.get(self.dimension_name, self.hierarchy_name, element_name)
        element.element_type = "Numeric"
        self.tm1.dimensions.hierarchies.elements.update(self.dimension_name, self.hierarchy_name, element)

        element = self.tm1.dimensions.hierarchies.elements.get(self.dimension_name, self.hierarchy_name, element_name)
        self.assertTrue(element.element_type == Element.Types.NUMERIC)

        self.tm1.dimensions.hierarchies.elements.delete(
            self.dimension_name,
            self.hierarchy_name,
            element.name)

    def test_get_element_attributes(self):
        element_attributes = self.tm1.dimensions.hierarchies.elements.get_element_attributes(
            self.dimension_name,
            self.hierarchy_name)
        self.assertIn('Previous Year', element_attributes)
        self.assertIn('Next Year', element_attributes)

    def test_get_elements_filtered_by_attribute(self):
        elements = self.tm1.dimensions.hierarchies.elements.get_elements_filtered_by_attribute(
            self.dimension_name,
            self.hierarchy_name,
            'Previous Year',
            '1988')
        self.assertIn('1989', elements)

    def test_get_element_by_attribute_without_elements(self):
        elements = self.tm1.dimensions.hierarchies.elements.get_attribute_of_elements(
            dimension_name=self.dimension_name,
            hierarchy_name=self.hierarchy_name,
            attribute='Previous Year')
        self.assertEqual('1989', elements['1990'])
        self.assertEqual('1990', elements['1991'])
        self.assertNotIn(self.extra_year, elements)
        self.assertIsInstance(elements, dict)

    def test_get_element_by_attribute_with_elements(self):
        elements = self.tm1.dimensions.hierarchies.elements.get_attribute_of_elements(
            dimension_name=self.dimension_name,
            hierarchy_name=self.hierarchy_name,
            elements=["1990", "1991"],
            attribute="Previous Year",
            element_unique_names=True)
        self.assertNotIn("[" + self.dimension_name + "]." + "[" + self.hierarchy_name + "]." + "[1989]", elements)
        self.assertEqual("1989",
                         elements["[" + self.dimension_name + "]." + "[" + self.hierarchy_name + "]." + "[1990]"])
        self.assertIn("[" + self.dimension_name + "]." + "[" + self.hierarchy_name + "]." + "[1991]", elements)
        self.assertIsInstance(elements, dict)

    def test_create_filter_and_delete_element_attribute(self):
        attribute = ElementAttribute('Leap Year', 'Numeric')
        self.tm1.dimensions.hierarchies.elements.create_element_attribute(
            self.dimension_name,
            self.hierarchy_name, attribute)
        # write one element attribute value
        self.tm1.cubes.cells.write_value(
            1,
            '}ElementAttributes_' + self.dimension_name,
            ('1992', 'Leap Year'))
        elements = self.tm1.dimensions.hierarchies.elements.get_elements_filtered_by_attribute(
            self.dimension_name,
            self.hierarchy_name,
            'Leap Year', 1)
        self.assertIn('1992', elements)
        self.assertEqual(len(elements), 1)

        self.tm1.dimensions.hierarchies.elements.delete_element_attribute(
            self.dimension_name,
            self.hierarchy_name,
            "Leap Year")

    def test_get_elements(self):
        elements = self.tm1.dimensions.hierarchies.elements.get_elements(
            self.dimension_name,
            self.hierarchy_name)
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
            use_blob=use_blob)

        expected_columns = (
            "TM1py_unittest_element_dimension",
            "Type",
            "Attribute Next Year",
            "Attribute Previous Year",
            "level001_Weight",
            "level000_Weight",
            "level001",
            "level000",)

        self.assertEqual((2, 8), df.shape)
        self.assertEqual(expected_columns, tuple(df.columns))
        row = df.loc[df[self.dimension_name] == "1989"]
        self.assertEqual(
            ('1989', 'Numeric', '', '1988', '1.000000', '1.000000', 'Total Years', 'All Consolidations'),
            tuple(row.values[0])
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
            elements=["No Year", ],
            skip_consolidations=True,
            attributes=["Financial Year", "Previous Year"],
            skip_parents=False,
            level_names=None,
            parent_attribute=None,
            skip_weights=False,
            allow_empty_alias=False,
            use_blob=use_blob)

        expected_columns = (
            "TM1py_unittest_element_dimension",
            "Type",
            "Financial Year",
            "Previous Year",
            "level001_Weight",
            "level000_Weight",
            "level001",
            "level000",)

        self.assertEqual((1, 8), df.shape)
        self.assertEqual(expected_columns, tuple(df.columns))

        row = df.loc[df[self.dimension_name] == "No Year"]
        self.assertEqual(
            ('No Year', 'Numeric', 'No Year', '', '1.000000', '1.000000', 'Total Years', 'All Consolidations'),
            tuple(row.values[0])
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
            elements=["No Year", ],
            skip_consolidations=True,
            attributes=["Financial Year", "Previous Year"],
            skip_parents=False,
            level_names=None,
            parent_attribute=None,
            skip_weights=False,
            allow_empty_alias=True,
            use_blob=use_blob)

        expected_columns = (
            "TM1py_unittest_element_dimension",
            "Type",
            "Financial Year",
            "Previous Year",
            "level001_Weight",
            "level000_Weight",
            "level001",
            "level000",)

        self.assertEqual((1, 8), df.shape)
        self.assertEqual(expected_columns, tuple(df.columns))

        row = df.loc[df[self.dimension_name] == "No Year"]
        self.assertEqual(
            ('No Year', 'Numeric', '', '', '1.000000', '1.000000', 'Total Years', 'All Consolidations'),
            tuple(row.values[0])
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
            use_blob=use_blob)

        expected_columns = (
            "TM1py_unittest_element_dimension",
            "Type",
            "Financial Year",
            "Previous Year",
            "level001_Weight",
            "level000_Weight",
            "level001",
            "level000",)

        self.assertEqual((2, 8), df.shape)
        self.assertEqual(expected_columns, tuple(df.columns))

        row = df.loc[df[self.dimension_name] == "No Year"]
        self.assertEqual(
            ('No Year', 'Numeric', 'No Year', '', '1.000000', '1.000000', 'Total Years', 'All Consolidations'),
            tuple(row.values[0])
        )

        row = df.loc[df[self.dimension_name] == "1990"]
        self.assertEqual(
            ('1990', 'Numeric', '1989/90', '1989', '1.000000', '1.000000', 'Total Years', 'All Consolidations'),
            tuple(row.values[0])
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
            use_blob=use_blob)

        expected_columns = (
            self.dimension_with_hierarchies_name,
            "Type",
            "level000_Weight",
            "level000",)

        self.assertEqual((1, 4), df.shape)
        self.assertEqual(expected_columns, tuple(df.columns))
        row = df.loc[df[self.dimension_with_hierarchies_name] == "Elem5"]
        self.assertEqual(
            ('Elem5', 'Numeric', '1.000000', 'Cons3'),
            tuple(row.values[0])
        )

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
            use_blob=use_blob)

        expected_columns = (
            "TM1py_unittest_element_dimension",
            "Type",
            "Next Year:s",
            "Previous Year:s",
            "level001_Weight",
            "level000_Weight",
            "level001",
            "level000",)

        self.assertEqual((2, 8), df.shape)
        self.assertEqual(expected_columns, tuple(df.columns))
        row = df.loc[df[self.dimension_name] == "1989"]
        self.assertEqual(
            ('1989', 'Numeric', '', '1988', '1.000000', '1.000000', 'Total Years', 'All Consolidations'),
            tuple(row.values[0])
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
            use_blob=use_blob)

        expected_columns = (
            "TM1py_unittest_element_dimension",
            "Type",
            "A_Next Year:s",
            "A_Previous Year:s",
            "level001_Weight",
            "level000_Weight",
            "level001",
            "level000",)

        self.assertEqual((2, 8), df.shape)
        self.assertEqual(expected_columns, tuple(df.columns))
        row = df.loc[df[self.dimension_name] == "1989"]
        self.assertEqual(
            ('1989', 'Numeric', '', '1988', '1.000000', '1.000000', 'Total Years', 'All Consolidations'),
            tuple(row.values[0])
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
            use_blob=use_blob)

        expected_columns = (
            "TM1py_unittest_element_dimension",
            "ElementType",
            "Next Year",
            "Previous Year",
            "level001_Weight",
            "level000_Weight",
            "level001",
            "level000",)

        self.assertEqual((2, 8), df.shape)
        self.assertEqual(expected_columns, tuple(df.columns))
        row = df.loc[df[self.dimension_name] == "1989"]
        self.assertEqual(
            ('1989', 'Numeric', '', '1988', '1.000000', '1.000000', 'Total Years', 'All Consolidations'),
            tuple(row.values[0])
        )

    @skip_if_no_pandas
    def test_get_elements_dataframe_element_type_column(self):
        self.run_test_get_elements_dataframe_element_type_column(False)

    @skip_if_no_pandas
    def test_get_elements_dataframe_element_type_column_use_blob(self):
        self.run_test_get_elements_dataframe_element_type_column(True)

    def test_get_element_names(self):
        element_names = self.tm1.dimensions.hierarchies.elements.get_element_names(
            self.dimension_name,
            self.hierarchy_name)
        for year in self.years:
            self.assertIn(year, element_names)

    def test_get_leaf_element_names(self):
        leaf_element_names = self.tm1.dimensions.hierarchies.elements.get_leaf_element_names(
            self.dimension_name,
            self.hierarchy_name)
        for leaf in leaf_element_names:
            self.assertIn(leaf, self.years)
        self.assertNotIn(self.extra_year, leaf_element_names)
        self.assertNotIn("Total Years", leaf_element_names)

    def test_get_consolidated_element_names(self):
        consol_element_names = self.tm1.dimensions.hierarchies.elements.get_consolidated_element_names(
            self.dimension_name,
            self.hierarchy_name)
        for consol in consol_element_names:
            self.assertNotIn(consol, self.years)
        self.assertIn("Total Years", consol_element_names)

    def test_get_numeric_element_names(self):
        numeric_element_names = self.tm1.dimensions.hierarchies.elements.get_numeric_element_names(
            self.dimension_name,
            self.hierarchy_name)
        for elem in numeric_element_names:
            self.assertIn(elem, self.years)
        self.assertNotIn(self.extra_year, numeric_element_names)
        self.assertNotIn("Total Years", numeric_element_names)

    def test_get_leaf_elements(self):
        leaf_elements = self.tm1.dimensions.hierarchies.elements.get_leaf_elements(
            self.dimension_name,
            self.hierarchy_name)
        for leaf in leaf_elements:
            self.assertIn(leaf.name, self.years)
            self.assertNotEqual(leaf.element_type, "Consolidated")
        leaf_element_names = [element.name for element in leaf_elements]
        self.assertNotIn(self.extra_year, leaf_element_names)
        self.assertNotIn("Total Year", leaf_element_names)

    def test_get_numeric_elements(self):
        numeric_elements = self.tm1.dimensions.hierarchies.elements.get_numeric_elements(
            self.dimension_name,
            self.hierarchy_name)
        for elem in numeric_elements:
            self.assertIn(elem.name, self.years)
            self.assertNotEqual(elem.element_type, "Consolidated")
        numeric_element_names = [element.name for element in numeric_elements]
        self.assertNotIn(self.extra_year, numeric_element_names)
        self.assertNotIn("Total Year", numeric_element_names)

    def test_get_consolidated_elements(self):
        consol_elements = self.tm1.dimensions.hierarchies.elements.get_consolidated_elements(
            self.dimension_name,
            self.hierarchy_name)
        for consol in consol_elements:
            self.assertNotIn(consol.name, self.years)
            self.assertNotEqual(consol.element_type, "Numeric")
        consol_element_names = [element.name for element in consol_elements]
        self.assertIn("Total Years", consol_element_names)

    def test_element_exists(self):
        for year in self.years:
            self.assertTrue(self.tm1.dimensions.hierarchies.elements.exists(
                self.dimension_name,
                self.hierarchy_name,
                year))

    def test_get_leaves_under_consolidation(self):
        leaves = self.tm1.dimensions.hierarchies.elements.get_leaves_under_consolidation(
            self.dimension_name,
            self.hierarchy_name,
            "All Consolidations")
        self.assertNotIn("Total Years", leaves)
        for year in self.years:
            self.assertIn(year, leaves)

    def test_get_edges_under_consolidation(self):
        edges = self.tm1.dimensions.hierarchies.elements.get_edges_under_consolidation(
            self.dimension_name,
            self.hierarchy_name,
            "All Consolidations")

        self.assertEqual(len(self.years) + 1, len(edges))
        self.assertEqual(1, edges["All Consolidations", "Total Years"])
        for year in self.years:
            self.assertEqual(1, edges["Total Years", year])

    def test_get_edges_under_consolidation_max_depth_1(self):
        edges = self.tm1.dimensions.hierarchies.elements.get_edges_under_consolidation(
            self.dimension_name,
            self.hierarchy_name,
            "All Consolidations",
            max_depth=1)

        self.assertEqual(1, len(edges))
        self.assertEqual(1, edges["All Consolidations", "Total Years"])

    def test_get_edges_under_consolidation_max_depth_1_with_n_components(self):
        edges = self.tm1.dimensions.hierarchies.elements.get_edges_under_consolidation(
            self.dimension_name,
            self.hierarchy_name,
            "Total Years",
            max_depth=1)

        self.assertEqual(len(self.years), len(edges))
        for year in self.years:
            self.assertEqual(1, edges["Total Years", year])

    def test_get_edges_under_consolidation_not_existing_consolidation(self):
        with self.assertRaises(TM1pyRestException) as _:
            self.tm1.dimensions.hierarchies.elements.get_edges_under_consolidation(
                self.dimension_name,
                self.hierarchy_name,
                "NotExistingConsolidation")

    def test_get_edges_under_consolidation_remove_read(self):
        edges = self.tm1.dimensions.hierarchies.elements.get_edges_under_consolidation(
            self.dimension_name,
            self.hierarchy_name,
            "All Consolidations",
            max_depth=99)
        h = self.tm1.hierarchies.get(self.dimension_name, self.hierarchy_name)
        h_original = copy.deepcopy(h)

        h.remove_all_edges()
        for edge, weight in edges.items():
            h.add_edge(edge[0], edge[1], weight=weight)

        self.assertEqual(h_original.edges, h.edges)

    def test_get_members_under_consolidation(self):
        leaves = self.tm1.dimensions.hierarchies.elements.get_members_under_consolidation(
            self.dimension_name,
            self.hierarchy_name,
            "All Consolidations",
            leaves_only=True)
        self.assertNotIn("Total Years", leaves)
        for year in self.years:
            self.assertIn(year, leaves)

        members = self.tm1.dimensions.hierarchies.elements.get_members_under_consolidation(
            self.dimension_name,
            self.hierarchy_name,
            "All Consolidations",
            leaves_only=False)
        self.assertIn("Total Years", members)
        for year in self.years:
            self.assertIn(year, members)

    def test_get_element_identifiers_with_iterable(self):
        expected_identifiers = {'1988/89', '1989/90', '1990/91', '1991/92', *self.years}
        elements = self.years
        identifiers = self.tm1.dimensions.hierarchies.elements.get_element_identifiers(
            dimension_name=self.dimension_name,
            hierarchy_name=self.hierarchy_name,
            elements=elements)
        self.assertEqual(expected_identifiers, set(identifiers))

    def test_get_element_identifiers_with_string(self):
        expected_identifiers = {'1988/89', '1989/90', '1990/91', '1991/92', *self.years}
        elements = "{" + ",".join(["[" + self.dimension_name + "].[" + year + "]" for year in self.years]) + "}"
        identifiers = self.tm1.dimensions.hierarchies.elements.get_element_identifiers(
            dimension_name=self.dimension_name,
            hierarchy_name=self.hierarchy_name,
            elements=elements)
        self.assertEqual(expected_identifiers, set(identifiers))

    def test_get_all_element_identifiers(self):
        expected_identifiers = {'1988/89', '1989/90', '1990/91', '1991/92', 'Total Years', 'All Consolidations',
                                *self.years}
        identifiers = self.tm1.dimensions.hierarchies.elements.get_all_element_identifiers(
            self.dimension_name,
            self.hierarchy_name)
        self.assertEqual(expected_identifiers, set(identifiers))

    def test_get_all_element_identifiers_no_attributes(self):
        expected_identifiers = {'Elem1', 'Elem2', 'Elem3'}
        identifiers = self.tm1.dimensions.hierarchies.elements.get_all_element_identifiers(
            self.dimension_with_hierarchies_name,
            "Hierarchy1")
        self.assertEqual(expected_identifiers, set(identifiers))

    def test_get_all_leaf_element_identifiers(self):
        expected_identifiers = {'1988/89', '1989/90', '1990/91', '1991/92', *self.years}
        identifiers = self.tm1.dimensions.hierarchies.elements.get_all_leaf_element_identifiers(
            self.dimension_name,
            self.hierarchy_name)
        self.assertEqual(expected_identifiers, set(identifiers))

    def test_get_elements_by_level(self):
        expected_elements = ['No Year', '1989', '1990', '1991', '1992']
        elements = self.tm1.dimensions.hierarchies.elements.get_elements_by_level(
            self.dimension_name, self.hierarchy_name, 0)

        self.assertEqual(elements, expected_elements)

        expected_elements = ['Total Years']
        elements = self.tm1.dimensions.hierarchies.elements.get_elements_by_level(
            self.dimension_name, self.hierarchy_name, 1)
        self.assertEqual(elements, expected_elements)

    def test_get_elements_by_wildcard(self):
        expected_elements = ['Total Years', 'No Year']
        elements = self.tm1.dimensions.hierarchies.elements.get_elements_filtered_by_wildcard(
            self.dimension_name, self.hierarchy_name, 'year')
        self.assertEqual(elements, expected_elements)

        expected_elements = ['Total Years']
        elements = self.tm1.dimensions.hierarchies.elements.get_elements_filtered_by_wildcard(
            self.dimension_name, self.hierarchy_name, 'talyear', 1)
        self.assertEqual(elements, expected_elements)

        expected_elements = ['1989', '1990', '1991', '1992']
        elements = self.tm1.dimensions.hierarchies.elements.get_elements_filtered_by_wildcard(
            self.dimension_name, self.hierarchy_name, '19', 0)
        self.assertEqual(elements, expected_elements)

        expected_elements = ['1990', '1991', '1992']
        elements = self.tm1.dimensions.hierarchies.elements.get_elements_filtered_by_wildcard(
            self.dimension_name, self.hierarchy_name, '99', 0)
        self.assertEqual(elements, expected_elements)

    def test_get_number_of_elements(self):
        number_of_elements = self.tm1.dimensions.hierarchies.elements.get_number_of_elements(
            self.dimension_name, self.hierarchy_name)
        self.assertEqual(number_of_elements, 7)

    def test_get_number_of_leaf_elements(self):
        number_of_elements = self.tm1.dimensions.hierarchies.elements.get_number_of_leaf_elements(
            self.dimension_name, self.hierarchy_name)

        self.assertEqual(number_of_elements, 5)

    def test_get_number_of_consolidated_elements(self):
        number_of_elements = self.tm1.dimensions.hierarchies.elements.get_number_of_consolidated_elements(
            self.dimension_name, self.hierarchy_name)

        self.assertEqual(number_of_elements, 2)

    def test_get_number_of_numeric_elements(self):
        number_of_elements = self.tm1.dimensions.hierarchies.elements.get_number_of_numeric_elements(
            self.dimension_name, self.hierarchy_name)

        self.assertEqual(number_of_elements, 5)

    def test_string_element_functions(self):
        string_elem = 'string_element'
        element = Element(string_elem, "String")
        self.tm1.dimensions.hierarchies.elements.create(
            self.dimension_name,
            self.hierarchy_name,
            element)

        number_of_elements = self.tm1.dimensions.hierarchies.elements.get_number_of_string_elements(
            self.dimension_name, self.hierarchy_name)
        self.assertEqual(number_of_elements, 1)

        string_element_names = self.tm1.dimensions.hierarchies.elements.get_string_element_names(
            self.dimension_name,
            self.hierarchy_name)
        for elem in string_element_names:
            self.assertIn(elem, [string_elem])
        self.assertNotIn('Total Years', string_element_names)
        self.assertNotIn("1989", string_element_names)

        string_elements = self.tm1.dimensions.hierarchies.elements.get_string_elements(
            self.dimension_name,
            self.hierarchy_name)
        for elem in string_elements:
            self.assertIn(elem.name, [string_elem])
            self.assertNotEqual(elem.element_type, "Consolidated")
            self.assertNotEqual(elem.element_type, "Numeric")
        string_element_names = [element.name for element in string_elements]
        self.assertNotIn('1989', string_element_names)
        self.assertNotIn("Total Year", string_element_names)

        self.tm1.dimensions.hierarchies.elements.delete(
            self.dimension_name,
            self.hierarchy_name,
            element.name)

    def test_create_element_attribute(self):
        element_attribute = ElementAttribute("NewAttribute", "String")
        self.tm1.dimensions.hierarchies.elements.create_element_attribute(
            self.dimension_name,
            self.dimension_name,
            element_attribute)

        element_attributes = self.tm1.dimensions.hierarchies.elements.get_element_attributes(
            self.dimension_name,
            self.dimension_name)

        self.assertIn(element_attribute, element_attributes)

    def test_delete_elements(self):
        self.assertIn(
            "1989",
            self.tm1.elements.get_element_names(self.dimension_name, self.hierarchy_name))

        self.assertIn(
            "1990",
            self.tm1.elements.get_element_names(self.dimension_name, self.hierarchy_name))

        element_names = ["1989", "1990"]
        self.tm1.elements.delete_elements(
            dimension_name=self.dimension_name,
            hierarchy_name=self.hierarchy_name,
            element_names=element_names,
            use_ti=False
        )
        self.assertNotIn(
            "1989",
            self.tm1.elements.get_element_names(self.dimension_name, self.hierarchy_name))

        self.assertNotIn(
            "1990",
            self.tm1.elements.get_element_names(self.dimension_name, self.hierarchy_name))

    def test_delete_elements_use_ti(self):
        self.assertIn(
            "1989",
            self.tm1.elements.get_element_names(self.dimension_name, self.hierarchy_name))

        self.assertIn(
            "1990",
            self.tm1.elements.get_element_names(self.dimension_name, self.hierarchy_name))

        element_names = ["1989", "1990"]
        self.tm1.elements.delete_elements(
            dimension_name=self.dimension_name,
            hierarchy_name=self.hierarchy_name,
            element_names=element_names,
            use_ti=True
        )
        self.assertNotIn(
            "1989",
            self.tm1.elements.get_element_names(self.dimension_name, self.hierarchy_name))

        self.assertNotIn(
            "1990",
            self.tm1.elements.get_element_names(self.dimension_name, self.hierarchy_name))

    def test_delete_element_attribute(self):
        element_attribute = ElementAttribute("NewAttribute", "String")
        self.tm1.dimensions.hierarchies.elements.create_element_attribute(
            self.dimension_name,
            self.dimension_name,
            element_attribute)

        self.tm1.dimensions.hierarchies.elements.delete_element_attribute(
            self.dimension_name,
            self.dimension_name,
            element_attribute.name)

        element_attributes = self.tm1.dimensions.hierarchies.elements.get_element_attributes(
            self.dimension_name,
            self.dimension_name)

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

    def test_add_element_attributes_single(self):
        element_attribute = ElementAttribute(name="Attribute1", attribute_type="String")
        self.tm1.elements.add_element_attributes(self.dimension_name, self.dimension_name, [element_attribute])

        self.assertIn(
            element_attribute,
            self.tm1.elements.get_element_attributes(self.dimension_name, self.dimension_name))

    def test_add_element_attributes_multi(self):
        element_attribute1 = ElementAttribute(name="Attribute1", attribute_type="String")
        element_attribute2 = ElementAttribute(name="Attribute2", attribute_type="String")
        self.tm1.elements.add_element_attributes(
            self.dimension_name,
            self.dimension_name,
            [element_attribute1, element_attribute2])

        self.assertIn(
            element_attribute1,
            self.tm1.elements.get_element_attributes(self.dimension_name, self.dimension_name))
        self.assertIn(
            element_attribute2,
            self.tm1.elements.get_element_attributes(self.dimension_name, self.dimension_name))

    def test_add_element_attributes_fail(self):
        with self.assertRaises(TM1pyRestException) as _:
            element_attribute = ElementAttribute(name=self.attributes[0], attribute_type="String")

            self.tm1.elements.add_element_attributes(
                self.dimension_name,
                self.dimension_name,
                [element_attribute])

    def test_execute_set_mdx(self):
        mdx = f"{{[{self.dimension_name}].[1990]}}"
        members = self.tm1.elements.execute_set_mdx(
            mdx=mdx,
            member_properties=["Name"],
            element_properties=None,
            parent_properties=None)

        self.assertEqual(members, [[{'Name': '1990'}]])

    def test_execute_set_mdx_attribute_with_space(self):
        mdx = f"{{[{self.dimension_name}].[1990]}}"
        members = self.tm1.elements.execute_set_mdx(
            mdx=mdx,
            member_properties=["Name", "Attributes/Previous Year"],
            element_properties=None,
            parent_properties=None)

        self.assertEqual(members, [[{'Name': '1990', 'Attributes': {'Previous Year': '1989'}}]])

    def test_get_element_types(self):
        element_types = self.tm1.elements.get_element_types(self.dimension_name, self.hierarchy_name)
        expected = {
            "No Year": "Numeric",
            "1989": "Numeric",
            "1990": "Numeric",
            "1991": "Numeric",
            "1992": "Numeric",
            "Total Years": "Consolidated",
            "All Consolidations": "Consolidated"
        }
        self.assertEqual(expected, element_types)

    def test_get_element_types_from_all_hierarchies_with_single_hierarchy(self):
        expected = {
            "No Year": "Numeric",
            "1989": "Numeric",
            "1990": "Numeric",
            "1991": "Numeric",
            "1992": "Numeric",
            "Total Years": "Consolidated",
            "All Consolidations": "Consolidated"
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
            "Cons3": "Consolidated"
        }
        element_types = self.tm1.elements.get_element_types_from_all_hierarchies(
            self.dimension_with_hierarchies_name)

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
            dimension_name=self.dimension_with_hierarchies_name,
            skip_consolidations=True)

        self.assertEqual(expected, element_types)

    def test_remove_edge_happy_case(self):
        self.tm1.elements.remove_edge(
            dimension_name=self.dimension_name,
            hierarchy_name=self.hierarchy_name,
            parent="Total Years",
            component="1989"
        )

        edges = self.tm1.elements.get_edges(self.dimension_name, self.dimension_name)
        self.assertNotIn(("Total Years", "1989"), edges)

    def test_remove_edge_parent_not_existing(self):
        with self.assertRaises(TM1pyRestException):
            self.tm1.elements.remove_edge(
                dimension_name=self.dimension_name,
                hierarchy_name=self.hierarchy_name,
                parent="Not Existing Consolidation",
                component="1989")

    def test_remove_edge_child_not_existing(self):
        with self.assertRaises(TM1pyRestException):
            self.tm1.elements.remove_edge(
                dimension_name=self.dimension_name,
                hierarchy_name=self.hierarchy_name,
                parent="Total Years",
                component="Not Existing Element")

    def test_get_parents_happy_case(self):
        parents = self.tm1.elements.get_parents(
            dimension_name=self.dimension_name,
            hierarchy_name=self.hierarchy_name,
            element_name="1989")

        self.assertEqual(["Total Years"], parents)

    def test_get_parents_case_and_space_insensitive(self):
        parents = self.tm1.elements.get_parents(
            dimension_name=self.dimension_name,
            hierarchy_name=self.hierarchy_name,
            element_name="TOTALYEARS")

        self.assertEqual(["All Consolidations"], parents)

    def test_get_parents_no_parents(self):
        parents = self.tm1.elements.get_parents(
            dimension_name=self.dimension_name,
            hierarchy_name=self.hierarchy_name,
            element_name="All Consolidations")

        self.assertEqual([], parents)

    def test_get_parents_not_existing(self):
        with self.assertRaises(TM1pyRestException):
            self.tm1.elements.get_parents(
                dimension_name=self.dimension_name,
                hierarchy_name=self.hierarchy_name,
                element_name="Not Existing Element")

    def test_get_parents_of_all_elements_happy_case(self):
        parents = self.tm1.elements.get_parents_of_all_elements(
            dimension_name=self.dimension_name,
            hierarchy_name=self.hierarchy_name
        )

        self.assertEqual(len(parents), 7)

    def test_element_is_parent_dim_not_exist(self):
        with self.assertRaises(TM1pyRestException):
            self.tm1.elements.element_is_parent(dimension_name=self.dimension_does_not_exist_name,
                                                hierarchy_name=self.hierarchy_name,
                                                parent_name='All Consolidations',
                                                element_name='Total Years')

    def test_element_is_parent(self):
        result = self.tm1.elements.element_is_parent(dimension_name=self.dimension_name,
                                                     hierarchy_name=self.hierarchy_name,
                                                     parent_name='All Consolidations',
                                                     element_name='Total Years')
        self.assertEqual(True, result)

    def test_element_is_not_parent(self):
        result = self.tm1.elements.element_is_parent(dimension_name=self.dimension_name,
                                                     hierarchy_name=self.hierarchy_name,
                                                     parent_name='All Consolidations',
                                                     element_name='1992')
        self.assertEqual(False, result)

    def test_element_is_ancestor(self):
        result = self.tm1.elements.element_is_ancestor(dimension_name=self.dimension_name,
                                                       hierarchy_name=self.hierarchy_name,
                                                       ancestor_name='All Consolidations',
                                                       element_name='1992')
        self.assertEqual(True, result)

    def test_element_is_ancestor_tm1drilldownmember_false(self):
        result = self.tm1.elements.element_is_ancestor(dimension_name=self.dimension_name,
                                                       hierarchy_name=self.hierarchy_name,
                                                       ancestor_name='1992',
                                                       element_name='1991',
                                                       method="TM1DrillDownMember")
        self.assertEqual(False, result)

    def test_element_is_ancestor_tm1drilldownmember_not_existing_element(self):
        result = self.tm1.elements.element_is_ancestor(dimension_name=self.dimension_name,
                                                       hierarchy_name=self.hierarchy_name,
                                                       ancestor_name='1992',
                                                       element_name='NotExisting',
                                                       method="TM1DrillDownMember")
        self.assertEqual(False, result)

    def test_element_is_ancestor_tm1drilldownmember_not_existing_dimension(self):
        with self.assertRaises(TM1pyException):
            self.tm1.elements.element_is_ancestor(dimension_name=self.dimension_does_not_exist_name,
                                                  hierarchy_name=self.hierarchy_name,
                                                  ancestor_name='All Consolidations',
                                                  element_name='1992',
                                                  method="TM1DrillDownMember")

    def test_element_is_ancestor_not_existing_hierarchy(self):
        with self.assertRaises(TM1pyException):
            self.tm1.elements.element_is_ancestor(dimension_name=self.dimension_name,
                                                  hierarchy_name=self.hierarchy_does_not_exist_name,
                                                  ancestor_name='All Consolidations',
                                                  element_name='Total Years')

    def test_element_is_ancestor_descendants_method(self):
        result = self.tm1.elements.element_is_ancestor(dimension_name=self.dimension_name,
                                                       hierarchy_name=self.hierarchy_name,
                                                       ancestor_name='All Consolidations',
                                                       element_name='1992',
                                                       method='Descendants')
        self.assertEqual(True, result)

    def test_element_is_ancestor_descendants_method_false(self):
        result = self.tm1.elements.element_is_ancestor(dimension_name=self.dimension_name,
                                                       hierarchy_name=self.hierarchy_name,
                                                       ancestor_name='1992',
                                                       element_name='1991',
                                                       method='Descendants')
        self.assertEqual(False, result)

    def test_element_is_ancestor_descendants_method_not_existing_element(self):
        result = self.tm1.elements.element_is_ancestor(dimension_name=self.dimension_name,
                                                       hierarchy_name=self.hierarchy_name,
                                                       ancestor_name='1992',
                                                       element_name='Not Existing',
                                                       method='descendants')
        self.assertEqual(False, result)

    def test_element_is_ancestor_descendants_method_not_existing_dimension(self):
        with self.assertRaises(TM1pyException):
            self.tm1.elements.element_is_ancestor(dimension_name=self.dimension_does_not_exist_name,
                                                  hierarchy_name=self.hierarchy_name,
                                                  ancestor_name='All Consolidations',
                                                  element_name='1992',
                                                  method='descendants')

    def test_element_is_ancestor_descendants_method_not_existing_hierarchy(self):
        with self.assertRaises(TM1pyException):
            self.tm1.elements.element_is_ancestor(dimension_name=self.dimension_name,
                                                  hierarchy_name=self.hierarchy_does_not_exist_name,
                                                  ancestor_name='All Consolidations',
                                                  element_name='1992',
                                                  method='descendants')

    def test_element_is_ancestor_ti_method(self):
        result = self.tm1.elements.element_is_ancestor(dimension_name=self.dimension_name,
                                                       hierarchy_name=self.hierarchy_name,
                                                       ancestor_name='All Consolidations',
                                                       element_name='1992',
                                                       method='TI')
        self.assertEqual(True, result)

    def test_element_is_ancestor_ti_method_false(self):
        result = self.tm1.elements.element_is_ancestor(dimension_name=self.dimension_name,
                                                       hierarchy_name=self.hierarchy_name,
                                                       ancestor_name='1992',
                                                       element_name='1991',
                                                       method='TI')
        self.assertEqual(False, result)

    def test_element_is_ancestor_ti_method_not_existing(self):
        result = self.tm1.elements.element_is_ancestor(dimension_name=self.dimension_name,
                                                       hierarchy_name=self.hierarchy_name,
                                                       ancestor_name='1992',
                                                       element_name='Not Existing',
                                                       method='TI')
        self.assertEqual(False, result)

    def test_element_is_ancestor_ti_method_not_existing_dimension(self):
        with self.assertRaises(TM1pyException):
            self.tm1.elements.element_is_ancestor(dimension_name=self.dimension_does_not_exist_name,
                                                  hierarchy_name=self.hierarchy_name,
                                                  ancestor_name='All Consolidations',
                                                  element_name='1992',
                                                  method='TI')

    def test_element_is_ancestor_ti_method_not_existing_hierarchy(self):
        with self.assertRaises(TM1pyException):
            self.tm1.elements.element_is_ancestor(dimension_name=self.dimension_name,
                                                  hierarchy_name=self.hierarchy_does_not_exist_name,
                                                  ancestor_name='All Consolidations',
                                                  element_name='1992',
                                                  method='TI')

    @classmethod
    def tearDownClass(cls):
        cls.tm1.logout()


if __name__ == '__main__':
    unittest.main()
