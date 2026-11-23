"""export_to_blob and load_from_blob: cube data copied through files in the file store, against a live server.

Runs on tm1srv01. Most cases copy between two cubes on the same instance (export -> load, the file never leaves the
file store); the cross-instance case runs only when tm1srv02 is configured and is skipped otherwise.
"""

import configparser
import unittest
from pathlib import Path

from mdxpy import MdxBuilder, MdxHierarchySet, Member

from TM1py import TM1Service
from TM1py.Exceptions import (
    TM1pyExportFailureException,
    TM1pyVersionException,
    TM1pyWriteFailureException,
    TM1pyWritePartialFailureException,
)
from TM1py.Objects import (
    AnonymousSubset,
    Cube,
    Dimension,
    Element,
    Hierarchy,
    NativeView,
    Process,
    Rules,
)
from TM1py.Utils import verify_version

CONFIG = configparser.ConfigParser()
CONFIG.read(Path(__file__).parent.joinpath("config.ini"))

PREFIX = "TM1py_Tests_BlobTransfer_"
D1, D1_CODE, D2, MEASURE = PREFIX + "D1", PREFIX + "D1Code", PREFIX + "D2", PREFIX + "Measure"
SOURCE, TARGET, ALIAS_TARGET = PREFIX + "Source", PREFIX + "Target", PREFIX + "AliasTarget"
# a cube without string measures: the generated load reads the value column as a number
NUMERIC_MEASURE, NUMERIC_TARGET = PREFIX + "NumericMeasure", PREFIX + "NumericTarget"
VIEW = PREFIX + "View"
LOADER = PREFIX + "Loader"
ALT = "Alt"
ALIAS = "Code"

D1_ELEMENTS = ["plain", 'quote"in', "O'Brien", "comma,el", "brack]et", "Ünïcode é"]
# 'brack]et' has a blank alias: it is written under its element name
CODES = {"plain": "P1", 'quote"in': 'Q"1', "O'Brien": "O'1", "comma,el": "C,1", "brack]et": "", "Ünïcode é": "Ü1"}
NUMBERS = [0.1234567891234, 123456789.987654, 1e-07, -42.5, 9876543210123.5, 1]
STRINGS = ['He said "hi"', "a,b", "O'Brien's", "Ünïcode", "plain", "line\nbreak"]


def connect(section: str) -> TM1Service:
    if section not in CONFIG:
        raise unittest.SkipTest(f"{section} not configured in config.ini")
    return TM1Service(**CONFIG[section])


def build_fixture(tm1: TM1Service):
    def dimension(name, elements, hierarchies=()):
        return Dimension(name, [Hierarchy(name, name, elements=elements), *hierarchies])

    numeric = lambda names: [Element(n, "Numeric") for n in names]  # noqa: E731
    d2_alt = Hierarchy(
        ALT, D2, elements=numeric(["e1", "e2"]) + [Element("Total", "Consolidated")], edges={("Total", "e1"): 1}
    )
    d1 = dimension(D1, numeric(D1_ELEMENTS))
    d1.hierarchies[0].add_element_attribute(ALIAS, "Alias")
    for d in (
        d1,
        dimension(D1_CODE, numeric([CODES[e] or e for e in D1_ELEMENTS])),
        dimension(D2, numeric(["e1", "e2"]), [d2_alt]),
        dimension(MEASURE, [Element("Value", "Numeric"), Element("Comment", "String"), Element("Double", "Numeric")]),
        dimension(NUMERIC_MEASURE, numeric(["Value"])),
    ):
        tm1.dimensions.update_or_create(d)
    tm1.cells.write("}ElementAttributes_" + D1, {(e, ALIAS): code for e, code in CODES.items() if code}, use_ti=True)

    for cube, dimensions in (
        (SOURCE, [D1, D2, MEASURE]),
        (TARGET, [D1, D2, MEASURE]),
        (ALIAS_TARGET, [D1_CODE, D2, MEASURE]),
        (NUMERIC_TARGET, [D1, D2, NUMERIC_MEASURE]),
    ):
        tm1.cubes.update_or_create(Cube(cube, dimensions))
    source = tm1.cubes.get(SOURCE)
    source.rules = Rules("SKIPCHECK;\n['Double'] = N: ['Value'] * 2;\nFEEDERS;\n['Value'] => ['Double'];")
    tm1.cubes.update(source)

    tm1.cells.write(SOURCE, {(e, "e1", "Value"): n for e, n in zip(D1_ELEMENTS, NUMBERS)}, use_ti=True)
    # through REST: a TI string literal can't hold a line break
    tm1.cells.write(SOURCE, {(e, "e2", "Comment"): s for e, s in zip(D1_ELEMENTS, STRINGS)})

    view = NativeView(SOURCE, VIEW)
    view.add_row(D1, AnonymousSubset(D1, D1, expression=f"{{TM1SUBSETALL([{D1}])}}"))
    view.add_row(D2, AnonymousSubset(D2, D2, elements=["e1", "e2"]))
    view.add_column(MEASURE, AnonymousSubset(MEASURE, MEASURE, elements=["Value", "Comment"]))
    tm1.views.update_or_create(view, private=False)


