"""Server-free tests of the TI processes that CellService generates for blob transfers.

The processes are built through CellService's private export and load builders on a CellService wired to a
mocked REST layer, so no TM1 server is needed. The tests check the process handed to the server (its JSON body).

Legacy snapshots: ``Tests/fixtures/blob_ti_snapshots/`` holds the TI that TM1py generated before the blob TI
generator was refactored. The default (legacy) output must keep matching them exactly. To regenerate them
deliberately, run with ``TM1PY_UPDATE_BLOB_SNAPSHOTS=1``.
"""

import configparser
import csv
import io
import json
import os
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from mdxpy import MdxBuilder, MdxHierarchySet, Member

from TM1py.Exceptions import TM1pyVersionException, TM1pyWriteFailureException
from TM1py.Objects import (
    AnonymousSubset,
    Cube,
    Dimension,
    Element,
    Hierarchy,
    NativeView,
    Subset,
)
from TM1py.Services import TM1Service
from TM1py.Services.CellService import CellService
from TM1py.Services.FileService import FileService
from TM1py.Services.ProcessService import ProcessService
from TM1py.Utils.BlobProcessBuilder import CubeProfile

from .Utils import skip_if_no_pandas

SNAPSHOT_DIR = Path(__file__).parent / "fixtures" / "blob_ti_snapshots"
UPDATE_SNAPSHOTS = os.environ.get("TM1PY_UPDATE_BLOB_SNAPSHOTS") == "1"

V11 = "11.8.02300.1"
V12 = "12.5.4"


def _cell_service(version: str = V11, sandboxing_disabled: bool = False) -> CellService:
    rest = MagicMock()
    rest.version = version
    rest.sandboxing_disabled = sandboxing_disabled
    return CellService(rest)


# ---------------------------------------------------------------------------------------------------------------- #
# representative inputs for the legacy builders
# ---------------------------------------------------------------------------------------------------------------- #

EXPORT_BASE = dict(
    cube="Sales",
    variables=["v3", "v1", "v2", "v4"],
    skip_variables=[],
    top=None,
    skip=None,
    skip_zeros=True,
    skip_consolidated_cells=True,
    skip_rule_derived_cells=False,
    value_separator=",",
    process_name="tm1py.export",
    view_name="tm1py.view",
    file_name="tm1py.export.csv",
    header=None,
)

EXPORT_CASES = {
    "export_v11_default": dict(),
    "export_v12_default": dict(version=V12),
    "export_v11_all_cells": dict(skip_zeros=False, skip_consolidated_cells=False, skip_rule_derived_cells=True),
    "export_v11_header_top_skip": dict(header=["Year", "Region", "Product", "Measure"], top=100, skip=10),
    "export_v11_top_only": dict(top=5),
    "export_v11_skip_only": dict(skip=7),
    "export_v11_title_variables_separator_quote": dict(skip_variables=["v4"], value_separator=";", quote_character="'"),
    "export_v11_sandbox": dict(sandbox_name="Scenario 1"),
    "export_v11_sandboxing_disabled": dict(sandboxing_disabled=True),
    "export_v12_header_sandbox": dict(version=V12, header=["Year"], sandbox_name="Scenario 1"),
}

LOAD_BASE = dict(
    cube_name="Sales",
    process_name="tm1py.load",
    blob_filename="tm1py.load.csv",
    dimensions=["Year", "Region", "Product", "Sales Measure"],
    increment=False,
    skip_non_updateable=False,
    sandbox_name=None,
    allow_spread=False,
    clear_view=None,
)

LOAD_CASES = {
    "load_v11_default": dict(),
    "load_v12_default": dict(version=V12),
    "load_v11_increment_skip_non_updateable": dict(increment=True, skip_non_updateable=True),
    "load_v11_allow_spread": dict(allow_spread=True),
    "load_v11_allow_spread_increment": dict(allow_spread=True, increment=True),
    "load_v11_attribute_cube_increment": dict(
        cube_name="}ElementAttributes_Region", dimensions=["Region", "}ElementAttributes_Region"], increment=True
    ),
    "load_v11_sandbox_clear_view": dict(sandbox_name="Scenario 1", clear_view="tm1py.clear"),
    "load_v12_sandboxing_disabled": dict(version=V12, sandboxing_disabled=True),
}


def build_legacy_export(case: dict):
    case = dict(case)
    version = case.pop("version", V11)
    sandboxing_disabled = case.pop("sandboxing_disabled", False)
    cell_service = _cell_service(version, sandboxing_disabled)
    with patch.object(CellService, "sandbox_exists", return_value=True):
        return cell_service._build_cube_to_blob_process(**{**EXPORT_BASE, **case})


def build_legacy_load(case: dict):
    case = dict(case)
    version = case.pop("version", V11)
    sandboxing_disabled = case.pop("sandboxing_disabled", False)
    cell_service = _cell_service(version, sandboxing_disabled)
    with patch.object(CellService, "sandbox_exists", return_value=True):
        return cell_service._build_blob_to_cube_process(**{**LOAD_BASE, **case})


