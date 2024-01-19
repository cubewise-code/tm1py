from requests import Response
from typing import List

from TM1py.Objects.User import User
from TM1py.Services.ObjectService import ObjectService
from TM1py.Services.RestService import RestService
from TM1py.Utils import format_url, case_and_space_insensitive_equals, require_admin, deprecated_in_version


class UserService(ObjectService):

    def __init__(self, rest: RestService):
        super().__init__(rest)

    def get(self, **kwargs) ->List[User]:
        """ Get all users

        :return: List of TM1py.User instances
        """
        url = '/Users?$expand=Groups'
        response = self._rest.GET(url, **kwargs)
        users = [User.from_dict(user) for user in response.json()['value']]
        return users

    def get_active(self, **kwargs) -> List[User]:
        """ Get the activate users in TM1

        :return: List of TM1py.User instances
        """
        url = '/Users?$filter=IsActive eq true&$expand=Groups'
        response = self._rest.GET(url, **kwargs)
        users = [User.from_dict(user) for user in response.json()['value']]
        return users

    def is_active(self, user_name: str, **kwargs) -> bool:
        """ Check if user is currently active in TM1

        :param user_name:
        :return: Boolean
        """
        url = format_url("/Users('{}')/IsActive", user_name)
        response = self._rest.GET(url, **kwargs)
        return bool(response.json()['value'])

    def disconnect(self, user_name: str, **kwargs) -> Response:
        """ Disconnect User

        :param user_name:
        :return:
        """
        url = format_url("/Users('{}')/tm1.Disconnect", user_name)
        response = self._rest.POST(url, **kwargs)
        return response

    @require_admin
    def disconnect_all(self, **kwargs) -> list:
        current_user = self.get_current(**kwargs)
        active_users = self.get_active(**kwargs)
        disconnected_users = list()
        for active_user in active_users:
            if not case_and_space_insensitive_equals(current_user.name, active_user.name):
                self.disconnect(active_user.name, **kwargs)
                disconnected_users += [active_user.name]
        return disconnected_users

    def get_current(self, **kwargs):
        from TM1py import SecurityService
        security_service = SecurityService(self._rest)
        return security_service.get_current_user(**kwargs)
