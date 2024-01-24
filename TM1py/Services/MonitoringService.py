# -*- coding: utf-8 -*-
from typing import List
from warnings import warn
from requests import Response

from TM1py.Objects.User import User
from TM1py.Services.ObjectService import ObjectService
from TM1py.Services.RestService import RestService
from TM1py.Utils import require_admin
from TM1py.Services.ThreadService import ThreadService
from TM1py.Services.SessionService import SessionService
from TM1py.Services.UserService import UserService


class MonitoringService(ObjectService):
    """ Service to Query and Cancel Threads in TM1
    
    """

    def __init__(self, rest: RestService):
        super().__init__(rest)
        warn("Monitoring Service will be moved to a new location in a future version", DeprecationWarning, 2)
        self.users = UserService(rest)
        self.threads = ThreadService(rest)
        self.session = SessionService(rest)

    def get_threads(self, **kwargs) -> List:
        """ Return a dict of the currently running threads from the TM1 Server

            :return:
                dict: the response
        """
        return self.threads.get_all(**kwargs)

    def get_active_threads(self, **kwargs):
        """Return a list of non-idle threads from the TM1 Server

            :return:
                list: TM1 threads as dict
        """
        return self.threads.get_active(**kwargs)

    def cancel_thread(self, thread_id: int, **kwargs) -> Response:
        """ Kill a running thread
        
        :param thread_id: 
        :return: 
        """
        return self.threads.cancel(thread_id, **kwargs)

    def cancel_all_running_threads(self, **kwargs) -> list:
        return self.threads.cancel_all_running(**kwargs)

    def get_active_users(self, **kwargs) -> List[User]:
        """ Get the activate users in TM1

        :return: List of TM1py.User instances
        """
        return self.users.get_active(**kwargs)

    def user_is_active(self, user_name: str, **kwargs) -> bool:
        """ Check if user is currently active in TM1

        :param user_name:
        :return: Boolean
        """
        return self.users.is_active(user_name, **kwargs)

    def disconnect_user(self, user_name: str, **kwargs) -> Response:
        """ Disconnect User
        
        :param user_name: 
        :return: 
        """
        return self.users.disconnect(user_name, **kwargs)

    def get_active_session_threads(self, exclude_idle: bool = True, **kwargs):
        return self.session.get_threads_for_current(exclude_idle, **kwargs)

    def get_sessions(self, include_user: bool = True, include_threads: bool = True, **kwargs) -> List:
        return self.session.get_all(include_user, include_threads, **kwargs)

    @require_admin
    def disconnect_all_users(self, **kwargs) -> list:
        return self.users.disconnect_all(**kwargs)

    def close_session(self, session_id, **kwargs) -> Response:
        return self.session.close(session_id, **kwargs)

    @require_admin
    def close_all_sessions(self, **kwargs) -> list:
        return self.session.close_all(**kwargs)

    def get_current_user(self, **kwargs):
        return self.users.get_current(**kwargs)