class TestLegacyBlobTiSnapshots(unittest.TestCase):
    """Default output of the blob builders must equal the TI TM1py generated before the refactor."""

    def _assert_matches_snapshot(self, name: str, process):
        path = SNAPSHOT_DIR / f"{name}.json"
        body = process.body_as_dict
        if UPDATE_SNAPSHOTS:
            SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(body, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        self.assertTrue(path.exists(), f"missing snapshot {path.name}; run with TM1PY_UPDATE_BLOB_SNAPSHOTS=1")
        self.assertEqual(json.loads(path.read_text(encoding="utf-8")), body)

    def test_export_snapshots(self):
        for name, case in EXPORT_CASES.items():
            with self.subTest(name):
                self._assert_matches_snapshot(name, build_legacy_export(case))

    def test_load_snapshots(self):
        for name, case in LOAD_CASES.items():
            with self.subTest(name):
                self._assert_matches_snapshot(name, build_legacy_load(case))


# ---------------------------------------------------------------------------------------------------------------- #
# lean mode
# ---------------------------------------------------------------------------------------------------------------- #

SALES_DIMENSIONS = ["Year", "Region", "Product", "Sales Measure"]


def build_lean_export(version: str = V11, string_measures=(), quoted_dimensions=(), cube="Sales", **overrides):
    cell_service = _cell_service(version)
    profile = CubeProfile(
        cube_name=cube,
        dimensions=SALES_DIMENSIONS,
        is_v12=version.startswith("12"),
        string_measures=string_measures,
        quoted_dimensions=quoted_dimensions,
    )
    # data source order (MDX view: columns, then rows) differs from the file's column order
    arguments = {
        **EXPORT_BASE,
        "cube": cube,
        "lean_ti": True,
        "profile": profile,
        "variable_hierarchies": [
            "[Sales Measure].[Sales Measure]",
            "[Year].[Year]",
            "[Region].[Region]",
            "[Product].[Product]",
        ],
        "variables": ["v4", "v1", "v2", "v3"],
        **overrides,
    }
    with patch.object(CellService, "sandbox_exists", return_value=True):
        return cell_service._build_cube_to_blob_process(**arguments)


def build_lean_load(version: str = V11, string_measures=(), **overrides):
    cell_service = _cell_service(version)
    with patch.object(CellService, "sandbox_exists", return_value=True):
        return cell_service._build_blob_to_cube_process(
            **{**LOAD_BASE, "lean_ti": True, "string_measures": string_measures, **overrides}
        )


def _variable_types(process) -> dict:
    return {variable["Name"]: variable["Type"] for variable in process.variables}


class TestLeanExportTi(unittest.TestCase):
    def test_numeric_cube_writes_without_any_escaping(self):
        process = build_lean_export()
        self.assertNotIn("SCAN", process.data_procedure)
        self.assertIn("TextOutput('tm1py.export.csv.blb',v1,v2,v3,v4,SVALUE);", process.data_procedure)

    def test_variables_keep_data_source_order(self):
        process = build_lean_export()
        self.assertEqual(["v4", "v1", "v2", "v3"], [variable["Name"] for variable in process.variables])

    def test_character_set_is_set_on_first_record(self):
        # v11 applies SetOutputCharacterSet only to the procedure it is called in
        for version, file_name in ((V11, "tm1py.export.csv.blb"), (V12, "tm1py.export.csv")):
            with self.subTest(version):
                process = build_lean_export(version)
                self.assertNotIn("SetOutputCharacterSet", process.prolog_procedure)
                self.assertIn("IF (nRecord = 0);", process.data_procedure)
                self.assertIn(f"SetOutputCharacterSet('{file_name}','TM1CS_UTF8');", process.data_procedure)

    def test_undefined_value_guard_only_on_v12(self):
        self.assertIn("ISUNDEFINEDCELLVALUE(NVALUE,'Sales')", build_lean_export(V12).data_procedure)
        self.assertNotIn("ISUNDEFINEDCELLVALUE", build_lean_export(V11).data_procedure)

    def test_escaping_only_for_dimensions_with_quotes(self):
        process = build_lean_export(quoted_dimensions=["region"])
        self.assertIn("""SCAN('"', v2)""", process.data_procedure)
        for variable in ("v1", "v3", "v4", "SVALUE"):
            self.assertNotIn(f"""SCAN('"', {variable})""", process.data_procedure)

    def test_value_escaping_only_for_string_measures_and_only_on_string_rows(self):
        self.assertNotIn("VALUE_IS_STRING", build_lean_export().data_procedure)
        process = build_lean_export(string_measures=["Comment"])
        self.assertIn("IF (VALUE_IS_STRING = 1);", process.data_procedure)
        self.assertIn("""SCAN('"', SVALUE)""", process.data_procedure)

    def test_attribute_cube_escapes_string_values(self):
        process = build_lean_export(cube="}ElementAttributes_Region")
        self.assertIn("IF (VALUE_IS_STRING = 1);", process.data_procedure)

    def test_custom_quote_character_is_escaped_as_ti_literal(self):
        process = build_lean_export(quoted_dimensions=["Year"], quote_character="'")
        self.assertIn("DatasourceAsciiQuoteCharacter='''';", process.prolog_procedure)
        self.assertIn("SCAN('''', v1)", process.data_procedure)

    def test_no_escaping_without_quote_character(self):
        process = build_lean_export(quoted_dimensions=["Year"], string_measures=["Comment"], quote_character="")
        self.assertNotIn("SCAN", process.data_procedure)

    def test_no_counters_or_header_unless_requested(self):
        process = build_lean_export()
        self.assertNotIn("nCell", process.all_procedures)
        self.assertNotIn("ProcessBreak", process.data_procedure)
        self.assertNotIn("ItemSkip", process.data_procedure)
        self.assertNotIn("'Value'", process.all_procedures)

    def test_top_and_skip(self):
        process = build_lean_export(top=100, skip=10)
        self.assertIn("nCell = 0;", process.prolog_procedure)
        self.assertIn("IF (nCell > 110);", process.data_procedure)
        self.assertIn("IF (nCell <= 10);", process.data_procedure)

    def test_top_only(self):
        process = build_lean_export(top=5)
        self.assertIn("IF (nCell > 5);", process.data_procedure)
        self.assertNotIn("ItemSkip", process.data_procedure)

    def test_header_on_first_record_with_escaped_labels(self):
        process = build_lean_export(V11, header=["Year", "O'Brien"])
        self.assertIn("TextOutput('tm1py.export.csv.blb','Year','O''Brien','Value');", process.data_procedure)

    def test_header_v12_on_first_record(self):
        # v12 overwrites a file written in the prolog when the data procedure writes to it
        process = build_lean_export(V12, header=["Year"])
        self.assertNotIn("TextOutput", process.prolog_procedure)
        self.assertIn("TextOutput('tm1py.export.csv','Year','Value');", process.data_procedure)

    def test_names_are_escaped_in_ti_literals(self):
        process = build_lean_export(cube="Bob's Cube", view_name="it's")
        self.assertIn("ViewExtractSkipZeroesSet('Bob''s Cube', 'it''s', 1);", process.prolog_procedure)

    def test_skip_flags(self):
        process = build_lean_export(skip_zeros=False, skip_consolidated_cells=False, skip_rule_derived_cells=True)
        self.assertIn("ViewExtractSkipCalcsSet('Sales', 'tm1py.view', 0);", process.prolog_procedure)
        self.assertIn("ViewExtractSkipRuleValuesSet('Sales', 'tm1py.view', 1);", process.prolog_procedure)
        self.assertIn("ViewExtractSkipZeroesSet('Sales', 'tm1py.view', 0);", process.prolog_procedure)

    def test_title_variables_are_not_written(self):
        process = build_lean_export(skip_variables=["v4"])
        self.assertIn("TextOutput('tm1py.export.csv.blb',v1,v2,v3,SVALUE);", process.data_procedure)

    def test_sandbox(self):
        process = build_lean_export(sandbox_name="Scenario 1")
        self.assertIn("ServerActiveSandboxSet('Scenario 1');SetUseActiveSandboxProperty(1);", process.prolog_procedure)

    def test_sandbox_name_is_escaped_in_ti_literal(self):
        process = build_lean_export(sandbox_name="Bob's plan")
        self.assertIn("ServerActiveSandboxSet('Bob''s plan');", process.prolog_procedure)


def _native_sales_view() -> NativeView:
    view = NativeView("Sales", "ignored")
    view.add_column("sales measure", AnonymousSubset("sales measure", elements=["Units", "Price's"]))
    view.add_row("Region", AnonymousSubset("Region", expression="{TM1SUBSETALL([Region].[Region])}"))
    view.add_title("Product", "P'1", AnonymousSubset("Product", elements=["P'1"]))
    return view


class TestLeanExportViewTi(unittest.TestCase):
    """The temporary view the lean export builds in its prolog."""

    def test_native_view_built_as_temporary_objects_before_extract_settings(self):
        process = build_lean_export(view_definition=_native_sales_view())
        prolog = process.prolog_procedure

        self.assertIn("ViewCreate('Sales', 'tm1py.view', 1);", prolog)
        self.assertLess(prolog.index("ViewCreate("), prolog.index("ViewExtractSkipCalcsSet("))
        self.assertEqual("tm1py.view", process.datasource_view)

    def test_native_view_subsets_in_cube_order(self):
        prolog = build_lean_export(view_definition=_native_sales_view()).prolog_procedure

        expected = [
            # Year is not in the view: its default member, as in MDX
            "sMdx = '{[year].[year].DEFAULTMEMBER}';",
            "SubsetCreateByMDX('tm1py_subset_1', sMdx, 'Year', 1);",
            "ViewSubsetAssign('Sales', 'tm1py.view', 'Year', 'tm1py_subset_1');",
            "sMdx = '{TM1SUBSETALL([Region].[Region])}';",
            "SubsetCreateByMDX('tm1py_subset_2', sMdx, 'Region', 1);",
            "ViewSubsetAssign('Sales', 'tm1py.view', 'Region', 'tm1py_subset_2');",
            "SubsetCreate('Product', 'tm1py_subset_3', 1);",
            "SubsetElementInsert('Product', 'tm1py_subset_3', 'P''1', 1);",
            "ViewSubsetAssign('Sales', 'tm1py.view', 'Product', 'tm1py_subset_3');",
            "SubsetCreate('Sales Measure', 'tm1py_subset_4', 1);",
            "SubsetElementInsert('Sales Measure', 'tm1py_subset_4', 'Units', 1);",
            "SubsetElementInsert('Sales Measure', 'tm1py_subset_4', 'Price''s', 2);",
            "ViewSubsetAssign('Sales', 'tm1py.view', 'Sales Measure', 'tm1py_subset_4');",
        ]
        lines = prolog.splitlines()
        positions = [lines.index(line) for line in expected]
        self.assertEqual(sorted(positions), positions)

    def test_native_view_named_subset_and_all_elements(self):
        view = NativeView("Sales", "ignored")
        view.add_row("Region", Subset("My Regions", "Region"))
        view.add_row("Year")
        prolog = build_lean_export(view_definition=view).prolog_procedure

        self.assertIn("ViewSubsetAssign('Sales', 'tm1py.view', 'Region', 'My Regions');", prolog)
        self.assertIn("sMdx = '{TM1SUBSETALL([year].[year])}';", prolog)

    def test_native_view_unknown_dimension_raises(self):
        view = NativeView("Sales", "ignored")
        view.add_row("Regoin", AnonymousSubset("Regoin", elements=["North"]))
        with self.assertRaises(ValueError):
            build_lean_export(view_definition=view)

    def test_native_view_alternate_hierarchy_raises_not_implemented(self):
        view = NativeView("Sales", "ignored")
        view.add_row("Region", AnonymousSubset("Region", "By Country", elements=["North"]))
        with self.assertRaises(NotImplementedError):
            build_lean_export(view_definition=view)

    def test_mdx_view(self):
        mdx = "SELECT {[Year].[Year].[2024]} ON 0 FROM [Sales] WHERE ([Region].[Region].[O'Brien])"
        prolog = build_lean_export(view_definition=mdx).prolog_procedure

        self.assertIn(
            "sMdx = 'SELECT {[Year].[Year].[2024]} ON 0 FROM [Sales] WHERE ([Region].[Region].[O''Brien])';", prolog
        )
        self.assertIn("ViewCreateByMDX('Sales', 'tm1py.view', sMdx, 1);", prolog)
        self.assertNotIn("ViewCreate(", prolog)

    def test_long_mdx_is_concatenated_in_pieces(self):
        mdx = "SELECT {" + ",".join(f"[Region].[Region].[R'{i}]" for i in range(2000)) + "} ON 0 FROM [Sales]"
        prolog = build_lean_export(view_definition=mdx).prolog_procedure

        pieces = [line for line in prolog.splitlines() if line.startswith("sMdx = ")]
        self.assertGreater(len(pieces), 1)
        self.assertTrue(all(len(line) < 5000 for line in pieces))
        self.assertTrue(pieces[1].startswith("sMdx = sMdx | '"))
        # the pieces, unquoted and joined, give back the MDX
        literals = [line.split(" = ", 1)[1].removeprefix("sMdx | ")[1:-2].replace("''", "'") for line in pieces]
        self.assertEqual(mdx, "".join(literals))

    def test_view_definition_requires_lean_ti(self):
        with self.assertRaises(ValueError):
            build_lean_export(view_definition="SELECT {} ON 0 FROM [Sales]", lean_ti=False)


class TestLeanLoadTi(unittest.TestCase):
    def test_numeric_cube_reads_value_as_number_and_writes_it_with_one_put(self):
        process = build_lean_load()
        self.assertEqual("Numeric", _variable_types(process)["vValue"])
        self.assertTrue(process.data_procedure.endswith("CellPutN(vValue,'Sales',v1,v2,v3,v4);\n"))
        self.assertNotIn("ElementType", process.data_procedure)

    def test_increment(self):
        process = build_lean_load(increment=True)
        self.assertIn("CellIncrementN(vValue,'Sales',v1,v2,v3,v4);", process.data_procedure)

    def test_string_measures_branch_by_element_name(self):
        process = build_lean_load(string_measures=["Comment", "Note"])
        self.assertEqual("String", _variable_types(process)["vValue"])
        self.assertIn("IF (v4 @= 'Comment' % v4 @= 'Note');", process.data_procedure)
        self.assertIn("CellPutS(vValue,'Sales',v1,v2,v3,v4);", process.data_procedure)
        self.assertIn("CellPutN(StringToNumber(vValue),'Sales',v1,v2,v3,v4);", process.data_procedure)
        self.assertNotIn("ElementType", process.data_procedure)

    def test_many_string_measures_branch_by_element_type(self):
        process = build_lean_load(string_measures=[f"Comment {i}" for i in range(50)])
        self.assertIn("IF (ElementType('Sales Measure', '', v4) @= 'S');", process.data_procedure)

    def test_attribute_cube_uses_element_type_branching_and_never_increments(self):
        process = build_lean_load(
            cube_name="}ElementAttributes_Region", dimensions=["Region", "}ElementAttributes_Region"], increment=True
        )
        self.assertEqual("String", _variable_types(process)["vValue"])
        self.assertIn("ElementType('}ElementAttributes_Region', '', v2) @= 'AS'", process.data_procedure)
        self.assertNotIn("CellIncrementN", process.data_procedure)

    def test_allow_spread_uses_element_type_branching(self):
        process = build_lean_load(allow_spread=True)
        self.assertEqual("String", _variable_types(process)["vValue"])
        self.assertIn("CellPutProportionalSpread(nValue,'Sales',v1,v2,v3,v4);", process.data_procedure)

    def test_updateable_check_only_when_requested(self):
        self.assertNotIn("CellIsUpdateable", build_lean_load().data_procedure)
        process = build_lean_load(skip_non_updateable=True)
        self.assertIn("IF (CellIsUpdateable('Sales',v1,v2,v3,v4) = 1);", process.data_procedure)
        self.assertIn("ItemSkip;", process.data_procedure)

    def test_sandbox_and_zero_out(self):
        process = build_lean_load(sandbox_name="Scenario 1", clear_view="tm1py.clear")
        self.assertIn("ServerActiveSandboxSet('Scenario 1');SetUseActiveSandboxProperty(1);", process.prolog_procedure)
        self.assertIn("ViewZeroOut('Sales', 'tm1py.clear');", process.prolog_procedure)

    def test_names_are_escaped_in_ti_literals(self):
        process = build_lean_load(cube_name="Bob's Cube", dimensions=["Bob's Dim", "Measure"], allow_spread=True)
        self.assertIn("CellPutProportionalSpread(nValue,'Bob''s Cube',v1,v2);", process.data_procedure)
        self.assertIn("ElementType('Bob''s Dim', '', v1) @= 'C'", process.data_procedure)

    def test_v12_reads_file_without_blb_extension(self):
        self.assertEqual("tm1py.load.csv", build_lean_load(V12).datasource_data_source_name_for_server)
        self.assertEqual("tm1py.load.csv.blb", build_lean_load(V11).datasource_data_source_name_for_server)

    def test_utf8_input(self):
        self.assertIn("SetInputCharacterSet('TM1CS_UTF8');", build_lean_load().prolog_procedure)


class TestViewCsvUseBlobChecksBeforeCreatingView(unittest.TestCase):
    """_execute_view_csv_use_blob copies the view as a temporary public view. Whatever can fail before the export
    runs must fail before that view exists, so nothing is left on the server."""

    ARGUMENTS = dict(
        cube_name="Sales",
        view_name="Default",
        top=None,
        skip=None,
        skip_zeros=True,
        skip_consolidated_cells=True,
        skip_rule_derived_cells=True,
        value_separator=",",
        cube_dimensions=SALES_DIMENSIONS,
        # titles, rows, columns
        arranged_axes=(
            ["[Year].[Year]", "[Product].[Product]"],
            ["[Region].[Region]"],
            ["[Sales Measure].[Sales Measure]"],
        ),
    )

    def setUp(self):
        self.cell_service = _cell_service()
        self.view_service = MagicMock()
        self.view_service.is_mdx_view.return_value = False
        self.view_service.get_native_view.return_value = _native_sales_view()
        services = (MagicMock(), MagicMock(), self.view_service)
        patcher = patch.object(CellService, "_prepare_blob_services", return_value=services)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_unknown_sandbox_raises_before_the_view_is_created(self):
        with patch.object(CellService, "sandbox_exists", return_value=False):
            with self.assertRaises(ValueError):
                self.cell_service._execute_view_csv_use_blob(**self.ARGUMENTS, sandbox_name="missing")

        self.view_service.create.assert_not_called()

    def test_failing_cube_profile_raises_before_the_view_is_created(self):
        with patch.object(CellService, "_get_blob_cube_profile", side_effect=RuntimeError("connection lost")):
            with self.assertRaises(RuntimeError):
                self.cell_service._execute_view_csv_use_blob(**self.ARGUMENTS, lean_ti=True)

        self.view_service.create.assert_not_called()


class TestMdxViewDataSourceHierarchies(unittest.TestCase):
    def test_dimension_on_two_axis_positions_raises(self):
        # the file has one column per cube dimension, so it can't hold two hierarchies of one dimension
        mdx = (
            MdxBuilder.from_cube("Sales")
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.tm1_subset_all("Region"))
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.tm1_subset_all("Region", "By Manager"))
        )

        with self.assertRaises(ValueError):
            _cell_service()._mdx_view_data_source_hierarchies(mdx, mdx.to_mdx(), SALES_DIMENSIONS)


