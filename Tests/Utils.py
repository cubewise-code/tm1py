import configparser
import os
import unittest
import uuid

import pandas as pd

from TM1py import Subset
from TM1py.Objects import Process, Dimension, Hierarchy, Cube
from TM1py.Services import TM1Service
from TM1py.Utils import TIObfuscator
from TM1py.Utils import Utils, MDXUtils
from TM1py.Utils.MDXUtils import DimensionSelection

config = configparser.ConfigParser()
config.read(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'config.ini'))


class TestMDXUtils(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Connect to TM1
        cls.tm1 = TM1Service(**config['tm1srv01'])

        # Build 4 Dimensions
        cls.dim1_name = str(uuid.uuid4())
        cls.dim1_element_names = [str(uuid.uuid4()) for _ in range(10)]
        d = Dimension(cls.dim1_name)
        h = Hierarchy(cls.dim1_name, cls.dim1_name)
        for element_name in cls.dim1_element_names:
            h.add_element(element_name, 'Numeric')
        d.add_hierarchy(h)
        cls.tm1.dimensions.create(d)

        cls.dim2_name = str(uuid.uuid4())
        cls.dim2_element_names = [str(uuid.uuid4()) for _ in range(10)]
        d = Dimension(cls.dim2_name)
        h = Hierarchy(cls.dim2_name, cls.dim2_name)
        for element_name in cls.dim2_element_names:
            h.add_element(element_name, 'Numeric')
        d.add_hierarchy(h)
        cls.tm1.dimensions.create(d)

        cls.dim3_name = str(uuid.uuid4())
        cls.dim3_element_names = [str(uuid.uuid4()) for _ in range(10)]
        d = Dimension(cls.dim3_name)
        h = Hierarchy(cls.dim3_name, cls.dim3_name)
        for element_name in cls.dim3_element_names:
            h.add_element(element_name, 'Numeric')
        d.add_hierarchy(h)
        cls.tm1.dimensions.create(d)

        cls.dim4_name = str(uuid.uuid4())
        cls.dim4_element_names = [str(uuid.uuid4()) for _ in range(10)]
        d = Dimension(cls.dim4_name)
        h = Hierarchy(cls.dim4_name, cls.dim4_name)
        for element_name in cls.dim4_element_names:
            h.add_element(element_name, 'Numeric')
        d.add_hierarchy(h)
        cls.tm1.dimensions.create(d)

        # Build Subset
        cls.dim4_subset_Name = "TM1pyTests"
        cls.dim4_subset = cls.tm1.dimensions.subsets.create(Subset(
            subset_name=cls.dim4_subset_Name,
            dimension_name=cls.dim4_name,
            hierarchy_name=cls.dim4_name,
            expression="HEAD([{}].Members, 1)".format(cls.dim4_name)))

        # Build Cube with 4 Dimensions
        cls.cube_name = str(uuid.uuid4())
        cube = Cube(name=cls.cube_name,
                    dimensions=[cls.dim1_name, cls.dim2_name, cls.dim3_name, cls.dim4_name])
        cls.tm1.cubes.create(cube)

    def test_construct_mdx(self):
        rows = [DimensionSelection(dimension_name=self.dim1_name),
                DimensionSelection(dimension_name=self.dim2_name, elements=self.dim2_element_names)]
        columns = [DimensionSelection(
            dimension_name=self.dim3_name,
            expression="TM1SubsetAll([{}])".format(self.dim3_name))]
        contexts = {self.dim4_name: self.dim4_element_names[0]}
        mdx = MDXUtils.construct_mdx(
            cube_name=self.cube_name,
            rows=rows,
            columns=columns,
            contexts=contexts,
            suppress=None)
        content = self.tm1.cubes.cells.execute_mdx(mdx)
        number_cells = len(content.keys())
        self.assertEqual(number_cells, 1000)

    def test_construct_mdx_no_titles(self):
        rows = [DimensionSelection(dimension_name=self.dim1_name),
                DimensionSelection(dimension_name=self.dim2_name, elements=self.dim2_element_names)]
        columns = [
            DimensionSelection(
                dimension_name=self.dim3_name,
                expression="TM1SubsetAll([{}])".format(self.dim3_name)),
            DimensionSelection(
                dimension_name=self.dim4_name,
                subset=self.dim4_subset_Name)]
        mdx = MDXUtils.construct_mdx(
            cube_name=self.cube_name,
            rows=rows,
            columns=columns,
            suppress=None)
        content = self.tm1.cubes.cells.execute_mdx(mdx)
        number_cells = len(content.keys())
        self.assertEqual(number_cells, 1000)

    def test_construct_mdx_suppress_zeroes(self):
        rows = [DimensionSelection(dimension_name=self.dim1_name),
                DimensionSelection(dimension_name=self.dim2_name, elements=self.dim2_element_names)]
        columns = [
            DimensionSelection(
                dimension_name=self.dim3_name,
                expression="TM1SubsetAll([{}])".format(self.dim3_name)),
            DimensionSelection(
                dimension_name=self.dim4_name,
                subset=self.dim4_subset_Name)]
        mdx = MDXUtils.construct_mdx(
            cube_name=self.cube_name,
            rows=rows,
            columns=columns,
            suppress="BOTH")
        content = self.tm1.cubes.cells.execute_mdx(mdx)
        number_cells = len(content.keys())
        self.assertLess(number_cells, 1000)

    def test_determine_selection_type(self):
        self.assertEqual(
            DimensionSelection.determine_selection_type(elements=["e1", "e2"], subset=None, expression=None),
            DimensionSelection.ITERABLE)
        self.assertEqual(
            DimensionSelection.determine_selection_type(["e1", "e2"]),
            DimensionSelection.ITERABLE)
        self.assertEqual(
            DimensionSelection.determine_selection_type(elements=None, subset="something", expression=None),
            DimensionSelection.SUBSET)
        self.assertEqual(
            DimensionSelection.determine_selection_type(None, "something", None),
            DimensionSelection.SUBSET)
        self.assertEqual(
            DimensionSelection.determine_selection_type(elements=None, subset=None, expression="{[d1].[e1]}"),
            DimensionSelection.EXPRESSION)
        self.assertEqual(
            DimensionSelection.determine_selection_type(None, None, "{[d1].[e1]}"),
            DimensionSelection.EXPRESSION)
        self.assertEqual(
            DimensionSelection.determine_selection_type(elements=None, subset=None, expression=None),
            None)
        self.assertEqual(
            DimensionSelection.determine_selection_type(None, None, None),
            None)
        self.assertEqual(
            DimensionSelection.determine_selection_type(),
            None)
        self.assertRaises(
            ValueError,
            DimensionSelection.determine_selection_type, ["e2"], "subset1", "{[d1].[e1]}")
        self.assertRaises(
            ValueError,
            DimensionSelection.determine_selection_type, ["e2"], "subset1")
        self.assertRaises(
            ValueError,
            DimensionSelection.determine_selection_type, ["e2"], None, "subset1")

    def test_curly_braces(self):
        self.assertEqual(
            MDXUtils.curly_braces("something"),
            "{something}")
        self.assertEqual(
            MDXUtils.curly_braces("something}"),
            "{something}")
        self.assertEqual(
            MDXUtils.curly_braces("{something"),
            "{something}")
        self.assertEqual(
            MDXUtils.curly_braces("{something}"),
            "{something}")

    def test_build_pandas_dataframe_from_cellset(self):
        rows = [DimensionSelection(dimension_name=self.dim1_name),
                DimensionSelection(dimension_name=self.dim2_name, elements=self.dim2_element_names)]
        columns = [
            DimensionSelection(
                dimension_name=self.dim3_name,
                expression="TM1SubsetAll([{}])".format(self.dim3_name)),
            DimensionSelection(
                dimension_name=self.dim4_name,
                subset=self.dim4_subset_Name)]
        suppress = None
        mdx = MDXUtils.construct_mdx(
            cube_name=self.cube_name,
            rows=rows,
            columns=columns,
            suppress=suppress)
        cellset = self.tm1.cubes.cells.execute_mdx(mdx)
        df = Utils.build_pandas_dataframe_from_cellset(cellset, multiindex=True)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertTrue(df.shape[0] == 1000)
        self.assertTrue(df.shape[1] == 1)
        cellset = Utils.build_cellset_from_pandas_dataframe(df)
        self.assertTrue(len(cellset.keys()) == 1000)
        self.assertIsInstance(cellset, Utils.CaseAndSpaceInsensitiveTuplesDict)

        df = Utils.build_pandas_dataframe_from_cellset(cellset, multiindex=False)
        self.assertTrue(df.shape[0] == 1000)
        self.assertTrue(df.shape[1] == 5)
        self.assertIsInstance(df, pd.DataFrame)
        cellset = Utils.build_cellset_from_pandas_dataframe(df)
        self.assertTrue(len(cellset.keys()) == 1000)
        self.assertIsInstance(cellset, Utils.CaseAndSpaceInsensitiveTuplesDict)

    def test_build_pandas_dataframe_empty_cellset(self):
        self.tm1.cubes.cells.write_value(
            value=0,
            cube_name=self.cube_name,
            element_tuple=(self.dim1_element_names[0], self.dim2_element_names[0],
                           self.dim3_element_names[0], self.dim4_element_names[0]),
            dimensions=(self.dim1_name, self.dim2_name, self.dim3_name, self.dim4_name))
        rows = [DimensionSelection(dimension_name=self.dim1_name, elements=(self.dim1_element_names[0],)),
                DimensionSelection(dimension_name=self.dim2_name, elements=(self.dim2_element_names[0],))]
        columns = [DimensionSelection(dimension_name=self.dim3_name, elements=(self.dim3_element_names[0],)),
                   DimensionSelection(dimension_name=self.dim4_name, elements=(self.dim4_element_names[0],))]
        suppress = "Both"
        mdx = MDXUtils.construct_mdx(
            cube_name=self.cube_name,
            rows=rows,
            columns=columns,
            suppress=suppress)
        empty_cellset = self.tm1.cubes.cells.execute_mdx(mdx)
        self.assertRaises(ValueError, Utils.build_pandas_dataframe_from_cellset, empty_cellset, True)
        self.assertRaises(ValueError, Utils.build_pandas_dataframe_from_cellset, empty_cellset, False)

    def test_read_cube_name_from_mdx(self):
        all_cube_names = self.tm1.cubes.get_all_names()
        for cube_name in all_cube_names:
            private_views, public_views = self.tm1.cubes.views.get_all(cube_name)
            for view in private_views + public_views:
                mdx = view.MDX
                self.assertEquals(
                    cube_name.upper().replace(" ", ""),
                    MDXUtils.read_cube_name_from_mdx(mdx))

    @classmethod
    def tearDownClass(cls):
        cls.tm1.cubes.delete(cls.cube_name)
        cls.tm1.dimensions.delete(cls.dim1_name)
        cls.tm1.dimensions.delete(cls.dim2_name)
        cls.tm1.dimensions.delete(cls.dim3_name)
        cls.tm1.dimensions.delete(cls.dim4_name)


class TestTIObfuscatorMethods(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Namings
        cls.expand_process_name = str(uuid.uuid4())
        cls.expand_process_name_obf = str(uuid.uuid4())
        cls.process_name = str(uuid.uuid4())
        cls.process_name_obf = str(uuid.uuid4())
        cls.dimension_name = str(uuid.uuid4())
        cls.dimension_name_cloned = str(uuid.uuid4())
        cls.cube_name = str(uuid.uuid4())
        cls.cube_name_cloned = str(uuid.uuid4())

        # Connect to TM1
        cls.tm1 = TM1Service(**config['tm1srv01'])

        # create process
        prolog = "\r\nSaveDataAll;\r\nsText='abcABC';\r\n"
        epilog = "SaveDataAll;"
        cls.process = Process(
            name=cls.process_name,
            prolog_procedure=prolog,
            epilog_procedure=epilog)
        # create process with expand in TM1
        if cls.tm1.processes.exists(cls.process.name):
            cls.tm1.processes.delete(cls.process.name)
        cls.tm1.processes.create(cls.process)

        # create process with expand
        prolog = "\r\nnRevenue = 20;\r\nsRevenue = EXPAND('%nrevenue%');\r\nIF(sRevenue @ <> '20.000');\r\n" \
                 "ProcessBreak;\r\nENDIF;"
        cls.expand_process = Process(
            name=cls.expand_process_name,
            prolog_procedure=prolog)
        # create process with expand in TM1
        if cls.tm1.processes.exists(cls.expand_process.name):
            cls.tm1.processes.delete(cls.expand_process.name)
        cls.tm1.processes.create(cls.expand_process)

        # create dimension that we clone through obfuscated bedrock as part of the test
        if not cls.tm1.dimensions.exists(cls.dimension_name):
            d = Dimension(cls.dimension_name)
            h = Hierarchy(cls.dimension_name, cls.dimension_name)
            h.add_element('Total Years', 'Consolidated')
            h.add_element('No Year', 'Numeric')
            for year in range(1989, 2040, 1):
                h.add_element(str(year), 'Numeric')
                h.add_edge('Total Years', str(year), 1)
            d.add_hierarchy(h)
            cls.tm1.dimensions.create(d)

            # Create 2 Attributes through TI
            ti_statements = ["AttrInsert('{}','','Previous Year', 'S')".format(cls.dimension_name),
                             "AttrInsert('{}','','Next Year', 'S');".format(cls.dimension_name)]
            ti = ';'.join(ti_statements)
            cls.tm1.processes.execute_ti_code(lines_prolog=ti)

        # create }ElementAttribute values
        cellset = {}
        for year in range(1989, 2040, 1):
            cellset[(str(year), 'Previous Year')] = year - 1
            cellset[(str(year), 'Next Year')] = year + 1
        cls.tm1.cubes.cells.write_values("}ElementAttributes_" + cls.dimension_name, cellset)

        # create a simple cube to be cloned through bedrock
        if not cls.tm1.cubes.exists(cls.cube_name):
            cube = Cube(cls.cube_name, ["}Dimensions", "}Cubes"], "[]=S:'TM1py';")
            cls.tm1.cubes.create(cube)

        # create bedrocks if they doesn't exist
        for bedrock in ("Bedrock.Dim.Clone", "Bedrock.Cube.Clone"):
            if not cls.tm1.processes.exists(bedrock):
                with open(r"resources\\" + bedrock + ".json", "r") as file:
                    process = Process.from_json(file.read())
                    cls.tm1.processes.create(process)

    def test_split_into_statements(self):
        code = "sText1 = 'abcdefgh';\r\n" \
               " nElem = 2;\r\n" \
               " # dasjd; dasjdas '' qdawdas\r\n" \
               "# daskldlaskjdla aksdlas;das \r\n" \
               "    # dasdwad\r\n" \
               "sText2 = 'dasjnd;jkas''dasdas'';dasdas';\r\n" \
               "SaveDataAll;"
        code = TIObfuscator.remove_comment_lines(code)
        statements = TIObfuscator.split_into_statements(code)
        self.assertEqual(len(statements), 4)

    def test_expand(self):
        if self.tm1.processes.exists(self.expand_process_name_obf):
            self.tm1.processes.delete(self.expand_process_name_obf)
        process = self.tm1.processes.get(self.expand_process_name)
        process_obf = TIObfuscator.obfuscate_process(process, self.expand_process_name_obf)
        self.tm1.processes.create(process_obf)
        self.tm1.processes.execute(process_obf.name, {})

    def test_remove_generated_code(self):
        code = "#****Begin: Generated Statements***\r\n" \
               "DIMENSIONELEMENTINSERT('Employee','',V1,'s');\r\n" \
               "DIMENSIONELEMENTINSERT('Employee','',V2,'s');\r\n" \
               "DIMENSIONELEMENTINSERT('Employee','',V3,'s');\r\n" \
               "DIMENSIONELEMENTINSERT('Employee','',V4,'s');\r\n" \
               "#****End: Generated Statements****\r\n" \
               "\r\n" \
               "sText = 'test';"

        code = TIObfuscator.remove_generated_code(code)
        self.assertNotIn("#****Begin", code)
        self.assertNotIn("DIMENSIONELEMENTINSERT", code)
        self.assertNotIn("#****End", code)
        self.assertIn("sText = 'test';", code)

    def test_obfuscate_code(self):
        if self.tm1.processes.exists(self.process_name_obf):
            self.tm1.processes.delete(self.process_name_obf)
        process_obf = TIObfuscator.obfuscate_process(self.process, self.process_name_obf)
        self.tm1.processes.create(process_obf)

    def test_bedrock_clone_dim(self):
        if self.tm1.processes.exists("Bedrock.Dim.Clone.Obf"):
            self.tm1.processes.delete("Bedrock.Dim.Clone.Obf")

        p = self.tm1.processes.get("Bedrock.Dim.Clone")
        p_obf = TIObfuscator.obfuscate_process(
            process=p,
            new_name='Bedrock.Dim.Clone.Obf')
        self.tm1.processes.create(p_obf)
        # call obfuscated process
        parameters = {
            "Parameters":
                [
                    {"Name": "pSourceDim", "Value": self.dimension_name},
                    {"Name": "pTargetDim", "Value": self.dimension_name_cloned},
                    {"Name": "pAttr", "Value": "1"}
                ]
        }
        self.tm1.processes.execute("Bedrock.Dim.Clone.Obf", parameters)

    def test_bedrock_clone_cube(self):
        if self.tm1.processes.exists("Bedrock.Cube.Clone.Obf"):
            self.tm1.processes.delete("Bedrock.Cube.Clone.Obf")

        p = self.tm1.processes.get("Bedrock.Cube.Clone")
        p_obf = TIObfuscator.obfuscate_process(process=p, new_name='Bedrock.Cube.Clone.Obf')
        self.tm1.processes.create(p_obf)
        # call obfuscated process
        parameters = {
            "Parameters":
                [
                    {"Name": "pSourceCube", "Value": self.cube_name},
                    {"Name": "pTargetCube", "Value": self.cube_name_cloned},
                    {"Name": "pIncludeRules", "Value": "1"},
                    {"Name": "pIncludeData", "Value": "1"},
                    {"Name": "pDebug", "Value": "1"}
                ]
        }
        self.tm1.processes.execute("Bedrock.Cube.Clone.Obf", parameters)

    @classmethod
    def tearDownClass(cls):
        # delete all this stuff
        cls.tm1.processes.delete(cls.expand_process_name)
        cls.tm1.processes.delete(cls.expand_process_name_obf)

        cls.tm1.processes.delete(cls.process_name)
        cls.tm1.processes.delete(cls.process_name_obf)

        cls.tm1.processes.delete("Bedrock.Dim.Clone.Obf")
        cls.tm1.processes.delete("Bedrock.Cube.Clone.Obf")

        cls.tm1.dimensions.delete(cls.dimension_name)
        cls.tm1.dimensions.delete(cls.dimension_name_cloned)

        cls.tm1.cubes.delete(cls.cube_name)
        cls.tm1.cubes.delete(cls.cube_name_cloned)

        cls.tm1.logout()


if __name__ == '__main__':
    unittest.main()
