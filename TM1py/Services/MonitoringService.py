# -*- coding: utf-8 -*-
from typing import List

from requests import Response

from TM1py.Objects.User import User
from TM1py.Services.ObjectService import ObjectService
from TM1py.Services.RestService import RestService
from TM1py.Utils import format_url, case_and_space_insensitive_equals, require_admin


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

    def cancel_all_running_threads(self, **kwargs) -> list:
        running_threads = self.get_threads(**kwargs)
        canceled_threads = list()
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
            canceled_threads.append(thread)
        return canceled_threads

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

    def get_sessions(self, include_user: bool = True, include_threads: bool = True, **kwargs) -> List:
        url = "/api/v1/Sessions"
        if include_user or include_threads:
            expands = list()
            if include_user:
                expands.append("User")
            if include_threads:
                expands.append("Threads")
            url += "?$expand=" + ",".join(expands)

        response = self._rest.GET(url, **kwargs)
        return response.json()["value"]

    @require_admin
    def disconnect_all_users(self, **kwargs) -> list:
        current_user = self.get_current_user(**kwargs)
        active_users = self.get_active_users(**kwargs)
        disconnected_users = list()
        for active_user in active_users:
            if not case_and_space_insensitive_equals(current_user.name, active_user.name):
                self.disconnect_user(active_user.name, **kwargs)
                disconnected_users += [active_user.name]
        return disconnected_users

    def close_session(self, session_id, **kwargs) -> Response:
        url = format_url(f"/api/v1/Sessions('{session_id}')/tm1.Close")
        return self._rest.POST(url, **kwargs)

    @require_admin
    def close_all_sessions(self, **kwargs) -> list:
        current_user = self.get_current_user(**kwargs)
        sessions = self.get_sessions(**kwargs)
        closed_sessions = list()
        for session in sessions:
            if "User" not in session:
                continue
            if session["User"] is None:
                continue
            if "Name" not in session["User"]:
                continue
            if case_and_space_insensitive_equals(current_user.name, session["User"]["Name"]):
                continue
            self.close_session(session['ID'], **kwargs)
            closed_sessions.append(session)
        return closed_sessions

    def get_current_user(self, **kwargs):
        from TM1py import SecurityService
        security_service = SecurityService(self._rest)
        return security_service.get_current_user(**kwargs)
