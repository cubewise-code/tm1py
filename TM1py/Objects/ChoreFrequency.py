# -*- coding: utf-8 -*-
from typing import Union

from TM1py.Objects.TM1Object import TM1Object


class ChoreFrequency(TM1Object):
    """ Utility class to handle time representation fore Chore Frequency
    
    """

    def __init__(self, days: Union[str, int], hours: Union[str, int], minutes: Union[str, int],
                 seconds: Union[str, int]):
        """
        Initialize the instance.

        Args:
            self: (todo): write your description
            days: (todo): write your description
            hours: (todo): write your description
            minutes: (int): write your description
            seconds: (int): write your description
        """
        self._days = str(days).zfill(2)
        self._hours = str(hours).zfill(2)
        self._minutes = str(minutes).zfill(2)
        self._seconds = str(seconds).zfill(2)

    @property
    def days(self) -> str:
        """
        The number of days.

        Args:
            self: (todo): write your description
        """
        return self._days

    @property
    def hours(self) -> str:
        """
        The hours of hours.

        Args:
            self: (todo): write your description
        """
        return self._hours

    @property
    def minutes(self) -> str:
        """
        Returns the minimum value of the request.

        Args:
            self: (todo): write your description
        """
        return self._minutes

    @property
    def seconds(self) -> str:
        """
        The number of seconds.

        Args:
            self: (todo): write your description
        """
        return self._seconds

    @days.setter
    def days(self, value: Union[str, int]):
        """
        Gets / sets the days

        Args:
            self: (todo): write your description
            value: (todo): write your description
        """
        self._days = str(value).zfill(2)

    @hours.setter
    def hours(self, value: Union[str, int]):
        """
        Gets / sets of hours.

        Args:
            self: (todo): write your description
            value: (str): write your description
        """
        self._hours = str(value).zfill(2)

    @minutes.setter
    def minutes(self, value: Union[str, int]):
        """
        Set the minimum value. min / max.

        Args:
            self: (todo): write your description
            value: (todo): write your description
        """
        self._minutes = str(value).zfill(2)

    @seconds.setter
    def seconds(self, value: Union[str, int]):
        """
        Set the time in seconds.

        Args:
            self: (todo): write your description
            value: (todo): write your description
        """
        self._seconds = str(value).zfill(2)

    @classmethod
    def from_string(cls, frequency_string: str) -> 'ChoreFrequency':
        """
        Parse a frequency object from a string.

        Args:
            cls: (todo): write your description
            frequency_string: (str): write your description
        """
        pos_dt = frequency_string.find('DT', 1)
        pos_h = frequency_string.find('H', pos_dt)
        pos_m = frequency_string.find('M', pos_h)
        pos_s = len(frequency_string) - 1
        return cls(days=frequency_string[1:pos_dt],
                   hours=frequency_string[pos_dt + 2:pos_h],
                   minutes=frequency_string[pos_h + 1:pos_m],
                   seconds=frequency_string[pos_m + 1:pos_s])

    @property
    def frequency_string(self) -> str:
        """
        Returns the frequency string representation.

        Args:
            self: (todo): write your description
        """
        return "P{}DT{}H{}M{}S".format(self._days, self._hours, self._minutes, self._seconds)

    def __str__(self) -> str:
        """
        Return the frequency of the frequency.

        Args:
            self: (todo): write your description
        """
        return self.frequency_string
