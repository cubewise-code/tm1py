import configparser
import datetime
import random
import re
import time
import unittest
from datetime import timedelta
from pathlib import Path

import dateutil

from TM1py.Exceptions import TM1pyRestException
from TM1py.Objects import Cube, Dimension, Hierarchy, Process
from TM1py.Services import TM1Service

PREFIX = "TM1py_Tests_Server_"


class TestServerService(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """
        Establishes a connection to TM1 and creates TM! objects to use across all tests
        """

        # Connection to TM1
        cls.config = configparser.ConfigParser()
        cls.config.read(Path(__file__).parent.joinpath('config.ini'))
        cls.tm1 = TM1Service(**cls.config['tm1srv01'])

        # Namings
        cls.dimension_name1 = PREFIX + "Dimension1"
        cls.dimension_name2 = PREFIX + "Dimension2"
        cls.cube_name = PREFIX + "Cube1"
        cls.process_name1 = PREFIX + "Process1"
        cls.process_name2 = PREFIX + "Process2"

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

        # inject process with ItemReject
        cls.process1 = Process(name=cls.process_name1, prolog_procedure="ItemReject('TM1py Tests');")
        cls.tm1.processes.create(cls.process1)

        # inject process that does nothing and runs successfull
        cls.process2 = Process(name=cls.process_name2, prolog_procedure="sText = 'text';")
        cls.tm1.processes.create(cls.process2)

    def test_get_server_name(self):
        server_name = self.tm1.server.get_server_name()
        self.assertIsInstance(server_name, str)
        self.assertGreater(len(server_name), 0)

        active_configuration = self.tm1.server.get_active_configuration()
        self.assertEqual(server_name, active_configuration["ServerName"])

    def test_get_product_version(self):
        product_version = self.tm1.server.get_product_version()
        self.assertIsInstance(product_version, str)
        self.assertGreater(len(product_version), 0)
        self.assertGreaterEqual(int(product_version[0:2]), 10)

    def test_get_admin_host(self):
        admin_host = self.tm1.server.get_admin_host()
        self.assertIsInstance(admin_host, str)

    def test_get_data_directory(self):
        data_directory = self.tm1.server.get_data_directory()
        self.assertIsInstance(data_directory, str)
        self.assertGreater(len(data_directory), 0)

        active_configuration = self.tm1.server.get_active_configuration()
        self.assertEqual(data_directory, active_configuration["Administration"]["DataBaseDirectory"])

    def test_get_static_configuration(self):
        static_configuration = self.tm1.server.get_static_configuration()
        self.assertIsInstance(static_configuration, dict)
        self.assertIn("ServerName", static_configuration)
        self.assertIn("Access", static_configuration)
        self.assertIn("Administration", static_configuration)
        self.assertIn("Modelling", static_configuration)
        self.assertIn("Performance", static_configuration)

    def test_get_active_configuration(self):
        active_configuration = self.tm1.server.get_active_configuration()
        self.assertEqual(
            int(self.tm1._tm1_rest._port),
            int(active_configuration["Access"]["HTTP"]["Port"]))

    def test_update_static_configuration(self):
        for new_mtq_threads in (4, 8):
            config_changes = {
                "Performance": {
                    "MTQ": {
                        "NumberOfThreadsToUse": new_mtq_threads
                    }
                }
            }
            response = self.tm1.server.update_static_configuration(config_changes)
            self.assertTrue(response.ok)

            active_config = self.tm1.server.get_active_configuration()
            self.assertEqual(
                active_config["Performance"]["MTQ"]["NumberOfThreadsToUse"],
                new_mtq_threads - 1)

    @unittest.skip("Doesn't work sometimes")
    def test_get_last_process_message_from_message_log(self):
        try:
            self.tm1.processes.execute(self.process_name1)
        except TM1pyRestException as e:
            if "ProcessCompletedWithMessages" in e.response:
                pass
            else:
                raise e
        # TM1 takes one second to write to the message-log
        time.sleep(1)
        log_entry = self.tm1.server.get_last_process_message_from_messagelog(self.process_name1)
        regex = re.compile('TM1ProcessError_.*.log')
        self.assertTrue(regex.search(log_entry))

        self.tm1.processes.execute(self.process_name2)
        # TM1 takes one second to write to the message-log
        time.sleep(1)
        log_entry = self.tm1.server.get_last_process_message_from_messagelog(self.process_name2)
        regex = re.compile('TM1ProcessError_.*.log')
        self.assertFalse(regex.search(log_entry))

    def test_get_last_transaction_log_entries(self):
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

        user = self.config['tm1srv01']['user']
        cube = self.cube_name

        # Query transaction log with top filter
        entries = self.tm1.server.get_transaction_log_entries(
            reverse=True,
            user=user,
            cube=cube,
            top=3)
        values_from_top = [entry['NewValue'] for entry in entries]
        self.assertGreaterEqual(len(values_from_top), 3)

        # Query transaction log with Since filter
        entries = self.tm1.server.get_transaction_log_entries(
            reverse=True,
            cube=cube,
            since=tmstp,
            top=10)
        values_from_since = [entry['NewValue'] for entry in entries]
        self.assertGreaterEqual(len(values_from_since), 3)

        # Compare values written to cube vs. values retrieved from transaction log
        self.assertEqual(len(values_from_top), len(values_from_since))
        for v1, v2, v3 in zip(random_values, reversed(values_from_top), reversed(values_from_since)):
            self.assertAlmostEqual(v1, v2, delta=0.000000001)

    def test_get_transaction_log_entries_from_today(self):
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

    def test_get_transaction_log_entries_until_yesterday(self):
        # get datetime until yesterday at 00:00:00
        yesterday = datetime.datetime.combine(datetime.date.today() - timedelta(days=1), datetime.time(0, 0))
        entries = self.tm1.server.get_transaction_log_entries(reverse=True, until=yesterday)
        self.assertTrue(len(entries) > 0)
        for entry in entries:
            # skip invalid timestamps from log
            if entry['TimeStamp'] == '0000-00-00T00:00Z':
                continue

            entry_timestamp = dateutil.parser.parse(entry['TimeStamp'])
            entry_date = entry_timestamp.date()
            yesterdays_date = datetime.date.today() - timedelta(days=1)
            self.assertTrue(entry_date <= yesterdays_date)

    def test_get_message_log_entries_from_today(self):
        # get datetime from today at 00:00:00
        today = datetime.datetime.combine(datetime.date.today(), datetime.time(0, 0))
        entries = self.tm1.server.get_message_log_entries(reverse=True, since=today)

        for entry in entries:
            entry_timestamp = dateutil.parser.parse(entry['TimeStamp'])
            # all the entries should have today's date
            entry_date = entry_timestamp.date()
            today_date = datetime.date.today()
            self.assertTrue(entry_date == today_date)

    def test_get_message_log_entries_until_yesterday(self):
        # get datetime until yesterday at 00:00:00
        yesterday = datetime.datetime.combine(datetime.date.today() - timedelta(days=1), datetime.time(0, 0))

        entries = self.tm1.server.get_message_log_entries(reverse=True, until=yesterday)
        self.assertTrue(len(entries) > 0)
        for entry in entries:
            # skip invalid timestamps from log
            if entry['TimeStamp'] == '0000-00-00T00:00Z':
                continue

            entry_timestamp = dateutil.parser.parse(entry['TimeStamp'])
            entry_date = entry_timestamp.date()
            yesterdays_date = datetime.date.today() - timedelta(days=1)
            self.assertTrue(entry_date <= yesterdays_date)

    def test_get_message_log_entries_only_yesterday(self):
        # get datetime only yesterday at 00:00:00
        yesterday = datetime.datetime.combine(datetime.date.today() - timedelta(days=1), datetime.time(0, 0))
        today = datetime.datetime.combine(datetime.date.today() - timedelta(days=1), datetime.time(0, 0))

        entries = self.tm1.server.get_message_log_entries(reverse=True, since=yesterday, until=today)
        for entry in entries:
            entry_timestamp = dateutil.parser.parse(entry['TimeStamp'])
            entry_date = entry_timestamp.date()
            yesterdays_date = datetime.date.today() - timedelta(days=1)
            self.assertTrue(entry_date == yesterdays_date)

    def test_get_message_log_with_contains_single(self):
        wildcards = ['TM1 Server is READY']

        entries = self.tm1.server.get_message_log_entries(
            reverse=True,
            msg_contains=wildcards,
            msg_contains_operator="AND")

        self.assertGreater(len(entries), 1)

        for entry in entries:
            message = entry['Message'].upper().replace(' ', '')

            self.assertIn(wildcards[0].upper().replace(' ', ''), message)

    def test_get_message_log_with_contains_filter_and(self):

        wildcards = ['TM1 Server is ready', 'elapsed time']

        entries = self.tm1.server.get_message_log_entries(
            reverse=True,
            msg_contains=wildcards,
            msg_contains_operator="AND")

        self.assertGreater(len(entries), 1)

        for entry in entries:
            message = entry['Message'].upper().replace(' ', '')

            self.assertIn(wildcards[0].upper().replace(' ', ''), message)
            self.assertIn(wildcards[1].upper().replace(' ', ''), message)

    def test_get_message_log_with_contains_filter_or_1(self):

        wildcards = ['TM1 Server is ready', 'invalid entry']

        entries = self.tm1.server.get_message_log_entries(
            reverse=True,
            msg_contains=wildcards,
            msg_contains_operator="OR")

        self.assertGreater(len(entries), 1)

        for entry in entries:
            message = entry['Message'].upper().replace(' ', '')

            self.assertIn(wildcards[0].upper().replace(' ', ''), message)
            self.assertNotIn(wildcards[1].upper().replace(' ', ''), message)

    def test_get_message_log_with_contains_filter_or_2(self):

        wildcards = ['invalid entry', 'elapsed time']

        entries = self.tm1.server.get_message_log_entries(
            reverse=True,
            msg_contains=wildcards,
            msg_contains_operator="OR")

        self.assertGreater(len(entries), 1)

        for entry in entries:
            message = entry['Message'].upper().replace(' ', '')

            self.assertNotIn(wildcards[0].upper().replace(' ', ''), message)
            self.assertIn(wildcards[1].upper().replace(' ', ''), message)

    def test_session_context_default(self):
        threads = self.tm1.monitoring.get_threads()
        for thread in threads:
            if "GET /api/v1/Threads" in thread["Function"] and thread["Name"] == self.config['tm1srv01']['user']:
                self.assertTrue(thread["Context"] == "TM1py")
                return
        raise Exception("Did not find my own Thread")

    def test_session_context_custom(self):
        app_name = "Some Application"
        with TM1Service(**self.config['tm1srv01'], session_context=app_name) as tm1:
            threads = tm1.monitoring.get_threads()
            for thread in threads:
                if "GET /api/v1/Threads" in thread["Function"] and thread["Name"] == self.config['tm1srv01']['user']:
                    self.assertTrue(thread["Context"] == app_name)
                    return
        raise Exception("Did not find my own Thread")

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
