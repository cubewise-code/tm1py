# -*- coding: utf-8 -*-

import functools
import json
from datetime import datetime
from typing import List

from requests import Response

from TM1py.Objects import Chore, ChoreTask
from TM1py.Services.ObjectService import ObjectService
from TM1py.Services.RestService import RestService
from TM1py.Utils import format_url


def deactivate_activate(func):
    """ Higher Order function to handle activation and deactivation of chores before updating them

    :param func:
    :return:
    """

    @functools.wraps(func)
    def wrapper(self, chore: Chore):
        # Get Chore
        chore_old = self.get(chore.name)
        # Deactivate
        if chore_old.active:
            self.deactivate(chore.name)
        # Do stuff
        try:
            response = func(self, chore)
        except Exception as e:
            raise e
        # Activate if necessary
        finally:
            if chore.active:
                self.activate(chore.name)
        return response

    return wrapper


class ChoreService(ObjectService):
    """ Service to handle Object Updates for TM1 Chores

    """

    def __init__(self, rest: RestService):
        super().__init__(rest)

    def get(self, chore_name: str, **kwargs) -> Chore:
        """ Get a chore from the TM1 Server
        :param chore_name:
        :return: instance of TM1py.Chore
        """
        url = format_url(
            "/api/v1/Chores('{}')?$expand=Tasks($expand=*,Process($select=Name),Chore($select=Name))",
            chore_name)
        response = self._rest.GET(url, **kwargs)
        return Chore.from_dict(response.json())

    def get_all(self, **kwargs) -> List[Chore]:
        """ get a List of all Chores
        :return: List of TM1py.Chore
        """
        url = "/api/v1/Chores?$expand=Tasks($expand=*,Process($select=Name),Chore($select=Name))"
        response = self._rest.GET(url, **kwargs)
        return [Chore.from_dict(chore_as_dict) for chore_as_dict in response.json()['value']]

    def get_all_names(self, **kwargs) -> List[str]:
        """ get a List of all Chores
        :return: List of TM1py.Chore
        """
        url = "/api/v1/Chores?$select=Name"
        response = self._rest.GET(url, **kwargs)
        return [chore['Name'] for chore in response.json()['value']]

    def create(self, chore: Chore, **kwargs) -> Response:
        """ create a chore
        :param chore: instance of TM1py.Chore
        :return:
        """
        url = "/api/v1/Chores"
        response = self._rest.POST(url=url, data=chore.body, **kwargs)

        if chore.dst_sensitivity:
            self.set_local_start_time(chore.name, chore.start_time.datetime)

        if chore.active:
            self.activate(chore.name)
        return response

    def delete(self, chore_name: str, **kwargs) -> Response:
        """ delete chore in TM1
        :param chore_name:
        :return: response
        """
        url = format_url("/api/v1/Chores('{}')", chore_name)
        response = self._rest.DELETE(url)
        return response

    def exists(self, chore_name: str, **kwargs) -> bool:
        """ Check if Chore exists

        :param chore_name:
        :return:
        """
        url = format_url("/api/v1/Chores('{}')", chore_name)
        return self._exists(url, **kwargs)

    @deactivate_activate
    def update(self, chore: Chore, **kwargs):
        """ update chore on TM1 Server
        does not update: DST Sensitivity!
        :param chore:
        :return:
        """
        # Update StartTime, ExecutionMode, Frequency
        url = format_url("/api/v1/Chores('{}')", chore.name)
        # Remove Tasks from Body. Tasks to be managed individually
        chore_dict_without_tasks = chore.body_as_dict
        chore_dict_without_tasks.pop("Tasks")
        self._rest.PATCH(url, json.dumps(chore_dict_without_tasks), **kwargs)

        # Update Tasks individually
        task_old_count = self._get_tasks_count(chore.name)
        for i, task_new in enumerate(chore.tasks):
            if i >= task_old_count:
                self._add_task(chore.name, task_new, **kwargs)
            else:
                task_old = self._get_task(chore.name, i)
                if task_new != task_old:
                    self._update_task(chore.name, task_new, **kwargs)
        for j in range(i + 1, task_old_count):
            self._delete_task(chore.name, i + 1, **kwargs)

        if chore.dst_sensitivity:
            self.set_local_start_time(chore.name, chore.start_time.datetime)

    def activate(self, chore_name: str, **kwargs) -> Response:
        """ activate chore on TM1 Server
        :param chore_name:
        :return: response
        """
        url = format_url("/api/v1/Chores('{}')/tm1.Activate", chore_name)
        return self._rest.POST(url, '', **kwargs)

    def deactivate(self, chore_name: str, **kwargs) -> Response:
        """ deactivate chore on TM1 Server
        :param chore_name:
        :return: response
        """
        url = format_url("/api/v1/Chores('{}')/tm1.Deactivate", chore_name)
        return self._rest.POST(url, '', **kwargs)

    def set_local_start_time(self, chore_name: str, date_time: datetime, **kwargs) -> Response:
        """ Makes Server crash if chore is activated (10.2.2 FP6) :)
        :param chore_name:
        :param date_time:
        :return:
        """
        url = format_url("/api/v1/Chores('{}')/tm1.SetServerLocalStartTime", chore_name)
        data = {
            "StartDate": "{}-{}-{}".format(
                date_time.year, date_time.month, date_time.day),
            "StartTime": "{}:{}:{}".format(
                self.zfill_two(date_time.hour), self.zfill_two(date_time.minute), self.zfill_two(date_time.second))
        }
        return self._rest.POST(url, json.dumps(data), **kwargs)

    def execute_chore(self, chore_name: str, **kwargs) -> Response:
        """ Ask TM1 Server to execute a chore
            :param chore_name: String, name of the chore to be executed
            :return: the response
        """
        return self._rest.POST(format_url("/api/v1/Chores('{}')/tm1.Execute", chore_name), '', **kwargs)

    def _get_tasks_count(self, chore_name: str, **kwargs) -> int:
        """ Query Chore tasks count on TM1 Server
        :param chore_name: name of Chore to count tasks
        :return: int
        """
        url = format_url("/api/v1/Chores('{}')/Tasks/$count", chore_name)
        response = self._rest.GET(url, **kwargs)
        return int(response.text)

    def _get_task(self, chore_name: str, step: int, **kwargs) -> ChoreTask:
        """ Get task from chore
        :param chore_name: name of the chore
        :param step:
        :return: instance of TM1py.ChoreTask
        """
        url = format_url(
            "/api/v1/Chores('{}')/Tasks({})?$expand=*,Process($select=Name),Chore($select=Name)", chore_name, str(step))
        response = self._rest.GET(url, **kwargs)
        return ChoreTask.from_dict(response.json())

    def _delete_task(self, chore_name: str, step: int, **kwargs) -> Response:
        """ Delete task from chore
        :param chore_name: name of the chore
        :param step: integer
        :return: response
        """
        url = format_url("/api/v1/Chores('{}')/Tasks({})", chore_name, str(step))
        response = self._rest.DELETE(url, **kwargs)
        return response

    def _add_task(self, chore_name: str, chore_task: ChoreTask, **kwargs) -> Response:
        """ Create Chore task on TM1 Server
        :param chore_name: name of Chore to update
        :param chore_task: instance of TM1py.ChoreTask
        :return: response
        """
        chore = self.get(chore_name, **kwargs)
        if chore.active:
            self.deactivate(chore_name, **kwargs)
        try:
            url = format_url("/api/v1/Chores('{}')/Tasks", chore_name)
            response = self._rest.POST(url, chore_task.body, **kwargs)
        except Exception as e:
            raise e
        finally:
            if chore.active:
                self.activate(chore_name, **kwargs)
        return response

    def _update_task(self, chore_name: str, chore_task: ChoreTask, **kwargs):
        """ update a chore task
        :param chore_name: name of the Chore
        :param chore_task: instance TM1py.ChoreTask
        :return: response
        """
        url = format_url("/api/v1/Chores('{}')/Tasks({})", chore_name, str(chore_task.step))
        return self._rest.PATCH(url, chore_task.body, **kwargs)

    @staticmethod
    def zfill_two(number: int) -> str:
        """ Pad an int with zeros on the left two create two digit string

        :param number:
        :return:
        """
        return str(number).zfill(2)
