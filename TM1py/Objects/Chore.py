# -*- coding: utf-8 -*-

import collections
import json
from typing import Dict, List, Iterable

from TM1py.Objects.ChoreFrequency import ChoreFrequency
from TM1py.Objects.ChoreStartTime import ChoreStartTime
from TM1py.Objects.ChoreTask import ChoreTask
from TM1py.Objects.TM1Object import TM1Object


class Chore(TM1Object):
    """ Abstraction of TM1 Chore

    """
    SINGLE_COMMIT = 'SingleCommit'
    MULTIPLE_COMMIT = 'MultipleCommit'

    def __init__(self, name: str, start_time: ChoreStartTime, dst_sensitivity: bool, active: bool,
                 execution_mode: str, frequency: ChoreFrequency, tasks: Iterable[ChoreTask]):
        """
        Initialize a new execution.

        Args:
            self: (todo): write your description
            name: (str): write your description
            start_time: (int): write your description
            dst_sensitivity: (todo): write your description
            active: (bool): write your description
            execution_mode: (todo): write your description
            frequency: (float): write your description
            tasks: (str): write your description
        """
        self._name = name
        self._start_time = start_time
        self._dst_sensitivity = dst_sensitivity
        self._active = active
        self._execution_mode = execution_mode
        self._frequency = frequency
        self._tasks = list(tasks)

    @classmethod
    def from_json(cls, chore_as_json: str) -> 'Chore':
        """ Alternative constructor

        :param chore_as_json: string, JSON. Response of /api/v1/Chores('x')/Tasks?$expand=*
        :return: Chore, an instance of this class
        """
        chore_as_dict = json.loads(chore_as_json)
        return cls.from_dict(chore_as_dict)

    @classmethod
    def from_dict(cls, chore_as_dict: Dict) -> 'Chore':
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
    def name(self) -> str:
        """
        Returns the name of this node.

        Args:
            self: (todo): write your description
        """
        return self._name

    @name.setter
    def name(self, name: str):
        """
        Get the name.

        Args:
            self: (todo): write your description
            name: (str): write your description
        """
        self._name = name

    @property
    def start_time(self) -> ChoreStartTime:
        """
        Start the timer.

        Args:
            self: (todo): write your description
        """
        return self._start_time

    @start_time.setter
    def start_time(self, start_time: ChoreStartTime):
        """
        Starts the timer.

        Args:
            self: (todo): write your description
            start_time: (todo): write your description
        """
        self._start_time = start_time

    @property
    def dst_sensitivity(self) -> bool:
        """
        The inverse of the dst.

        Args:
            self: (todo): write your description
        """
        return self._dst_sensitivity

    @dst_sensitivity.setter
    def dst_sensitivity(self, dst_sensitivity: bool):
        """
        Set the dst_sensitivity.

        Args:
            self: (todo): write your description
            dst_sensitivity: (todo): write your description
        """
        self._dst_sensitivity = dst_sensitivity

    @property
    def active(self) -> bool:
        """
        The active : class.

        Args:
            self: (todo): write your description
        """
        return self._active

    @property
    def execution_mode(self) -> str:
        """
        Return the mode of the execution.

        Args:
            self: (todo): write your description
        """
        return self._execution_mode

    @execution_mode.setter
    def execution_mode(self, execution_mode):
        """
        Set the mode of the execution mode.

        Args:
            self: (todo): write your description
            execution_mode: (str): write your description
        """
        self._execution_mode = execution_mode

    @property
    def frequency(self) -> ChoreFrequency:
        """
        The frequency of the frequency.

        Args:
            self: (todo): write your description
        """
        return self._frequency

    @frequency.setter
    def frequency(self, frequency: ChoreFrequency):
        """
        Set the frequency.

        Args:
            self: (todo): write your description
            frequency: (list): write your description
        """
        self._frequency = frequency

    @property
    def tasks(self) -> List[ChoreTask]:
        """
        The list of tasks.

        Args:
            self: (todo): write your description
        """
        return self._tasks

    @tasks.setter
    def tasks(self, tasks: List[ChoreTask]):
        """
        * list tasks.

        Args:
            self: (todo): write your description
            tasks: (str): write your description
        """
        self._tasks = tasks

    @property
    def body(self) -> str:
        """
        Return the body.

        Args:
            self: (todo): write your description
        """
        return self.construct_body()

    @property
    def body_as_dict(self) -> Dict:
        """
        Return the json - serializable dict.

        Args:
            self: (todo): write your description
        """
        return json.loads(self.body)

    def add_task(self, task: ChoreTask):
        """
        Add a new task.

        Args:
            self: (todo): write your description
            task: (todo): write your description
        """
        self._tasks.append(task)

    def activate(self):
        """
        Closes the active window.

        Args:
            self: (todo): write your description
        """
        self._active = True

    def deactivate(self):
        """
        Deactivate the current session.

        Args:
            self: (todo): write your description
        """
        self._active = False

    def reschedule(self, days: int = 0, hours: int = 0, minutes: int = 0, seconds: int = 0):
        """
        Reschedule the given number of days.

        Args:
            self: (todo): write your description
            days: (array): write your description
            hours: (todo): write your description
            minutes: (todo): write your description
            seconds: (float): write your description
        """
        self._start_time.add(days=days, hours=hours, minutes=minutes, seconds=seconds)

    def construct_body(self) -> str:
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
