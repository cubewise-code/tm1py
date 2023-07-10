# -*- coding: utf-8 -*-

import json
from typing import List, Iterable

from requests import Response

from TM1py.Objects.User import User
from TM1py.Services.ObjectService import ObjectService
from TM1py.Services.RestService import RestService
from TM1py.Utils.Utils import format_url, CaseAndSpaceInsensitiveSet, require_admin


class SecurityService(ObjectService):
    """ Service to handle Security stuff
    
    """

    def __init__(self, rest: RestService):
        super().__init__(rest)

    def determine_actual_user_name(self, user_name: str, **kwargs) -> str:
        return self.determine_actual_object_name(object_class="Users", object_name=user_name, **kwargs)

    def determine_actual_group_name(self, group_name: str, **kwargs) -> str:
        return self.determine_actual_object_name(object_class="Groups", object_name=group_name, **kwargs)

    @require_admin
    def create_user(self, user: User, **kwargs) -> Response:
        """ Create a user on TM1 Server

        :param user: instance of TM1py.User
        :return: response
        """
        url = '/Users'
        return self._rest.POST(url, user.body, **kwargs)

    @require_admin
    def create_group(self, group_name: str, **kwargs) -> Response:
        """ Create a Security group in the TM1 Server

        :param group_name:
        :return:
        """
        url = '/Groups'
        return self._rest.POST(url, json.dumps({"Name": group_name}), **kwargs)

    def get_user(self, user_name: str, **kwargs) -> User:
        """ Get user from TM1 Server

        :param user_name:
        :return: instance of TM1py.User
        """
        user_name = self.determine_actual_user_name(user_name, **kwargs)
        url = format_url(
            "/Users('{}')?$select=Name,FriendlyName,Password,Type,Enabled&$expand=Groups",
            user_name)
        response = self._rest.GET(url, **kwargs)
        return User.from_dict(response.json())

    def get_current_user(self, **kwargs) -> User:
        """ Get user and group assignments of this session

        :return: instance of TM1py.User
        """
        url = "/ActiveUser?$select=Name,FriendlyName,Password,Type,Enabled&$expand=Groups"
        response = self._rest.GET(url, **kwargs)
        return User.from_dict(response.json())

    @require_admin
    def update_user(self, user: User, **kwargs) -> Response:
        """ Update user on TM1 Server

        :param user: instance of TM1py.User
        :return: response
        """
        user.name = self.determine_actual_user_name(user.name, **kwargs)
        for current_group in self.get_groups(user.name, **kwargs):
            if current_group not in user.groups:
                self.remove_user_from_group(current_group, user.name, **kwargs)
        url = format_url("/Users('{}')", user.name)
        return self._rest.PATCH(url, user.body, **kwargs)

    def update_user_password(self, user_name: str, password: str, **kwargs) -> Response:
        url = format_url("/Users('{}')", user_name)
        body = {"Password": password}
        return self._rest.PATCH(url, json.dumps(body), **kwargs)

    @require_admin
    def delete_user(self, user_name: str, **kwargs) -> Response:
        """ Delete user on TM1 Server

        :param user_name:
        :return: response
        """
        user_name = self.determine_actual_user_name(user_name, **kwargs)
        url = format_url("/Users('{}')", user_name)
        return self._rest.DELETE(url, **kwargs)

    @require_admin
    def delete_group(self, group_name: str, **kwargs) -> Response:
        """ Delete a group in the TM1 Server

        :param group_name:
        :return:
        """
        group_name = self.determine_actual_group_name(group_name, **kwargs)
        url = format_url("/Groups('{}')", group_name)
        return self._rest.DELETE(url, **kwargs)

    def get_all_users(self, **kwargs):
        """ Get all users from TM1 Server

        :return: List of TM1py.User instances
        """
        url = '/Users?$select=Name,FriendlyName,Password,Type,Enabled&$expand=Groups'
        response = self._rest.GET(url, **kwargs)
        users = [User.from_dict(user) for user in response.json()['value']]
        return users

    def get_all_user_names(self, **kwargs):
        """ Get all user names from TM1 Server

        :return: List of TM1py.User instances
        """
        url = '/Users?select=Name'
        response = self._rest.GET(url, **kwargs)
        users = [user["Name"] for user in response.json()['value']]
        return users

    def get_users_from_group(self, group_name: str, **kwargs):
        """ Get all users from group

        :param group_name:
        :return: List of TM1py.User instances
        """
        url = format_url(
            "/Groups('{}')?$expand=Users($select=Name,FriendlyName,Password,Type,Enabled;$expand=Groups)",
            group_name)
        response = self._rest.GET(url, **kwargs)
        users = [User.from_dict(user) for user in response.json()['Users']]
        return users

    def get_user_names_from_group(self, group_name: str, **kwargs) -> List[str]:
        """ Get all users from group

        :param group_name:
        :return: List of strings
        """
        url = format_url("/Groups('{}')?$expand=Users($expand=Groups)", group_name)
        response = self._rest.GET(url, **kwargs)
        users = [user["Name"] for user in response.json()['Users']]
        return users

    def get_groups(self, user_name: str, **kwargs) -> List[str]:
        """ Get the groups of a user in TM1 Server

        :param user_name:
        :return: List of strings
        """
        user_name = self.determine_actual_user_name(user_name, **kwargs)
        url = format_url("/Users('{}')/Groups", user_name)
        response = self._rest.GET(url, **kwargs)
        return [group['Name'] for group in response.json()['value']]

    @require_admin
    def add_user_to_groups(self, user_name: str, groups: Iterable[str], **kwargs) -> Response:
        """
        
        :param user_name: name of user
        :param groups: iterable of groups
        :return: response
        """
        user_name = self.determine_actual_user_name(user_name, **kwargs)
        url = format_url("/Users('{}')", user_name)
        body = {
            "Name": user_name,
            "Groups@odata.bind": [
                format_url("Groups('{}')", self.determine_actual_group_name(group))
                for group
                in groups]
        }
        return self._rest.PATCH(url, json.dumps(body), **kwargs)

    @require_admin
    def remove_user_from_group(self, group_name: str, user_name: str, **kwargs) -> Response:
        """ Remove user from group in TM1 Server

        :param group_name:
        :param user_name:
        :return: response
        """
        user_name = self.determine_actual_user_name(user_name, **kwargs)
        group_name = self.determine_actual_group_name(group_name, **kwargs)
        url = format_url("/Users('{}')/Groups?$id=Groups('{}')", user_name, group_name)
        return self._rest.DELETE(url, **kwargs)

    def get_all_groups(self, **kwargs) -> List[str]:
        """ Get all groups from TM1 Server

        :return: List of strings
        """
        url = '/Groups?$select=Name'
        response = self._rest.GET(url, **kwargs)
        groups = [entry['Name'] for entry in response.json()['value']]
        return groups

    @require_admin
    def security_refresh(self, **kwargs) -> Response:
        from TM1py.Services import ProcessService
        ti = "SecurityRefresh;"
        process_service = ProcessService(self._rest)
        return process_service.execute_ti_code(ti, **kwargs)

    def user_exists(self, user_name: str, **kwargs) -> bool:
        url = format_url("/Users('{}')", user_name)
        return self._exists(url, **kwargs)

    def group_exists(self, group_name: str, **kwargs) -> bool:
        url = format_url("/Groups('{}')", group_name)
        return self._exists(url, **kwargs)

    def get_custom_security_groups(self, **kwargs) -> List[str]:
        custom_groups = CaseAndSpaceInsensitiveSet(*self.get_all_groups(**kwargs))
        custom_groups.discard('Admin')
        custom_groups.discard('DataAdmin')
        custom_groups.discard('SecurityAdmin')
        custom_groups.discard('OperationsAdmin')
        custom_groups.discard('}tp_Everyone')

        return list(custom_groups)

    def get_read_only_users(self, **kwargs) -> List[str]:
        read_only_users = list()

        mdx = """
        SELECT
        {[}ClientProperties].[ReadOnlyUser]} ON COLUMNS,
        NON EMPTY {[}Clients].MEMBERS} ON ROWS
        FROM [}ClientProperties]
        """

        from TM1py import CellService
        cell_service = CellService(self._rest)

        users_with_flag = cell_service.execute_mdx_rows_and_values(
            mdx=mdx,
            element_unique_names=False,
            **kwargs)

        for row, values in users_with_flag.items():
            user = row[0]
            read_only = values[0]
            if read_only:
                read_only_users.append(user)
        return read_only_users
