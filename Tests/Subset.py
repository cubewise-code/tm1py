__author__ = 'Marius Wirtz'

from TM1py import TM1Queries, Subset
import uuid
import json
import unittest


class TestAnnotationMethods(unittest.TestCase):
    q = TM1Queries(ip='', port=8008, user='admin', password='apple', ssl=True)
    random_string1 = str(uuid.uuid4()).replace('-', '_')
    random_string2 = str(uuid.uuid4()).replace('-', '_')

    # 1. create subset
    def test_create_subset(self):
        s = Subset(dimension_name='plan_business_unit', subset_name=self.random_string1,
                   elements=['10110', '10300', '10210', '10000'])
        response = self.q.create_subset(s)
        print(response)
        response_as_dict = json.loads(response)
        name_in_response = response_as_dict['Name']
        self.assertEqual(self.random_string1, name_in_response)

        s = Subset(dimension_name='plan_business_unit', subset_name=self.random_string2,
                   expression='{ HIERARCHIZE( {TM1SUBSETALL( [plan_business_unit] )} ) }')
        response = self.q.create_subset(s)
        response_as_dict = json.loads(response)
        name_in_response = response_as_dict['Name']
        self.assertEqual(self.random_string2, name_in_response)

    # 2. get subset
    def test_get_subset(self):
        s = self.q.get_subset(dimension_name='plan_business_unit', subset_name='static_subset_for_unit_test')
        self.assertIsInstance(s, Subset)

        s = self.q.get_subset(dimension_name='plan_business_unit', subset_name='dynamic_subset_for_unit_test')
        self.assertIsInstance(s, Subset)

    # 3. update subset
    def test_update_subset(self):
        s = self.q.get_subset(dimension_name='plan_business_unit', subset_name='static_subset_for_unit_test')
        s.add_elements(['10110'])
        self.q.update_subset(s)

        s = self.q.get_subset(dimension_name='plan_business_unit', subset_name='dynamic_subset_for_unit_test')
        s.set_expression('{ HIERARCHIZE( {TM1SUBSETALL( [plan_business_unit] )} ) }')
        self.q.update_subset(s)

    # 4. delete subset
    def test_delete_subset(self):
        response = self.q.delete_subset('plan_business_unit', self.random_string1)
        self.assertEqual(response, '')
        response = self.q.delete_subset('plan_business_unit', self.random_string2)
        self.assertEqual(response, '')


if __name__ == '__main__':
    unittest.main()
