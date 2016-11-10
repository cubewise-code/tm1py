from TM1py import TM1pyQueries as TM1, TM1pyLogin, Subset
import uuid
import unittest
import random

class TestSubsetMethods(unittest.TestCase):
    login = TM1pyLogin.native('admin', 'apple')
    tm1 = TM1(ip='', port=8001, login=login, ssl=False)

    random_string = str(uuid.uuid4())
    subset_name_static = 'TM1py_unittest_static_subset_' + random_string
    subset_name_dynamic = 'TM1py_unittest_dynamic_subset_' + random_string
    private = bool(random.getrandbits(1))

    # 1. create subset
    def test_1create_subset(self):
        s = Subset(dimension_name='plan_business_unit',
                   subset_name=self.subset_name_static,
                   alias='BusinessUnit',
                   elements=['10110', '10300', '10210', '10000'])
        self.tm1.create_subset(s, private=self.private)

        s = Subset(dimension_name='plan_business_unit',
                   subset_name=self.subset_name_dynamic,
                   alias='BusinessUnit',
                   expression='{ HIERARCHIZE( {TM1SUBSETALL( [plan_business_unit] )} ) }')
        self.tm1.create_subset(s, private=self.private)

    # 2. get subset
    def test_2get_subset(self):
        s = self.tm1.get_subset(dimension_name='plan_business_unit',
                                subset_name=self.subset_name_static,
                                private=self.private)
        self.assertIsInstance(s, Subset)

        s = self.tm1.get_subset(dimension_name='plan_business_unit',
                                subset_name=self.subset_name_dynamic,
                                private=self.private)
        self.assertIsInstance(s, Subset)

    # 3. update subset
    def test_3update_subset(self):
        s = self.tm1.get_subset(dimension_name='plan_business_unit',
                                subset_name=self.subset_name_static,
                                private=self.private)
        s.add_elements(['10110'])
        # update it
        self.tm1.update_subset(s, private=self.private)

        # get it again
        s = self.tm1.get_subset(dimension_name='plan_business_unit',
                                subset_name=self.subset_name_static,
                                private=self.private)
        # test it !
        self.assertEquals(len(s.elements), 5)

        # get subset
        s = self.tm1.get_subset(dimension_name='plan_business_unit',
                                subset_name=self.subset_name_dynamic,
                                private=self.private)
        s.expression = '{FILTER( {TM1SUBSETALL( [plan_business_unit] )}, [plan_business_unit].[Currency] = "EUR")}'

        # update it
        self.tm1.update_subset(subset=s,
                               private=self.private)

        # get it again
        s = self.tm1.get_subset(dimension_name='plan_business_unit',
                                subset_name=self.subset_name_dynamic,
                                private=self.private)

        # test it !
        self.assertEquals(s.expression, '{FILTER( {TM1SUBSETALL( [plan_business_unit] )}, [plan_business_unit].[Currency] = "EUR")}')



    # 4. delete subset
    def test_4delete_subset(self):
        self.tm1.delete_subset(dimension_name='plan_business_unit',
                               subset_name=self.subset_name_static,
                               private=self.private)
        self.tm1.delete_subset(dimension_name='plan_business_unit',
                               subset_name=self.subset_name_dynamic,
                               private=self.private)

    def test_5logout(self):
        self.tm1.logout()

if __name__ == '__main__':
    unittest.main()
