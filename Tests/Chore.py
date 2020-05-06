import configparser
import copy
import random
import unittest
import uuid
from datetime import datetime
from pathlib import Path

from TM1py.Objects import Chore, ChoreStartTime, ChoreFrequency, ChoreTask, Process
from TM1py.Services import TM1Service

config = configparser.ConfigParser()
config.read(Path(__file__).parent.joinpath('config.ini'))

# Hard stuff for this test
PREFIX = "TM1py_Tests_Chore_"
PROCESS_NAME1 = PREFIX + 'Process1'
PROCESS_NAME2 = PREFIX + 'Process2'
CHORE_NAME1 = PREFIX + "Chore1"
CHORE_NAME2 = PREFIX + "Chore2"
CHORE_NAME3 = PREFIX + "Chore3"
CHORE_NAME4 = PREFIX + "Chore4"


class TestChoreMethods(unittest.TestCase):
    tm1 = None
    start_time = None
    frequency = None
    tasks = None

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
                   execution_mode=Chore.MULTIPLE_COMMIT,
                   frequency=cls.frequency,
                   tasks=cls.tasks)
        cls.tm1.chores.create(c1)

        c2 = Chore(name=CHORE_NAME2,
                   start_time=ChoreStartTime(cls.start_time.year, cls.start_time.month, cls.start_time.day,
                                             cls.start_time.hour, cls.start_time.minute, cls.start_time.second),
                   dst_sensitivity=False,
                   active=False,
                   execution_mode=Chore.SINGLE_COMMIT,
                   frequency=cls.frequency,
                   tasks=cls.tasks)
        cls.tm1.chores.create(c2)

        # chore without tasks
        c3 = copy.copy(c2)
        c3.name = CHORE_NAME3
        c3.tasks = []
        cls.tm1.chores.create(c3)

    @classmethod
    def tearDown(cls):
        if cls.tm1.chores.exists(CHORE_NAME1):
            cls.tm1.chores.delete(CHORE_NAME1)
        if cls.tm1.chores.exists(CHORE_NAME2):
            cls.tm1.chores.delete(CHORE_NAME2)
        if cls.tm1.chores.exists(CHORE_NAME3):
            cls.tm1.chores.delete(CHORE_NAME3)
        if cls.tm1.chores.exists(CHORE_NAME4):
            cls.tm1.chores.delete(CHORE_NAME4)

    def test_create_chore_with_dst(self):
        # create chores
        c4 = Chore(name=CHORE_NAME4,
                   start_time=ChoreStartTime(self.start_time.year, self.start_time.month, self.start_time.day,
                                             self.start_time.hour, self.start_time.minute, self.start_time.second),
                   dst_sensitivity=True,
                   active=True,
                   execution_mode=Chore.MULTIPLE_COMMIT,
                   frequency=self.frequency,
                   tasks=self.tasks)
        self.tm1.chores.create(c4)

        c4 = self.tm1.chores.get(CHORE_NAME4)

        # delta in start time is expected to be <= 1h due to potential DST
        self.assertLessEqual(abs(c4.start_time.datetime.hour - self.start_time.hour), 1)
        self.assertEqual(c4._start_time._datetime.replace(hour=0), self.start_time.replace(hour=0, microsecond=0))
        self.assertEqual(c4._name, CHORE_NAME4)
        self.assertEqual(c4.active, True)
        self.assertEqual(c4._dst_sensitivity, True)
        # Fails on TM1 <= 11.7.00002.1.
        self.assertEqual(c4._execution_mode, Chore.MULTIPLE_COMMIT)
        self.assertEqual(c4._frequency._days, str(self.frequency_days).zfill(2))
        self.assertEqual(c4._frequency._hours, str(self.frequency_hours).zfill(2))
        self.assertEqual(c4._frequency._minutes, str(self.frequency_minutes).zfill(2))
        self.assertEqual(c4._frequency._seconds, str(self.frequency_seconds).zfill(2))
        for task1, task2 in zip(self.tasks, c4._tasks):
            self.assertEqual(task1, task2)

    def test_get_chore(self):
        c1 = self.tm1.chores.get(CHORE_NAME1)
        # check all properties
        self.assertEqual(c1._start_time._datetime, self.start_time.replace(microsecond=0))
        self.assertEqual(c1._name, CHORE_NAME1)
        self.assertEqual(c1.active, True)
        self.assertEqual(c1._dst_sensitivity, False)
        self.assertEqual(c1._execution_mode, Chore.MULTIPLE_COMMIT)
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
        self.assertEqual(c2._execution_mode, Chore.SINGLE_COMMIT)
        self.assertEqual(c2._frequency._days, str(self.frequency_days).zfill(2))
        self.assertEqual(c2._frequency._hours, str(self.frequency_hours).zfill(2))
        self.assertEqual(c2._frequency._minutes, str(self.frequency_minutes).zfill(2))
        self.assertEqual(c2._frequency._seconds, str(self.frequency_seconds).zfill(2))
        for task1, task2 in zip(self.tasks, c2._tasks):
            self.assertEqual(task1, task2)

    def test_get_chore_without_tasks(self):
        c3 = self.tm1.chores.get(chore_name=CHORE_NAME3)
        self.assertFalse(len(c3.tasks))

    def test_get_all(self):
        all_chores = self.tm1.chores.get_all()
        # only check if names are returned
        self.assertIn(CHORE_NAME1, (c.name for c in all_chores))
        self.assertIn(CHORE_NAME2, (c.name for c in all_chores))
        self.assertIn(CHORE_NAME3, (c.name for c in all_chores))

    def test_get_all_names(self):
        all_chore_names = self.tm1.chores.get_all_names()
        self.assertIn(CHORE_NAME1, all_chore_names)
        self.assertIn(CHORE_NAME2, all_chore_names)
        self.assertIn(CHORE_NAME3, all_chore_names)

    def test_update_chore_dst(self):
        # get chore
        c = self.tm1.chores.get(CHORE_NAME1)
        # update all properties
        # update start time
        start_time = datetime(2020, 5, 6, 17, 4, 2)
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
        c._execution_mode = Chore.SINGLE_COMMIT
        # dst sensitivity
        c.dst_sensitivity = True
        # activate
        c.deactivate()
        # update chore in TM1
        self.tm1.chores.update(c)
        # get chore and check all properties
        c = self.tm1.chores.get(chore_name=CHORE_NAME1)

        # delta in start time is expected to be <= 1h due to potential DST
        self.assertLessEqual(abs(c.start_time.datetime.hour - start_time.hour), 1)
        self.assertEqual(c._start_time._datetime.replace(hour=0), start_time.replace(hour=0))

        self.assertEqual(c._name, CHORE_NAME1)
        self.assertEqual(c._dst_sensitivity, True)
        self.assertEqual(c._active, False)
        self.assertEqual(c._execution_mode, Chore.SINGLE_COMMIT)
        self.assertEqual(int(c._frequency._days), int(frequency_days))
        self.assertEqual(int(c._frequency._hours), int(frequency_hours))
        self.assertEqual(int(c._frequency._minutes), int(frequency_minutes))
        self.assertEqual(len(tasks), len(c._tasks))
        # sometimes there is one second difference. Probably a small bug in the REST API
        self.assertAlmostEqual(int(c._frequency._seconds), int(frequency_seconds), delta=1)
        for task1, task2 in zip(tasks, c._tasks):
            self.assertEqual(task1, task2)

    def test_update_active_chore(self):
        self.tm1.chores.activate(CHORE_NAME1)

        c = self.tm1.chores.get(CHORE_NAME1)
        c.execution_mode = Chore.MULTIPLE_COMMIT

        self.tm1.chores.update(c)

        c = self.tm1.chores.get(chore_name=CHORE_NAME1)

        self.assertEqual(c.execution_mode, Chore.MULTIPLE_COMMIT)

    def test_update_chore_without_tasks(self):
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

        # execution mode
        c._execution_mode = Chore.SINGLE_COMMIT
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
        self.assertEqual(c._execution_mode, Chore.SINGLE_COMMIT)
        self.assertEqual(int(c._frequency._days), int(frequency_days))
        self.assertEqual(int(c._frequency._hours), int(frequency_hours))
        self.assertEqual(int(c._frequency._minutes), int(frequency_minutes))

    def test_update_chore_add_tasks(self):
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
                 ChoreTask(2, PROCESS_NAME2, parameters=[{'Name': 'pRegion', 'Value': 'CH'}]),
                 ChoreTask(3, PROCESS_NAME2, parameters=[{'Name': 'pRegion', 'Value': 'US'}])]
        c._tasks = tasks
        # execution mode
        c._execution_mode = Chore.SINGLE_COMMIT
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
        self.assertEqual(c._execution_mode, Chore.SINGLE_COMMIT)
        self.assertEqual(int(c._frequency._days), int(frequency_days))
        self.assertEqual(int(c._frequency._hours), int(frequency_hours))
        self.assertEqual(int(c._frequency._minutes), int(frequency_minutes))
        self.assertEqual(len(tasks), len(c._tasks))
        # sometimes there is one second difference. Probably a small bug in the REST API
        self.assertAlmostEqual(int(c._frequency._seconds), int(frequency_seconds), delta=1)
        for task1, task2 in zip(tasks, c._tasks):
            self.assertEqual(task1, task2)

    def test_update_chore_remove_tasks(self):
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
                 ChoreTask(1, PROCESS_NAME2, parameters=[{'Name': 'pRegion', 'Value': 'US'}])]
        c._tasks = tasks
        # execution mode
        c._execution_mode = Chore.SINGLE_COMMIT
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
        self.assertEqual(c._execution_mode, Chore.SINGLE_COMMIT)
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
        self.assertTrue(self.tm1.chores.exists(CHORE_NAME3))
        self.assertFalse(self.tm1.chores.exists(uuid.uuid4()))

    @classmethod
    def teardown_class(cls):
        cls.tm1.processes.delete(PROCESS_NAME1)
        cls.tm1.processes.delete(PROCESS_NAME2)
        cls.tm1.logout()


if __name__ == '__main__':
    unittest.main()
