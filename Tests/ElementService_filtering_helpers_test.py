import unittest
from unittest.mock import MagicMock, patch

from TM1py.Objects import Element
from TM1py.Services.ElementService import (
    ElementService,
    _build_elements_filter,
    _coerce_element_types,
    _odata_str_literal,
)


class TestCoerceElementTypes(unittest.TestCase):
    def test_none_returns_empty_list(self):
        self.assertEqual(_coerce_element_types(None), [])

    def test_enum_numeric(self):
        self.assertEqual(_coerce_element_types(Element.Types.NUMERIC), [1])

    def test_enum_string(self):
        self.assertEqual(_coerce_element_types(Element.Types.STRING), [2])

    def test_enum_consolidated(self):
        self.assertEqual(_coerce_element_types(Element.Types.CONSOLIDATED), [3])

    def test_str_lowercase(self):
        self.assertEqual(_coerce_element_types("numeric"), [1])

    def test_str_mixed_case(self):
        self.assertEqual(_coerce_element_types("Numeric"), [1])

    def test_str_uppercase(self):
        self.assertEqual(_coerce_element_types("NUMERIC"), [1])

    def test_str_string(self):
        self.assertEqual(_coerce_element_types("string"), [2])

    def test_str_consolidated(self):
        self.assertEqual(_coerce_element_types("consolidated"), [3])

    def test_int_codes(self):
        self.assertEqual(_coerce_element_types(1), [1])
        self.assertEqual(_coerce_element_types(2), [2])
        self.assertEqual(_coerce_element_types(3), [3])

    def test_list_of_ints(self):
        self.assertEqual(_coerce_element_types([1, 3]), [1, 3])

    def test_list_mixed_input_shapes(self):
        self.assertEqual(
            _coerce_element_types([1, "string", Element.Types.CONSOLIDATED]),
            [1, 2, 3],
        )

    def test_list_dedupes_preserving_order(self):
        self.assertEqual(_coerce_element_types([3, 1, 1, "consolidated", "Numeric"]), [3, 1])

    def test_tuple_works(self):
        self.assertEqual(_coerce_element_types((1, 2)), [1, 2])

    def test_invalid_string_raises(self):
        with self.assertRaisesRegex(ValueError, "Invalid element_type 'bogus'"):
            _coerce_element_types("bogus")

    def test_invalid_int_too_low_raises(self):
        with self.assertRaisesRegex(ValueError, "Invalid element_type 0"):
            _coerce_element_types(0)

    def test_invalid_int_too_high_raises(self):
        with self.assertRaisesRegex(ValueError, "Invalid element_type 4"):
            _coerce_element_types(4)

    def test_empty_list_raises(self):
        with self.assertRaisesRegex(ValueError, "cannot be empty"):
            _coerce_element_types([])

    def test_list_with_invalid_entry_raises(self):
        with self.assertRaisesRegex(ValueError, "Invalid element_type 'bogus'"):
            _coerce_element_types([1, "bogus"])

    def test_bool_not_treated_as_int(self):
        # True/False are technically ints in Python but should not coerce to type 1
        with self.assertRaisesRegex(ValueError, "Invalid element_type"):
            _coerce_element_types(True)


