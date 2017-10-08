
import unittest
import uuid
import random

from TM1py.Services import TM1Service
from TM1py.Objects import Cube, Dimension, Hierarchy

from Tests.config import test_config


class TestServerMethods(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Namings
        cls.dimension_name1 = str(uuid.uuid4())
        cls.dimension_name2 = str(uuid.uuid4())
        cls.cube_name = str(uuid.uuid4())

        # Connect to TM1
        cls.tm1 = TM1Service(**test_config)

        # create a simple cube with dimensions to test transactionlog methods
        if not cls.tm1.dimensions.exists(cls.dimension_name1):
            d = Dimension(cls.dimension_name1)
            h = Hierarchy(cls.dimension_name1, cls.dimension_name1)
            h.add_element('Total Years', 'Consolidated')
            h.add_element('No Year', 'Numeric')
            for year in range(1989, 2040, 1):
                h.add_element(str(year), 'Numeric')
                h.add_edge('Total Years', str(year), 1)
            d.add_hierarchy(h)
            cls.tm1.dimensions.create(d)

        if not cls.tm1.dimensions.exists(cls.dimension_name2):
            d = Dimension(cls.dimension_name2)
            h = Hierarchy(cls.dimension_name2, cls.dimension_name2)
            h.add_element('Value', 'Numeric')
            d.add_hierarchy(h)
            cls.tm1.dimensions.create(d)

        if not cls.tm1.cubes.exists(cls.cube_name):
            cube = Cube(cls.cube_name, [cls.dimension_name1, cls.dimension_name2])
            cls.tm1.cubes.create(cube)

    def test_get_last_transaction_log_entries(self):
        # Generate 3 random numbers
        random_values = [random.uniform(-10, 10) for _ in range(3)]
        # Write value 1 to cube
        cellset = {
            ('2000', 'Value'): random_values[0]
        }
        self.tm1.cubes.cells.write_values(self.cube_name, cellset)
        # Write value 2 to cube
        cellset = {
            ('2001', 'Value'): random_values[1]
        }
        self.tm1.cubes.cells.write_values(self.cube_name, cellset)
        # Write value 3 to cube
        cellset = {
            ('2002', 'Value'): random_values[2]
        }
        self.tm1.cubes.cells.write_values(self.cube_name, cellset)
        # Query transaction log
        user = test_config['user']
        cube = self.cube_name
        entries = self.tm1.server.get_transaction_log_entries(reverse=True, user=user, cube=cube, top=3)
        values = [entry['NewValue'] for entry in entries]
        # Compare values written to cube vs. values retrieved from transaction log
        for v1, v2 in zip(random_values, reversed(values)):
            self.assertAlmostEqual(v1, v2, delta=0.000000001)

    @classmethod
    def tearDownClass(cls):
        cls.tm1.cubes.delete(cls.cube_name)
        cls.tm1.logout()

if __name__ == '__main__':
    unittest.main()