class TestLoadFromBlobTransactionLog(unittest.TestCase):
    """load_from_blob switches transaction logging like the other write functions: `deactivate_transaction_log`
    switches it off before the load, `reactivate_transaction_log` switches it on afterwards."""

    def setUp(self):
        self.deactivate = self.patch(CellService, "deactivate_transactionlog")
        self.activate = self.patch(CellService, "activate_transactionlog")
        self.patch(CellService, "_get_blob_cube_profile")
        self.build = self.patch(CellService, "_build_blob_to_cube_process")
        self.execute = self.patch(
            ProcessService, "execute_process_with_return", return_value=(True, "CompletedSuccessfully", None)
        )
        self.patch(FileService, "delete")

    def patch(self, target, attribute: str, **kwargs) -> MagicMock:
        patcher = patch.object(target, attribute, **kwargs)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def load(self, version: str = V11, **kwargs):
        _cell_service(version).load_from_blob("load.csv", cube_name="Sales", dimensions=SALES_DIMENSIONS, **kwargs)

    def test_each_flag_switches_logging_on_its_own(self):
        for deactivate, reactivate in ((False, False), (True, False), (False, True), (True, True)):
            with self.subTest(deactivate=deactivate, reactivate=reactivate):
                self.deactivate.reset_mock()
                self.activate.reset_mock()

                self.load(deactivate_transaction_log=deactivate, reactivate_transaction_log=reactivate)

                self.assertEqual(1 if deactivate else 0, self.deactivate.call_count)
                self.assertEqual(1 if reactivate else 0, self.activate.call_count)

    def test_reactivates_when_the_load_fails(self):
        self.execute.return_value = (False, "Aborted", "TM1ProcessError.log")

        with self.assertRaises(TM1pyWriteFailureException):
            self.load(reactivate_transaction_log=True)

        self.activate.assert_called_once()

    def test_reactivates_when_the_process_can_not_be_built(self):
        self.build.side_effect = ValueError("Sandbox 'missing' does not exist")

        with self.assertRaises(ValueError):
            self.load(deactivate_transaction_log=True, reactivate_transaction_log=True)

        self.deactivate.assert_not_called()
        self.activate.assert_called_once()

    def test_either_flag_raises_on_v12(self):
        for option in ("deactivate_transaction_log", "reactivate_transaction_log"):
            with self.subTest(option=option):
                with self.assertRaises(TM1pyVersionException):
                    self.load(version=V12, **{option: True})

        self.execute.assert_not_called()

    def test_reactivate_with_process_name_raises(self):
        with self.assertRaises(ValueError):
            _cell_service().load_from_blob("load.csv", process_name="loader", reactivate_transaction_log=True)


