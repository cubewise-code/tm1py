# -*- coding: utf-8 -*-
from typing import Union

from TM1py.Objects.TM1Object import TM1Object


class ChoreFrequency(TM1Object):
    """Utility class to handle time representation fore Chore Frequency"""

    def __init__(
        self, days: Union[str, int], hours: Union[str, int], minutes: Union[str, int], seconds: Union[str, int]
    ):
        self._days = str(days).zfill(2)
        self._hours = str(hours).zfill(2)
        self._minutes = str(minutes).zfill(2)
        self._seconds = str(seconds).zfill(2)

    @property
    def days(self) -> str:
        return self._days

    @property
    def hours(self) -> str:
        return self._hours

    @property
    def minutes(self) -> str:
        return self._minutes

    @property
    def seconds(self) -> str:
        return self._seconds

    @days.setter
    def days(self, value: Union[str, int]):
        self._days = str(value).zfill(2)

    @hours.setter
    def hours(self, value: Union[str, int]):
        self._hours = str(value).zfill(2)

    @minutes.setter
    def minutes(self, value: Union[str, int]):
        self._minutes = str(value).zfill(2)

    @seconds.setter
    def seconds(self, value: Union[str, int]):
        self._seconds = str(value).zfill(2)

    @classmethod
    def from_string(cls, frequency_string: str) -> "ChoreFrequency":
        pos_dt = frequency_string.find("DT", 1)
        pos_h = frequency_string.find("H", pos_dt)
        pos_m = frequency_string.find("M", pos_h)
        pos_s = len(frequency_string) - 1
        return cls(
            days=frequency_string[1:pos_dt],
            hours=frequency_string[pos_dt + 2 : pos_h],
            minutes=frequency_string[pos_h + 1 : pos_m],
            seconds=frequency_string[pos_m + 1 : pos_s],
        )

    @property
    def frequency_string(self) -> str:
        return "P{}DT{}H{}M{}S".format(self._days, self._hours, self._minutes, self._seconds)

    def __str__(self) -> str:
        return self.frequency_string
