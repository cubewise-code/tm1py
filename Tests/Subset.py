from TM1py import TM1Queries as TM1, Subset
import uuid
import unittest


class TestAnnotationMethods(unittest.TestCase):
    tm1 = TM1(ip='localhost', port=8001, user='admin', password='apple', ssl=False)

    random_string = str(uuid.uuid4())
    subset_name_static = 'TM1py_unittest_static_subset_' + random_string
    subset_name_dynamic = 'TM1py_unittest_dynamic_subset_' + random_string

    # 1. create subset
    def test_1create_subset(self):
        s = Subset(dimension_name='plan_business_unit',
                   subset_name=self.subset_name_static,
                   elements=['10110', '10300', '10210', '10000'])
        self.tm1.create_subset(s)

        s = Subset(dimension_name='plan_business_unit',
                   subset_name=self.subset_name_dynamic,
                   expression='{ HIERARCHIZE( {TM1SUBSETALL( [plan_business_unit] )} ) }')
        self.tm1.create_subset(s)

    # 2. get subset
    def test_2get_subset(self):
        s = self.tm1.get_subset(dimension_name='plan_business_unit',
                              subset_name=self.subset_name_static)
        self.assertIsInstance(s, Subset)

        s = self.tm1.get_subset(dimension_name='plan_business_unit',
                              subset_name=self.subset_name_dynamic)
        self.assertIsInstance(s, Subset)

    # 3. update subset
    def test_3update_subset(self):
        s = self.q.get_subset(dimension_name='plan_business_unit',
                              subset_name=self.subset_name_static)
        s.add_elements(['10110'])
        self.tm1.update_subset(s)

        s = self.tm1.get_subset(dimension_name='plan_business_unit',
                              subset_name=self.subset_name_dynamic)
        s.set_expression('{ HIERARCHIZE( {TM1SUBSETALL( [plan_business_unit] )} ) }')
        self.tm1.update_subset(s)

    # 4. delete subset
    def test_4delete_subset(self):
        self.tm1.delete_subset(dimension_name='plan_business_unit',
                             subset_name=self.subset_name_static)
        self.tm1.delete_subset(dimension_name='plan_business_unit',
                             subset_name=self.subset_name_dynamic)

    def test_5logout(self):
        self.tm1.logout()

if __name__ == '__main__':
    unittest.main()