# ---------------------------------------------------------------------------------------------------------------- #
# live: lean TI gives the same results as legacy TI (runs only when tm1srv01 is configured)
# ---------------------------------------------------------------------------------------------------------------- #

CONFIG = Path(__file__).parent / "config.ini"


def _live_config():
    config = configparser.ConfigParser()
    config.read(CONFIG)
    return config["tm1srv01"] if config.has_section("tm1srv01") else None


def _parse_csv(text: str) -> list:
    return sorted(tuple(row) for row in csv.reader(io.StringIO(text.lstrip("﻿"))) if row)


@unittest.skipIf(_live_config() is None, "tm1srv01 not configured in Tests/config.ini")
class TestLeanBlobTiLive(unittest.TestCase):
    prefix = "TM1py_Tests_LeanBlob_"
    source_cube = prefix + "Source"
    target_cube = prefix + "Target"
    view_name = prefix + "View"
    d1 = prefix + "D1"
    d2 = prefix + "D2"
    measure = prefix + "Measure"
    alt_hierarchy = "Alt"
    d1_elements = ["plain", 'quote"in', "O'Brien", "comma,el", "brack]et", "Ünïcode é"]
    d2_elements = ["e1", "e2"]
    numbers = [0.1234567891234, 123456789.987654, 1e-07, -42.5, 9876543210123.5, 1]
    strings = ['He said "hi"', "a,b", "O'Brien's", "Ünïcode", "plain", 'x""y']

    @classmethod
    def setUpClass(cls):
        cls.tm1 = TM1Service(**_live_config())
        for name, elements in (
            (cls.d1, [Element(e, "Numeric") for e in cls.d1_elements]),
            (cls.d2, [Element(e, "Numeric") for e in cls.d2_elements]),
            (cls.measure, [Element("Value", "Numeric"), Element("Comment", "String")]),
        ):
            hierarchies = [Hierarchy(name, name, elements=elements)]
            if name == cls.d1:
                # an alternate hierarchy with the same leaves under one consolidation
                alt_elements = [Element(e, "Numeric") for e in cls.d1_elements] + [Element("Total", "Consolidated")]
                edges = {("Total", e): 1 for e in cls.d1_elements}
                hierarchies.append(Hierarchy(cls.alt_hierarchy, name, elements=alt_elements, edges=edges))
            cls.tm1.dimensions.update_or_create(Dimension(name, hierarchies))
        for cube in (cls.source_cube, cls.target_cube):
            cls.tm1.cubes.update_or_create(Cube(cube, [cls.d1, cls.d2, cls.measure]))

        cells = {}
        for i, element in enumerate(cls.d1_elements):
            cells[element, "e1", "Value"] = cls.numbers[i]
            cells[element, "e2", "Comment"] = cls.strings[i]
        cls.tm1.cells.write(cls.source_cube, cells, use_ti=True)

        view = NativeView(cube_name=cls.source_cube, view_name=cls.view_name, suppress_empty_rows=True)
        view.add_row(cls.d1, AnonymousSubset(cls.d1, cls.d1, expression=f"{{TM1SUBSETALL([{cls.d1}])}}"))
        view.add_row(cls.d2, AnonymousSubset(cls.d2, cls.d2, expression=f"{{TM1SUBSETALL([{cls.d2}])}}"))
        view.add_column(cls.measure, AnonymousSubset(cls.measure, cls.measure, elements=["Value", "Comment"]))
        cls.tm1.views.update_or_create(view, private=False)

    @classmethod
    def tearDownClass(cls):
        for cube in (cls.source_cube, cls.target_cube):
            if cls.tm1.cubes.exists(cube):
                cls.tm1.cubes.delete(cube)
        for dimension in (cls.d1, cls.d2, cls.measure):
            if cls.tm1.dimensions.exists(dimension):
                cls.tm1.dimensions.delete(dimension)
        cls.tm1.logout()

    def setUp(self):
        self.tm1.processes.execute_ti_code([f"CubeClearData('{self.target_cube}');"])

    def _mdx(self, cube: str) -> MdxBuilder:
        return (
            MdxBuilder.from_cube(cube)
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.tm1_subset_all(self.d1))
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.tm1_subset_all(self.d2))
            .add_hierarchy_set_to_column_axis(
                MdxHierarchySet.members([Member.of(self.measure, "Value"), Member.of(self.measure, "Comment")])
            )
        )

    def _cells(self, cube: str) -> dict:
        return dict(self.tm1.cells.execute_mdx_rows_and_values(self._mdx(cube).to_mdx(), element_unique_names=False))

    def test_execute_mdx_csv_lean_equals_legacy(self):
        legacy = self.tm1.cells.execute_mdx_csv(self._mdx(self.source_cube), use_blob=True)
        lean = self.tm1.cells.execute_mdx_csv(self._mdx(self.source_cube), use_blob=True, lean_ti=True)
        self.assertEqual(_parse_csv(legacy), _parse_csv(lean))
        self.assertEqual(len(self.d1_elements) * 2 + 1, len(_parse_csv(lean)))

    def test_execute_mdx_csv_lean_mdx_string_equals_legacy(self):
        mdx = self._mdx(self.source_cube).to_mdx()
        legacy = self.tm1.cells.execute_mdx_csv(mdx, use_blob=True)
        lean = self.tm1.cells.execute_mdx_csv(mdx, use_blob=True, lean_ti=True)
        self.assertEqual(_parse_csv(legacy), _parse_csv(lean))

    def test_execute_view_csv_lean_equals_legacy(self):
        legacy = self.tm1.cells.execute_view_csv(self.source_cube, self.view_name, use_blob=True)
        lean = self.tm1.cells.execute_view_csv(self.source_cube, self.view_name, use_blob=True, lean_ti=True)
        self.assertEqual(_parse_csv(legacy), _parse_csv(lean))

    @skip_if_no_pandas
    def test_dataframe_round_trip_lean(self):
        df = self.tm1.cells.execute_mdx_dataframe(self._mdx(self.source_cube), use_blob=True, lean_ti=True)
        self.tm1.cells.write_dataframe(self.target_cube, df, use_blob=True, lean_ti=True)
        self.assertEqual(self._cells(self.source_cube), self._cells(self.target_cube))

    def _value(self, *elements):
        coordinates = zip((self.d1, self.d2, self.measure), elements)
        return self.tm1.cells.get_value(self.target_cube, list(coordinates))

    def test_write_lean_numeric_and_string_measures(self):
        cells = {("plain", "e1", "Value"): 1e-07, ('quote"in', "e2", "Comment"): 'He said "hi"'}
        self.tm1.cells.write(self.target_cube, cells, use_blob=True, lean_ti=True)
        self.assertEqual(1e-07, self._value("plain", "e1", "Value"))
        self.assertEqual('He said "hi"', self._value('quote"in', "e2", "Comment"))

    def test_write_lean_increment(self):
        cells = {("plain", "e1", "Value"): 2}
        self.tm1.cells.write(self.target_cube, cells, use_blob=True, lean_ti=True)
        self.tm1.cells.write(self.target_cube, cells, use_blob=True, lean_ti=True, increment=True)
        self.assertEqual(4, self._value("plain", "e1", "Value"))

    # -- views built inside the export process (step 3) ------------------------------------------------------- #

    def _export_with_view(self, view_definition, data_source_dimensions) -> list:
        """Run a lean export whose prolog builds `view_definition`; return the file's rows, columns in cube order.

        :param data_source_dimensions: dimensions in data source order
        """
        cells = self.tm1.cells
        cube_dimensions = [self.d1, self.d2, self.measure]
        name = cells.suggest_unique_object_name()
        file_name = name + ".csv"
        self.tm1.files.create(file_name, b"")
        try:
            process = cells._build_cube_to_blob_process(
                cube=self.source_cube,
                variables=[f"v{cube_dimensions.index(d) + 1}" for d in data_source_dimensions],
                skip_variables=[],
                top=None,
                skip=None,
                skip_zeros=True,
                skip_consolidated_cells=True,
                skip_rule_derived_cells=True,
                value_separator=",",
                process_name=name,
                view_name=name,
                file_name=file_name,
                lean_ti=True,
                variable_hierarchies=list(data_source_dimensions),
                profile=cells._get_blob_cube_profile(self.source_cube, hierarchies=data_source_dimensions),
                view_definition=view_definition,
            )
            success, status, log = self.tm1.processes.execute_process_with_return(process)
            self.assertTrue(success, f"{status}: {log}")
            return _parse_csv(self.tm1.files.get(file_name).decode("utf-8-sig"))
        finally:
            self.tm1.files.delete(file_name)

    def _expected_rows(self, d1_elements=None, d2_elements=None) -> list:
        rows = []
        for i, element in enumerate(self.d1_elements):
            if d1_elements is not None and element not in d1_elements:
                continue
            if d2_elements is None or "e1" in d2_elements:
                rows.append((element, "e1", "Value", f"{self.numbers[i]:.15g}"))
            if d2_elements is None or "e2" in d2_elements:
                rows.append((element, "e2", "Comment", self.strings[i]))
        return sorted(rows)

    def _assert_rows(self, expected: list, actual: list):
        # numbers as TM1 writes them may differ in formatting; compare them as floats
        def normalize(row):
            *coordinates, value = row
            return (*coordinates, float(value)) if coordinates[-1] == "Value" else row

        self.assertEqual([normalize(r) for r in expected], [normalize(r) for r in actual])

    def test_native_view_from_mdx_builder(self):
        view = NativeView.from_mdx_builder(self._mdx(self.source_cube))
        rows = self._export_with_view(view, [self.d1, self.d2, self.measure])
        self._assert_rows(self._expected_rows(), rows)

    def test_native_view_with_title_and_static_subset(self):
        mdx = (
            MdxBuilder.from_cube(self.source_cube)
            .add_hierarchy_set_to_row_axis(
                MdxHierarchySet.members([Member.of(self.d1, "O'Brien"), Member.of(self.d1, "brack]et")])
            )
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.tm1_subset_all(self.measure))
            .where(Member.of(self.d2, "e1"))
        )
        rows = self._export_with_view(NativeView.from_mdx_builder(mdx), [self.d1, self.d2, self.measure])
        self._assert_rows(self._expected_rows(["O'Brien", "brack]et"], ["e1"]), rows)

    def test_native_view_unmentioned_dimension_uses_default_member(self):
        default = self.tm1.elements.execute_set_mdx_element_names(f"{{[{self.d2}].[{self.d2}].DEFAULTMEMBER}}")
        mdx = (
            MdxBuilder.from_cube(self.source_cube)
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.tm1_subset_all(self.d1))
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.tm1_subset_all(self.measure))
        )
        rows = self._export_with_view(NativeView.from_mdx_builder(mdx), [self.d1, self.d2, self.measure])
        self._assert_rows(self._expected_rows(d2_elements=default), rows)

    def test_mdx_view_with_alternate_hierarchy(self):
        mdx = (
            MdxBuilder.from_cube(self.source_cube)
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.tm1_subset_all(self.measure))
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.tm1_subset_all(self.d1, self.alt_hierarchy))
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.tm1_subset_all(self.d2))
        )
        with self.assertRaises(NotImplementedError):
            NativeView.from_mdx_builder(mdx)

        # MDX view variables: column dimensions, then row dimensions, then the rest in cube order.
        # DIMENSION PROPERTIES would add data source variables, so the MDX is written without them
        rows = self._export_with_view(mdx.to_mdx(skip_dimension_properties=True), [self.measure, self.d1, self.d2])
        self._assert_rows(self._expected_rows(), rows)

    def test_split_mdx_slices_cover_the_query_once(self):
        mdx = self._mdx(self.source_cube)

        slices = self.tm1.cells.split_mdx(mdx, self.d1, 4)

        self.assertEqual(4, len(slices))
        sizes = [len(s.axes[1].dim_sets[0].members) for s in slices]
        self.assertEqual(len(self.d1_elements), sum(sizes))
        self.assertLessEqual(max(sizes) - min(sizes), 1)
        # the original query is unchanged
        self.assertNotIsInstance(mdx.axes[1].dim_sets[0], type(slices[0].axes[1].dim_sets[0]))

        rows = []
        for mdx_slice in slices:
            view = NativeView.from_mdx_builder(mdx_slice)
            rows += self._export_with_view(view, [self.d1, self.d2, self.measure])
        self._assert_rows(self._expected_rows(), sorted(rows))

    def test_split_mdx_more_parts_than_elements(self):
        slices = self.tm1.cells.split_mdx(self._mdx(self.source_cube), self.d2, 5)
        self.assertEqual(len(self.d2_elements), len(slices))

    def test_split_mdx_dimension_not_on_an_axis_raises(self):
        mdx = self._mdx(self.source_cube)
        with self.assertRaises(ValueError):
            self.tm1.cells.split_mdx(mdx, "not a dimension", 2)
        with self.assertRaises(ValueError):
            self.tm1.cells.split_mdx(mdx, self.d1, 0)


if __name__ == "__main__":
    unittest.main()
