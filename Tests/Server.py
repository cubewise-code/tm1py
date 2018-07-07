import unittest
import uuid
import random
import datetime
import os
import dateutil.parser
import time
import re
import configparser

from TM1py.Services import TM1Service
from TM1py.Objects import Cube, Dimension, Hierarchy, Process
from TM1py.Exceptions import TM1pyException

config = configparser.ConfigParser()
config.read(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'config.ini'))


class TestServerMethods(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Namings
        cls.prefix = "TM1py_unittest_server_"
        cls.dimension_name1 = cls.prefix + str(uuid.uuid4())
        cls.dimension_name2 = cls.prefix + str(uuid.uuid4())
        cls.cube_name = cls.prefix + str(uuid.uuid4())
        cls.process_name1 = cls.prefix + str(uuid.uuid4())
        cls.process_name2 = cls.prefix + str(uuid.uuid4())

        # Connect to TM1
        cls.tm1 = TM1Service(**config['tm1srv01'])

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

    def test1_get_last_process_message_from_message_log(self):
        # inject process with ItemReject
        p = Process(name=self.process_name1, prolog_procedure="ItemReject('TM1py Tests');")
        self.tm1.processes.create(p)
        try:
            self.tm1.processes.execute(p.name)
        except TM1pyException as e:
            if "ProcessCompletedWithMessages" in e._response:
                pass
            else:
                raise e
        # TM1 takes one second to write to the message-log
        time.sleep(1)
        log_entry = self.tm1.server.get_last_process_message_from_messagelog(p.name)
        regex = re.compile('TM1ProcessError_.*.log')
        self.assertTrue(regex.search(log_entry))
        # inject process that does nothing and runs successfull
        p = Process(name=self.process_name2, prolog_procedure="sText = 'text';")
        self.tm1.processes.create(p)
        self.tm1.processes.execute(p.name)
        # TM1 takes one second to write to the message-log
        time.sleep(1)
        log_entry = self.tm1.server.get_last_process_message_from_messagelog(p.name)
        regex = re.compile('TM1ProcessError_.*.log')
        self.assertFalse(regex.search(log_entry))

    def test2_get_last_transaction_log_entries(self):
        self.tm1.processes.execute_ti_code(lines_prolog="CubeSetLogChanges('{}', {});".format(self.cube_name, 1))

        tmstp = datetime.datetime.utcnow()

        # Generate 3 random numbers
        random_values = [random.uniform(-10, 10) for _ in range(3)]
        # Write value 1 to cube
        cellset = {
            ('2000', 'Value'): random_values[0]
        }
        self.tm1.cubes.cells.write_values(self.cube_name, cellset)

        # Digest time in TM1
        time.sleep(1)

        # Write value 2 to cube
        cellset = {
            ('2001', 'Value'): random_values[1]
        }
        self.tm1.cubes.cells.write_values(self.cube_name, cellset)

        # Digest time in TM1
        time.sleep(1)

        # Write value 3 to cube
        cellset = {
            ('2002', 'Value'): random_values[2]
        }
        self.tm1.cubes.cells.write_values(self.cube_name, cellset)

        # Digest time in TM1
        time.sleep(8)

        user = config['tm1srv01']['user']
        cube = self.cube_name

        # Query transaction log with top filter
        entries = self.tm1.server.get_transaction_log_entries(reverse=True, user=user, cube=cube, top=3)
        values_from_top = [entry['NewValue'] for entry in entries]

        # Query transaction log with Since filter
        entries = self.tm1.server.get_transaction_log_entries(reverse=True, cube=cube, since=tmstp, top=10)
        values_from_since = [entry['NewValue'] for entry in entries]

        # Compare values written to cube vs. values retrieved from transaction log
        self.assertEqual(len(values_from_top), len(values_from_since))
        for v1, v2, v3 in zip(random_values, reversed(values_from_top), reversed(values_from_since)):
            self.assertAlmostEqual(v1, v2, delta=0.000000001)

    def test3_get_transaction_log_entries_from_today(self):
        # get datetime from today at 00:00:00
        today = datetime.datetime.combine(datetime.date.today(), datetime.time(0, 0))
        entries = self.tm1.server.get_transaction_log_entries(reverse=True, since=today)
        self.assertTrue(len(entries) > 0)
        for entry in entries:
            entry_timestamp = dateutil.parser.parse(entry['TimeStamp'])
            # all the entries should have today's date
            entry_date = entry_timestamp.date()
            today_date = datetime.date.today()
            self.assertTrue(entry_date == today_date)

    @classmethod
    def tearDownClass(cls):
        cls.tm1.cubes.delete(cls.cube_name)
        cls.tm1.dimensions.delete(cls.dimension_name1)
        cls.tm1.dimensions.delete(cls.dimension_name2)
        cls.tm1.processes.delete(cls.process_name1)
        cls.tm1.processes.delete(cls.process_name2)
        cls.tm1.logout()

if __name__ == '__main__':
    unittest.main()
