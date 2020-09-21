import configparser
import unittest
import uuid
from pathlib import Path

from TM1py.Objects import Cube, Dimension, Hierarchy, Process
from TM1py.Services import TM1Service
from TM1py.Utils import TIObfuscator

PREFIX = "TM1py_Tests_Utils_"

MDX_TEMPLATE = """
SELECT 
{rows} ON ROWS,
{columns} ON COLUMNS
FROM {cube}
WHERE {where}
"""

MDX_TEMPLATE_SHORT = """
SELECT 
{rows} ON ROWS,
{columns} ON COLUMNS
FROM {cube}
"""


class TestTIObfuscatorMethods(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """
        Establishes a connection to TM1 and creates TM1 objects to use across all tests
        """

        # Connection to TM1
        cls.config = configparser.ConfigParser()
        cls.config.read(Path(__file__).parent.joinpath("config.ini"))
        cls.tm1 = TM1Service(**cls.config["tm1srv01"])

        # Namings
        cls.expand_process_name = str(uuid.uuid4())
        cls.expand_process_name_obf = str(uuid.uuid4())
        cls.process_name = str(uuid.uuid4())
        cls.process_name_obf = str(uuid.uuid4())
        cls.dimension_name = str(uuid.uuid4())
        cls.dimension_name_cloned = str(uuid.uuid4())
        cls.cube_name = str(uuid.uuid4())
        cls.cube_name_cloned = str(uuid.uuid4())

        # create process
        prolog = "\r\nSaveDataAll;\r\nsText='abcABC';\r\n"
        epilog = "SaveDataAll;"
        cls.process = Process(
            name=cls.process_name, prolog_procedure=prolog, epilog_procedure=epilog
        )
        # create process with expand in TM1
        if cls.tm1.processes.exists(cls.process.name):
            cls.tm1.processes.delete(cls.process.name)
        cls.tm1.processes.create(cls.process)

        # create process with expand
        prolog = (
            "\r\nnRevenue = 20;\r\nsRevenue = EXPAND('%nrevenue%');\r\nIF(sRevenue @ <> '20.000');\r\n"
            "ProcessBreak;\r\nENDIF;"
        )
        cls.expand_process = Process(
            name=cls.expand_process_name, prolog_procedure=prolog
        )
        # create process with expand in TM1
        if cls.tm1.processes.exists(cls.expand_process.name):
            cls.tm1.processes.delete(cls.expand_process.name)
        cls.tm1.processes.create(cls.expand_process)

        # create dimension that we clone through obfuscated bedrock as part of the test
        if not cls.tm1.dimensions.exists(cls.dimension_name):
            d = Dimension(cls.dimension_name)
            h = Hierarchy(cls.dimension_name, cls.dimension_name)
            h.add_element("Total Years", "Consolidated")
            h.add_element("No Year", "Numeric")
            for year in range(1989, 2040, 1):
                h.add_element(str(year), "Numeric")
                h.add_edge("Total Years", str(year), 1)
            d.add_hierarchy(h)
            cls.tm1.dimensions.create(d)

            # Create 2 Attributes through TI
            ti_statements = [
                "AttrInsert('{}','','Previous Year', 'S')".format(cls.dimension_name),
                "AttrInsert('{}','','Next Year', 'S');".format(cls.dimension_name),
            ]
            ti = ";".join(ti_statements)
            cls.tm1.processes.execute_ti_code(lines_prolog=ti)

        # create }ElementAttribute values
        cellset = {}
        for year in range(1989, 2040, 1):
            cellset[(str(year), "Previous Year")] = year - 1
            cellset[(str(year), "Next Year")] = year + 1
        cls.tm1.cubes.cells.write_values(
            "}ElementAttributes_" + cls.dimension_name, cellset
        )

        # create a simple cube to be cloned through bedrock
        if not cls.tm1.cubes.exists(cls.cube_name):
            cube = Cube(cls.cube_name, ["}Dimensions", "}Cubes"], "[]=S:'TM1py';")
            cls.tm1.cubes.create(cube)

        # create bedrocks if they doesn't exist
        for bedrock in ("Bedrock.Dim.Clone", "Bedrock.Cube.Clone"):
            if not cls.tm1.processes.exists(bedrock):
                with open(
                    Path(__file__).parent.joinpath("resources", bedrock + ".json"), "r"
                ) as file:
                    process = Process.from_json(file.read())
                    cls.tm1.processes.create(process)

    def test_split_into_statements(self):
        code = (
            "sText1 = 'abcdefgh';\r\n"
            " nElem = 2;\r\n"
            " # dasjd; dasjdas '' qdawdas\r\n"
            "# daskldlaskjdla aksdlas;das \r\n"
            "    # dasdwad\r\n"
            "sText2 = 'dasjnd;jkas''dasdas'';dasdas';\r\n"
            "SaveDataAll;"
        )
        code = TIObfuscator.remove_comment_lines(code)
        statements = TIObfuscator.split_into_statements(code)
        self.assertEqual(len(statements), 4)

    def test_expand(self):
        if self.tm1.processes.exists(self.expand_process_name_obf):
            self.tm1.processes.delete(self.expand_process_name_obf)
        process = self.tm1.processes.get(self.expand_process_name)
        process_obf = TIObfuscator.obfuscate_process(
            process, self.expand_process_name_obf
        )
        self.tm1.processes.create(process_obf)
        self.tm1.processes.execute(process_obf.name, {})

    def test_remove_generated_code(self):
        code = (
            "#****Begin: Generated Statements***\r\n"
            "DIMENSIONELEMENTINSERT('Employee','',V1,'s');\r\n"
            "DIMENSIONELEMENTINSERT('Employee','',V2,'s');\r\n"
            "DIMENSIONELEMENTINSERT('Employee','',V3,'s');\r\n"
            "DIMENSIONELEMENTINSERT('Employee','',V4,'s');\r\n"
            "#****End: Generated Statements****\r\n"
            "\r\n"
            "sText = 'test';"
        )

        code = TIObfuscator.remove_generated_code(code)
        self.assertNotIn("#****Begin", code)
        self.assertNotIn("DIMENSIONELEMENTINSERT", code)
        self.assertNotIn("#****End", code)
        self.assertIn("sText = 'test';", code)

    def test_obfuscate_code(self):
        if self.tm1.processes.exists(self.process_name_obf):
            self.tm1.processes.delete(self.process_name_obf)
        process_obf = TIObfuscator.obfuscate_process(
            self.process, self.process_name_obf
        )
        self.tm1.processes.create(process_obf)

    def test_bedrock_clone_dim(self):
        if self.tm1.processes.exists("Bedrock.Dim.Clone.Obf"):
            self.tm1.processes.delete("Bedrock.Dim.Clone.Obf")

        p = self.tm1.processes.get("Bedrock.Dim.Clone")
        p_obf = TIObfuscator.obfuscate_process(
            process=p, new_name="Bedrock.Dim.Clone.Obf"
        )
        self.tm1.processes.create(p_obf)
        # call obfuscated process
        parameters = {
            "Parameters": [
                {"Name": "pSourceDim", "Value": self.dimension_name},
                {"Name": "pTargetDim", "Value": self.dimension_name_cloned},
                {"Name": "pAttr", "Value": "1"},
            ]
        }
        self.tm1.processes.execute("Bedrock.Dim.Clone.Obf", parameters)

    def test_bedrock_clone_cube(self):
        if self.tm1.processes.exists("Bedrock.Cube.Clone.Obf"):
            self.tm1.processes.delete("Bedrock.Cube.Clone.Obf")

        p = self.tm1.processes.get("Bedrock.Cube.Clone")
        p_obf = TIObfuscator.obfuscate_process(
            process=p, new_name="Bedrock.Cube.Clone.Obf"
        )
        self.tm1.processes.create(p_obf)
        # call obfuscated process
        parameters = {
            "Parameters": [
                {"Name": "pSourceCube", "Value": self.cube_name},
                {"Name": "pTargetCube", "Value": self.cube_name_cloned},
                {"Name": "pIncludeRules", "Value": "1"},
                {"Name": "pIncludeData", "Value": "1"},
                {"Name": "pDebug", "Value": "1"},
            ]
        }
        self.tm1.processes.execute("Bedrock.Cube.Clone.Obf", parameters)

    @classmethod
    def tearDownClass(cls):
        # delete all the stuff
        if cls.tm1.processes.exists(cls.expand_process_name):
            cls.tm1.processes.delete(cls.expand_process_name)
        if cls.tm1.processes.exists(cls.expand_process_name_obf):
            cls.tm1.processes.delete(cls.expand_process_name_obf)

        if cls.tm1.processes.exists(cls.process_name):
            cls.tm1.processes.delete(cls.process_name)
        if cls.tm1.processes.exists(cls.process_name_obf):
            cls.tm1.processes.delete(cls.process_name_obf)

        if cls.tm1.processes.exists("Bedrock.Dim.Clone.Obf"):
            cls.tm1.processes.delete("Bedrock.Dim.Clone.Obf")
        if cls.tm1.processes.exists("Bedrock.Cube.Clone.Obf"):
            cls.tm1.processes.delete("Bedrock.Cube.Clone.Obf")

        if cls.tm1.dimensions.exists(cls.dimension_name):
            cls.tm1.dimensions.delete(cls.dimension_name)
        if cls.tm1.dimensions.exists(cls.dimension_name_cloned):
            cls.tm1.dimensions.delete(cls.dimension_name_cloned)

        if cls.tm1.cubes.exists(cls.cube_name):
            cls.tm1.cubes.delete(cls.cube_name)
        if cls.tm1.cubes.exists(cls.cube_name_cloned):
            cls.tm1.cubes.delete(cls.cube_name_cloned)

        cls.tm1.logout()


if __name__ == "__main__":
    unittest.main()
