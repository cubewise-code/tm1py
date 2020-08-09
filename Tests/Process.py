import configparser
import copy
import random
import time
import unittest
import uuid
from pathlib import Path

from TM1py.Objects import Process, Subset
from TM1py.Services import TM1Service

from .TestUtils import skip_if_insufficient_version

config = configparser.ConfigParser()
config.read(Path(__file__).parent.joinpath('config.ini'))

PROCESS_PREFIX = 'TM1py_Tests_'

class TestProcessMethods(unittest.TestCase):
    tm1 = None

    @classmethod
    def setUpClass(cls):
        cls.tm1 = TM1Service(**config['tm1srv01'])

        cls.some_name = "some_name"

        cls.all_dimension_names = cls.tm1.dimensions.get_all_names()
        cls.random_dimension = cls.tm1.dimensions.get(random.choice(cls.all_dimension_names))
        cls.random_dimension_all_elements = cls.random_dimension.default_hierarchy.elements
        cls.random_dimension_elements = [element for element in cls.random_dimension_all_elements][0:2]

        # None process
        cls.p_none = Process(name=PROCESS_PREFIX + '_none_' + cls.some_name, datasource_type='None')

        # ACII process
        cls.p_ascii = Process(name=PROCESS_PREFIX + '_ascii_' + cls.some_name,
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
        cls.p_view = Process(name=PROCESS_PREFIX + '_view_' + cls.some_name,
                             datasource_type='TM1CubeView',
                             datasource_view='view1',
                             datasource_data_source_name_for_client='Plan_BudgetPlan',
                             datasource_data_source_name_for_server='Plan_BudgetPlan')

        # ODBC process
        cls.p_odbc = Process(name=PROCESS_PREFIX + '_odbc_' + cls.some_name,
                             datasource_type='ODBC',
                             datasource_password='password',
                             datasource_user_name='user')

        # Subset process
        cls.subset_name = PROCESS_PREFIX + '_subset_' + cls.some_name
        cls.subset = Subset(dimension_name=cls.random_dimension.name,
                            subset_name=cls.subset_name,
                            elements=cls.random_dimension_elements)
        cls.tm1.dimensions.subsets.create(cls.subset, False)
        cls.p_subset = Process(name=PROCESS_PREFIX + '_subset_' + cls.some_name,
                               datasource_type='TM1DimensionSubset',
                               datasource_data_source_name_for_server=cls.subset.dimension_name,
                               datasource_subset=cls.subset.name,
                               metadata_procedure="sTest = 'abc';")

        with open(Path(__file__).parent.joinpath('resources', 'Bedrock.Server.Wait.json'), 'r') as file:
            cls.p_bedrock_server_wait = Process.from_json(file.read())

    @classmethod
    def setUp(cls):
        cls.tm1.processes.create(cls.p_none)
        cls.tm1.processes.create(cls.p_ascii)
        cls.tm1.processes.create(cls.p_view)
        cls.tm1.processes.create(cls.p_odbc)
        cls.tm1.processes.create(cls.p_subset)

    @classmethod
    def tearDown(cls):
        cls.tm1.processes.delete(cls.p_none.name)
        cls.tm1.processes.delete(cls.p_ascii.name)
        cls.tm1.processes.delete(cls.p_view.name)
        cls.tm1.processes.delete(cls.p_odbc.name)
        cls.tm1.processes.delete(cls.p_subset.name)


    def test_execute_process(self):
        if not self.tm1.processes.exists(self.p_bedrock_server_wait.name):
            self.tm1.processes.create(self.p_bedrock_server_wait)

        # with parameters argument
        start_time = time.time()
        self.tm1.processes.execute(self.p_bedrock_server_wait.name, parameters={"Parameters": [
            {"Name": "pWaitSec", "Value": "3"}]})
        elapsed_time = time.time() - start_time
        self.assertGreater(elapsed_time, 3)

        # with kwargs
        start_time = time.time()
        self.tm1.processes.execute(self.p_bedrock_server_wait.name, pWaitSec="1")
        elapsed_time = time.time() - start_time
        self.assertGreater(elapsed_time, 1)

        # without arguments
        self.tm1.processes.execute(self.p_bedrock_server_wait.name)

    @skip_if_insufficient_version(version="11.4")
    def test_execute_with_return_success(self):
        process = self.p_bedrock_server_wait
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

    @skip_if_insufficient_version(version="11.4")
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

    @skip_if_insufficient_version(version="11.4")
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

    def test_compile_success(self):
        p_good = Process(
            name=str(uuid.uuid4()),
            prolog_procedure="nPro = DimSiz('}Processes');")
        self.tm1.processes.create(p_good)
        errors = self.tm1.processes.compile(p_good.name)
        self.assertTrue(len(errors) == 0)
        self.tm1.processes.delete(p_good.name)

    def test_compile_with_errors(self):
        p_bad = Process(
            name=str(uuid.uuid4()),
            prolog_procedure="nPro = DimSize('}Processes');")
        self.tm1.processes.create(p_bad)
        errors = self.tm1.processes.compile(p_bad.name)
        self.assertTrue(len(errors) == 1)
        self.assertIn("Variable \"dimsize\" is undefined", errors[0]["Message"])
        self.tm1.processes.delete(p_bad.name)


    def test_execute_process_with_return_compile_error(self):
        process = Process(name=str(uuid.uuid4()))
        process.prolog_procedure = "sText = 'text';sText = 2;"

        success, status, error_log_file = self.tm1.processes.execute_process_with_return(process)
        self.assertFalse(success)
        self.assertEqual(status, "Aborted")
        self.assertIsNotNone(error_log_file)

    def test_execute_process_with_return_with_item_reject(self):
        process = Process(name=str(uuid.uuid4()))
        process.epilog_procedure = "ItemReject('Not Relevant');"

        success, status, error_log_file = self.tm1.processes.execute_process_with_return(process)
        self.assertFalse(success)
        self.assertEqual(status, "CompletedWithMessages")
        self.assertIsNotNone(error_log_file)

    @skip_if_insufficient_version(version="11.4")
    def test_execute_process_with_return_with_process_break(self):
        process = Process(name=str(uuid.uuid4()))
        process.prolog_procedure = "sText = 'Something'; ProcessBreak;"

        success, status, error_log_file = self.tm1.processes.execute_process_with_return(process)
        self.assertTrue(success)
        self.assertEqual(status, "CompletedSuccessfully")
        self.assertIsNone(error_log_file)

    @skip_if_insufficient_version(version="11.4")
    def test_execute_process_with_return_with_process_quit(self):
        process = Process(name=str(uuid.uuid4()))
        process.prolog_procedure = "sText = 'Something'; ProcessQuit;"

        success, status, error_log_file = self.tm1.processes.execute_process_with_return(process)
        self.assertFalse(success)
        self.assertEqual(status, "QuitCalled")
        self.assertIsNone(error_log_file)

    def test_compile_process_success(self):
        p_good = Process(
            name=str(uuid.uuid4()),
            prolog_procedure="nPro = DimSiz('}Processes');")

        errors = self.tm1.processes.compile_process(p_good)
        self.assertTrue(len(errors) == 0)

    def test_compile_process_with_errors(self):
        p_bad = Process(
            name=str(uuid.uuid4()),
            prolog_procedure="nPro = DimSize('}Processes');")

        errors = self.tm1.processes.compile_process(p_bad)
        self.assertTrue(len(errors) == 1)
        self.assertIn("Variable \"dimsize\" is undefined", errors[0]["Message"])

    def test_get_process(self):
        p_ascii_orig = copy.deepcopy(self.p_ascii)
        p_none_orig = copy.deepcopy(self.p_none)
        p_view_orig = copy.deepcopy(self.p_view)
        p_subset_orig = copy.deepcopy(self.p_subset)
        p_odbc_orig = copy.deepcopy(self.p_odbc)

        p1 = self.tm1.processes.get(p_ascii_orig.name)
        self.assertEqual(p1.body, p_ascii_orig.body)
        p2 = self.tm1.processes.get(p_none_orig.name)
        self.assertEqual(p2.body, p_none_orig.body)
        p3 = self.tm1.processes.get(p_view_orig.name)
        self.assertEqual(p3.body, p_view_orig.body)
        p4 = self.tm1.processes.get(p_odbc_orig.name)
        p4.datasource_password = None
        p_odbc_orig.datasource_password = None
        self.assertEqual(p4.body, p_odbc_orig.body)
        p5 = self.tm1.processes.get(p_subset_orig.name)
        self.assertEqual(p5.body, p_subset_orig.body)

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

    def test_delete_process(self):
        process = self.p_bedrock_server_wait
        process.name = str(uuid.uuid4())
        if not self.tm1.processes.exists(process.name):
            self.tm1.processes.create(process)
        self.tm1.processes.delete(process.name)

    @classmethod
    def tearDownClass(cls):
        cls.tm1.dimensions.subsets.delete(
            dimension_name=cls.subset.dimension_name,
            subset_name=cls.subset_name,
            private=False)
        cls.tm1.logout()


if __name__ == '__main__':
    unittest.main()
