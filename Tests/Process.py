import unittest
import uuid

from Services.RESTService import RESTService
from Services.LoginService import LoginService
from Services.ProcessService import ProcessService
from Services.SubsetService import SubsetService
from Objects.Process import Process
from Objects.Subset import Subset


# Configuration for tests
port = 8001
user = 'admin'
pwd = 'apple'


class TestProcessMethods(unittest.TestCase):
    login = LoginService.native(user, pwd)
    tm1_rest = RESTService(ip='', port=port, login=login, ssl=False)
    process_service = ProcessService(tm1_rest)
    subset_service = SubsetService(tm1_rest)

    random_string = str(uuid.uuid4())

    # None process
    p_none = Process(name='}TM1py_unittest_none_' + random_string,
                     datasource_type='None')

    # ACII process
    p_ascii = Process(name='}TM1py_unittest_ascii_' + random_string,
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
    p_view = Process(name='}TM1py_unittest_view_' + random_string,
                     datasource_type='TM1CubeView',
                     datasource_view='view1',
                     datasource_data_source_name_for_client='Plan_BudgetPlan',
                     datasource_data_source_name_for_server='Plan_BudgetPlan')

    # ODBC process
    p_odbc = Process(name='}TM1py_unittest_odbc_' + random_string,
                     datasource_type='ODBC',
                     datasource_password='password',
                     datasource_user_name='user')

    # Subset process
    subset_name = '}TM1py_unittest_subset_' + random_string
    subset = Subset(dimension_name='plan_business_unit',
                    subset_name=subset_name,
                    elements=['10110', '10120', '10200', '10210'])
    subset_service.create(subset, False)
    p_subset = Process(name='}TM1py_unittest_subset_' + random_string,
                       datasource_type='TM1DimensionSubset',
                       datasource_data_source_name_for_server=subset.dimension_name,
                       datasource_subset=subset.name,
                       metadata_procedure="sTest = 'abc';")

    # Create Process
    def test1_create_process(self):
        self.process_service.create(self.p_none)
        self.process_service.create(self.p_ascii)
        self.process_service.create(self.p_view)
        self.process_service.create(self.p_odbc)
        self.process_service.create(self.p_subset)

    # Get Process
    def test2_get_process(self):
        p1 = self.process_service.get(self.p_ascii.name)
        self.assertEqual(p1.body, self.p_ascii.body)
        p2 = self.process_service.get(self.p_none.name)
        self.assertEqual(p2.body, self.p_none.body)
        p3 = self.process_service.get(self.p_view.name)
        self.assertEqual(p3.body, self.p_view.body)
        p4 = self.process_service.get(self.p_odbc.name)
        p4.datasource_password = None
        self.p_odbc.datasource_password = None
        self.assertEqual(p4.body, self.p_odbc.body)
        p5 = self.process_service.get(self.p_subset.name)
        self.assertEqual(p5.body, self.p_subset.body)

    # Update process
    def test3_update_process(self):
        # get
        p = self.process_service.get(self.p_ascii.name)
        # modify
        p.data_procedure = "SaveDataAll;"
        # update on Server
        self.process_service.update(p)
        # get again
        p_ascii_updated = self.process_service.get(p.name)
        # assert
        self.assertNotEqual(p_ascii_updated.data_procedure, self.p_ascii.data_procedure)

    # Delete process
    def test4_delete_process(self):
        self.process_service.delete(self.p_none.name)
        self.process_service.delete(self.p_ascii.name)
        self.process_service.delete(self.p_view.name)
        self.process_service.delete(self.p_odbc.name)
        self.process_service.delete(self.p_subset.name)
        self.subset_service.delete(self.subset.dimension_name, self.subset_name, False)

    def test5_logout(self):
        self.tm1_rest.logout()


if __name__ == '__main__':
    unittest.main()
