# -*- coding: utf-8 -*-

import datetime

from TM1py.Objects.TM1Object import TM1Object


class ChoreStartTime(TM1Object):
    """ Utility class to handle time representation for Chore Start Time
        
    """

    def __init__(self, year: int, month: int, day: int, hour: int, minute: int, second: int):
        """
        
        :param year: year 
        :param month: month
        :param day: day
        :param hour: hour or None
        :param minute: minute or None
        :param second: second or None
        """
        self._datetime = datetime.datetime.combine(datetime.date(year, month, day), datetime.time(hour, minute, second))

    @classmethod
    def from_string(cls, start_time_string: str) -> 'ChoreStartTime':
        """
        Create a new time instance from a string.

        Args:
            cls: (todo): write your description
            start_time_string: (str): write your description
        """
        # f to handle strange timestamp 2016-09-25T20:25Z instead of common 2016-09-25T20:25:01Z
        f = lambda x: int(x) if x else 0
        return cls(year=f(start_time_string[0:4]),
                   month=f(start_time_string[5:7]),
                   day=f(start_time_string[8:10]),
                   hour=f(start_time_string[11:13]),
                   minute=f(start_time_string[14:16]),
                   second=f(start_time_string[17:19]))

    @property
    def start_time_string(self) -> str:
        """
        Return the start time of the node.

        Args:
            self: (todo): write your description
        """
        return self._datetime.strftime("%Y-%m-%dT%H:%M:%SZ")

    @property
    def datetime(self) -> datetime:
        """
        Return datetime.

        Args:
            self: (todo): write your description
        """
        return self._datetime

    def __str__(self):
        """
        Return the string representation of the object

        Args:
            self: (todo): write your description
        """
        return self.start_time_string

    def set_time(self, year: int = None, month: int = None, day: int = None, hour: int = None, minute: int = None,
                 second: int = None):
        """
        Set the time value of the instance.

        Args:
            self: (todo): write your description
            year: (todo): write your description
            month: (todo): write your description
            day: (todo): write your description
            hour: (todo): write your description
            minute: (float): write your description
            second: (todo): write your description
        """
        if year:
            self._datetime = self._datetime.replace(year=year)
        if month:
            self._datetime = self._datetime.replace(month=month)
        if day:
            self._datetime = self._datetime.replace(day=day)
        if hour:
            self._datetime = self._datetime.replace(hour=hour)
        if minute:
            self._datetime = self._datetime.replace(minute=minute)
        if second:
            self._datetime = self._datetime.replace(second=second)

    def add(self, days: int = 0, hours: int = 0, minutes: int = 0, seconds: int = 0):
        """
        Add a timedelta to the instance.

        Args:
            self: (todo): write your description
            days: (int): write your description
            hours: (todo): write your description
            minutes: (int): write your description
            seconds: (int): write your description
        """
        self._datetime = self._datetime + datetime.timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)

    def subtract(self, days: int = 0, hours: int = 0, minutes: int = 0, seconds: int = 0):
        """
        Subtracts the given number of days.

        Args:
            self: (todo): write your description
            days: (todo): write your description
            hours: (todo): write your description
            minutes: (int): write your description
            seconds: (todo): write your description
        """
        self._datetime = self._datetime - datetime.timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
