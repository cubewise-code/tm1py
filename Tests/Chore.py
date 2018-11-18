import configparser
import os
import random
import unittest
import uuid
from datetime import datetime

from TM1py.Objects import Chore, ChoreStartTime, ChoreFrequency, ChoreTask, Process
from TM1py.Services import TM1Service

config = configparser.ConfigParser()
config.read(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'config.ini'))

# Hard stuff for this test
PREFIX = "TM1py_Tests_Chore_"
PROCESS_NAME1 = PREFIX + 'Process1'
PROCESS_NAME2 = PREFIX + 'Process2'
CHORE_NAME1 = PREFIX + "Chore1"
CHORE_NAME2 = PREFIX + "Chore2"


class TestChoreMethods(unittest.TestCase):

    # Check if process exists. If not create it
    @classmethod
    def setup_class(cls):
        cls.tm1 = TM1Service(**config['tm1srv01'])

        # create processes
        p1 = Process(name=PROCESS_NAME1)
        p1.add_parameter('pRegion', 'pRegion (String)', value='US')
        if cls.tm1.processes.exists(p1.name):
            cls.tm1.processes.delete(p1.name)
        cls.tm1.processes.create(p1)
        p2 = Process(name=PROCESS_NAME2)
        p2.add_parameter('pRegion', 'pRegion (String)', value='UK')
        if cls.tm1.processes.exists(p2.name):
            cls.tm1.processes.delete(p2.name)
        cls.tm1.processes.create(p2)

        # chore properties
        cls.start_time = datetime.now()
        cls.frequency_days = int(random.uniform(0, 355))
        cls.frequency_hours = int(random.uniform(0, 23))
        cls.frequency_minutes = int(random.uniform(0, 59))
        cls.frequency_seconds = int(random.uniform(0, 59))
        cls.frequency = ChoreFrequency(
            days=cls.frequency_days,
            hours=cls.frequency_hours,
            minutes=cls.frequency_minutes,
            seconds=cls.frequency_seconds)
        cls.tasks = [
            ChoreTask(0, PROCESS_NAME1, parameters=[{'Name': 'pRegion', 'Value': 'UK'}]),
            ChoreTask(1, PROCESS_NAME1, parameters=[{'Name': 'pRegion', 'Value': 'FR'}]),
            ChoreTask(2, PROCESS_NAME1, parameters=[{'Name': 'pRegion', 'Value': 'CH'}])]

    @classmethod
    def setUp(cls):
        # create chores
        c1 = Chore(name=CHORE_NAME1,
                   start_time=ChoreStartTime(cls.start_time.year, cls.start_time.month, cls.start_time.day,
                                             cls.start_time.hour, cls.start_time.minute, cls.start_time.second),
                   dst_sensitivity=False,
                   active=True,
                   execution_mode='MultipleCommit',
                   frequency=cls.frequency,
                   tasks=cls.tasks)
        cls.tm1.chores.create(c1)
        c2 = Chore(name=CHORE_NAME2,
                   start_time=ChoreStartTime(cls.start_time.year, cls.start_time.month, cls.start_time.day,
                                             cls.start_time.hour, cls.start_time.minute, cls.start_time.second),
                   dst_sensitivity=False,
                   active=False,
                   execution_mode='SingleCommit',
                   frequency=cls.frequency,
                   tasks=cls.tasks)
        # No exceptions -> means test passed
        cls.tm1.chores.create(c2)

    @classmethod
    def tearDown(cls):
        cls.tm1.chores.delete(CHORE_NAME1)
        cls.tm1.chores.delete(CHORE_NAME2)

    def test_get_chore(self):
        c1 = self.tm1.chores.get(CHORE_NAME1)
        # check all properties
        self.assertEqual(c1._start_time._datetime, self.start_time.replace(microsecond=0))
        self.assertEqual(c1._name, CHORE_NAME1)
        self.assertEqual(c1.active, True)
        self.assertEqual(c1._dst_sensitivity, False)
        self.assertEqual(c1._execution_mode, 'MultipleCommit')
        self.assertEqual(c1._frequency._days, str(self.frequency_days).zfill(2))
        self.assertEqual(c1._frequency._hours, str(self.frequency_hours).zfill(2))
        self.assertEqual(c1._frequency._minutes, str(self.frequency_minutes).zfill(2))
        self.assertEqual(c1._frequency._seconds, str(self.frequency_seconds).zfill(2))
        for task1, task2 in zip(self.tasks, c1._tasks):
            self.assertEqual(task1, task2)

        c2 = self.tm1.chores.get(CHORE_NAME2)
        # check all properties
        self.assertEqual(c2._start_time._datetime, self.start_time.replace(microsecond=0))
        self.assertEqual(c2._name, CHORE_NAME2)
        self.assertEqual(c2.active, False)
        self.assertEqual(c2._dst_sensitivity, False)
        self.assertEqual(c2._execution_mode, 'SingleCommit')
        self.assertEqual(c2._frequency._days, str(self.frequency_days).zfill(2))
        self.assertEqual(c2._frequency._hours, str(self.frequency_hours).zfill(2))
        self.assertEqual(c2._frequency._minutes, str(self.frequency_minutes).zfill(2))
        self.assertEqual(c2._frequency._seconds, str(self.frequency_seconds).zfill(2))
        for task1, task2 in zip(self.tasks, c2._tasks):
            self.assertEqual(task1, task2)

    def test_get_all(self):
        all_chores = self.tm1.chores.get_all()
        # only check if names are returned
        self.assertIn(CHORE_NAME1, (c.name for c in all_chores))
        self.assertIn(CHORE_NAME2, (c.name for c in all_chores))

    def test_get_all_names(self):
        all_chore_names = self.tm1.chores.get_all_names()
        self.assertIn(CHORE_NAME1, all_chore_names)
        self.assertIn(CHORE_NAME2, all_chore_names)

    def test_update_chore(self):
        # get chore
        c = self.tm1.chores.get(CHORE_NAME1)
        # update all properties
        # update start time
        start_time = datetime.now()
        c._start_time = ChoreStartTime(start_time.year, start_time.month, start_time.day,
                                       start_time.hour, start_time.minute, start_time.second)
        # update frequency
        frequency_days = int(random.uniform(0, 355))
        frequency_hours = int(random.uniform(0, 23))
        frequency_minutes = int(random.uniform(0, 59))
        frequency_seconds = int(random.uniform(0, 59))
        c._frequency = ChoreFrequency(days=frequency_days, hours=frequency_hours,
                                      minutes=frequency_minutes, seconds=frequency_seconds)
        # update tasks
        tasks = [ChoreTask(0, PROCESS_NAME2, parameters=[{'Name': 'pRegion', 'Value': 'DE'}]),
                 ChoreTask(1, PROCESS_NAME2, parameters=[{'Name': 'pRegion', 'Value': 'ES'}]),
                 ChoreTask(2, PROCESS_NAME2, parameters=[{'Name': 'pRegion', 'Value': 'US'}])]
        c._tasks = tasks
        # execution mode
        c._execution_mode = "SingleCommit"
        # activate
        c.deactivate()
        # update chore in TM1
        self.tm1.chores.update(c)
        # get chore and check all properties
        c = self.tm1.chores.get(chore_name=CHORE_NAME1)
        self.assertEqual(c._start_time._datetime.replace(microsecond=0), start_time.replace(microsecond=0))
        self.assertEqual(c._name, CHORE_NAME1)
        self.assertEqual(c._dst_sensitivity, False)
        self.assertEqual(c._active, False)
        self.assertEqual(c._execution_mode, 'SingleCommit')
        self.assertEqual(int(c._frequency._days), int(frequency_days))
        self.assertEqual(int(c._frequency._hours), int(frequency_hours))
        self.assertEqual(int(c._frequency._minutes), int(frequency_minutes))
        self.assertEqual(len(tasks), len(c._tasks))
        # sometimes there is one second difference. Probably a small bug in the REST API
        self.assertAlmostEqual(int(c._frequency._seconds), int(frequency_seconds), delta=1)
        for task1, task2 in zip(tasks, c._tasks):
            self.assertEqual(task1, task2)

    def test_activate(self):
        chore = self.tm1.chores.get(CHORE_NAME1)
        if chore.active:
            self.tm1.chores.deactivate(CHORE_NAME1)
        self.tm1.chores.activate(CHORE_NAME1)

    def test_deactivate(self):
        chore = self.tm1.chores.get(CHORE_NAME1)
        if not chore.active:
            self.tm1.chores.activate(CHORE_NAME1)
        self.tm1.chores.deactivate(CHORE_NAME1)

    def test_execute_chore(self):
        response = self.tm1.chores.execute_chore(CHORE_NAME1)
        self.assertTrue(response.ok)

    def test_exists(self):
        self.assertTrue(self.tm1.chores.exists(CHORE_NAME1))
        self.assertTrue(self.tm1.chores.exists(CHORE_NAME2))
        self.assertFalse(self.tm1.chores.exists(uuid.uuid4()))

    @classmethod
    def teardown_class(cls):
        cls.tm1.processes.delete(PROCESS_NAME1)
        cls.tm1.processes.delete(PROCESS_NAME2)
        cls.tm1.logout()


if __name__ == '__main__':
    unittest.main()