class TestBuildElementsFilter(unittest.TestCase):
    NAME_EXPR = "tolower(replace(Name,' ',''))"

    # --- empty / no-op ---
    def test_all_none_returns_empty(self):
        self.assertEqual(_build_elements_filter(None, None, None), "")

    # --- type only ---
    def test_type_single(self):
        self.assertEqual(_build_elements_filter(1, None, None), "Type eq 1")

    def test_type_list_two(self):
        self.assertEqual(_build_elements_filter([1, 3], None, None), "(Type eq 1 or Type eq 3)")

    def test_type_list_three(self):
        self.assertEqual(
            _build_elements_filter([1, 2, 3], None, None),
            "(Type eq 1 or Type eq 2 or Type eq 3)",
        )

    def test_type_via_enum(self):
        self.assertEqual(_build_elements_filter(Element.Types.NUMERIC, None, None), "Type eq 1")

    def test_type_via_string(self):
        self.assertEqual(_build_elements_filter("Consolidated", None, None), "Type eq 3")

    # --- pattern only ---
    def test_pattern_exact(self):
        self.assertEqual(
            _build_elements_filter(None, "Region", None),
            f"{self.NAME_EXPR} eq 'region'",
        )

    def test_pattern_startswith(self):
        self.assertEqual(
            _build_elements_filter(None, "Region*", None),
            f"startswith({self.NAME_EXPR},'region')",
        )

    def test_pattern_endswith(self):
        self.assertEqual(
            _build_elements_filter(None, "*Region", None),
            f"endswith({self.NAME_EXPR},'region')",
        )

    def test_pattern_contains(self):
        self.assertEqual(
            _build_elements_filter(None, "*Region*", None),
            f"contains({self.NAME_EXPR},'region')",
        )

    def test_pattern_strips_spaces_in_literal(self):
        self.assertEqual(
            _build_elements_filter(None, "Region 1", None),
            f"{self.NAME_EXPR} eq 'region1'",
        )

    def test_pattern_lowercases_literal(self):
        self.assertEqual(
            _build_elements_filter(None, "REGION*", None),
            f"startswith({self.NAME_EXPR},'region')",
        )

    def test_pattern_multi_contains_bare(self):
        # *foo*bar* -> contains(foo) and contains(bar)
        self.assertEqual(
            _build_elements_filter(None, "*foo*bar*", None),
            f"contains({self.NAME_EXPR},'foo') and contains({self.NAME_EXPR},'bar')",
        )

    def test_pattern_startswith_with_middle_contains(self):
        # foo*mid*bar* -> startswith(foo) and contains(mid) and contains(bar)
        self.assertEqual(
            _build_elements_filter(None, "foo*mid*bar*", None),
            f"startswith({self.NAME_EXPR},'foo') and contains({self.NAME_EXPR},'mid') and contains({self.NAME_EXPR},'bar')",
        )

    def test_pattern_endswith_with_middle_contains(self):
        # *foo*mid*bar -> contains(foo) and contains(mid) and endswith(bar)
        self.assertEqual(
            _build_elements_filter(None, "*foo*mid*bar", None),
            f"contains({self.NAME_EXPR},'foo') and contains({self.NAME_EXPR},'mid') and endswith({self.NAME_EXPR},'bar')",
        )

    def test_pattern_startswith_endswith(self):
        # foo*bar -> startswith(foo) and endswith(bar)
        self.assertEqual(
            _build_elements_filter(None, "foo*bar", None),
            f"startswith({self.NAME_EXPR},'foo') and endswith({self.NAME_EXPR},'bar')",
        )

    def test_pattern_quote_escaping(self):
        self.assertEqual(
            _build_elements_filter(None, "*O'Brien*", None),
            f"contains({self.NAME_EXPR},'o''brien')",
        )

    def test_pattern_only_asterisks_matches_all(self):
        # '*' alone matches everything; emit a tautology
        result = _build_elements_filter(None, "*", None)
        self.assertEqual(result, f"{self.NAME_EXPR} eq {self.NAME_EXPR}")

    # --- level only ---
    def test_level_zero(self):
        self.assertEqual(_build_elements_filter(None, None, 0), "Level eq 0")

    def test_level_nonzero(self):
        self.assertEqual(_build_elements_filter(None, None, 2), "Level eq 2")

    # --- composed ---
    def test_all_three_composed(self):
        self.assertEqual(
            _build_elements_filter(1, "*foo*", 0),
            f"Type eq 1 and contains({self.NAME_EXPR},'foo') and Level eq 0",
        )

    def test_type_list_with_pattern_and_level(self):
        self.assertEqual(
            _build_elements_filter([1, 3], "Region*", 1),
            f"(Type eq 1 or Type eq 3) and startswith({self.NAME_EXPR},'region') and Level eq 1",
        )

    # --- validation errors ---
    def test_pattern_question_mark_raises(self):
        with self.assertRaisesRegex(ValueError, r"'\?' wildcard not supported"):
            _build_elements_filter(None, "foo?", None)

    def test_pattern_empty_raises(self):
        with self.assertRaisesRegex(ValueError, "cannot be empty"):
            _build_elements_filter(None, "", None)

    def test_pattern_non_string_raises(self):
        with self.assertRaisesRegex(TypeError, "name_pattern must be str"):
            _build_elements_filter(None, 123, None)

    def test_level_negative_raises(self):
        with self.assertRaisesRegex(ValueError, "must be >= 0"):
            _build_elements_filter(None, None, -1)

    def test_level_non_int_raises(self):
        with self.assertRaisesRegex(TypeError, "level must be int"):
            _build_elements_filter(None, None, "0")

    def test_level_bool_raises(self):
        # bool is a subclass of int in Python; reject anyway since it's meaningless here
        with self.assertRaisesRegex(TypeError, "level must be int"):
            _build_elements_filter(None, None, True)


