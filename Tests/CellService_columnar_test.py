"""Offline unit tests for the TM1 12.6.1 columnar (ARROW/PARQUET) write path on CellService.

Covers the two pure pieces that need no TM1 server:
  - CellService._encode_dataframe_columnar  (DataFrame -> Arrow-IPC / Parquet bytes)
  - CellService._build_columnar_blob_to_cube_process  (the ARROW/PARQUET TI process body)
"""

import unittest
from types import SimpleNamespace

import pandas as pd
import pyarrow as pa
import pyarrow.ipc
import pyarrow.parquet as pq

from TM1py.Services.CellService import CellService


class TestEncodeDataframeColumnar(unittest.TestCase):

    @staticmethod
    def _numeric_df():
        return pd.DataFrame(
            [["2024", "Revenue", 123456789.12345678], ["2025", "Revenue", 0.1]],
            columns=["Year", "Measure", "Value"],
        )

    def test_parquet_numeric_fields_types_and_exact_roundtrip(self):
        blob, value_is_numeric, extension = CellService._encode_dataframe_columnar(
            self._numeric_df(), "PARQUET", "zstd"
        )
        self.assertTrue(value_is_numeric)
        self.assertEqual(extension, ".parquet")
        self.assertEqual(blob[:4], b"PAR1")  # parquet magic
        table = pq.read_table(pa.BufferReader(blob))
        self.assertEqual(table.schema.names, ["v1", "v2", "vValue"])
        self.assertEqual(table.schema.field("vValue").type, pa.float64())
        # exact f64 round-trip (the whole point of the numeric columnar path)
        self.assertEqual(table.column("vValue").to_pylist()[0], 123456789.12345678)

    def test_arrow_ipc_numeric_is_readable_stream(self):
        blob, value_is_numeric, extension = CellService._encode_dataframe_columnar(self._numeric_df(), "ARROW", None)
        self.assertTrue(value_is_numeric)
        self.assertEqual(extension, ".arrow")
        table = pa.ipc.open_stream(pa.BufferReader(blob)).read_all()
        self.assertEqual(table.schema.names, ["v1", "v2", "vValue"])
        self.assertEqual(table.schema.field("vValue").type, pa.float64())
        self.assertEqual(table.num_rows, 2)

    def test_string_measure_encodes_as_string_column(self):
        df = pd.DataFrame([["2024", "Comment", "hello"]], columns=["Year", "Measure", "Value"])
        blob, value_is_numeric, extension = CellService._encode_dataframe_columnar(df, "PARQUET", None)
        self.assertFalse(value_is_numeric)
        table = pq.read_table(pa.BufferReader(blob))
        self.assertEqual(table.schema.field("vValue").type, pa.string())
        self.assertEqual(table.column("vValue").to_pylist(), ["hello"])


class TestBuildColumnarBlobToCubeProcess(unittest.TestCase):

    @staticmethod
    def _cell_service():
        # Build a CellService without connecting; the process builder only touches
        # self._rest.sandboxing_disabled (via generate_enable_sandbox_ti).
        cs = CellService.__new__(CellService)
        cs._rest = SimpleNamespace(sandboxing_disabled=True)
        return cs

    def _build(self, datasource_type, value_is_numeric, **overrides):
        kwargs = dict(
            cube_name="Sales",
            process_name="p_test",
            blob_filename="data" + (".parquet" if datasource_type == "PARQUET" else ".arrow"),
            dimensions=["Year", "Measure"],
            datasource_type=datasource_type,
            value_is_numeric=value_is_numeric,
            increment=False,
            skip_non_updateable=False,
            sandbox_name=None,
            allow_spread=False,
            clear_view=None,
        )
        kwargs.update(overrides)
        return self._cell_service()._build_columnar_blob_to_cube_process(**kwargs)

    def test_parquet_numeric_datasource_and_exact_numeric_binding(self):
        process = self._build("PARQUET", value_is_numeric=True)
        datasource = process.body_as_dict["DataSource"]
        self.assertEqual(datasource["Type"], "PARQUET")
        self.assertEqual(datasource["dataSourceNameForServer"], "data.parquet")
        self.assertFalse(any(key.startswith("ascii") for key in datasource))
        # numeric column -> Numeric vValue used directly (exact f64), never StringToNumber
        self.assertIn("nValue = vValue;", process.data_procedure)
        self.assertNotIn("StringToNumber", process.data_procedure)
        self.assertIn("CellPutN(nValue,'Sales',v1,v2)", process.data_procedure)
        value_variable = next(v for v in process.variables if v["Name"] == "vValue")
        self.assertEqual(value_variable["Type"], "Numeric")
        # coordinate variables stay String and are named to match the columnar fields
        self.assertEqual([v["Name"] for v in process.variables], ["v1", "v2", "vValue"])
        self.assertEqual(process.variables[0]["Type"], "String")

    def test_arrow_string_measure_uses_stringtonumber_and_string_var(self):
        process = self._build("ARROW", value_is_numeric=False)
        datasource = process.body_as_dict["DataSource"]
        self.assertEqual(datasource["Type"], "ARROW")
        self.assertFalse(any(key.startswith("ascii") for key in datasource))
        self.assertIn("nValue = StringToNumber(vValue);", process.data_procedure)
        value_variable = next(v for v in process.variables if v["Name"] == "vValue")
        self.assertEqual(value_variable["Type"], "String")

    def test_numeric_value_into_string_measure_is_stringified(self):
        process = self._build("PARQUET", value_is_numeric=True)
        # a numeric column written into a string measure must be stringified (var is Numeric)
        self.assertIn("CellPutS(sValue,'Sales',v1,v2)", process.data_procedure)
        self.assertIn("NumberToString(vValue)", process.data_procedure)

    def test_increment_uses_cellincrementn(self):
        process = self._build("PARQUET", value_is_numeric=True, increment=True)
        self.assertIn("CellIncrementN(nValue,'Sales',v1,v2)", process.data_procedure)

    def test_allow_spread_emits_proportional_spread(self):
        process = self._build("PARQUET", value_is_numeric=True, allow_spread=True)
        self.assertIn("CellPutProportionalSpread(nValue,'Sales',v1,v2)", process.data_procedure)

    def test_skip_non_updateable_wraps_in_cell_is_updateable(self):
        process = self._build("PARQUET", value_is_numeric=True, skip_non_updateable=True)
        self.assertIn("CellIsUpdateable('Sales',v1,v2)", process.data_procedure)
        self.assertIn("ItemSkip", process.data_procedure)

    def test_clear_view_adds_viewzeroout_to_prolog(self):
        process = self._build("PARQUET", value_is_numeric=True, clear_view="ToClear")
        self.assertIn("ViewZeroOut('Sales', 'ToClear')", process.prolog_procedure)

    def test_attribute_cube_forces_cellputn_even_with_increment(self):
        process = self._build(
            "PARQUET",
            value_is_numeric=True,
            cube_name="}ElementAttributes_Region",
            dimensions=["Region", "}ElementAttributes_Region"],
            increment=True,
        )
        self.assertIn("CellPutN(nValue,", process.data_procedure)
        self.assertNotIn("CellIncrementN", process.data_procedure)


if __name__ == "__main__":
    unittest.main()
