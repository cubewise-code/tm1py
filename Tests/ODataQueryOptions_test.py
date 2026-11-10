import unittest

from TM1py.Utils import add_odata_query_options


class TestAddODataQueryOptions(unittest.TestCase):
    def test_no_options_returns_url_unchanged(self):
        for url in ("/Cubes", "/Cubes?$select=Name", "/Cubes?$select=Name&$filter=Rules ne null"):
            with self.subTest(url=url):
                self.assertEqual(add_odata_query_options(url), url)
                self.assertEqual(add_odata_query_options(url, filter="", order_by=""), url)

    def test_append_to_url_without_query(self):
        self.assertEqual(add_odata_query_options("/Cubes", top=5), "/Cubes?$top=5")

    def test_append_to_url_with_query(self):
        self.assertEqual(
            add_odata_query_options("/Cubes?$select=Name", filter="Name eq 'Sales'", top=10, order_by="Name desc"),
            "/Cubes?$select=Name&$filter=Name%20eq%20'Sales'&$top=10&$orderby=Name%20desc",
        )

    def test_filter_is_combined_with_existing_filter(self):
        self.assertEqual(
            add_odata_query_options("/Cubes?$select=Name&$filter=Rules ne null", filter="startswith(Name,'S')"),
            "/Cubes?$select=Name&$filter=(Rules ne null) and (startswith(Name,'S'))",
        )

    def test_or_in_user_filter_cannot_widen_existing_filter(self):
        url = add_odata_query_options("/Processes?$filter=Type eq 1", filter="Name eq 'a' or Name eq 'b'")
        self.assertEqual(url, "/Processes?$filter=(Type eq 1) and (Name%20eq%20'a'%20or%20Name%20eq%20'b')")

    def test_existing_filter_with_encoded_name_is_combined(self):
        url = add_odata_query_options("/Cubes?%24filter=Rules ne null", filter="Name eq 'X'")
        self.assertEqual(url, "/Cubes?%24filter=(Rules ne null) and (Name%20eq%20'X')")

    def test_nested_expand_options_are_not_touched(self):
        url = "/Dimensions?$expand=Hierarchies($select=Name;$filter=Name ne 'Leaves';$top=1)"
        self.assertEqual(
            add_odata_query_options(url, filter="Name eq 'Region'", top=2, order_by="Name"),
            url + "&$filter=Name%20eq%20'Region'&$top=2&$orderby=Name",
        )

    def test_reserved_characters_in_values_are_encoded(self):
        url = add_odata_query_options("/Cubes", filter="Name eq 'A&B#C+D%E=F'", order_by="Name")
        self.assertEqual(url, "/Cubes?$filter=Name%20eq%20'A%26B%23C%2BD%25E%3DF'&$orderby=Name")

    def test_top_zero_is_retained(self):
        self.assertEqual(add_odata_query_options("/Cubes", top=0), "/Cubes?$top=0")

    def test_invalid_top(self):
        for top, error in ((True, TypeError), ("10", TypeError), (1.5, TypeError), (-1, ValueError)):
            with self.subTest(top=top):
                with self.assertRaises(error):
                    add_odata_query_options("/Cubes", top=top)

    def test_invalid_filter_and_order_by_types(self):
        with self.assertRaises(TypeError):
            add_odata_query_options("/Cubes", filter=["Name eq 'a'"])
        with self.assertRaises(TypeError):
            add_odata_query_options("/Cubes", order_by=["Name"])

    def test_duplicate_top_or_orderby_raises(self):
        with self.assertRaisesRegex(ValueError, r"\$top"):
            add_odata_query_options("/Cubes?$top=0", top=5)
        with self.assertRaisesRegex(ValueError, r"\$orderby"):
            add_odata_query_options("/Cubes?$orderby=Name", order_by="Name desc")

    def test_existing_top_is_kept_when_not_requested(self):
        self.assertEqual(
            add_odata_query_options("/Cubes?$top=0&$count", filter="Name eq 'a'"),
            "/Cubes?$top=0&$count&$filter=Name%20eq%20'a'",
        )


if __name__ == "__main__":
    unittest.main()
