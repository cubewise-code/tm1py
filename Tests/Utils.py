import configparser
import json
import unittest
import uuid
import functools
from pathlib import Path

from TM1py import Subset
from TM1py.Objects import Process, Dimension, Hierarchy, Cube
from TM1py.Services import TM1Service
from TM1py.Utils import TIObfuscator, format_url
from TM1py.Utils import Utils, MDXUtils
from TM1py.Utils.MDXUtils import DimensionSelection, read_dimension_composition_from_mdx, \
    read_dimension_composition_from_mdx_set_or_tuple, read_dimension_composition_from_mdx_set, \
    read_dimension_composition_from_mdx_tuple, split_mdx, _find_case_and_space_insensitive_first_occurrence
from TM1py.Utils.Utils import dimension_hierarchy_element_tuple_from_unique_name, get_dimensions_from_where_clause, \
    integerize_version, verify_version

from .TestUtils import skip_if_no_pandas

try:
    import pandas as pd
except ImportError:
    pass


class TestUtilsMethods(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """
        Establishes a connection to TM1 and creates a dimensions and a cube to use across all tests
        """

        # Connection to TM1
        cls.config = configparser.ConfigParser()
        cls.config.read(Path(__file__).parent.joinpath('config.ini'))
        cls.tm1 = TM1Service(**cls.config['tm1srv01'])


    def test_get_instances_from_adminhost(self):
        servers = Utils.get_all_servers_from_adminhost(self.config['tm1srv01']['address'])
        self.assertGreater(len(servers), 0)


    @classmethod
    def tearDownClass(cls):
        cls.tm1.logout()


if __name__ == '__main__':
    unittest.main()
