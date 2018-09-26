import unittest
import uuid
import random
import time
import configparser
import os

from TM1py.Objects import Process
from TM1py.Objects import Subset
from TM1py.Services import TM1Service
from TM1py.Utils import Utils

config = configparser.ConfigParser()
config.read(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'config.ini'))


process_prefix = '}TM1py_unittest'


class TestProcessMethods(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tm1 = TM1Service(**config['tm1srv01'])

        cls.random_string = str(uuid.uuid4())

        cls.all_dimension_names = cls.tm1.dimensions.get_all_names()
        cls.random_dimension = cls.tm1.dimensions.get(random.choice(cls.all_dimension_names))
        cls.random_dimension_all_elements = cls.random_dimension.default_hierarchy.elements
        cls.random_dimension_elements = [element for element in cls.random_dimension_all_elements][0:2]

        # None process
        cls.p_none = Process(name=process_prefix + '_none_' + cls.random_string, datasource_type='None')

        # ACII process
        cls.p_ascii = Process(name=process_prefix + '_ascii_' + cls.random_string,
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
        cls.p_ascii.add_variable('v_1', 'Numeric')
        cls.p_ascii.add_variable('v_2', 'Numeric')
        cls.p_ascii.add_variable('v_3', 'Numeric')
        cls.p_ascii.add_variable('v_4', 'Numeric')
        # Parameters
        cls.p_ascii.add_parameter('p_Year', 'year?', '2016')
        cls.p_ascii.add_parameter('p_Number', 'number?', 2)

        # View process
        cls.p_view = Process(name=process_prefix + '_view_' + cls.random_string,
                             datasource_type='TM1CubeView',
                             datasource_view='view1',
                             datasource_data_source_name_for_client='Plan_BudgetPlan',
                             datasource_data_source_name_for_server='Plan_BudgetPlan')

        # ODBC process
        cls.p_odbc = Process(name=process_prefix + '_odbc_' + cls.random_string,
                             datasource_type='ODBC',
                             datasource_password='password',
                             datasource_user_name='user')

        # Subset process
        cls.subset_name = process_prefix + '_subset_' + cls.random_string
        cls.subset = Subset(dimension_name=cls.random_dimension.name,
                            subset_name=cls.subset_name,
                            elements=cls.random_dimension_elements)
        cls.tm1.dimensions.subsets.create(cls.subset, False)
        cls.p_subset = Process(name=process_prefix + '_subset_' + cls.random_string,
                               datasource_type='TM1DimensionSubset',
                               datasource_data_source_name_for_server=cls.subset.dimension_name,
                               datasource_subset=cls.subset.name,
                               metadata_procedure="sTest = 'abc';")

    # Create Process
    def test_create_process(self):
        self.tm1.processes.create(self.p_none)
        self.tm1.processes.create(self.p_ascii)
        self.tm1.processes.create(self.p_view)
        self.tm1.processes.create(self.p_odbc)
        self.tm1.processes.create(self.p_subset)

    def test_execute_process(self):
        process = Utils.load_bedrock_from_github("Bedrock.Server.Wait")
        if not self.tm1.processes.exists(process.name):
            self.tm1.processes.create(process)

        # with parameters argument
        start_time = time.time()
        self.tm1.processes.execute(process.name, parameters={"Parameters": [
            {"Name": "pWaitSec", "Value": "3"}]})
        elapsed_time = time.time() - start_time
        self.assertGreater(elapsed_time, 3)

        # with kwargs
        start_time = time.time()
        self.tm1.processes.execute(process.name, pWaitSec="1")
        elapsed_time = time.time() - start_time
        self.assertGreater(elapsed_time, 1)

        # without arguments
        self.tm1.processes.execute(process.name)

    def test_execute_with_return_success(self):
        process = Utils.load_bedrock_from_github("Bedrock.Server.Wait")
        if not self.tm1.processes.exists(process.name):
            self.tm1.processes.create(process)
        # with parameters
        success, status, error_log_file = self.tm1.processes.execute_with_return(
            process_name=process.name,
            pWaitSec=2)
        self.assertTrue(success)
        self.assertEqual(status, "CompletedSuccessfully")
        self.assertIsNone(error_log_file)
        # without parameters
        success, status, error_log_file = self.tm1.processes.execute_with_return(
            process_name=process.name)
        self.assertTrue(success)
        self.assertEqual(status, "CompletedSuccessfully")
        self.assertIsNone(error_log_file)

    def test_execute_with_return_compile_error(self):
        process = Process(name=str(uuid.uuid4()))
        process.prolog_procedure = "sText = 'text';sText = 2;"

        if not self.tm1.processes.exists(process.name):
            self.tm1.processes.create(process)
        # with parameters
        success, status, error_log_file = self.tm1.processes.execute_with_return(process_name=process.name)
        self.assertFalse(success)
        self.assertEqual(status, "Aborted")
        self.assertIsNotNone(error_log_file)

        self.tm1.processes.delete(process.name)

    def test_execute_with_return_with_item_reject(self):
        process = Process(name=str(uuid.uuid4()))
        process.epilog_procedure = "ItemReject('Not Relevant');"

        if not self.tm1.processes.exists(process.name):
            self.tm1.processes.create(process)
        # with parameters
        success, status, error_log_file = self.tm1.processes.execute_with_return(process_name=process.name)
        self.assertFalse(success)
        self.assertEqual(status, "CompletedWithMessages")
        self.assertIsNotNone(error_log_file)

        self.tm1.processes.delete(process.name)

    def test_execute_with_return_with_process_break(self):
        process = Process(name=str(uuid.uuid4()))
        process.prolog_procedure = "sText = 'Something'; ProcessBreak;"

        if not self.tm1.processes.exists(process.name):
            self.tm1.processes.create(process)
        # with parameters
        success, status, error_log_file = self.tm1.processes.execute_with_return(
            process_name=process.name)
        self.assertTrue(success)
        self.assertEqual(status, "CompletedSuccessfully")
        self.assertIsNone(error_log_file)

        self.tm1.processes.delete(process.name)

    def test_execute_with_return_with_process_quit(self):
        process = Process(name=str(uuid.uuid4()))
        process.prolog_procedure = "sText = 'Something'; ProcessQuit;"

        if not self.tm1.processes.exists(process.name):
            self.tm1.processes.create(process)
        # with parameters
        success, status, error_log_file = self.tm1.processes.execute_with_return(
            process_name=process.name)
        self.assertFalse(success)
        self.assertEqual(status, "QuitCalled")
        self.assertIsNone(error_log_file)

        self.tm1.processes.delete(process.name)

    def test_compile_process_success(self):
        p_good = Process(
            name=str(uuid.uuid4()),
            prolog_procedure="nPro = DimSiz('}Processes');")
        self.tm1.processes.create(p_good)
        errors = self.tm1.processes.compile(p_good.name)
        self.assertTrue(len(errors) == 0)
        self.tm1.processes.delete(p_good.name)

    def test_compile_process_with_errors(self):
        p_bad = Process(
            name=str(uuid.uuid4()),
            prolog_procedure="nPro = DimSize('}Processes');")
        self.tm1.processes.create(p_bad)
        errors = self.tm1.processes.compile(p_bad.name)
        self.assertTrue(len(errors) == 1)
        self.assertIn("Variable \"dimsize\" is undefined", errors[0]["Message"])
        self.tm1.processes.delete(p_bad.name)

    # Get Process
    def test_get_process(self):
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
    def test_update_process(self):
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

    def test_get_error_log_file_content(self):
        process = Process(name=str(uuid.uuid4()))
        process.epilog_procedure = "ItemReject('Not Relevant');"

        if not self.tm1.processes.exists(process.name):
            self.tm1.processes.create(process)
        # with parameters
        success, status, error_log_file = self.tm1.processes.execute_with_return(process_name=process.name)
        self.assertFalse(success)
        self.assertEqual(status, "CompletedWithMessages")
        self.assertIsNotNone(error_log_file)

        content = self.tm1.processes.get_error_log_file_content(file_name=error_log_file)
        self.assertIn("Not Relevant", content)

        self.tm1.processes.delete(process.name)

    # Delete process
    def test_delete_process(self):
        process = Utils.load_bedrock_from_github("Bedrock.Server.Wait")
        process.name = str(uuid.uuid4())
        if not self.tm1.processes.exists(process.name):
            self.tm1.processes.create(process)
        self.tm1.processes.delete(process.name)

    @classmethod
    def tearDownClass(cls):
        cls.tm1.processes.delete(cls.p_none.name)
        cls.tm1.processes.delete(cls.p_ascii.name)
        cls.tm1.processes.delete(cls.p_view.name)
        cls.tm1.processes.delete(cls.p_odbc.name)
        cls.tm1.processes.delete(cls.p_subset.name)
        cls.tm1.dimensions.subsets.delete(
            dimension_name=cls.subset.dimension_name,
            subset_name=cls.subset_name,
            private=False)
        cls.tm1.logout()


if __name__ == '__main__':
    unittest.main()
