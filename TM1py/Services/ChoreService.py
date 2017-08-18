# -*- coding: utf-8 -*-

import json

from TM1py.Objects import Chore, ChoreTask
from TM1py.Services.ObjectService import ObjectService


class ChoreService(ObjectService):
    """ Service to handle Object Updates for TM1 Chores
    
    """
    def __init__(self, rest):
        super().__init__(rest)

    def get(self, chore_name):
        """ Get a chore from the TM1 Server

        :param chore_name:
        :return: instance of TM1py.Chore
        """
        request = "/api/v1/Chores('{}')?$expand=Tasks($expand=*,Process($select=Name),Chore($select=Name))" \
            .format(chore_name)
        response = self._rest.GET(request)
        response_as_dict = json.loads(response)
        return Chore.from_dict(response_as_dict)

    def get_all(self):
        """ get a List of all Chores

        :return: List of TM1py.Chore
        """
        request = "/api/v1/Chores?$expand=Tasks($expand=*,Process($select=Name),Chore($select=Name))"
        response = self._rest.GET(request)
        response_as_dict = json.loads(response)
        return [Chore.from_dict(chore_as_dict) for chore_as_dict in response_as_dict['value']]

    def create(self, chore):
        """ create chore in TM1

        :param chore: instance of TM1py.Chore
        :return:
        """
        request = "/api/v1/Chores"
        response = self._rest.POST(request, chore.body)
        if chore.activate:
            self.activate(chore.name)
        return response

    def delete(self, chore_name):
        """ delete chore in TM1

        :param chore_name:
        :return: response
        """

        request = "/api/v1/Chores('{}')".format(chore_name)
        response = self._rest.DELETE(request)
        return response

    def update(self, chore):
        """ update chore on TM1 Server

        does not update: DST Sensitivity!
        :param chore:
        :return: response
        """
        try:
            # deactivate
            self.deactivate(chore.name)

            # update StartTime, ExecutionMode, Frequency
            request = "/api/v1/Chores('{}')".format(chore.name)
            self._rest.PATCH(request, chore.body)

            # update Tasks
            for i, task_new in enumerate(chore.tasks):
                task_old = self.get_task(chore.name, i)
                if task_old is None:
                    self.create_task(chore.name, task_new)
                elif task_new != task_old:
                    self.update_task(chore.name, task_new)
        finally:
            # activate
            if chore.active:
                self.activate(chore.name)

    def activate(self, chore_name):
        """ activate chore on TM1 Server

        :param chore_name:
        :return: response
        """
        request = "/api/v1/Chores('{}')/tm1.Activate".format(chore_name)
        return self._rest.POST(request, '')

    def deactivate(self, chore_name):
        """ deactivate chore on TM1 Server

        :param chore_name:
        :return: response
        """

        request = "/api/v1/Chores('{}')/tm1.Deactivate".format(chore_name)
        return self._rest.POST(request, '')

    def set_local_start_time(self, chore_name, date_time):
        """ Makes Server crash if chore is activate (FP6) :)

        :param chore_name:
        :param date_time:
        :return:
        """
        request = "/api/v1/Chores('{}')/tm1.SetServerLocalStartTime".format(chore_name)
        # function for 3 to '03'
        fill = lambda t: str(t).zfill(2)
        data = {
            "StartDate": "{}-{}-{}".format(date_time.year, date_time.month, date_time.day),
            "StartTime": "{}:{}:{}".format(fill(date_time.hour), fill(date_time.minute), fill(date_time.second))
        }
        return self._rest.POST(request, json.dumps(data))

    def get_task(self, chore_name, step):
        """ Get task from chore

        :param chore_name: name of the chore
        :param step: integer
        :return: instance of TM1py.ChoreTask
        """
        request = "/api/v1/Chores('{}')/Tasks({})?$expand=*,Process($select=Name),Chore($select=Name)" \
            .format(chore_name, step)
        response = self._rest.GET(request)
        response_as_dict = json.loads(response)
        return ChoreTask.from_dict(response_as_dict)

    def create_task(self, chore_name, chore_task):
        """ Create Chore task on TM1 Server

        :param chore_name: name of Chore to update
        :param chore_task: instance of TM1py.ChoreTask
        :return: response
        """
        request = "/api/v1/Chores('{}')/Tasks".format(chore_name)
        response = self._rest.POST(request, chore_task.body)
        return response

    def update_task(self, chore_name, chore_task):
        """ update a chore task

        :param chore_name: name of the Chore
        :param chore_task: instance TM1py.ChoreTask
        :return: response
        """
        request = "/api/v1/Chores('{}')/Tasks({})".format(chore_name, chore_task.step)
        response = self._rest.PATCH(request, chore_task.body)
        return response

    def execute_chore(self, name_chore):
        """ Ask TM1 Server to execute a chore

            :param name_chore: String, name of the chore to be executed
            :return: String, the response
        """
        return self._rest.POST("/api/v1/Chores('" + name_chore + "')/tm1.Execute", '')
