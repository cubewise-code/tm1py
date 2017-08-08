import random
import unittest
import uuid

from TM1py.Objects import Dimension
from TM1py.Objects import Element
from TM1py.Objects import ElementAttribute
from TM1py.Objects import Hierarchy
from TM1py.Objects import Subset
from TM1py.Services import DimensionService
from TM1py.Services import LoginService
from TM1py.Services import RESTService
from TM1py.Services import SubsetService

# Configuration for tests
port = 8001
user = 'admin'
pwd = 'apple'


class TestSubsetMethods(unittest.TestCase):
    login = LoginService.native(user, pwd)
    tm1_rest = RESTService(ip='', port=port, login=login, ssl=False)
    subset_service = SubsetService(tm1_rest)

    # Do random stuff
    random_string = str(uuid.uuid4())
    private = bool(random.getrandbits(1))

    # Define Names
    dimension_name = 'TM1py_unittest_dimension_' + random_string
    subset_name_static = 'TM1py_unittest_static_subset_' + random_string
    subset_name_dynamic = 'TM1py_unittest_dynamic_subset_' + random_string

    # Instantiate Subsets
    static_subset = Subset(dimension_name=dimension_name,
                           subset_name=subset_name_static,
                           elements=['USD', 'EUR', 'NZD'])
    dynamic_subset = Subset(dimension_name=dimension_name,
                            subset_name=subset_name_dynamic,
                            expression='{ HIERARCHIZE( {TM1SUBSETALL( [' + dimension_name + '] )} ) }')

    # Check if Dimensions exists. If not create it
    @classmethod
    def setup_class(cls):
        tm1_rest = RESTService(ip='', port=port, login=LoginService.native(user, pwd), ssl=False)
        dimension_service = DimensionService(tm1_rest)
        elements = [Element('USD', 'Numeric'),
                    Element('EUR', 'Numeric'),
                    Element('JPY', 'Numeric'),
                    Element('CNY', 'Numeric'),
                    Element('GBP', 'Numeric'),
                    Element('NZD', 'Numeric')]
        element_attributes = [ElementAttribute('Currency Name', 'String')]
        h = Hierarchy(cls.dimension_name, cls.dimension_name, elements, element_attributes)
        d = Dimension(cls.dimension_name, hierarchies=[h])
        dimension_service.create(d)
        tm1_rest.logout()

    # 1. Create subset
    def test_1create_subset(self):
        self.subset_service.create(self.static_subset, private=self.private)
        self.subset_service.create(self.dynamic_subset, private=self.private)

    # 2. Get subset
    def test_2get_subset(self):
        s = self.subset_service.get(dimension_name=self.dimension_name,
                                    subset_name=self.subset_name_static,
                                    private=self.private)
        self.assertEqual(self.static_subset.body, s.body)
        s = self.subset_service.get(dimension_name=self.dimension_name,
                                    subset_name=self.subset_name_dynamic,
                                    private=self.private)
        self.assertEqual(self.dynamic_subset.body, s.body)

    # 3. Update subset
    def test_3update_subset(self):
        s = self.subset_service.get(dimension_name=self.dimension_name,
                                    subset_name=self.subset_name_static,
                                    private=self.private)
        s.add_elements(['NZD'])
        # Update it
        self.subset_service.update(s, private=self.private)
        # Get it again
        s = self.subset_service.get(dimension_name=self.dimension_name,
                                    subset_name=self.subset_name_static,
                                    private=self.private)
        # Test it !
        self.assertEquals(len(s.elements), 4)
        # Get subset
        s = self.subset_service.get(dimension_name=self.dimension_name,
                                    subset_name=self.subset_name_dynamic,
                                    private=self.private)

        s.expression = '{{ [{}].[EUR], [{}].[USD] }})'.format(self.dimension_name, self.dimension_name)
        # Update it
        self.subset_service.update(subset=s,
                                   private=self.private)
        # Get it again
        s = self.subset_service.get(dimension_name=self.dimension_name,
                                    subset_name=self.subset_name_dynamic,
                                    private=self.private)
        # Test it !
        self.assertEquals(s.expression,
                          '{{ [{}].[EUR], [{}].[USD] }})'.format(self.dimension_name, self.dimension_name))

    # 4. Delete subsets
    def test_4delete_subset(self):
        self.subset_service.delete(dimension_name=self.dimension_name,
                                   subset_name=self.subset_name_static,
                                   private=self.private)
        self.subset_service.delete(dimension_name=self.dimension_name,
                                   subset_name=self.subset_name_dynamic,
                                   private=self.private)

    @classmethod
    def teardown_class(cls):
        dimension_service = DimensionService(cls.tm1_rest)
        dimension_service.delete(cls.dimension_name)
        cls.tm1_rest.logout()

if __name__ == '__main__':
    unittest.main()
