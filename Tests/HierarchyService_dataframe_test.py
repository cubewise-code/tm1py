import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

from TM1py.Exceptions.Exceptions import TM1pyNotDataAdminException
from TM1py.Objects import Element, Hierarchy
from TM1py.Services.HierarchyService import HierarchyService
from TM1py.Utils.Utils import CaseAndSpaceInsensitiveSet


class TestHierarchyServiceDataFrame(unittest.TestCase):
    """DataFrame functions of the HierarchyService against a mocked TM1 server

    Total (2) -> Food (1) -> SKU1, SKU2, SKU3 and Total -> Promo (1) -> SKU1 (alternate rollup),
    with SKU3 also sitting directly under Total
    """

    dimension_name = "Product"
    edges = {
        ("Total", "Food"): 1,
        ("Total", "Promo"): 1,
        ("Total", "SKU3"): 1,
        ("Food", "SKU1"): 1,
        ("Food", "SKU2"): 2,
        ("Food", "SKU3"): 1,
        ("Promo", "SKU1"): 1,
    }

    @staticmethod
    def build_service(is_admin: bool) -> HierarchyService:
        service = HierarchyService.__new__(HierarchyService)
        service._rest = MagicMock()
        service._rest.version = "11.8.01900.10"
        service._rest.is_admin = is_admin
        service._rest.is_data_admin = is_admin
        service._rest.is_ops_admin = is_admin
        service.elements = MagicMock()
        return service

    def build_hierarchy(self) -> Hierarchy:
        elements = [Element(name, "Consolidated") for name in ("Total", "Food", "Promo")]
        elements += [Element(name, "Numeric") for name in ("SKU1", "SKU2", "SKU3")]
        return Hierarchy(self.dimension_name, self.dimension_name, elements=elements, edges=self.edges)

    def build_elements_dataframe(self) -> pd.DataFrame:
        """the hierarchy as `ElementService.get_elements_dataframe` returns it: one row per path"""
        columns = [self.dimension_name, "ElementType", "level001_Weight", "level000_Weight", "level001", "level000"]
        rows = [
            ("Total", "Consolidated", "0.000000", "0.000000", "", ""),
            ("Food", "Consolidated", "0.000000", "1.000000", "", "Total"),
            ("SKU1", "Numeric", "1.000000", "1.000000", "Food", "Total"),
            ("SKU2", "Numeric", "2.000000", "1.000000", "Food", "Total"),
            ("SKU3", "Numeric", "1.000000", "1.000000", "Food", "Total"),
            ("Promo", "Consolidated", "0.000000", "1.000000", "", "Total"),
            ("SKU1", "Numeric", "1.000000", "1.000000", "Promo", "Total"),
            ("SKU3", "Numeric", "0.000000", "1.000000", "", "Total"),
        ]
        return pd.DataFrame(rows, columns=columns)

    def mock_server_hierarchy(self, service: HierarchyService):
        service.elements.get_elements_dataframe.return_value = self.build_elements_dataframe()
        service.elements.get_level_names.return_value = ["level002", "level001", "level000"]
        service.elements.get_element_attributes.return_value = []
        service.elements.get_all_element_identifiers.return_value = CaseAndSpaceInsensitiveSet(
            ["Total", "Food", "Promo", "SKU1", "SKU2", "SKU3"]
        )
        service.elements.get_edges.return_value = dict(self.edges)

    def test_get_hierarchy_dataframe_as_non_admin(self):
        service = self.build_service(is_admin=False)
        self.mock_server_hierarchy(service)

        df = service.get_hierarchy_dataframe(self.dimension_name, self.dimension_name)

        self.assertEqual(8, len(df))

    def test_update_or_create_hierarchy_from_dataframe_as_non_admin_is_rejected_before_any_change(self):
        service = self.build_service(is_admin=False)
        self.mock_server_hierarchy(service)

        with patch.object(service, "exists", return_value=True):
            with self.assertRaises(TM1pyNotDataAdminException):
                service.update_or_create_hierarchy_from_dataframe(
                    self.dimension_name, self.dimension_name, self.build_elements_dataframe()
                )

        service.elements.add_elements.assert_not_called()
        service.elements.add_edges.assert_not_called()

    def test_update_or_create_hierarchy_from_dataframe_keeps_unchanged_edges(self):
        # weights in the DataFrame are strings ('1.000000'), weights in TM1 are numbers
        service = self.build_service(is_admin=True)
        self.mock_server_hierarchy(service)

        with patch.object(service, "exists", return_value=True):
            service.update_or_create_hierarchy_from_dataframe(
                self.dimension_name, self.dimension_name, self.build_elements_dataframe()
            )

        service.elements.delete_edges.assert_not_called()
        service.elements.add_edges.assert_not_called()

    def test_get_hierarchy_dataframe_leaf_level(self):
        service = self.build_service(is_admin=True)
        self.mock_server_hierarchy(service)

        with patch.object(service, "get", return_value=self.build_hierarchy()):
            with self.assertWarns(UserWarning):
                df = service.get_hierarchy_dataframe(self.dimension_name, self.dimension_name, leaf_level=1)

        # SKU1 and SKU2 are cut. SKU3 survives through its direct edge to Total, not through Food
        expected = pd.DataFrame(
            [
                ("Total", "Consolidated", "0.000000", ""),
                ("Food", "Numeric", "1.000000", "Total"),
                ("Promo", "Numeric", "1.000000", "Total"),
                ("SKU3", "Numeric", "1.000000", "Total"),
            ],
            columns=[self.dimension_name, "ElementType", "level000_Weight", "level000"],
        )
        pd.testing.assert_frame_equal(expected, df)

    def test_get_hierarchy_dataframe_invalid_leaf_level_fails_before_retrieving_elements(self):
        service = self.build_service(is_admin=True)
        self.mock_server_hierarchy(service)

        with patch.object(service, "get", return_value=self.build_hierarchy()):
            with self.assertRaises(ValueError):
                service.get_hierarchy_dataframe(self.dimension_name, self.dimension_name, leaf_level=3)

        service.elements.get_elements_dataframe.assert_not_called()


if __name__ == "__main__":
    unittest.main()
