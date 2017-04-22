from TM1py import TM1pyQueries as TM1, TM1pyLogin, Chore, ChoreFrequency, ChoreStartTime, ChoreTask
import uuid
import unittest
import random
from datetime import datetime

class TestChoreMethods(unittest.TestCase):
    login = TM1pyLogin.native('admin', 'apple')
    tm1 = TM1(ip='', port=8001, login=login, ssl=False)

    # chore properties
    chore_name = 'TM1py_unittest_chore_' + str(uuid.uuid4())
    start_time = datetime.now()
    frequency_days = int(random.uniform(0, 355))
    frequency_hours = int(random.uniform(0, 23))
    frequency_minutes = int(random.uniform(0, 59))
    frequency_seconds = int(random.uniform(0, 59))

    tasks = [ChoreTask(0, 'import_actuals', parameters=[{'Name': 'region', 'Value': 'UK'}]),
             ChoreTask(1, 'import_actuals', parameters=[{'Name': 'region', 'Value': 'FR'}]),
             ChoreTask(2, 'import_actuals', parameters=[{'Name': 'region', 'Value': 'CH'}])]

    # 1. create chore
    def test_1create_chore(self):

        frequency = ChoreFrequency(days=self.frequency_days, hours=self.frequency_hours,
                                   minutes=self.frequency_minutes, seconds=self.frequency_seconds)

        c = Chore(name=self.chore_name,
                  start_time=ChoreStartTime(self.start_time.year, self.start_time.month, self.start_time.day,
                                            self.start_time.hour, self.start_time.minute, self.start_time.second),
                  dst_sensitivity=False,
                  active=True,
                  execution_mode='MultipleCommit',
                  frequency=frequency,
                  tasks=self.tasks)


        # no exceptions means test passed
        self.tm1.create_chore(c)

    # 2. get chore
    def test_2get_chore(self):
        c = self.tm1.get_chore(self.chore_name)
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

    # 3. update chore
    def test_3update_chore(self):
        # get chore
        c = self.tm1.get_chore(self.chore_name)

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
        tasks = [ChoreTask(0, 'import_forecast', parameters=[{'Name': 'region', 'Value': 'DE'}]),
                 ChoreTask(1, 'import_forecast', parameters=[{'Name': 'region', 'Value': 'ES'}]),
                 ChoreTask(2, 'import_forecast', parameters=[{'Name': 'region', 'Value': 'US'}])]
        c._tasks = tasks

        # execution mode
        c._execution_mode = "SingleCommit"

        # active
        c.deactivate()

        # update chore in TM1
        self.tm1.update_chore(c)

        # get chore and check all properties
        c = self.tm1.get_chore(chore_name=self.chore_name)
        self.assertEqual(c._start_time._datetime.replace(microsecond=0), self.start_time.replace(microsecond=0))
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

    # 4. delete chore
    def test_4delete_chore(self):
        self.tm1.delete_chore(self.chore_name)

    # logout
    def test_5logout(self):
        pass
        self.tm1.logout()

if __name__ == '__main__':
    unittest.main()