def drop_fixture(tm1: TM1Service):
    for cube in (SOURCE, TARGET, ALIAS_TARGET, NUMERIC_TARGET):
        if tm1.cubes.exists(cube):
            tm1.cubes.delete(cube)
    for d in (D1, D1_CODE, D2, MEASURE, NUMERIC_MEASURE):
        if tm1.dimensions.exists(d):
            tm1.dimensions.delete(d)
    if tm1.processes.exists(LOADER):
        tm1.processes.delete(LOADER)


def server_objects(tm1: TM1Service) -> dict:
    """Names of the objects an export or load could leave behind: public subsets on the fixture's hierarchies and
    TM1py's generated processes (other sessions' processes don't carry its prefix)"""
    hierarchies = [(D1, D1), (D1_CODE, D1_CODE), (D2, D2), (D2, ALT), (MEASURE, MEASURE)]
    objects = {f"subsets {d}:{h}": set(tm1.subsets.get_all_names(d, h)) for d, h in hierarchies}
    objects["processes"] = {name for name in tm1.processes.get_all_names() if name.startswith("tm1py.")}
    return objects


def all_cells_mdx(cube: str, d1: str = D1, d2_hierarchy: str = D2, measure: str = MEASURE) -> MdxBuilder:
    return (
        MdxBuilder.from_cube(cube)
        .add_hierarchy_set_to_row_axis(MdxHierarchySet.tm1_subset_all(d1))
        .add_hierarchy_set_to_row_axis(MdxHierarchySet.tm1_subset_all(D2, d2_hierarchy))
        .add_hierarchy_set_to_column_axis(MdxHierarchySet.tm1_subset_all(measure))
    )


def cells(tm1: TM1Service, cube: str, d1: str = D1, measure: str = MEASURE) -> dict:
    """Non-empty leaf cells of a cube, as {(d1, d2, measure): value}"""
    mdx = all_cells_mdx(cube, d1, measure=measure).to_mdx()
    result = tm1.cells.execute_mdx(mdx, cell_properties=["Value"], skip_zeros=True, skip_consolidated_cells=True)
    return {
        tuple(element.split("].[")[-1][:-1].replace("]]", "]") for element in coordinates): cell["Value"]
        for coordinates, cell in result.items()
        if cell["Value"] not in (None, "")
    }


def assert_cells_close(test: unittest.TestCase, expected: dict, actual: dict):
    test.assertEqual(set(expected), set(actual))
    for key, value in expected.items():
        if isinstance(value, float):
            test.assertAlmostEqual(value, actual[key], delta=abs(value) * 1e-12, msg=key)
        else:
            test.assertEqual(value, actual[key], msg=key)


def expected_cells(rule_derived: bool = False) -> dict:
    expected = {}
    for element, number, string in zip(D1_ELEMENTS, NUMBERS, STRINGS):
        expected[element, "e1", "Value"] = number
        expected[element, "e2", "Comment"] = string
        if rule_derived:
            expected[element, "e1", "Double"] = number * 2
    return expected


