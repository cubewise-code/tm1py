import unittest
import uuid
import random

from TM1py.Objects import Process
from TM1py.Objects import Subset
from TM1py.Services import TM1Service

from .config import test_config


process_prefix = '}TM1py_unittest'


class TestProcessMethods(unittest.TestCase):
    tm1 = TM1Service(**test_config)

    random_string = str(uuid.uuid4())

    all_dimension_names = tm1.dimensions.get_all_names()
    random_dimension = tm1.dimensions.get(random.choice(all_dimension_names))
    random_dimension_all_elements = random_dimension.default_hierarchy.elements
    random_dimension_elements = [element for element in random_dimension_all_elements][0:2]

    # None process
    p_none = Process(name=process_prefix + '_none_' + random_string,
                     datasource_type='None')

    # ACII process
    p_ascii = Process(name=process_prefix + '_ascii_' + random_string,
                      datasource_type='ASCII',
                      datasource_ascii_delimiter_type='Character',
                      datasource_ascii_delimiter_char=',',
                      datasource_ascii_header_records=2,
                      datasource_ascii_quote_character='^',
                      datasource_ascii_thousand_separator='~',
                      prolog_procedure="sTestProlog = 'test prolog procedure'",
                      metadata_procedure="sTestMeta = 'test metadata procedure'",
                      data_procedure="sTestData =  'test data procedure'",
                      epilog_procedure="sTestEpilog = 'test epilog procedure'",
                      datasource_data_source_name_for_server=r'C:\Data\file.csv',
                      datasource_data_source_name_for_client=r'C:\Data\file.csv')
    # Variables
    p_ascii.add_variable('v_1', 'Numeric')
    p_ascii.add_variable('v_2', 'Numeric')
    p_ascii.add_variable('v_3', 'Numeric')
    p_ascii.add_variable('v_4', 'Numeric')
    # Parameters
    p_ascii.add_parameter('p_Year', 'year?', '2016')

    # View process
    p_view = Process(name=process_prefix + '_view_' + random_string,
                     datasource_type='TM1CubeView',
                     datasource_view='view1',
                     datasource_data_source_name_for_client='Plan_BudgetPlan',
                     datasource_data_source_name_for_server='Plan_BudgetPlan')

    # ODBC process
    p_odbc = Process(name=process_prefix + '_odbc_' + random_string,
                     datasource_type='ODBC',
                     datasource_password='password',
                     datasource_user_name='user')

    # Subset process
    subset_name = process_prefix + '_subset_' + random_string
    subset = Subset(dimension_name=random_dimension.name,
                    subset_name=subset_name,
                    elements=random_dimension_elements)
    tm1.dimensions.subsets.create(subset, False)
    p_subset = Process(name=process_prefix + '_subset_' + random_string,
                       datasource_type='TM1DimensionSubset',
                       datasource_data_source_name_for_server=subset.dimension_name,
                       datasource_subset=subset.name,
                       metadata_procedure="sTest = 'abc';")

    # Create Process
    def test1_create_process(self):
        self.tm1.processes.create(self.p_none)
        self.tm1.processes.create(self.p_ascii)
        self.tm1.processes.create(self.p_view)
        self.tm1.processes.create(self.p_odbc)
        self.tm1.processes.create(self.p_subset)

    # Get Process
    def test2_get_process(self):
        p1 = self.tm1.processes.get(self.p_ascii.name)
        self.assertEqual(p1.body, self.p_ascii.body)
        p2 = self.tm1.processes.get(self.p_none.name)
        self.assertEqual(p2.body, self.p_none.body)
        p3 = self.tm1.processes.get(self.p_view.name)
        self.assertEqual(p3.body, self.p_view.body)
        p4 = self.tm1.processes.get(self.p_odbc.name)
        p4.datasource_password = None
        self.p_odbc.datasource_password = None
        self.assertEqual(p4.body, self.p_odbc.body)
        p5 = self.tm1.processes.get(self.p_subset.name)
        self.assertEqual(p5.body, self.p_subset.body)

    # Update process
    def test3_update_process(self):
        # get
        p = self.tm1.processes.get(self.p_ascii.name)
        # modify
        p.data_procedure = "SaveDataAll;"
        # update on Server
        self.tm1.processes.update(p)
        # get again
        p_ascii_updated = self.tm1.processes.get(p.name)
        # assert
        self.assertNotEqual(p_ascii_updated.data_procedure, self.p_ascii.data_procedure)

    # Delete process
    def test4_delete_process(self):
        self.tm1.processes.delete(self.p_none.name)
        self.tm1.processes.delete(self.p_ascii.name)
        self.tm1.processes.delete(self.p_view.name)
        self.tm1.processes.delete(self.p_odbc.name)
        self.tm1.processes.delete(self.p_subset.name)
        self.tm1.dimensions.subsets.delete(dimension_name=self.subset.dimension_name,
                                           subset_name=self.subset_name, private=False)

    def test5_logout(self):
        self.tm1.logout()


if __name__ == '__main__':
    unittest.main()
