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