class TestBlobTransfer(unittest.TestCase):
    tm1: TM1Service

    @classmethod
    def setUpClass(cls):
        cls.tm1 = connect("tm1srv01")
        build_fixture(cls.tm1)

    @classmethod
    def tearDownClass(cls):
        drop_fixture(cls.tm1)
        cls.tm1.logout()

    def setUp(self):
        self.tm1.processes.execute_ti_code(
            [f"CubeClearData('{cube}');" for cube in (TARGET, ALIAS_TARGET, NUMERIC_TARGET)]
        )
        self.files_before = set(self.tm1.files.get_all_names())
        self.views_before = self.tm1.views.get_all_names(SOURCE)
        self.objects_before = server_objects(self.tm1)

    def tearDown(self):
        for name in set(self.tm1.files.get_all_names()) - self.files_before:
            self.tm1.files.delete(name)

    def assert_nothing_left(self):
        self.assertEqual(self.files_before, set(self.tm1.files.get_all_names()))
        self.assertEqual(self.views_before, self.tm1.views.get_all_names(SOURCE))
        self.assertEqual(self.objects_before, server_objects(self.tm1))

    def assert_cells_close(self, expected: dict, actual: dict):
        assert_cells_close(self, expected, actual)

    def round_trip(self, **export_arguments) -> dict:
        file_name = self.tm1.cells.export_to_blob(**export_arguments)
        self.tm1.cells.load_from_blob(file_name, cube_name=TARGET)
        self.assert_nothing_left()
        return cells(self.tm1, TARGET)

    # -- export sources ------------------------------------------------------------------------------------ #

    def test_mdx_builder_through_native_view(self):
        self.assert_cells_close(expected_cells(), self.round_trip(mdx=all_cells_mdx(SOURCE)))

    def test_mdx_builder_through_mdx_view(self):
        self.assert_cells_close(expected_cells(), self.round_trip(mdx=all_cells_mdx(SOURCE), use_native_view=False))

    def test_mdx_string(self):
        mdx = all_cells_mdx(SOURCE).to_mdx()
        self.assertIn("DIMENSION PROPERTIES", mdx)
        self.assert_cells_close(expected_cells(), self.round_trip(mdx=mdx))

    def test_existing_view_by_name(self):
        self.assert_cells_close(expected_cells(), self.round_trip(cube_name=SOURCE, view_name=VIEW))

    def test_alternate_hierarchy_falls_back_to_mdx_view(self):
        mdx = all_cells_mdx(SOURCE, d2_hierarchy=ALT)
        self.assert_cells_close(expected_cells(), self.round_trip(mdx=mdx))

    def test_where_member_is_written(self):
        mdx = (
            MdxBuilder.from_cube(SOURCE)
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.tm1_subset_all(D1))
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.tm1_subset_all(MEASURE))
            .where(Member.of(D2, "e1"))
        )
        expected = {key: value for key, value in expected_cells().items() if key[1] == "e1"}
        self.assert_cells_close(expected, self.round_trip(mdx=mdx))

    def test_rule_derived_cells_included_on_request(self):
        actual = self.round_trip(mdx=all_cells_mdx(SOURCE), skip_rule_derived_cells=False)
        self.assert_cells_close(expected_cells(rule_derived=True), actual)

    def test_split_mdx_slices_round_trip(self):
        for mdx_slice in self.tm1.cells.split_mdx(all_cells_mdx(SOURCE), D1, 3):
            file_name = self.tm1.cells.export_to_blob(mdx=mdx_slice)
            self.tm1.cells.load_from_blob(file_name, cube_name=TARGET)
        self.assert_nothing_left()
        self.assert_cells_close(expected_cells(), cells(self.tm1, TARGET))

    def test_sandbox_export(self):
        sandbox = PREFIX + "Sandbox"
        if self.tm1.sandboxes.exists(sandbox):
            self.tm1.sandboxes.delete(sandbox)
        from TM1py.Objects import Sandbox

        self.tm1.sandboxes.create(Sandbox(sandbox, True))
        try:
            self.tm1.cells.write(SOURCE, {("plain", "e1", "Value"): 777}, sandbox_name=sandbox)
            actual = self.round_trip(mdx=all_cells_mdx(SOURCE), sandbox_name=sandbox)
        finally:
            self.tm1.sandboxes.delete(sandbox)
        self.assertEqual(777, actual["plain", "e1", "Value"])

    # -- file contents ------------------------------------------------------------------------------------ #

    def test_header_and_columns_in_cube_order(self):
        mdx = (
            MdxBuilder.from_cube(SOURCE)
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.member(Member.of(MEASURE, "Value")))
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.member(Member.of(D2, "e1")))
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.member(Member.of(D1, "plain")))
        )
        for use_native_view in (True, False):
            with self.subTest(use_native_view=use_native_view):
                file_name = self.tm1.cells.export_to_blob(mdx=mdx, include_header=True, use_native_view=use_native_view)
                content = self.tm1.files.get(file_name).decode("utf-8-sig").splitlines()
                self.tm1.files.delete(file_name)
                self.assertEqual(f'"{D1}","{D2}","{MEASURE}","Value"', content[0])
                self.assertEqual('"plain","e1","Value","0.1234567891234"', content[1])

    def test_aliases_with_blank_fallback(self):
        file_name = self.tm1.cells.export_to_blob(mdx=all_cells_mdx(SOURCE), aliases={D1: ALIAS})
        self.tm1.cells.load_from_blob(file_name, cube_name=ALIAS_TARGET)

        expected = {(CODES[d1] or d1, d2, m): v for (d1, d2, m), v in expected_cells().items()}
        self.assert_cells_close(expected, cells(self.tm1, ALIAS_TARGET, d1=D1_CODE))

    def test_unknown_alias_dimension_or_attribute_raises_before_running(self):
        for aliases in ({"not a dimension": ALIAS}, {D1: "not an attribute"}):
            with self.subTest(aliases=aliases):
                with self.assertRaises(ValueError):
                    self.tm1.cells.export_to_blob(mdx=all_cells_mdx(SOURCE), aliases=aliases)
        self.assert_nothing_left()

    def test_source_arguments_are_validated(self):
        for arguments in (
            {},
            {"cube_name": SOURCE},
            {"mdx": all_cells_mdx(SOURCE), "cube_name": SOURCE, "view_name": VIEW},
        ):
            with self.subTest(arguments=arguments):
                with self.assertRaises(ValueError):
                    self.tm1.cells.export_to_blob(**arguments)

    # -- export failure ------------------------------------------------------------------------------------ #

    def test_failed_export_raises_and_removes_its_file(self):
        # the process aborts in its prolog: the static subset can't take an element that doesn't exist
        mdx = (
            MdxBuilder.from_cube(SOURCE)
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.members([Member.of(D1, "no such element")]))
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.tm1_subset_all(MEASURE))
        )
        with self.assertRaises(TM1pyExportFailureException) as context:
            self.tm1.cells.export_to_blob(mdx=mdx)

        self.assertIsInstance(context.exception, RuntimeError)
        self.assertEqual("Aborted", context.exception.status)
        self.assertTrue(context.exception.error_log_file)
        self.assert_nothing_left()

    # -- load ------------------------------------------------------------------------------------------- #

    def test_load_increment_and_clear_view(self):
        self.round_trip(mdx=all_cells_mdx(SOURCE))
        file_name = self.tm1.cells.export_to_blob(mdx=all_cells_mdx(SOURCE))
        self.tm1.cells.load_from_blob(file_name, cube_name=TARGET, increment=True)
        self.assertAlmostEqual(-85, cells(self.tm1, TARGET)["comma,el", "e1", "Value"])

        clear_view = NativeView(TARGET, PREFIX + "Clear")
        clear_view.add_row(D1, AnonymousSubset(D1, D1, elements=["plain"]))
        clear_view.add_row(D2, AnonymousSubset(D2, D2, elements=["e1"]))
        clear_view.add_column(MEASURE, AnonymousSubset(MEASURE, MEASURE, elements=["Value"]))
        self.tm1.views.update_or_create(clear_view, private=False)
        try:
            self.tm1.cells.write(TARGET, {("O'Brien", "e1", "Value"): 5})
            file_name = self.tm1.cells.export_to_blob(
                mdx=MdxBuilder.from_cube(SOURCE)
                .add_hierarchy_set_to_row_axis(MdxHierarchySet.member(Member.of(D1, "O'Brien")))
                .add_hierarchy_set_to_column_axis(MdxHierarchySet.member(Member.of(MEASURE, "Value")))
                .where(Member.of(D2, "e1"))
            )
            self.tm1.cells.load_from_blob(file_name, cube_name=TARGET, clear_view=clear_view.name)
        finally:
            self.tm1.views.delete(TARGET, clear_view.name)
        actual = cells(self.tm1, TARGET)
        self.assertNotIn(("plain", "e1", "Value"), actual)
        self.assertAlmostEqual(1e-07, actual["O'Brien", "e1", "Value"])

    def test_load_into_rule_cells(self):
        file_name = self.tm1.cells.export_to_blob(mdx=all_cells_mdx(SOURCE), skip_rule_derived_cells=False)

        with self.assertRaises(TM1pyWritePartialFailureException):
            self.tm1.cells.load_from_blob(file_name, cube_name=SOURCE)
        # kept after a failed load, for inspection
        self.assertTrue(self.tm1.files.exists(file_name))

        self.tm1.cells.load_from_blob(file_name, cube_name=SOURCE, skip_non_updateable=True)
        self.assertFalse(self.tm1.files.exists(file_name))

    def test_load_keeps_file_on_request(self):
        file_name = self.tm1.cells.export_to_blob(mdx=all_cells_mdx(SOURCE))
        self.tm1.cells.load_from_blob(file_name, cube_name=TARGET, remove_blob=False)
        self.assertTrue(self.tm1.files.exists(file_name))

    # -- cube without string measures: the generated load reads the value column as a number ----------- #

    def test_numeric_cube_round_trip(self):
        mdx = (
            MdxBuilder.from_cube(SOURCE)
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.tm1_subset_all(D1))
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.tm1_subset_all(D2))
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.member(Member.of(MEASURE, "Value")))
        )

        file_name = self.tm1.cells.export_to_blob(mdx=mdx)
        self.tm1.cells.load_from_blob(file_name, cube_name=NUMERIC_TARGET)

        expected = {(element, "e1", "Value"): number for element, number in zip(D1_ELEMENTS, NUMBERS)}
        self.assert_cells_close(expected, cells(self.tm1, NUMERIC_TARGET, measure=NUMERIC_MEASURE))

    def write_to_numeric_cube(self, value, lean_ti: bool) -> tuple:
        """Write `value` next to a valid value over existing data. Returns the exception raised (its type name, or
        None) and the cube's cells afterwards"""
        self.tm1.processes.execute_ti_code([f"CubeClearData('{NUMERIC_TARGET}');"])
        self.tm1.cells.write(NUMERIC_TARGET, {("plain", "e1", "Value"): 5})
        raised = None
        try:
            self.tm1.cells.write(
                NUMERIC_TARGET,
                {("plain", "e1", "Value"): value, ("plain", "e2", "Value"): 7},
                use_blob=True,
                lean_ti=lean_ti,
            )
        except (TM1pyWriteFailureException, TM1pyWritePartialFailureException) as e:
            raised = type(e).__name__
        return raised, cells(self.tm1, NUMERIC_TARGET, measure=NUMERIC_MEASURE)

    def test_numeric_cube_lean_load_treats_invalid_values_like_legacy_load(self):
        # legacy converts the value with StringToNumber; lean reads the value column as a number
        for value in ("abc", "", None):
            with self.subTest(value=value):
                legacy = self.write_to_numeric_cube(value, lean_ti=False)
                lean = self.write_to_numeric_cube(value, lean_ti=True)
                self.assertEqual(legacy, lean)

    def test_attribute_cube_round_trip(self):
        attribute_cube = "}ElementAttributes_" + D1
        mdx = (
            MdxBuilder.from_cube(attribute_cube)
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.tm1_subset_all(D1))
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.member(Member.of(attribute_cube, ALIAS)))
        )
        expected = {element: code for element, code in CODES.items() if code}

        def aliases() -> dict:
            result = self.tm1.cells.execute_mdx(mdx.to_mdx(), cell_properties=["Value"], skip_zeros=True)
            return {
                coordinates[0].split("].[")[-1][:-1].replace("]]", "]"): cell["Value"]
                for coordinates, cell in result.items()
                if cell["Value"]
            }

        file_name = self.tm1.cells.export_to_blob(mdx=mdx)
        try:
            self.tm1.cells.write(attribute_cube, {(element, ALIAS): "" for element in expected})
            self.assertEqual({}, aliases())
            self.tm1.cells.load_from_blob(file_name, cube_name=attribute_cube)
            actual = aliases()
        finally:
            self.tm1.cells.write(attribute_cube, {(element, ALIAS): code for element, code in expected.items()})
        self.assertEqual(expected, actual)
        self.assert_nothing_left()

    def test_cube_only_options_with_process_name_raise(self):
        for option in (
            {"increment": True},
            {"skip_non_updateable": True},
            {"allow_spread": True},
            {"sandbox_name": "any"},
            {"clear_view": "any"},
            {"deactivate_transaction_log": True},
            {"reactivate_transaction_log": True},
            {"dimensions": [D1, D2, MEASURE]},
        ):
            with self.subTest(option=option):
                with self.assertRaises(ValueError):
                    self.tm1.cells.load_from_blob("any.csv", process_name=LOADER, **option)

    def test_load_requires_exactly_one_target(self):
        for arguments in ({}, {"cube_name": TARGET, "process_name": LOADER}):
            with self.subTest(arguments=arguments):
                with self.assertRaises(ValueError):
                    self.tm1.cells.load_from_blob("any.csv", **arguments)

    def test_transaction_log_deactivated_and_reactivated(self):
        if verify_version("12", self.tm1.version):
            self.skipTest("v11 only")

        def logging():
            return self.tm1.cells.get_value("}CubeProperties", f"{SOURCE},LOGGING")

        self.tm1.cells.write_value("YES", "}CubeProperties", (SOURCE, "LOGGING"))
        file_name = self.tm1.cells.export_to_blob(mdx=all_cells_mdx(SOURCE), skip_rule_derived_cells=False)
        try:
            # only deactivated: logging stays off. The load fails partially (rule cells), so the file is kept
            with self.assertRaises(TM1pyWritePartialFailureException):
                self.tm1.cells.load_from_blob(file_name, cube_name=SOURCE, deactivate_transaction_log=True)
            self.assertEqual("NO", logging())

            # reactivated although the load fails
            with self.assertRaises(TM1pyWritePartialFailureException):
                self.tm1.cells.load_from_blob(file_name, cube_name=SOURCE, reactivate_transaction_log=True)
            self.assertEqual("YES", logging())

            self.tm1.cells.load_from_blob(
                file_name,
                cube_name=SOURCE,
                deactivate_transaction_log=True,
                reactivate_transaction_log=True,
                skip_non_updateable=True,
            )
            self.assertEqual("YES", logging())
        finally:
            self.tm1.cells.write_value("YES", "}CubeProperties", (SOURCE, "LOGGING"))

    # -- developer process -------------------------------------------------------------------------------- #

    def create_loader(self, parameters=("pFileName", "pFactor")):
        process = Process(
            LOADER, datasource_type="ASCII", datasource_ascii_delimiter_char=",", datasource_ascii_header_records=0
        )
        for name in parameters:
            process.add_parameter(
                name, "", "" if name != "pFactor" else 1, "Numeric" if name == "pFactor" else "String"
            )
        for name in ("vD1", "vD2", "vMeasure", "vValue"):
            process.add_variable(name, "String")
        process.prolog_procedure = (
            "DatasourceNameForServer = pFileName;\nDatasourceASCIIQuoteCharacter = '\"';\n"
            "SetInputCharacterSet('TM1CS_UTF8');"
        )
        process.data_procedure = (
            f"IF (vMeasure @= 'Value');\n"
            f"  CellPutN(StringToNumber(vValue) * pFactor, '{TARGET}', vD1, vD2, vMeasure);\n"
            f"ENDIF;"
        )
        self.tm1.processes.update_or_create(process)

    def test_developer_process(self):
        self.create_loader()
        file_name = self.tm1.cells.export_to_blob(mdx=all_cells_mdx(SOURCE))

        self.tm1.cells.load_from_blob(file_name, process_name=LOADER, parameters={"pFactor": 10})

        expected = {k: v * 10 for k, v in expected_cells().items() if k[2] == "Value"}
        self.assert_cells_close(expected, cells(self.tm1, TARGET))
        self.assertFalse(self.tm1.files.exists(file_name))

    def test_developer_process_missing_or_without_file_parameter(self):
        if self.tm1.processes.exists(LOADER):
            self.tm1.processes.delete(LOADER)
        with self.assertRaises(ValueError):
            self.tm1.cells.load_from_blob("any.csv", process_name=LOADER)

        self.create_loader(parameters=("pFactor",))
        with self.assertRaises(ValueError):
            self.tm1.cells.load_from_blob("any.csv", process_name=LOADER)
        with self.assertRaises(ValueError):
            self.tm1.cells.load_from_blob("any.csv", process_name=LOADER, file_parameter="pFile")

    def test_developer_process_failure(self):
        self.create_loader()
        file_name = self.tm1.cells.export_to_blob(mdx=all_cells_mdx(SOURCE))

        # every record writes to an element that doesn't exist
        process = self.tm1.processes.get(LOADER)
        process.data_procedure = f"CellPutN(1, '{TARGET}', 'no such element', vD2, 'Value');"
        self.tm1.processes.update(process)
        with self.assertRaises((TM1pyWritePartialFailureException, TM1pyWriteFailureException)):
            self.tm1.cells.load_from_blob(file_name, process_name=LOADER)
        self.assertTrue(self.tm1.files.exists(file_name))


