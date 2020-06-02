# -*- coding: utf-8 -*-
from typing import List

from requests import Response

from TM1py.Objects.User import User
from TM1py.Services.ObjectService import ObjectService
from TM1py.Services.RestService import RestService
from TM1py.Utils import format_url


class MonitoringService(ObjectService):
    """ Service to Query and Cancel Threads in TM1
    
    """

    def __init__(self, rest: RestService):
        super().__init__(rest)

    def get_threads(self, **kwargs) -> List:
        """ Return a dict of the currently running threads from the TM1 Server

            :return:
                dict: the response
        """
        url = '/api/v1/Threads'
        response = self._rest.GET(url, **kwargs)
        return response.json()['value']

    def cancel_thread(self, thread_id: int, **kwargs) -> Response:
        """ Kill a running thread
        
        :param thread_id: 
        :return: 
        """
        url = format_url("/api/v1/Threads('{}')/tm1.CancelOperation", str(thread_id))
        response = self._rest.POST(url, **kwargs)
        return response

    def cancel_all_running_threads(self, **kwargs) -> int:
        running_threads = self.get_threads(**kwargs)
        cancellations = 0
        for thread in running_threads:
            if thread["State"] == "Idle":
                continue
            if thread["Type"] == "System":
                continue
            if thread["Name"] == "Pseudo":
                continue
            if thread["Function"] == "GET /api/v1/Threads":
                continue
            self.cancel_thread(thread["ID"], **kwargs)
            cancellations += 1
        return cancellations

    def get_active_users(self, **kwargs) -> List[User]:
        """ Get the activate users in TM1

        :return: List of TM1py.User instances
        """
        url = '/api/v1/Users?$filter=IsActive eq true&$expand=Groups'
        response = self._rest.GET(url, **kwargs)
        users = [User.from_dict(user) for user in response.json()['value']]
        return users

    def user_is_active(self, user_name: str, **kwargs) -> bool:
        """ Check if user is currently active in TM1

        :param user_name:
        :return: Boolean
        """
        url = format_url("/api/v1/Users('{}')/IsActive", user_name)
        response = self._rest.GET(url, **kwargs)
        return bool(response.json()['value'])

    def disconnect_user(self, user_name: str, **kwargs) -> Response:
        """ Disconnect User
        
        :param user_name: 
        :return: 
        """
        url = format_url("/api/v1/Users('{}')/tm1.Disconnect", user_name)
        response = self._rest.POST(url, **kwargs)
        return response

    def disconnect_all_users(self, *exceptions, **kwargs) -> int:
        active_users = self.get_active_users(**kwargs)
        disconnects = 0
        for active_user in active_users:
            if active_user.name not in exceptions:
                self.disconnect_user(active_user.name, **kwargs)
                disconnects += 1
        return disconnects