class TestOdataStrLiteralUrlSafety(unittest.TestCase):
    """The filter clause is concatenated raw into the URL query string
    (url += '&$filter=' + clause), so any string literal inside it must
    percent-encode URL-reserved characters (&, %, #, ?) — not just escape
    OData single quotes. Otherwise an element name like 'Sales & Marketing'
    would prematurely terminate $filter and corrupt the query."""

    NAME_EXPR = "tolower(replace(Name,' ',''))"

    def test_literal_url_escapes_ampersand(self):
        self.assertEqual(_odata_str_literal("a&b"), "'a%26b'")

    def test_literal_url_escapes_percent(self):
        self.assertEqual(_odata_str_literal("a%b"), "'a%25b'")

    def test_literal_url_escapes_hash(self):
        self.assertEqual(_odata_str_literal("a#b"), "'a%23b'")

    def test_literal_url_escapes_question_mark(self):
        self.assertEqual(_odata_str_literal("a?b"), "'a%3Fb'")

    def test_literal_still_escapes_single_quote(self):
        # OData spec requires doubling embedded single quotes; the URL fix
        # must not regress this.
        self.assertEqual(_odata_str_literal("O'Brien"), "'O''Brien'")

    def test_pattern_with_ampersand_produces_url_safe_filter(self):
        # The bug: 'Sales & Marketing' would emit a raw '&' that splits the
        # query string at &$filter= and creates a phantom '$filter' param.
        result = _build_elements_filter(None, "*Sales & Marketing*", None)
        self.assertNotIn("&", result)
        self.assertIn("%26", result)
        self.assertEqual(result, f"contains({self.NAME_EXPR},'sales%26marketing')")


class TestGetElementsDataFrameForwardsKwargs(unittest.TestCase):
    """Regression: in the trio-filter branch of get_elements_dataframe, the
    internal call to get_element_names previously dropped **kwargs, silently
    discarding request-level options (timeout, cancel_at_timeout,
    async_requests_mode) that the rest of the method forwards consistently."""

    def test_trio_path_forwards_kwargs_to_get_element_names(self):
        service = ElementService.__new__(ElementService)
        service._rest = MagicMock()

        sentinel = RuntimeError("__stop__")
        recorded = {}

        def fake_get_element_names(*args, **kwargs):
            recorded["kwargs"] = kwargs
            raise sentinel

        with patch.object(service, "get_element_names", side_effect=fake_get_element_names):
            with self.assertRaises(RuntimeError) as ctx:
                service.get_elements_dataframe(
                    dimension_name="d",
                    hierarchy_name="h",
                    name_pattern="foo*",
                    timeout=42,
                    cancel_at_timeout=True,
                    async_requests_mode=True,
                )
            self.assertIs(ctx.exception, sentinel)

        self.assertEqual(recorded["kwargs"].get("timeout"), 42)
        self.assertEqual(recorded["kwargs"].get("cancel_at_timeout"), True)
        self.assertEqual(recorded["kwargs"].get("async_requests_mode"), True)


if __name__ == "__main__":
    unittest.main()
