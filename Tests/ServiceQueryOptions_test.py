"""Dedicated filter / top / order_by arguments on list methods of the services. No TM1 server required."""

import unittest
from unittest.mock import MagicMock
from urllib.parse import unquote

from TM1py.Services.ChoreService import ChoreService
from TM1py.Services.CubeService import CubeService
from TM1py.Services.DimensionService import DimensionService
from TM1py.Services.ElementService import ElementService
from TM1py.Services.HierarchyService import HierarchyService
from TM1py.Services.ProcessService import ProcessService
from TM1py.Services.SecurityService import SecurityService
from TM1py.Services.SubsetService import SubsetService
from TM1py.Services.ViewService import ViewService

PROCESS = {
    "Name": "p",
    "HasSecurityAccess": False,
    "PrologProcedure": "",
    "MetadataProcedure": "",
    "DataProcedure": "",
    "EpilogProcedure": "",
    "DataSource": {"Type": "None"},
    "Parameters": [],
    "Variables": [],
    "UIData": "",
    "VariablesUIData": [],
}
ELEMENT = {"Name": "e", "Type": "Numeric", "UniqueName": "[d].[e]", "Index": 1, "Attributes": {}}

# (service class, method name, positional args, internal $filter, response entity)
CASES = [
    (CubeService, "get_all_names", (), None, {"Name": "e"}),
    (CubeService, "get_all_names_with_rules", (), "Rules ne null", {"Name": "e"}),
    (CubeService, "get_all_names_without_rules", (), "Rules eq null", {"Name": "e"}),
    (DimensionService, "get_all_names", (), None, {"Name": "e"}),
    (HierarchyService, "get_all_names", ("d",), None, {"Name": "e"}),
    (ProcessService, "get_all", (), None, PROCESS),
    (ProcessService, "get_all_names", (), None, {"Name": "e"}),
    (ElementService, "get_elements", ("d", "h"), None, ELEMENT),
    (ElementService, "get_element_names", ("d", "h"), None, {"Name": "e"}),
    (ElementService, "get_leaf_elements", ("d", "h"), "Type ne 3", ELEMENT),
    (ElementService, "get_leaf_element_names", ("d", "h"), "Type ne 3", {"Name": "e"}),
    (ElementService, "get_consolidated_elements", ("d", "h"), "Type eq 3", ELEMENT),
    (ElementService, "get_consolidated_element_names", ("d", "h"), "Type eq 3", {"Name": "e"}),
    (ChoreService, "get_all_names", (), None, {"Name": "e"}),
    (SubsetService, "get_all_names", ("d",), None, {"Name": "e"}),
    (ViewService, "get_all_names", ("c",), None, {"Name": "e"}),
    (SecurityService, "get_all_user_names", (), None, {"Name": "e"}),
    (SecurityService, "get_all_groups", (), None, {"Name": "e"}),
]


def _query_options(url):
    query = url.partition("?")[2]
    return dict((unquote(name), unquote(value)) for name, _, value in (o.partition("=") for o in query.split("&")))


class TestServiceQueryOptions(unittest.TestCase):
    def _service(self, service_class, entity):
        service = object.__new__(service_class)
        service._rest = MagicMock()
        service._rest.GET.return_value.json.return_value = {"value": [entity]}
        return service

    def _urls(self, service):
        return [
            call.kwargs.get("url", call.args[0] if call.args else None) for call in service._rest.GET.call_args_list
        ]

    def test_options_are_added_to_each_get(self):
        for service_class, method, args, internal_filter, entity in CASES:
            with self.subTest(method=f"{service_class.__name__}.{method}"):
                service = self._service(service_class, entity)
                result = getattr(service, method)(*args, filter="Name ne 'x'", top=3, order_by="Name desc")
                self.assertTrue(result)

                urls = self._urls(service)
                self.assertTrue(urls)
                for url in urls:
                    options = _query_options(url)
                    expected_filter = f"({internal_filter}) and (Name ne 'x')" if internal_filter else "Name ne 'x'"
                    self.assertEqual(options["$filter"], expected_filter)
                    self.assertEqual(options["$top"], "3")
                    self.assertEqual(options["$orderby"], "Name desc")

    def test_without_options_url_is_unchanged(self):
        for service_class, method, args, _, entity in CASES:
            with self.subTest(method=f"{service_class.__name__}.{method}"):
                service = self._service(service_class, entity)
                getattr(service, method)(*args)
                for url in self._urls(service):
                    self.assertNotIn("$top", url)
                    self.assertNotIn("$orderby", url)

    def test_other_kwargs_are_still_forwarded(self):
        for service_class, method, args, _, entity in CASES:
            with self.subTest(method=f"{service_class.__name__}.{method}"):
                service = self._service(service_class, entity)
                getattr(service, method)(*args, top=1, timeout=7)
                for call in service._rest.GET.call_args_list:
                    self.assertEqual(call.kwargs["timeout"], 7)

    def test_options_are_keyword_only(self):
        service = self._service(CubeService, {"Name": "e"})
        with self.assertRaises(TypeError):
            service.get_all_names(False, "Name eq 'a'")

    def test_combined_with_skip_control_objects(self):
        service = self._service(ProcessService, {"Name": "e"})
        service.get_all_names(skip_control_processes=True, filter="startswith(Name,'Load')")
        options = _query_options(self._urls(service)[0])
        self.assertEqual(
            options["$filter"],
            "(startswith(Name,'}') eq false and startswith(Name,'{') eq false) and (startswith(Name,'Load'))",
        )

    def test_combined_with_element_filter_arguments(self):
        service = self._service(ElementService, {"Name": "e"})
        service.get_element_names("d", "h", element_type="consolidated", filter="Level gt 1")
        options = _query_options(self._urls(service)[0])
        self.assertTrue(options["$filter"].endswith(") and (Level gt 1)"))
        self.assertIn("Type eq 3", options["$filter"])

    def test_view_names_split_into_private_and_public(self):
        service = self._service(ViewService, {"Name": "v"})
        private_views, public_views = service.get_all_names("c", top=1)
        self.assertEqual((private_views, public_views), (["v"], ["v"]))
        urls = self._urls(service)
        self.assertIn("/PrivateViews?", urls[0])
        self.assertIn("/Views?", urls[1])


if __name__ == "__main__":
    unittest.main()
