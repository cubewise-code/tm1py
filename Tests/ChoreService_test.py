import configparser
import copy
import random
import unittest
import uuid
from datetime import datetime
from pathlib import Path

from TM1py.Objects import Chore, ChoreFrequency, ChoreStartTime, ChoreTask, Process
from TM1py.Services import TM1Service

from .Utils import skip_if_version_lower_than


class TestChoreService(unittest.TestCase):
    tm1: TM1Service
    prefix = "TM1py_Tests_Chore_"
    process_name1 = prefix + "Process1"
    process_name2 = prefix + "Process2"
    chore_name1 = prefix + "Chore1"
    chore_name2 = prefix + "Chore2"
    chore_name3 = prefix + "Chore3"
    chore_name4 = prefix + "Chore4"
    start_time = datetime.now()
    frequency_days = int(random.uniform(0, 355))
    frequency_hours = int(random.uniform(0, 23))
    frequency_minutes = int(random.uniform(0, 59))
    frequency_seconds = int(random.uniform(0, 59))
    frequency = ChoreFrequency(
        days=frequency_days, hours=frequency_hours, minutes=frequency_minutes, seconds=frequency_seconds
    )
    tasks = [
        ChoreTask(0, process_name1, parameters=[{"Name": "pRegion", "Value": "UK"}]),
        ChoreTask(1, process_name1, parameters=[{"Name": "pRegion", "Value": "FR"}]),
        ChoreTask(2, process_name1, parameters=[{"Name": "pRegion", "Value": "CH"}]),
    ]

    @classmethod
    def setUpClass(cls):
        """
        Establishes a connection to TM1 and creates objects to use across all tests
        """

        # Connection to TM1
        cls.config = configparser.ConfigParser()
        cls.config.read(Path(__file__).parent.joinpath("config.ini"))
        cls.tm1 = TM1Service(**cls.config["tm1srv01"])

        # create processes
        p1 = Process(name=cls.process_name1)
        p1.add_parameter("pRegion", "pRegion (String)", value="US")

        cls.tm1.processes.update_or_create(p1)
        p2 = Process(name=cls.process_name2)
        p2.add_parameter("pRegion", "pRegion (String)", value="UK")
        cls.tm1.processes.update_or_create(p2)

    def setUp(self):
        # create chores
        c1 = Chore(
            name=self.chore_name1,
            start_time=ChoreStartTime(
                self.start_time.year,
                self.start_time.month,
                self.start_time.day,
                self.start_time.hour,
                self.start_time.minute,
                self.start_time.second,
            ),
            dst_sensitivity=True,
            active=True,
            execution_mode=Chore.MULTIPLE_COMMIT,
            frequency=self.frequency,
            tasks=self.tasks,
        )
        self.tm1.chores.update_or_create(c1)

        c2 = Chore(
            name=self.chore_name2,
            start_time=ChoreStartTime(
                self.start_time.year,
                self.start_time.month,
                self.start_time.day,
                self.start_time.hour,
                self.start_time.minute,
                self.start_time.second,
            ),
            dst_sensitivity=True,
            active=False,
            execution_mode=Chore.SINGLE_COMMIT,
            frequency=self.frequency,
            tasks=self.tasks,
        )
        self.tm1.chores.update_or_create(c2)

        # chore without tasks
        c3 = copy.copy(c2)
        c3.name = self.chore_name3
        c3.tasks = []
        self.tm1.chores.update_or_create(c3)

    def tearDown(self):
        if self.tm1.chores.exists(self.chore_name1):
            self.tm1.chores.delete(self.chore_name1)
        if self.tm1.chores.exists(self.chore_name2):
            self.tm1.chores.delete(self.chore_name2)
        if self.tm1.chores.exists(self.chore_name3):
            self.tm1.chores.delete(self.chore_name3)
        if self.tm1.chores.exists(self.chore_name4):
            self.tm1.chores.delete(self.chore_name4)

    @skip_if_version_lower_than(version="11.7.00002.1")
    def test_create_chore_with_dst_multi_commit(self):
        # create chores
        c4 = Chore(
            name=self.chore_name4,
            start_time=ChoreStartTime(
                self.start_time.year,
                self.start_time.month,
                self.start_time.day,
                self.start_time.hour,
                self.start_time.minute,
                self.start_time.second,
            ),
            dst_sensitivity=True,
            active=True,
            execution_mode=Chore.MULTIPLE_COMMIT,
            frequency=self.frequency,
            tasks=self.tasks,
        )
        self.tm1.chores.create(c4)

        c4 = self.tm1.chores.get(self.chore_name4)

        self.assertEqual(c4.start_time.datetime.hour, self.start_time.hour)
        self.assertEqual(c4._start_time._datetime.replace(hour=0), self.start_time.replace(hour=0, microsecond=0))
        self.assertEqual(c4._name, self.chore_name4)
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

    def test_create_chore_with_dst_single_commit(self):
        # create chores
        c4 = Chore(
            name=self.chore_name4,
            start_time=ChoreStartTime(
                self.start_time.year,
                self.start_time.month,
                self.start_time.day,
                self.start_time.hour,
                self.start_time.minute,
                self.start_time.second,
            ),
            dst_sensitivity=True,
            active=True,
            execution_mode=Chore.SINGLE_COMMIT,
            frequency=self.frequency,
            tasks=self.tasks,
        )
        self.tm1.chores.create(c4)

        c4 = self.tm1.chores.get(self.chore_name4)

        self.assertEqual(c4.start_time.datetime.hour, self.start_time.hour)
        self.assertEqual(c4._start_time._datetime.replace(hour=0), self.start_time.replace(hour=0, microsecond=0))
        self.assertEqual(c4._name, self.chore_name4)
        self.assertEqual(c4.active, True)
        self.assertEqual(c4._dst_sensitivity, True)
        self.assertEqual(c4._execution_mode, Chore.SINGLE_COMMIT)
        self.assertEqual(c4._frequency._days, str(self.frequency_days).zfill(2))
        self.assertEqual(c4._frequency._hours, str(self.frequency_hours).zfill(2))
        self.assertEqual(c4._frequency._minutes, str(self.frequency_minutes).zfill(2))
        self.assertEqual(c4._frequency._seconds, str(self.frequency_seconds).zfill(2))
        for task1, task2 in zip(self.tasks, c4._tasks):
            self.assertEqual(task1, task2)

    def test_get_chore(self):
        c1 = self.tm1.chores.get(self.chore_name1)
        # check all properties
        self.assertEqual(c1._start_time._datetime, self.start_time.replace(microsecond=0))
        self.assertEqual(c1._name, self.chore_name1)
        self.assertEqual(c1.active, True)
        self.assertEqual(c1._dst_sensitivity, True)
        self.assertEqual(c1._execution_mode, Chore.MULTIPLE_COMMIT)
        self.assertEqual(c1._frequency._days, str(self.frequency_days).zfill(2))
        self.assertEqual(c1._frequency._hours, str(self.frequency_hours).zfill(2))
        self.assertEqual(c1._frequency._minutes, str(self.frequency_minutes).zfill(2))
        self.assertEqual(c1._frequency._seconds, str(self.frequency_seconds).zfill(2))
        for task1, task2 in zip(self.tasks, c1._tasks):
            self.assertEqual(task1, task2)

        c2 = self.tm1.chores.get(self.chore_name2)
        # check all properties
        self.assertEqual(c2._start_time._datetime, self.start_time.replace(microsecond=0))
        self.assertEqual(c2._name, self.chore_name2)
        self.assertEqual(c2.active, False)
        self.assertEqual(c2._dst_sensitivity, True)
        self.assertEqual(c2._execution_mode, Chore.SINGLE_COMMIT)
        self.assertEqual(c2._frequency._days, str(self.frequency_days).zfill(2))
        self.assertEqual(c2._frequency._hours, str(self.frequency_hours).zfill(2))
        self.assertEqual(c2._frequency._minutes, str(self.frequency_minutes).zfill(2))
        self.assertEqual(c2._frequency._seconds, str(self.frequency_seconds).zfill(2))
        for task1, task2 in zip(self.tasks, c2._tasks):
            self.assertEqual(task1, task2)

    def test_get_chore_without_tasks(self):
        c3 = self.tm1.chores.get(chore_name=self.chore_name3)
        self.assertFalse(len(c3.tasks))

    def test_get_all(self):
        all_chores = self.tm1.chores.get_all()
        # only check if names are returned
        self.assertIn(self.chore_name1, (c.name for c in all_chores))
        self.assertIn(self.chore_name2, (c.name for c in all_chores))
        self.assertIn(self.chore_name3, (c.name for c in all_chores))

    def test_get_all_names(self):
        all_chore_names = self.tm1.chores.get_all_names()
        self.assertIn(self.chore_name1, all_chore_names)
        self.assertIn(self.chore_name2, all_chore_names)
        self.assertIn(self.chore_name3, all_chore_names)

    def test_search_for_process_name_happy_case(self):
        chore_names = self.tm1.chores.search_for_process_name(process_name=self.process_name1)
        self.assertEqual(2, len(chore_names))
        self.assertEqual(self.chore_name1, chore_names[0].name)
        self.assertEqual(self.chore_name2, chore_names[1].name)

    def test_search_for_parameter_value_no_match(self):
        chore_names = self.tm1.chores.search_for_parameter_value(parameter_value="NotAParamValue")
        self.assertEqual([], chore_names)

    def test_search_for_parameter_value_happy_case(self):
        chore_names = self.tm1.chores.search_for_parameter_value(parameter_value="UK")
        self.assertEqual(2, len(chore_names))
        self.assertEqual(self.chore_name1, chore_names[0].name)
        self.assertEqual(self.chore_name2, chore_names[1].name)

    def test_update_chore_dst(self):
        # get chore
        c = self.tm1.chores.get(self.chore_name1)
        # update all properties
        # update start time
        start_time = datetime(2020, 5, 6, 17, 4, 2)
        c._start_time = ChoreStartTime(
            start_time.year, start_time.month, start_time.day, start_time.hour, start_time.minute, start_time.second
        )
        # update frequency
        frequency_days = int(random.uniform(0, 355))
        frequency_hours = int(random.uniform(0, 23))
        frequency_minutes = int(random.uniform(0, 59))
        frequency_seconds = int(random.uniform(0, 59))
        c._frequency = ChoreFrequency(
            days=frequency_days, hours=frequency_hours, minutes=frequency_minutes, seconds=frequency_seconds
        )
        # update tasks
        tasks = [
            ChoreTask(0, self.process_name2, parameters=[{"Name": "pRegion", "Value": "DE"}]),
            ChoreTask(1, self.process_name2, parameters=[{"Name": "pRegion", "Value": "ES"}]),
            ChoreTask(2, self.process_name2, parameters=[{"Name": "pRegion", "Value": "US"}]),
        ]
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
        c = self.tm1.chores.get(chore_name=self.chore_name1)

        self.assertEqual(c.start_time.datetime.hour, start_time.hour)
        self.assertEqual(c._start_time._datetime.replace(hour=0), start_time.replace(hour=0))

        self.assertEqual(c._name, self.chore_name1)
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
        self.tm1.chores.activate(self.chore_name1)

        c = self.tm1.chores.get(self.chore_name1)
        c.execution_mode = Chore.MULTIPLE_COMMIT

        self.tm1.chores.update(c)

        c = self.tm1.chores.get(chore_name=self.chore_name1)

        self.assertEqual(c.execution_mode, Chore.MULTIPLE_COMMIT)

    def test_update_chore_without_tasks(self):
        # get chore
        c = self.tm1.chores.get(self.chore_name3)
        # update all properties
        # update start time
        start_time = datetime(2023, 4, 5, 12, 5, 30)
        c._start_time = ChoreStartTime(
            start_time.year, start_time.month, start_time.day, start_time.hour, start_time.minute, start_time.second
        )
        c.dst_sensitivity = True
        # update frequency
        frequency_days = int(random.uniform(0, 355))
        frequency_hours = int(random.uniform(0, 23))
        frequency_minutes = int(random.uniform(0, 59))
        frequency_seconds = int(random.uniform(0, 59))
        c._frequency = ChoreFrequency(
            days=frequency_days, hours=frequency_hours, minutes=frequency_minutes, seconds=frequency_seconds
        )

        # execution mode
        c._execution_mode = Chore.SINGLE_COMMIT
        # activate
        c.deactivate()
        # update chore in TM1
        self.tm1.chores.update(c)
        # get chore and check all properties
        c = self.tm1.chores.get(chore_name=self.chore_name3)
        self.assertEqual(c._start_time._datetime.replace(microsecond=0), start_time.replace(microsecond=0))
        self.assertEqual(c._name, self.chore_name3)
        self.assertEqual(c._dst_sensitivity, True)
        self.assertEqual(c._active, False)
        self.assertEqual(c._execution_mode, Chore.SINGLE_COMMIT)
        self.assertEqual(int(c._frequency._days), int(frequency_days))
        self.assertEqual(int(c._frequency._hours), int(frequency_hours))
        self.assertEqual(int(c._frequency._minutes), int(frequency_minutes))

    def test_update_chore_add_tasks(self):
        # get chore
        c = self.tm1.chores.get(self.chore_name1)
        # update all properties
        # update start time
        start_time = datetime.now()
        c._start_time = ChoreStartTime(
            start_time.year, start_time.month, start_time.day, start_time.hour, start_time.minute, start_time.second
        )
        c.dst_sensitivity = True
        # update frequency
        frequency_days = int(random.uniform(0, 355))
        frequency_hours = int(random.uniform(0, 23))
        frequency_minutes = int(random.uniform(0, 59))
        frequency_seconds = int(random.uniform(0, 59))
        c._frequency = ChoreFrequency(
            days=frequency_days, hours=frequency_hours, minutes=frequency_minutes, seconds=frequency_seconds
        )
        # update tasks
        tasks = [
            ChoreTask(0, self.process_name2, parameters=[{"Name": "pRegion", "Value": "DE"}]),
            ChoreTask(1, self.process_name2, parameters=[{"Name": "pRegion", "Value": "ES"}]),
            ChoreTask(2, self.process_name2, parameters=[{"Name": "pRegion", "Value": "CH"}]),
            ChoreTask(3, self.process_name2, parameters=[{"Name": "pRegion", "Value": "US"}]),
        ]
        c._tasks = tasks
        # execution mode
        c._execution_mode = Chore.SINGLE_COMMIT
        # activate
        c.deactivate()
        # update chore in TM1
        self.tm1.chores.update(c)
        # get chore and check all properties
        c = self.tm1.chores.get(chore_name=self.chore_name1)
        self.assertEqual(c._start_time._datetime.replace(microsecond=0), start_time.replace(microsecond=0))
        self.assertEqual(c._name, self.chore_name1)
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

    def test_update_chore_remove_last_task(self):
        # get chore
        c = self.tm1.chores.get(self.chore_name1)
        # update all properties
        # update start time
        start_time = datetime.now()
        c._start_time = ChoreStartTime(
            start_time.year, start_time.month, start_time.day, start_time.hour, start_time.minute, start_time.second
        )
        c.dst_sensitivity = True
        # update frequency
        frequency_days = int(random.uniform(0, 355))
        frequency_hours = int(random.uniform(0, 23))
        frequency_minutes = int(random.uniform(0, 59))
        frequency_seconds = int(random.uniform(0, 59))
        c._frequency = ChoreFrequency(
            days=frequency_days, hours=frequency_hours, minutes=frequency_minutes, seconds=frequency_seconds
        )
        # update tasks
        del c._tasks[2]
        # execution mode
        c._execution_mode = Chore.SINGLE_COMMIT
        # activate
        c.deactivate()
        # update chore in TM1
        self.tm1.chores.update(c)
        # get chore and check all properties
        c = self.tm1.chores.get(chore_name=self.chore_name1)
        self.assertEqual(c._start_time._datetime.replace(microsecond=0), start_time.replace(microsecond=0))
        self.assertEqual(c._name, self.chore_name1)
        self.assertEqual(c._dst_sensitivity, True)
        self.assertEqual(c._active, False)
        self.assertEqual(c._execution_mode, Chore.SINGLE_COMMIT)
        self.assertEqual(int(c._frequency._days), int(frequency_days))
        self.assertEqual(int(c._frequency._hours), int(frequency_hours))
        self.assertEqual(int(c._frequency._minutes), int(frequency_minutes))
        self.assertEqual(2, len(c._tasks))
        # sometimes there is one second difference. Probably a small bug in the REST API
        self.assertAlmostEqual(int(c._frequency._seconds), int(frequency_seconds), delta=1)
        for task1, task2 in zip(self.tasks, c._tasks):
            self.assertEqual(task1, task2)

    def test_update_chore_remove_first_task(self):
        # get chore
        c = self.tm1.chores.get(self.chore_name1)
        # update all properties
        # update start time
        start_time = datetime.now()
        c._start_time = ChoreStartTime(
            start_time.year, start_time.month, start_time.day, start_time.hour, start_time.minute, start_time.second
        )
        c.dst_sensitivity = True
        # update frequency
        frequency_days = int(random.uniform(0, 355))
        frequency_hours = int(random.uniform(0, 23))
        frequency_minutes = int(random.uniform(0, 59))
        frequency_seconds = int(random.uniform(0, 59))
        c._frequency = ChoreFrequency(
            days=frequency_days, hours=frequency_hours, minutes=frequency_minutes, seconds=frequency_seconds
        )
        # update tasks
        del c._tasks[0]
        # execution mode
        c._execution_mode = Chore.SINGLE_COMMIT
        # activate
        c.deactivate()
        # update chore in TM1
        self.tm1.chores.update(c)
        # get chore and check all properties
        c = self.tm1.chores.get(chore_name=self.chore_name1)
        self.assertEqual(c._start_time._datetime.replace(microsecond=0), start_time.replace(microsecond=0))
        self.assertEqual(c._name, self.chore_name1)
        self.assertEqual(c._dst_sensitivity, True)
        self.assertEqual(c._active, False)
        self.assertEqual(c._execution_mode, Chore.SINGLE_COMMIT)
        self.assertEqual(int(c._frequency._days), int(frequency_days))
        self.assertEqual(int(c._frequency._hours), int(frequency_hours))
        self.assertEqual(int(c._frequency._minutes), int(frequency_minutes))
        self.assertEqual(2, len(c._tasks))
        # sometimes there is one-second difference. Probably a small bug in the REST API
        self.assertAlmostEqual(int(c._frequency._seconds), int(frequency_seconds), delta=1)

        task1, task2 = self.tasks[1], c._tasks[0]
        self.assertEqual(task1, task2)

        task1, task2 = self.tasks[2], c._tasks[1]
        self.assertEqual(task1, task2)


    def test_activate(self):
        chore = self.tm1.chores.get(self.chore_name1)
        if chore.active:
            self.tm1.chores.deactivate(self.chore_name1)
        self.tm1.chores.activate(self.chore_name1)

    def test_deactivate(self):
        chore = self.tm1.chores.get(self.chore_name1)
        if not chore.active:
            self.tm1.chores.activate(self.chore_name1)
        self.tm1.chores.deactivate(self.chore_name1)

    def test_execute_chore(self):
        response = self.tm1.chores.execute_chore(self.chore_name1)
        self.assertTrue(response.ok)

    def test_exists(self):
        self.assertTrue(self.tm1.chores.exists(self.chore_name1))
        self.assertTrue(self.tm1.chores.exists(self.chore_name2))
        self.assertTrue(self.tm1.chores.exists(self.chore_name3))
        self.assertFalse(self.tm1.chores.exists(uuid.uuid4()))

    def test_search_for_process_name_no_match(self):
        chore_names = self.tm1.chores.search_for_process_name(process_name="NotAProcessName")
        self.assertEqual([], chore_names)

    @classmethod
    def teardown_class(cls):
        for chore_name in [cls.chore_name1, cls.chore_name2, cls.chore_name3, cls.chore_name4]:
            if cls.tm1.chores.exists(chore_name):
                cls.tm1.chores.delete(chore_name)
        cls.tm1.processes.delete(cls.process_name1)
        cls.tm1.processes.delete(cls.process_name2)
        cls.tm1.logout()


if __name__ == "__main__":
    unittest.main()
