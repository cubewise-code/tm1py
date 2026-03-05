import json
import unittest
import warnings

from TM1py import MDXView


class TestMDXView(unittest.TestCase):
    cube_name = "c1"
    view_name = "v1"
    mdx = """
    SELECT
    {[d1].[e1], [d1].[e2], [d1].[e3]} ON ROWS,
    {Tm1SubsetAll([d2])} ON COLUMNS
    FROM [c1]
    WHERE ([d3].[d3].[e1], [d4].[e1], [d5].[h1].[e1])
    """

    def setUp(self) -> None:
        self.view = MDXView(cube_name=self.cube_name, view_name=self.view_name, MDX=self.mdx)

    def test_substitute_title(self):
        self.view.substitute_title(dimension="d3", hierarchy="d3", element="e2")
        expected_mdx = """
    SELECT
    {[d1].[e1], [d1].[e2], [d1].[e3]} ON ROWS,
    {Tm1SubsetAll([d2])} ON COLUMNS
    FROM [c1]
    WHERE ([d3].[d3].[e2], [d4].[e1], [d5].[h1].[e1])
    """
        self.assertEqual(expected_mdx, self.view.mdx)

    def test_substitute_title_different_case(self):
        self.view.substitute_title(dimension="D3", hierarchy="D3", element="e2")
        expected_mdx = """
    SELECT
    {[d1].[e1], [d1].[e2], [d1].[e3]} ON ROWS,
    {Tm1SubsetAll([d2])} ON COLUMNS
    FROM [c1]
    WHERE ([D3].[D3].[e2], [d4].[e1], [d5].[h1].[e1])
    """
        self.assertEqual(expected_mdx, self.view.mdx)

    def test_substitute_title_without_hierarchy(self):
        self.view.substitute_title(dimension="d4", hierarchy="d4", element="e2")
        expected_mdx = """
    SELECT
    {[d1].[e1], [d1].[e2], [d1].[e3]} ON ROWS,
    {Tm1SubsetAll([d2])} ON COLUMNS
    FROM [c1]
    WHERE ([d3].[d3].[e1], [d4].[e2], [d5].[h1].[e1])
    """
        self.assertEqual(expected_mdx, self.view.mdx)

    def test_substitute_title_with_hierarchy(self):
        self.view.substitute_title(dimension="d5", hierarchy="h1", element="e2")
        expected_mdx = """
    SELECT
    {[d1].[e1], [d1].[e2], [d1].[e3]} ON ROWS,
    {Tm1SubsetAll([d2])} ON COLUMNS
    FROM [c1]
    WHERE ([d3].[d3].[e1], [d4].[e1], [d5].[h1].[e2])
    """
        self.assertEqual(expected_mdx, self.view.mdx)

    def test_substitute_title_value_error(self):
        with self.assertRaises(ValueError) as error:
            self.view.substitute_title(dimension="d6", hierarchy="d6", element="e2")
            print(error)

    properties = {
        "Meta": {
            "Aliases": {"[d3].[d3]": "Default"},
            "ContextSets": {
                "[d3].[d3]": {"Expression": '{TM1SubsetToSet([d3].[d3],"Default","public")}'},
                "[d4].[d4]": {"IsPublic": True, "SubsetName": "Default"},
            },
            "ExpandAboves": {
                "[d1].[d1]": False,
                "[d2].[d2]": False,
                "[d3].[d3]": False,
                "[d4].[d4]": False,
                "[d5].[d5]": False,
            },
        }
    }

    def test_properties_default_is_empty_dict(self):
        self.assertEqual({}, self.view.properties)

    def test_properties_none_resets_to_empty_dict(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            self.view.properties = self.properties
        self.view.properties = None
        self.assertEqual({}, self.view.properties)

    def test_properties_setter_raises_user_warning(self):
        with self.assertWarns(UserWarning):
            self.view.properties = self.properties

    def test_properties_no_warning_when_none(self):
        with warnings.catch_warnings():
            warnings.simplefilter("error", UserWarning)
            # Should not raise when setting None
            self.view.properties = None

    def test_properties_meta_included_in_body(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            self.view.properties = self.properties
        body = json.loads(self.view.body)
        self.assertIn("Meta", body)
        self.assertEqual(self.properties["Meta"], body["Meta"])

    def test_properties_meta_aliases_in_body(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            self.view.properties = self.properties
        body = json.loads(self.view.body)
        self.assertIn("Aliases", body["Meta"])
        self.assertEqual({"[d3].[d3]": "Default"}, body["Meta"]["Aliases"])

    def test_properties_meta_context_sets_in_body(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            self.view.properties = self.properties
        body = json.loads(self.view.body)
        self.assertIn("ContextSets", body["Meta"])
        self.assertIn("[d3].[d3]", body["Meta"]["ContextSets"])
        self.assertIn("[d4].[d4]", body["Meta"]["ContextSets"])

    def test_properties_meta_expand_aboves_in_body(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            self.view.properties = self.properties
        body = json.loads(self.view.body)
        self.assertIn("ExpandAboves", body["Meta"])
        self.assertTrue(all(v is False for v in body["Meta"]["ExpandAboves"].values()))

    def test_properties_not_in_body_when_empty(self):
        body = json.loads(self.view.body)
        self.assertNotIn("Meta", body)

    def test_properties_set_via_constructor(self):
        with self.assertWarns(UserWarning):
            view = MDXView(
                cube_name=self.cube_name,
                view_name=self.view_name,
                MDX=self.mdx,
                properties=self.properties,
            )
        self.assertEqual(self.properties, view.properties)
