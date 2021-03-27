import unittest

from TM1py import ChoreStartTime


class TestChoreStartTime(unittest.TestCase):

    def test_start_time_string_happy_case(self):
        chore_start_time = ChoreStartTime(year=2020, month=11, day=26, hour=10, minute=11, second=2)
        self.assertEqual(chore_start_time.start_time_string, "2020-11-26T10:11:02Z")

    def test_start_time_string_no_seconds(self):
        chore_start_time = ChoreStartTime(year=2020, month=11, day=26, hour=10, minute=11, second=0)
        self.assertEqual(chore_start_time.start_time_string, "2020-11-26T10:11Z")

    def test_start_time_string_no_minutes_no_seconds(self):
        chore_start_time = ChoreStartTime(year=2020, month=11, day=26, hour=10, minute=0, second=0)
        self.assertEqual(chore_start_time.start_time_string, "2020-11-26T10:00Z")

    def test_start_time_string_with_positive_tz(self):
        chore_start_time = ChoreStartTime(year=2020, month=11, day=26, hour=10, minute=1, second=1, tz="+02:00")
        self.assertEqual(chore_start_time.start_time_string, "2020-11-26T10:01:01Z+02:00")

    def test_start_time_string_with_negative_tz(self):
        chore_start_time = ChoreStartTime(year=2020, month=11, day=26, hour=10, minute=1, second=1, tz="-01:00")
        self.assertEqual(chore_start_time.start_time_string, "2020-11-26T10:01:01Z-01:00")

    def test_start_time_string_without_tz(self):
        chore_start_time = ChoreStartTime(year=2020, month=11, day=26, hour=10, minute=1, second=1)
        self.assertEqual(chore_start_time.start_time_string, "2020-11-26T10:01:01Z")
