import random
import unittest
import uuid
from datetime import datetime

from TM1py.Objects import Chore, ChoreStartTime, ChoreFrequency, ChoreTask, Process
from TM1py.Services import ChoreService, LoginService, ProcessService, RESTService

# Configuration for tests
port = 8001
user = 'admin'
pwd = 'apple'
process_name1 = 'TM1py_unittest_process1'
process_name2 = 'TM1py_unittest_process2'


class TestChoreMethods(unittest.TestCase):
    login = LoginService.native(user, pwd)
    tm1_rest = RESTService(ip='', port=port, login=login, ssl=False)

    chore_service = ChoreService(tm1_rest)

    # chore properties
    chore_name = 'TM1py_unittest_chore_' + str(uuid.uuid4())
    start_time = datetime.now()
    frequency_days = int(random.uniform(0, 355))
    frequency_hours = int(random.uniform(0, 23))
    frequency_minutes = int(random.uniform(0, 59))
    frequency_seconds = int(random.uniform(0, 59))
    frequency = ChoreFrequency(days=frequency_days, hours=frequency_hours,
                               minutes=frequency_minutes, seconds=frequency_seconds)

    tasks = [ChoreTask(0, process_name1, parameters=[{'Name': 'pRegion', 'Value': 'UK'}]),
             ChoreTask(1, process_name1, parameters=[{'Name': 'pRegion', 'Value': 'FR'}]),
             ChoreTask(2, process_name1, parameters=[{'Name': 'pRegion', 'Value': 'CH'}])]

    # Check if process exists. If not create it
    @classmethod
    def setup_class(cls):
        process_service = ProcessService(cls.tm1_rest)
        p1 = Process(name=process_name1)
        p1.add_parameter('pRegion', 'pRegion (String)', value='US')
        if process_service.exists(p1.name):
            process_service.delete(p1.name)
        process_service.create(p1)
        p2 = Process(name=process_name2)
        p2.add_parameter('pRegion', 'pRegion (String)', value='UK')
        if process_service.exists(p2.name):
            process_service.delete(p2.name)
        process_service.create(p2)

    # 1. Create chore
    def test_1create_chore(self):
        c = Chore(name=self.chore_name,
                  start_time=ChoreStartTime(self.start_time.year, self.start_time.month, self.start_time.day,
                                            self.start_time.hour, self.start_time.minute, self.start_time.second),
                  dst_sensitivity=False,
                  active=True,
                  execution_mode='MultipleCommit',
                  frequency=self.frequency,
                  tasks=self.tasks)
        # No exceptions -> means test passed
        self.chore_service.create(c)

    # 2. Get chore
    def test_2get_chore(self):
        c = self.chore_service.get(self.chore_name)
        # check all properties
        self.assertEqual(c._start_time._datetime, self.start_time.replace(microsecond=0))
        self.assertEqual(c._name, self.chore_name)
        self.assertEqual(c._dst_sensitivity, False)
        self.assertEqual(c._active, True)
        self.assertEqual(c._execution_mode, 'MultipleCommit')
        self.assertEqual(c._frequency._days, str(self.frequency_days))
        self.assertEqual(c._frequency._hours, str(self.frequency_hours).zfill(2))
        self.assertEqual(c._frequency._minutes, str(self.frequency_minutes).zfill(2))
        self.assertEqual(c._frequency._seconds, str(self.frequency_seconds).zfill(2))
        for task1, task2 in zip(self.tasks, c._tasks):
            self.assertEqual(task1, task2)

    # 3. Update chore
    def test_3update_chore(self):
        # get chore
        c = self.chore_service.get(self.chore_name)

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
        tasks = [ChoreTask(0, process_name2, parameters=[{'Name': 'pRegion', 'Value': 'DE'}]),
                 ChoreTask(1, process_name2, parameters=[{'Name': 'pRegion', 'Value': 'ES'}]),
                 ChoreTask(2, process_name2, parameters=[{'Name': 'pRegion', 'Value': 'US'}])]
        c._tasks = tasks

        # execution mode
        c._execution_mode = "SingleCommit"

        # activate
        c.deactivate()

        # update chore in TM1
        self.chore_service.update(c)

        # get chore and check all properties
        c = self.chore_service.get(chore_name=self.chore_name)
        self.assertEqual(c._start_time._datetime.replace(microsecond=0), start_time.replace(microsecond=0))
        self.assertEqual(c._name, self.chore_name)
        self.assertEqual(c._dst_sensitivity, False)
        self.assertEqual(c._active, False)
        self.assertEqual(c._execution_mode, 'SingleCommit')
        self.assertEqual(c._frequency._days, str(frequency_days))
        self.assertEqual(c._frequency._hours, str(frequency_hours).zfill(2))
        self.assertEqual(c._frequency._minutes, str(frequency_minutes).zfill(2))
        self.assertEqual(c._frequency._seconds, str(frequency_seconds).zfill(2))
        for task1, task2 in zip(tasks, c._tasks):
            self.assertEqual(task1, task2)

    # 4. Delete chore
    def test_4delete_chore(self):
        self.chore_service.delete(self.chore_name)

    @classmethod
    def teardown_class(cls):
        process_service = ProcessService(cls.tm1_rest)
        process_service.delete(process_name1)
        process_service.delete(process_name2)
        cls.tm1_rest.logout()

if __name__ == '__main__':
    unittest.main()
