# -*- coding: utf-8 -*-

import json

from TM1py.Objects.User import User
from TM1py.Services.ObjectService import ObjectService


class SecurityService(ObjectService):
    """ Service to handle Security stuff
    
    """
    def __init__(self, rest):
        super().__init__(rest)

    def create_user(self, user):
        """ Create a user on TM1 Server

        :param user: instance of TM1py.User
        :return: response
        """
        request = '/api/v1/Users'
        self._rest.POST(request, user.body)

    def get_user(self, user_name):
        """ Get user from TM1 Server

        :param user_name:
        :return: instance of TM1py.User
        """
        request = '/api/v1/Users(\'{}\')?$expand=Groups'.format(user_name)
        response = self._rest.GET(request)
        return User.from_json(response)

    def update_user(self, user):
        """ Update user on TM1 Server

        :param user: instance of TM1py.User
        :return: response
        """
        for current_group in self.get_groups(user.name):
            if current_group not in user.groups:
                self.remove_user_from_group(current_group, user.name)
        request = '/api/v1/Users(\'{}\')'.format(user.name)
        return self._rest.PATCH(request, user.body)

    def delete_user(self, user_name):
        """ Delete user on TM1 Server

        :param user_name:
        :return: response
        """
        request = '/api/v1/Users(\'{}\')'.format(user_name)
        return self._rest.DELETE(request)

    def get_all_users(self):
        """ Get all users from TM1 Server

        :return: List of TM1py.User instances
        """
        request = '/api/v1/Users?$expand=Groups'
        response = self._rest.GET(request)
        response_as_dict = json.loads(response)
        users = [User.from_dict(user) for user in response_as_dict['value']]
        return users

    def get_users_from_group(self, group_name):
        """ Get all users from group

        :param group_name:
        :return: List of TM1py.User instances
        """
        request = '/api/v1/Groups(\'{}\')?$expand=Users($expand=Groups)'.format(group_name)
        response = self._rest.GET(request)
        response_as_dict = json.loads(response)
        users = [User.from_dict(user) for user in response_as_dict['Users']]
        return users

    def get_groups(self, user_name):
        """ Get the groups of a user in TM1 Server

        :param user_name:
        :return: List of strings
        """
        request = '/api/v1/Users(\'{}\')/Groups'.format(user_name)
        response = self._rest.GET(request)
        groups = json.loads(response)['value']
        return [group['Name'] for group in groups]

    def remove_user_from_group(self, group_name, user_name):
        """ Remove user from group in TM1 Server

        :param group_name:
        :param user_name:
        :return: response
        """
        request = '/api/v1/Users(\'{}\')/Groups?$id=Groups(\'{}\')'.format(user_name, group_name)
        return self._rest.DELETE(request)

    def get_all_groups(self):
        """ Get all groups from TM1 Server

        :return: List of strings
        """
        request = '/api/v1/Groups?$select=Name'
        response = self._rest.GET(request)
        response_as_dict = json.loads(response)
        groups = [entry['Name'] for entry in response_as_dict['value']]
        return groups
