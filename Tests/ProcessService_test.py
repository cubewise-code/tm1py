import configparser
import copy
import random
import time
import unittest
import uuid
from pathlib import Path

from TM1py.Exceptions import TM1pyException
from TM1py.Objects import Process, Subset, ProcessDebugBreakpoint, BreakPointType, HitMode
from TM1py.Services import TM1Service
from .Utils import skip_if_insufficient_version, skip_if_deprecated_in_version
from TM1py.Utils import verify_version


class TestProcessService(unittest.TestCase):
    tm1: TM1Service

    prefix = 'TM1py_Tests_'

    some_name = "some_name"

    p_none = Process(name=prefix + '_none_' + some_name, datasource_type='None')
    p_ascii = Process(name=prefix + '_ascii_' + some_name,
                      datasource_type='ASCII',
                      datasource_ascii_delimiter_type='Character',
                      datasource_ascii_delimiter_char=',',
                      datasource_ascii_header_records=2,
                      datasource_ascii_quote_character='^',
                      datasource_ascii_thousand_separator='~',
                      prolog_procedure="sTestProlog = 'test prolog procedure';",
                      metadata_procedure="sTestMeta = 'test metadata procedure';",
                      data_procedure="sTestData =  'test data procedure';",
                      epilog_procedure="sTestEpilog = 'test epilog procedure';",
                      datasource_data_source_name_for_server=r'C:\Data\file.csv',
                      datasource_data_source_name_for_client=r'C:\Data\file.csv')
    p_ascii.add_variable('v_1', 'Numeric')
    p_ascii.add_variable('v_2', 'Numeric')
    p_ascii.add_variable('v_3', 'Numeric')
    p_ascii.add_variable('v_4', 'Numeric')
    p_ascii.add_parameter('p_Year', 'year?', '2016')
    p_ascii.add_parameter('p_Number', 'number?', 2)

    p_view = Process(name=prefix + '_view_' + some_name,
                     datasource_type='TM1CubeView',
                     datasource_view='view1',
                     datasource_data_source_name_for_client='Plan_BudgetPlan',
                     datasource_data_source_name_for_server='Plan_BudgetPlan')

    p_odbc = Process(name=prefix + '_odbc_' + some_name,
                     datasource_type='ODBC',
                     datasource_password='password',
                     datasource_user_name='user')

    p_debug = Process(
        name=prefix + "_debug",
        datasource_type="None",
        prolog_procedure="sleep(1);\r\nsleep(1);\r\nsleep(1);\r\nsleep(1);\r\nsleep(1);\r\nsleep(1);\r\n")

    subset: Subset
    subset_name: str
    p_subset: Process
    p_error: Process

    @classmethod
    def setUpClass(cls):
        """
        Establishes a connection to TM1 and creates TM! objects to use across all tests
        """

        # Connection to TM1
        cls.config = configparser.ConfigParser()
        cls.config.read(Path(__file__).parent.joinpath('config.ini'))
        cls.tm1 = TM1Service(**cls.config['tm1srv01'])

        cls.all_dimension_names = cls.tm1.dimensions.get_all_names()
        cls.random_dimension = cls.tm1.dimensions.get(random.choice(cls.all_dimension_names))
        cls.random_dimension_all_elements = cls.random_dimension.default_hierarchy.elements
        cls.random_dimension_elements = [element for element in cls.random_dimension_all_elements][0:2]

        # Subset process
        cls.subset_name = cls.prefix + '_subset_' + cls.some_name
        cls.subset = Subset(dimension_name=cls.random_dimension.name,
                            subset_name=cls.subset_name,
                            elements=cls.random_dimension_elements)
        cls.tm1.dimensions.subsets.update_or_create(cls.subset, False)
        cls.p_subset = Process(name=cls.prefix + '_subset_' + cls.some_name,
                               datasource_type='TM1DimensionSubset',
                               datasource_data_source_name_for_server=cls.subset.dimension_name,
                               datasource_subset=cls.subset.name,
                               metadata_procedure="sTest = 'abc';")

        cls.p_error = Process(name=cls.prefix + "_error")
        cls.p_error.epilog_procedure = "ItemReject('just an error');"

        with open(Path(__file__).parent.joinpath('resources', 'Bedrock.Server.Wait.json'), 'r') as file:
            cls.p_bedrock_server_wait = Process.from_json(file.read())

    @classmethod
    def setUp(cls):
        cls.tm1.processes.update_or_create(cls.p_none)
        cls.tm1.processes.update_or_create(cls.p_ascii)
        cls.tm1.processes.update_or_create(cls.p_view)
        cls.tm1.processes.update_or_create(cls.p_odbc)
        cls.tm1.processes.update_or_create(cls.p_subset)
        cls.tm1.processes.update_or_create(cls.p_debug)
        cls.tm1.processes.update_or_create(cls.p_error)

    @classmethod
    def tearDown(cls):
        cls.tm1.processes.delete(cls.p_none.name)
        cls.tm1.processes.delete(cls.p_ascii.name)
        cls.tm1.processes.delete(cls.p_view.name)
        cls.tm1.processes.delete(cls.p_odbc.name)
        cls.tm1.processes.delete(cls.p_subset.name)
        cls.tm1.processes.delete(cls.p_debug.name)
        cls.tm1.processes.delete(cls.p_error.name)

    def test_update_or_create(self):
        if self.tm1.processes.exists(self.p_bedrock_server_wait.name):
            self.tm1.processes.delete(self.p_bedrock_server_wait.name)
        self.assertFalse(self.tm1.processes.exists(self.p_bedrock_server_wait.name))

        self.tm1.processes.update_or_create(self.p_bedrock_server_wait)
        self.assertTrue(self.tm1.processes.exists(self.p_bedrock_server_wait.name))

        temp_prolog = self.p_bedrock_server_wait.prolog_procedure
        self.p_bedrock_server_wait.prolog_procedure += "sleep(10);"

        self.tm1.processes.update_or_create(self.p_bedrock_server_wait)
        self.assertTrue(self.tm1.processes.exists(self.p_bedrock_server_wait.name))

        self.p_bedrock_server_wait.prolog_procedure = temp_prolog
        self.tm1.processes.delete(self.p_bedrock_server_wait.name)

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
        self.tm1.processes.execute(self.p_bedrock_server_wait.name, pWaitSec="1.01")
        elapsed_time = time.time() - start_time
        self.assertGreater(elapsed_time, 1)

        # without arguments
        self.tm1.processes.execute(self.p_bedrock_server_wait.name)

    @skip_if_insufficient_version(version="11.4")
    def test_execute_with_return_success(self):
        process = self.p_bedrock_server_wait
        self.tm1.processes.update_or_create(process)
        # with parameters
        success, status, error_log_file = self.tm1.processes.execute_with_return(
            process_name=process.name,
            pWaitSec=2)
        self.assertTrue(success)
        self.assertEqual(status, "CompletedSuccessfully")
        # v12 returns a log file for every process execution
        if not verify_version(required_version="12", version=self.tm1.version):
            self.assertIsNone(error_log_file)
        # without parameters
        success, status, error_log_file = self.tm1.processes.execute_with_return(
            process_name=process.name)
        self.assertTrue(success)
        self.assertEqual(status, "CompletedSuccessfully")
        # v12 returns a log file for every process execution
        if not verify_version(required_version="12", version=self.tm1.version):
            self.assertIsNone(error_log_file)

    def test_execute_with_return_compile_error(self):
        process = Process(name=str(uuid.uuid4()))
        process.prolog_procedure = "sText = 'text';sText = 2;"
        self.tm1.processes.update_or_create(process)

        # with parameters
        success, status, error_log_file = self.tm1.processes.execute_with_return(process_name=process.name)
        self.assertFalse(success)
        self.assertEqual(status, "Aborted")
        self.assertIsNotNone(error_log_file)

        self.tm1.processes.delete(process.name)

    def test_execute_with_return_with_item_reject(self):
        process = Process(name=str(uuid.uuid4()))
        process.epilog_procedure = "ItemReject('Not Relevant');"

        self.tm1.processes.update_or_create(process)
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

        self.tm1.processes.update_or_create(process)
        # with parameters
        success, status, error_log_file = self.tm1.processes.execute_with_return(
            process_name=process.name)
        self.assertTrue(success)
        self.assertEqual(status, "CompletedSuccessfully")
        # v12 returns a log file for every process execution
        if not verify_version(required_version="12", version=self.tm1.version):
            self.assertIsNone(error_log_file)

        self.tm1.processes.delete(process.name)

    @skip_if_insufficient_version(version="11.4")
    def test_execute_with_return_with_process_quit(self):
        process = Process(name=str(uuid.uuid4()))
        process.prolog_procedure = "sText = 'Something'; ProcessQuit;"

        self.tm1.processes.update_or_create(process)
        # with parameters
        success, status, error_log_file = self.tm1.processes.execute_with_return(
            process_name=process.name)
        self.assertFalse(success)
        self.assertEqual(status, "QuitCalled")
        # v12 returns a log file for every process execution
        if not verify_version(required_version="12", version=self.tm1.version):
            self.assertIsNone(error_log_file)

        self.tm1.processes.delete(process.name)

    def test_compile_success(self):
        p_good = Process(
            name=str(uuid.uuid4()),
            prolog_procedure="nPro = DimSiz('}Processes');")
        self.tm1.processes.update_or_create(p_good)
        errors = self.tm1.processes.compile(p_good.name)
        self.assertTrue(len(errors) == 0)
        self.tm1.processes.delete(p_good.name)

    def test_compile_with_errors(self):
        p_bad = Process(
            name=str(uuid.uuid4()),
            prolog_procedure="nPro = DimSize('}Processes');")
        self.tm1.processes.update_or_create(p_bad)
        errors = self.tm1.processes.compile(p_bad.name)
        self.assertTrue(len(errors) == 1)
        self.assertIn("\"dimsize\"", errors[0]["Message"])
        self.tm1.processes.delete(p_bad.name)

    @skip_if_insufficient_version(version="11.4")
    def test_execute_process_with_return_success(self):
        process = Process(name=str(uuid.uuid4()))
        process.prolog_procedure = "Sleep(100);"

        success, status, error_log_file = self.tm1.processes.execute_process_with_return(process)
        self.assertTrue(success)
        self.assertEqual(status, "CompletedSuccessfully")
        # v12 returns a log file for every process execution
        if not verify_version(required_version="12", version=self.tm1.version):
            self.assertIsNone(error_log_file)

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
        # v12 returns a log file for every process execution
        if not verify_version(required_version="12", version=self.tm1.version):
            self.assertIsNone(error_log_file)

    @skip_if_insufficient_version(version="11.4")
    def test_execute_process_with_return_with_process_quit(self):
        process = Process(name=str(uuid.uuid4()))
        process.prolog_procedure = "sText = 'Something'; ProcessQuit;"

        success, status, error_log_file = self.tm1.processes.execute_process_with_return(process)
        self.assertFalse(success)
        self.assertEqual(status, "QuitCalled")
        # v12 returns a log file for every process execution
        if not verify_version(required_version="12", version=self.tm1.version):
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
        self.assertIn("\"dimsize\"", errors[0]["Message"])

    def test_get_process(self):
        p_ascii_orig = copy.deepcopy(self.p_ascii)
        p_none_orig = copy.deepcopy(self.p_none)
        p_view_orig = copy.deepcopy(self.p_view)
        p_subset_orig = copy.deepcopy(self.p_subset)

        p1 = self.tm1.processes.get(p_ascii_orig.name)
        p1._ui_data = p_ascii_orig._ui_data = None
        self.assertEqual(p_ascii_orig.body, p1.body)

        p2 = self.tm1.processes.get(p_none_orig.name)
        p2._ui_data = p_none_orig._ui_data = None
        self.assertEqual(p_none_orig.body, p2.body)

        p3 = self.tm1.processes.get(p_view_orig.name)
        p3._ui_data = p_view_orig._ui_data = None
        self.assertEqual(p_view_orig.body, p3.body)

        p4 = self.tm1.processes.get(p_subset_orig.name)
        p4._ui_data = p_subset_orig._ui_data = None
        self.assertEqual(p_subset_orig.body, p4.body)

    @skip_if_deprecated_in_version("12")
    def test_get_process_odbc(self):
        p_odbc_orig = copy.deepcopy(self.p_odbc)

        p = self.tm1.processes.get(p_odbc_orig.name)
        # edge cases
        p.datasource_password = None
        p_odbc_orig.datasource_password = None
        p_odbc_orig._ui_data = p._ui_data = None

        self.assertEqual(p.body, p_odbc_orig.body)

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

        self.tm1.processes.update_or_create(process)
        # with parameters
        success, status, error_log_file = self.tm1.processes.execute_with_return(process_name=process.name)
        self.assertFalse(success)
        self.assertEqual(status, "CompletedWithMessages")
        self.assertIsNotNone(error_log_file)

        content = self.tm1.processes.get_error_log_file_content(file_name=error_log_file)
        self.assertIn("Not Relevant", content)

        self.tm1.processes.delete(process.name)

    @skip_if_deprecated_in_version(version='12')
    def test_get_last_message_from_processerrorlog(self):
        process = Process(name=str(uuid.uuid4()))
        process.epilog_procedure = "ItemReject('Not Relevant');"

        self.tm1.processes.update_or_create(process)
        # with parameters
        success, status, error_log_file = self.tm1.processes.execute_with_return(process_name=process.name)
        self.assertFalse(success)
        self.assertEqual(status, "CompletedWithMessages")
        self.assertIsNotNone(error_log_file)

        content = self.tm1.processes.get_last_message_from_processerrorlog(process_name=process.name)
        self.assertIn("Not Relevant", content)

        self.tm1.processes.delete(process.name)

    def test_get_error_log_filenames(self):
        # with parameters
        success, status, error_log_file = self.tm1.processes.execute_with_return(process_name=self.p_error.name)
        self.assertFalse(success)
        self.assertEqual(status, "CompletedWithMessages")
        self.assertIsNotNone(error_log_file)

        content = self.tm1.processes.get_error_log_filenames(process_name=self.p_error.name, top=1)
        self.assertEqual(1, len(content))

    def test_search_error_log_filenames(self):
        # with parameters
        success, status, error_log_file = self.tm1.processes.execute_with_return(process_name=self.p_error.name)
        self.assertFalse(success)
        self.assertEqual(status, "CompletedWithMessages")
        self.assertIsNotNone(error_log_file)

        # many process error logs have been generated by this point, expecting more than 1 that begin with TM1
        content = self.tm1.processes.search_error_log_filenames(search_string='TM1')
        self.assertGreater(len(content), 0)

    def test_search_error_log_filenames_top_3(self):
        for _ in range(3):
            self.tm1.processes.execute_with_return(process_name=self.p_error.name)

        content = self.tm1.processes.search_error_log_filenames(search_string='TM1', top=3)
        self.assertEqual(len(content), 3)

    def test_delete_process(self):
        process = self.p_bedrock_server_wait
        process.name = str(uuid.uuid4())
        self.tm1.processes.update_or_create(process)
        self.tm1.processes.delete(process.name)

    def test_search_string_in_name_no_match_startswith(self):
        process_names = self.tm1.processes.search_string_in_name(
            name_startswith="NotAProcessName")
        self.assertEqual([], process_names)

    def test_search_string_in_name_no_match_contains(self):
        process_names = self.tm1.processes.search_string_in_name(
            name_contains="NotAProcessName")
        self.assertEqual([], process_names)

    def test_search_string_in_name_startswith_happy_case(self):
        process_names = self.tm1.processes.search_string_in_name(name_startswith=self.p_ascii.name)
        self.assertEqual([self.p_ascii.name], process_names)

    def test_search_string_in_name_contains_happy_case(self):
        process_names = self.tm1.processes.search_string_in_name(name_contains=self.p_ascii.name)
        self.assertEqual([self.p_ascii.name], process_names)

    def test_search_string_in_name_contains_multiple(self):
        process_names = self.tm1.processes.search_string_in_name(name_contains=self.p_ascii.name.split("_"))
        self.assertEqual([self.p_ascii.name], process_names)

    def test_search_string_in_code(self):
        process_names = self.tm1.processes.search_string_in_code("sTestProlog = 'test prolog procedure'")
        self.assertEqual([self.p_ascii.name], process_names)

    def test_search_string_in_code_space_insensitive(self):
        process_names = self.tm1.processes.search_string_in_code("sTestProlog = 'test PROLOG procedure'")
        self.assertEqual([self.p_ascii.name], process_names)

    def test_get_all_names(self):
        process = Process(name='}' + f'{self.prefix}_ControlProcess')
        process.epilog_procedure = "#Empty Process"
        self.tm1.processes.update_or_create(process)
        self.assertNotEqual(self.tm1.processes.get_all_names(),
                            self.tm1.processes.get_all_names(skip_control_processes=True))
        self.assertNotEqual('}', self.tm1.processes.get_all_names(skip_control_processes=True)[-1][0][0])
        self.assertEqual('}', self.tm1.processes.get_all_names()[-1][0][0])
        self.tm1.processes.delete(process.name)

    def test_ti_formula(self):
        result = self.tm1.processes.evaluate_ti_expression("2+2")
        self.assertEqual(4, int(result))

    def test_ti_formula_no_code(self):
        with self.assertRaises(ValueError):
            _ = self.tm1.processes.evaluate_ti_expression("")

    def test_debug_get_variable_values(self):
        result = self.tm1.processes.debug_process(self.p_debug.name)
        debug_id = result['ID']
        time.sleep(0.1)

        result = self.tm1.processes.debug_get_variable_values(debug_id=debug_id)

        self.assertEqual(result['DATASOURCETYPE'], 'NULL')

        self.tm1.processes.debug_step_out(debug_id=debug_id)

    def test_debug_get_single_variable_value(self):
        result = self.tm1.processes.debug_process(self.p_debug.name)
        debug_id = result['ID']
        time.sleep(0.1)

        value = self.tm1.processes.debug_get_single_variable_value(debug_id=debug_id, variable_name="DATASOURCETYPE")

        self.assertEqual(value, 'NULL')

        self.tm1.processes.debug_step_out(debug_id=debug_id)

    def test_debug_step_over(self):
        result = self.tm1.processes.debug_process(self.p_debug.name)
        debug_id = result['ID']
        time.sleep(0.1)

        result = self.tm1.processes.debug_step_over(debug_id=debug_id)
        self.assertEqual(
            4,
            result['CallStack'][0]['LineNumber'])
        time.sleep(0.1)

        result = self.tm1.processes.debug_step_over(debug_id=debug_id)
        self.assertEqual(
            5,
            result['CallStack'][0]['LineNumber'])
        time.sleep(0.1)

        result = self.tm1.processes.debug_step_over(debug_id=debug_id)
        self.assertEqual(
            6,
            result['CallStack'][0]['LineNumber'])
        time.sleep(0.1)

        result = self.tm1.processes.debug_step_over(debug_id=debug_id)
        self.assertEqual(
            7,
            result['CallStack'][0]['LineNumber'])
        time.sleep(0.1)

        result = self.tm1.processes.debug_step_out(debug_id=debug_id)
        self.assertEqual(result["Status"], "Complete")

    def test_debug_continue(self):
        line_numbers = 4, 5

        result = self.tm1.processes.debug_process(self.p_debug.name)
        debug_id = result['ID']
        time.sleep(0.1)

        break_points = []
        for i, line_number in enumerate(line_numbers):
            break_points.append(ProcessDebugBreakpoint(
                breakpoint_id=i,
                breakpoint_type=BreakPointType.PROCESS_DEBUG_CONTEXT_LINE_BREAK_POINT,
                process_name=self.p_debug.name,
                procedure="Prolog",
                hit_mode=HitMode.BREAK_ALWAYS,
                line_number=line_number))

        self.tm1.processes.debug_add_breakpoints(debug_id, break_points)

        time.sleep(0.1)
        result = self.tm1.processes.debug_continue(debug_id=debug_id)
        self.assertEqual(
            line_numbers[0],
            result['CallStack'][0]['LineNumber'])
        time.sleep(0.1)

        result = self.tm1.processes.debug_continue(debug_id=debug_id)
        self.assertEqual(
            line_numbers[1],
            result['CallStack'][0]['LineNumber'])
        time.sleep(0.1)

        result = self.tm1.processes.debug_step_out(debug_id=debug_id)
        self.assertEqual(
            2,
            len(result['Breakpoints']))
        self.assertEqual(result["Status"], "Complete")

    def test_debug_add_breakpoint(self):
        line_number = 4

        result = self.tm1.processes.debug_process(self.p_debug.name)
        debug_id = result['ID']

        time.sleep(0.1)
        break_point = ProcessDebugBreakpoint(
            breakpoint_id=1,
            breakpoint_type=BreakPointType.PROCESS_DEBUG_CONTEXT_LINE_BREAK_POINT,
            process_name=self.p_debug.name,
            procedure="Prolog",
            hit_mode=HitMode.BREAK_ALWAYS,
            line_number=line_number)
        self.tm1.processes.debug_add_breakpoint(debug_id, break_point)

        time.sleep(0.1)
        result = self.tm1.processes.debug_continue(debug_id=debug_id)
        self.assertEqual(
            line_number,
            result['CallStack'][0]['LineNumber'])

        time.sleep(0.1)
        result = self.tm1.processes.debug_step_out(debug_id=debug_id)
        self.assertEqual(
            1,
            len(result['Breakpoints']))
        self.assertEqual(result["Status"], "Complete")

    def test_debug_remove_breakpoint(self):
        result = self.tm1.processes.debug_process(self.p_debug.name)
        debug_id = result['ID']

        time.sleep(0.1)
        break_point = ProcessDebugBreakpoint(
            breakpoint_id=1,
            breakpoint_type=BreakPointType.PROCESS_DEBUG_CONTEXT_LINE_BREAK_POINT,
            process_name=self.p_debug.name,
            procedure="Prolog",
            hit_mode=HitMode.BREAK_ALWAYS,
            line_number=4)
        self.tm1.processes.debug_add_breakpoint(debug_id, break_point)
        time.sleep(0.1)
        break_point = ProcessDebugBreakpoint(
            breakpoint_id=2,
            breakpoint_type=BreakPointType.PROCESS_DEBUG_CONTEXT_LINE_BREAK_POINT,
            process_name=self.p_debug.name,
            procedure="Prolog",
            hit_mode=HitMode.BREAK_ALWAYS,
            line_number=5)
        self.tm1.processes.debug_add_breakpoint(debug_id, break_point)

        time.sleep(0.1)
        result = self.tm1.processes.debug_step_out(debug_id=debug_id)
        self.assertEqual(
            4,
            result['CallStack'][0]['LineNumber'])
        self.assertEqual(
            2,
            len(result['Breakpoints']))

        time.sleep(0.1)
        self.tm1.processes.debug_remove_breakpoint(debug_id, breakpoint_id=2)

        time.sleep(0.1)
        result = self.tm1.processes.debug_step_out(debug_id=debug_id)
        self.assertEqual(
            1,
            len(result['Breakpoints']))
        self.assertEqual(result["Status"], "Complete")

    def test_evaluate_boolean_ti_expression_true(self):
        value = self.tm1.processes.evaluate_boolean_ti_expression("1>0")
        self.assertEqual(True, value)

    def test_evaluate_boolean_ti_expression_false(self):
        value = self.tm1.processes.evaluate_boolean_ti_expression("1=0")
        self.assertEqual(False, value)

    def test_evaluate_boolean_ti_expression_function_true(self):
        value = self.tm1.processes.evaluate_boolean_ti_expression("cos(0)=1")
        self.assertEqual(True, value)

    def test_evaluate_boolean_ti_expression_function_false(self):
        value = self.tm1.processes.evaluate_boolean_ti_expression("cos(0)=0")
        self.assertEqual(False, value)

    def test_evaluate_boolean_ti_expression_syntax_error(self):
        with self.assertRaises(TM1pyException):
            value = self.tm1.processes.evaluate_boolean_ti_expression("1@=1")
            self.assertEqual(True, value)

    @classmethod
    def tearDownClass(cls):
        cls.tm1.dimensions.subsets.delete(
            dimension_name=cls.subset.dimension_name,
            subset_name=cls.subset_name,
            private=False)
        cls.tm1.logout()


if __name__ == '__main__':
    unittest.main()
