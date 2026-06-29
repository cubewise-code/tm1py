import unittest

from TM1py.Objects import BreakPointType, HitMode, Process


class TestBreakPointType(unittest.TestCase):

    def test_BreakPointType_init(self):
        break_point_type = BreakPointType("ProcessDebugContextDataBreakpoint")
        self.assertEqual(BreakPointType.PROCESS_DEBUG_CONTEXT_DATA_BREAK_POINT, break_point_type)

    def test_BreakPointType_init_case(self):
        break_point_type = BreakPointType("ProcessDebugContextDataBREAKPOINT")
        self.assertEqual(BreakPointType.PROCESS_DEBUG_CONTEXT_DATA_BREAK_POINT, break_point_type)

    def test_BreakPointType_str(self):
        break_point_type = BreakPointType.PROCESS_DEBUG_CONTEXT_DATA_BREAK_POINT
        self.assertEqual("ProcessDebugContextDataBreakpoint", str(break_point_type))


class TestHitMode(unittest.TestCase):

    def test_HitMode_init(self):
        hit_mode = HitMode("BreakAlways")
        self.assertEqual(HitMode.BREAK_ALWAYS, hit_mode)

    def test_BreakPointType_init_case(self):
        hit_mode = HitMode("BreakAlways")
        self.assertEqual(HitMode.BREAK_ALWAYS, hit_mode)

    def test_BreakPointType_str(self):
        hit_mode = HitMode.BREAK_ALWAYS
        self.assertEqual("BreakAlways", str(hit_mode))


class TestProcessDataSource(unittest.TestCase):
    """Offline unit tests for the TM1 12.6.1 columnar (ARROW/PARQUET) and Arrow Flight datasource body shapes."""

    @staticmethod
    def _process_dict(datasource: dict) -> dict:
        """Minimal Process payload wrapping a given DataSource block (for Process.from_dict)."""
        return {
            "Name": "p_test",
            "HasSecurityAccess": False,
            "Parameters": [],
            "Variables": [],
            "PrologProcedure": "",
            "MetadataProcedure": "",
            "DataProcedure": "",
            "EpilogProcedure": "",
            "DataSource": datasource,
        }

    def test_arrow_body(self):
        process = Process(
            name="p_arrow",
            datasource_type="ARROW",
            datasource_data_source_name_for_server="data.arrow",
            datasource_data_source_name_for_client="data.arrow",
        )
        datasource = process.body_as_dict["DataSource"]
        self.assertEqual(
            datasource,
            {
                "Type": "ARROW",
                "dataSourceNameForClient": "data.arrow",
                "dataSourceNameForServer": "data.arrow",
            },
        )
        # columnar files carry none of the ascii* delimiter/quote/header keys
        self.assertFalse(any(key.startswith("ascii") for key in datasource))

    def test_parquet_body(self):
        process = Process(
            name="p_parquet",
            datasource_type="PARQUET",
            datasource_data_source_name_for_server="data.parquet",
            datasource_data_source_name_for_client="data.parquet",
        )
        datasource = process.body_as_dict["DataSource"]
        self.assertEqual(
            datasource,
            {
                "Type": "PARQUET",
                "dataSourceNameForClient": "data.parquet",
                "dataSourceNameForServer": "data.parquet",
            },
        )
        self.assertFalse(any(key.startswith("ascii") for key in datasource))

    def test_arrow_body_with_json_treatment(self):
        process = Process(
            name="p_arrow_json",
            datasource_type="ARROW",
            datasource_data_source_name_for_server="data.arrow",
            datasource_data_source_name_for_client="data.arrow",
            datasource_json_root_pointer="data",
            datasource_json_variable_mapping="{}",
        )
        datasource = process.body_as_dict["DataSource"]
        self.assertEqual(datasource["jsonRootPointer"], "data")
        self.assertEqual(datasource["jsonVariableMapping"], "{}")

    def test_arrow_body_omits_empty_json_treatment(self):
        process = Process(
            name="p_arrow_plain",
            datasource_type="ARROW",
            datasource_data_source_name_for_server="data.arrow",
        )
        datasource = process.body_as_dict["DataSource"]
        self.assertNotIn("jsonRootPointer", datasource)
        self.assertNotIn("jsonVariableMapping", datasource)

    def test_flight_body(self):
        process = Process(
            name="p_flight",
            datasource_type="FLIGHT",
            datasource_flight_location="grpc+tls://host:443",
            datasource_flight_descriptor_type="COMMAND",
            datasource_flight_descriptor="SELECT * FROM t",
            datasource_flight_auth="Bearer token",
        )
        self.assertEqual(
            process.body_as_dict["DataSource"],
            {
                "Type": "FLIGHT",
                "flightLocation": "grpc+tls://host:443",
                "flightDescriptorType": "COMMAND",
                "flightDescriptor": "SELECT * FROM t",
                "flightAuth": "Bearer token",
            },
        )

    def test_arrow_roundtrip(self):
        datasource = {
            "Type": "ARROW",
            "dataSourceNameForClient": "data.arrow",
            "dataSourceNameForServer": "data.arrow",
        }
        process = Process.from_dict(self._process_dict(datasource))
        self.assertEqual(process.body_as_dict["DataSource"], datasource)

    def test_parquet_roundtrip(self):
        datasource = {
            "Type": "PARQUET",
            "dataSourceNameForClient": "data.parquet",
            "dataSourceNameForServer": "data.parquet",
        }
        process = Process.from_dict(self._process_dict(datasource))
        self.assertEqual(process.body_as_dict["DataSource"], datasource)

    def test_arrow_roundtrip_with_json_treatment(self):
        datasource = {
            "Type": "ARROW",
            "dataSourceNameForClient": "data.arrow",
            "dataSourceNameForServer": "data.arrow",
            "jsonRootPointer": "data",
            "jsonVariableMapping": "{}",
        }
        process = Process.from_dict(self._process_dict(datasource))
        self.assertEqual(process.body_as_dict["DataSource"], datasource)

    def test_flight_roundtrip(self):
        datasource = {
            "Type": "FLIGHT",
            "flightLocation": "grpc://host:8443",
            "flightDescriptorType": "PATH",
            "flightDescriptor": "dataset/path",
            "flightAuth": "Basic user:pass",
        }
        process = Process.from_dict(self._process_dict(datasource))
        self.assertEqual(process.body_as_dict["DataSource"], datasource)

    def test_arrow_from_dict_title_case_type(self):
        # The server canonicalizes Type to title-case ("Arrow") on read-back; from_dict
        # of such a response must still produce a proper Arrow body, not an empty {}.
        datasource = {
            "Type": "Arrow",
            "dataSourceNameForClient": "data.arrow",
            "dataSourceNameForServer": "data.arrow",
        }
        process = Process.from_dict(self._process_dict(datasource))
        self.assertEqual(process.body_as_dict["DataSource"], datasource)

    def test_flight_from_dict_title_case_type(self):
        # Title-case "Flight" (as returned by the server) must round-trip too.
        datasource = {
            "Type": "Flight",
            "flightLocation": "grpc://host:8443",
            "flightDescriptorType": "PATH",
            "flightDescriptor": "dataset/path",
            "flightAuth": "Basic user:pass",
        }
        process = Process.from_dict(self._process_dict(datasource))
        self.assertEqual(process.body_as_dict["DataSource"], datasource)


if __name__ == "__main__":
    unittest.main()
