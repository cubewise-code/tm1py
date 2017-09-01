# -*- coding: utf-8 -*-

import collections
import json

from TM1py.Objects.ChoreFrequency import ChoreFrequency
from TM1py.Objects.ChoreTask import ChoreTask

from TM1py.Objects.ChoreStartTime import ChoreStartTime

from TM1py.Objects.TM1Object import TM1Object


class Chore(TM1Object):
    """ Abstraction of TM1 Chore
        
    
    """
    def __init__(self, name, start_time, dst_sensitivity, active, execution_mode, frequency, tasks):
        self._name = name
        self._start_time = start_time
        self._dst_sensitivity = dst_sensitivity
        self._active = active
        self._execution_mode = execution_mode
        self._frequency = frequency
        self._tasks = tasks

    @classmethod
    def from_json(cls, chore_as_json):
        """ Alternative constructor

        :param chore_as_json: string, JSON. Response of /api/v1/Chores('x')/Tasks?$expand=*
        :return: Chore, an instance of this class
        """
        chore_as_dict = json.loads(chore_as_json)
        return cls.from_dict(chore_as_dict)

    @classmethod
    def from_dict(cls, chore_as_dict):
        """ Alternative constructor

        :param chore_as_dict: Chore as dict
        :return: Chore, an instance of this class
        """
        return cls(name=chore_as_dict['Name'],
                   start_time=ChoreStartTime.from_string(chore_as_dict['StartTime']),
                   dst_sensitivity=chore_as_dict['DSTSensitive'],
                   active=chore_as_dict['Active'],
                   execution_mode=chore_as_dict['ExecutionMode'],
                   frequency=ChoreFrequency.from_string(chore_as_dict['Frequency']),
                   tasks=[ChoreTask.from_dict(task) for task in chore_as_dict['Tasks']])

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

    @property
    def start_time(self):
        return self._start_time

    @start_time.setter
    def start_time(self, start_time):
        self._start_time = start_time

    @property
    def dst_sensitivity(self):
        return self._dst_sensitivity

    @dst_sensitivity.setter
    def dst_sensitivity(self, dst_sensitivity):
        self._dst_sensitivity = dst_sensitivity

    @property
    def active(self):
        return self._active

    @property
    def execution_mode(self):
        return self._execution_mode

    @execution_mode.setter
    def execution_mode(self, execution_mode):
        self._execution_mode = execution_mode

    @property
    def frequency(self):
        return self._frequency

    @frequency.setter
    def frequency(self, frequency):
        self._frequency = frequency

    @property
    def tasks(self):
        return self._tasks

    @tasks.setter
    def tasks(self, tasks):
        self._tasks = tasks

    @property
    def body(self):
        return self.construct_body()

    def add_task(self, task):
        self._tasks.append(task)

    def activate(self):
        self._active = True

    def deactivate(self):
        self._active = False

    def reschedule(self, days=0, hours=0, minutes=0, seconds=0):
        self._start_time.add(days=days, hours=hours, minutes=minutes, seconds=seconds)

    def construct_body(self):
        """
        construct self.body (json) from the class attributes
        :return: String, TM1 JSON representation of a chore
        """
        body_as_dict = collections.OrderedDict()
        body_as_dict['Name'] = self._name
        body_as_dict['StartTime'] = self._start_time.start_time_string
        body_as_dict['DSTSensitive'] = self._dst_sensitivity
        body_as_dict['Active'] = self._active
        body_as_dict['ExecutionMode'] = self._execution_mode
        body_as_dict['Frequency'] = self._frequency.frequency_string
        body_as_dict['Tasks'] = [task.body_as_dict for task in self._tasks]
        return json.dumps(body_as_dict, ensure_ascii=False)

