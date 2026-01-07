from typing import List

from requests import Response

from TM1py.Services.ObjectService import ObjectService
from TM1py.Services.RestService import RestService
from TM1py.Services.UserService import UserService
from TM1py.Utils import case_and_space_insensitive_equals, format_url, require_admin


class SessionService(ObjectService):
    """Service to Query and Cancel Threads in TM1"""

    def __init__(self, rest: RestService):
        super().__init__(rest)
        self.users = UserService(rest)

    def get_all(self, include_user: bool = True, include_threads: bool = True, **kwargs) -> List:
        url = "/Sessions"
        if include_user or include_threads:
            expands = list()
            if include_user:
                expands.append("User")
            if include_threads:
                expands.append("Threads")
            url += "?$expand=" + ",".join(expands)

        response = self._rest.GET(url, **kwargs)
        return response.json()["value"]

    def get_current(self, **kwargs):
        url = "/ActiveSession"

        response = self._rest.GET(url, **kwargs)
        return response.json()["value"]

    def get_threads_for_current(self, exclude_idle: bool = True, **kwargs):
        url = "/ActiveSession/Threads?$filter=Function ne 'GET /ActiveSession/Threads' and Function ne 'GET /api/v1/ActiveSession/Threads'"
        if exclude_idle:
            url += " and State ne 'Idle'"

        response = self._rest.GET(url, **kwargs)
        return response.json()["value"]

    def close(self, session_id, **kwargs) -> Response:
        url = format_url(f"/Sessions('{session_id}')/tm1.Close")
        return self._rest.POST(url, **kwargs)

    @require_admin
    def close_all(self, **kwargs) -> list:
        current_user = self.users.get_current(**kwargs)
        sessions = self.get_all(**kwargs)
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
            self.close(session["ID"], **kwargs)
            closed_sessions.append(session)
        return closed_sessions
