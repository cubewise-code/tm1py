import unittest

from TM1py import MDXView
from unittest.mock import Mock, patch 
from TM1py import ViewService
import json 


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
    
    rest_response = '''{"@odata.context":"../$metadata#Cubes(\'Cube\')/Views/ibm.tm1.api.v1.MDXView(Cube,LocalizedAttributes)/$entity","@odata.type":"#ibm.tm1.api.v1.MDXView","Name":"MDX View","Attributes":{"Caption":"MDX View"},"MDX":"SELECT {[Dim B].[Dim B].Members} PROPERTIES [Dim B].[Dim B].[Description B]  ON COLUMNS , {[Dim A].[Dim A].Members} PROPERTIES [Dim A].[Dim A].[Description]  ON ROWS FROM [Cube] ","Cube":{"Name":"Cube","Rules":null,"DrillthroughRules":null,"LastSchemaUpdate":"2025-07-26T10:53:18.870Z","LastDataUpdate":"2025-07-26T10:53:18.870Z","Attributes":{"Caption":"Cube"}},"LocalizedAttributes":[],"FormatString":"0.#########"\n,"Meta":{"Aliases":{"[Dim A].[Dim A]":"Description","[Dim B].[Dim B]":"Description B"},"ContextSets":{},"ExpandAboves":{}}\n}'''

    def setUp(self) -> None:
        self.view = MDXView(
            cube_name=self.cube_name,
            view_name=self.view_name,
            MDX=self.mdx)

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

    @patch('TM1py.Services.RestService.RestService')
    def test_get_with_retrieving_meta_from_response(self, mock_rest):
        mock_response_dict = json.loads(self.rest_response)
        mock_response = Mock()
        mock_response.json.return_value = mock_response_dict
        mock_rest.GET.return_value = mock_response
        
        service = ViewService(mock_rest)
        view = service.get('Cube', 'MDX View', private=False)
        self.assertIsInstance(view, MDXView)
        self.assertDictEqual(view.aliases, {"Dim A": "Description", "Dim B": "Description B"})
    
    def test_from_json_with_Meta_key(self):
        view = MDXView.from_json(view_as_json=self.rest_response, cube_name='Cube')
        self.assertIsInstance(view, MDXView)
        self.assertDictEqual(view.aliases, {"Dim A": "Description", "Dim B": "Description B"})
