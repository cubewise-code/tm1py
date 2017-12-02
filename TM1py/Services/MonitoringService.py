# -*- coding: utf-8 -*-

import json

from TM1py.Services.ObjectService import ObjectService
from TM1py.Objects.User import User


class MonitoringService(ObjectService):
    """ Service to Query and Cancel Threads in TM1
    
    """
    def __init__(self, rest):
        super().__init__(rest)

    def get_threads(self):
        """ Return a dict of the currently running threads from the TM1 Server

            :return:
                dict: the response
        """
        request = '/api/v1/Threads'
        response = self._rest.GET(request)
        response_as_dict = json.loads(response)['value']
        return response_as_dict

    def cancel_thread(self, thread_id):
        """ Kill a running thread
        
        :param thread_id: 
        :return: 
        """
        request = "/api/v1/Threads('{}')/tm1.CancelOperation".format(thread_id)
        response = self._rest.POST(request, '')
        return response

    def get_active_users(self):
        """ Get the activate users in TM1 Server

        :return: List of TM1py.User instances
        """
        request = '/api/v1/Users?$filter=IsActive eq true&$expand=Groups'
        response = self._rest.GET(request)
        response_as_dict = json.loads(response)
        users = [User.from_dict(user) for user in response_as_dict['value']]
        return users

    def user_is_active(self, user_name):
        """ Check if user is currently activate in TM1

        :param user_name:
        :return: Boolean
        """
        request = "/api/v1/Users('{}')/IsActive".format(user_name)
        response = self._rest.GET(request)
        return json.loads(response)['value']

    def disconnect_user(self, user_name):
        """ Disconnect User
        
        :param user_name: 
        :return: 
        """
        request = "/api/v1/Users('{}')/tm1.Disconnect".format(user_name)
        response = self._rest.POST(request)
        return response
