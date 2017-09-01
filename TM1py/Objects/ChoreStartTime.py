# -*- coding: utf-8 -*-

import datetime

from TM1py.Objects.TM1Object import TM1Object


class ChoreStartTime(TM1Object):
    """ Utility class to handle time representation for Chore Start Time
        
    """
    def __init__(self, year, month, day, hour, minute, second):
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
    def from_string(cls, start_time_string):
        # f to handle strange timestamp 2016-09-25T20:25Z instead of common 2016-09-25T20:25:01Z
        f = lambda x: int(x) if x else 0
        return cls(year=f(start_time_string[0:4]),
                   month=f(start_time_string[5:7]),
                   day=f(start_time_string[8:10]),
                   hour=f(start_time_string[11:13]),
                   minute=f(start_time_string[14:16]),
                   second=f(start_time_string[17:19]))

    @property
    def start_time_string(self):
        return self._datetime.strftime("%Y-%m-%dT%H:%M:%SZ")

    def __str__(self):
        return self._datetime.strftime("%Y-%m-%dT%H:%M:%SZ")

    def set_time(self, year=None, month=None, day=None, hour=None, minute=None, second=None):
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

    def add(self, days=0, hours=0, minutes=0, seconds=0):
        self._datetime = self._datetime + datetime.timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)

    def substract(self, days=0, hours=0, minutes=0, seconds=0):
        self._datetime = self._datetime - datetime.timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
