# -*- coding: utf-8 -*-

import datetime


class ChoreStartTime:
    """Utility class to handle time representation for Chore Start Time"""

    def __init__(self, year: int, month: int, day: int, hour: int, minute: int, second: int, tz: str = None):
        """

        :param year: year
        :param month: month
        :param day: day
        :param hour: hour or None
        :param minute: minute or None
        :param second: second or None
        """
        self._datetime = datetime.datetime.combine(datetime.date(year, month, day), datetime.time(hour, minute, second))
        self.tz = tz

    @classmethod
    def from_string(cls, start_time_string: str) -> "ChoreStartTime":
        # extract optional tz info (e.g., +01:00) from string end
        if "+" in start_time_string:
            # case "2020-11-05T08:00:01+01:00",
            tz = "+" + start_time_string.split("+")[1]
        elif start_time_string.count("-") == 3:
            # case: "2020-11-05T08:00:01-01:00",
            tz = "-" + start_time_string.split("-")[-1]
        else:
            tz = None

        # f to handle strange timestamp 2016-09-25T20:25Z instead of common 2016-09-25T20:25:00Z
        # second is defaulted to 0 if not specified in the chore schedule
        def format_time(value: int) -> str:
            return int(value or 0)

        return cls(
            year=format_time(start_time_string[0:4]),
            month=format_time(start_time_string[5:7]),
            day=format_time(start_time_string[8:10]),
            hour=format_time(start_time_string[11:13]),
            minute=format_time(start_time_string[14:16]),
            second=format_time(0 if start_time_string[16] != ":" else start_time_string[17:19]),
            tz=tz,
        )

    @property
    def start_time_string(self) -> str:
        # produce timestamp 2016-09-25T20:25:00Z instead of common 2016-09-25T20:25Z where no seconds are specified
        start_time = self._datetime.strftime("%Y-%m-%dT%H:%M:%S")

        if self.tz:
            start_time += self.tz
        else:
            start_time += "Z"

        return start_time

    @property
    def datetime(self) -> datetime:
        return self._datetime

    def __str__(self):
        return self.start_time_string

    def set_time(
        self,
        year: int = None,
        month: int = None,
        day: int = None,
        hour: int = None,
        minute: int = None,
        second: int = None,
    ):

        _year = year if year is not None else self._datetime.year
        _month = month if month is not None else self._datetime.month
        _day = day if day is not None else self._datetime.day
        _hour = hour if hour is not None else self._datetime.hour
        _minute = minute if minute is not None else self._datetime.minute
        _second = second if second is not None else self._datetime.second

        self._datetime = self._datetime.replace(
            year=_year, month=_month, day=_day, hour=_hour, minute=_minute, second=_second
        )

    def add(self, days: int = 0, hours: int = 0, minutes: int = 0, seconds: int = 0):
        self._datetime = self._datetime + datetime.timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)

    def subtract(self, days: int = 0, hours: int = 0, minutes: int = 0, seconds: int = 0):
        self._datetime = self._datetime - datetime.timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
