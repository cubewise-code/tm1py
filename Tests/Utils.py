import configparser
import unittest
from pathlib import Path

from TM1py.Services import TM1Service
from TM1py.Utils import Utils
from TM1py.Utils import integerize_version, verify_version, get_dimensions_from_where_clause

class TestUtilsMethods(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """
        Establishes a connection to TM1 and creates TM1 objects to use across all tests
        """

        # Connection to TM1
        cls.config = configparser.ConfigParser()
        cls.config.read(Path(__file__).parent.joinpath('config.ini'))
        cls.tm1 = TM1Service(**cls.config['tm1srv01'])


    def test_get_instances_from_adminhost(self):
        servers = Utils.get_all_servers_from_adminhost(self.config['tm1srv01']['address'])
        self.assertGreater(len(servers), 0)

    def test_integerize_version(self):
        version = "11.0.00000.918"
        integerized_version = integerize_version(version)
        self.assertEqual(110, integerized_version)

        version = "11.0.00100.927-0"
        integerized_version = integerize_version(version)
        self.assertEqual(110, integerized_version)

        version = "11.1.00004.2"
        integerized_version = integerize_version(version)
        self.assertEqual(111, integerized_version)

        version = "11.2.00000.27"
        integerized_version = integerize_version(version)
        self.assertEqual(112, integerized_version)

        version = "11.3.00003.1"
        integerized_version = integerize_version(version)
        self.assertEqual(113, integerized_version)

        version = "11.4.00003.8"
        integerized_version = integerize_version(version)
        self.assertEqual(114, integerized_version)

        version = "11.7.00002.1"
        integerized_version = integerize_version(version)
        self.assertEqual(117, integerized_version)

        version = "11.8.00000.33"
        integerized_version = integerize_version(version)
        self.assertEqual(118, integerized_version)

    def test_verify_version_true(self):
        required_version = "11.7.00002.1"
        version = "11.8.00000.33"

        result = verify_version(required_version=required_version, version=version)
        self.assertEqual(True, result)

    def test_verify_version_false(self):
        required_version = "11.7.00002.1"
        version = "11.2.00000.27"

        result = verify_version(required_version=required_version, version=version)
        self.assertEqual(False, result)

    def test_verify_version_equal(self):
        required_version = "11.7.00002.1"
        version = "11.7.00002.1"

        result = verify_version(required_version=required_version, version=version)
        self.assertEqual(True, result)

    def test_get_dimensions_from_where_clause_happy_case(self):
        mdx = """
        SELECT {[dim3].[e2]} COLUMNS, {[dim4].[e5]} ON ROWS FROM [cube] WHERE ([dim2].[e1], [dim1].[e4])
        """
        dimensions = get_dimensions_from_where_clause(mdx)
        self.assertEqual(["DIM2", "DIM1"], dimensions)

    def test_get_dimensions_from_where_clause_no_where(self):
        mdx = """
        SELECT {[dim3].[e2]} COLUMNS, {[dim4].[e5]} ON ROWS FROM [cube]
        """
        dimensions = get_dimensions_from_where_clause(mdx)
        self.assertEqual([], dimensions)

    def test_get_dimensions_from_where_clause_casing(self):
        mdx = """
        SELECT {[dim3].[e2]} COLUMNS, {[dim4].[e5]} ON ROWS FROM [cube] WhEre ([dim1].[e4])
        """
        dimensions = get_dimensions_from_where_clause(mdx)
        self.assertEqual(["DIM1"], dimensions)

    def test_get_dimensions_from_where_clause_spacing(self):
        mdx = """
        SELECT {[dim3].[e2]} COLUMNS, {[dim4].[e5]} ON ROWS FROM [cube] WHERE([dim5]. [e4] )
        """
        dimensions = get_dimensions_from_where_clause(mdx)
        self.assertEqual(["DIM5"], dimensions)




    @classmethod
    def tearDownClass(cls):
        cls.tm1.logout()


if __name__ == '__main__':
    unittest.main()