class TestBlobTransferV12Logging(unittest.TestCase):
    def test_transaction_log_options_on_v12_raise(self):
        tm1 = connect("tm1srv02")
        try:
            for option in ("deactivate_transaction_log", "reactivate_transaction_log"):
                with self.subTest(option=option):
                    with self.assertRaises(TM1pyVersionException):
                        tm1.cells.load_from_blob("any.csv", cube_name="any", **{option: True})
        finally:
            tm1.logout()


class TestBlobTransferCrossInstance(unittest.TestCase):
    """export on v11 -> transfer_from on v12 -> load on v12, and back"""

    def test_round_trip_v11_v12(self):
        v11, v12 = connect("tm1srv01"), connect("tm1srv02")
        try:
            build_fixture(v11)
            build_fixture(v12)
            for source, target in ((v11, v12), (v12, v11)):
                with self.subTest(source=source.version, target=target.version):
                    target.processes.execute_ti_code([f"CubeClearData('{TARGET}');"])
                    file_name = source.cells.export_to_blob(mdx=all_cells_mdx(SOURCE))
                    target.files.transfer_from(source.files, file_name, remove_source=True)
                    target.cells.load_from_blob(file_name, cube_name=TARGET)
                    assert_cells_close(self, expected_cells(), cells(target, TARGET))
                    self.assertFalse(source.files.exists(file_name))
                    self.assertFalse(target.files.exists(file_name))
        finally:
            for tm1 in (v11, v12):
                drop_fixture(tm1)
                tm1.logout()


if __name__ == "__main__":
    unittest.main()
