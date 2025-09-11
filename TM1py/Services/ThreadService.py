from requests import Response
from warnings import warn

from typing import List

from TM1py.Services.ObjectService import ObjectService
from TM1py.Services.RestService import RestService
from TM1py.Utils.Utils import format_url, verify_version, deprecated_in_version


class ThreadService(ObjectService):
    """Service to work with Threads in TM1
    Deprecated as of TM1 Server v12

    """

    def __init__(self, rest: RestService):
        super().__init__(rest)
        if verify_version(required_version="12.0.0", version=self.version):
            # warn only due to use in Monitoring Service
            warn("Threads not available in this version of TM1, removed as of 12.0.0", DeprecationWarning, 2)

    @deprecated_in_version(version="12.0.0")
    def get_all(self, **kwargs) -> List:
        """Return a list of the currently running threads from the TM1 Server

        :return:
            dict: the response
        """
        url = "/Threads"
        response = self._rest.GET(url, **kwargs)
        return response.json()["value"]

    @deprecated_in_version(version="12.0.0")
    def get_active(self, **kwargs):
        """Return a list of non-idle threads from the TM1 Server

        :return:
            list: TM1 threads as dict
        """
        url = "/Threads?$filter=Function ne 'GET /Threads' and State ne 'Idle'"
        response = self._rest.GET(url, **kwargs)
        return response.json()["value"]

    @deprecated_in_version(version="12.0.0")
    def cancel(self, thread_id: int, **kwargs) -> Response:
        """Kill a running thread

        :param thread_id:
        :return:
        """
        url = format_url("/Threads('{}')/tm1.CancelOperation", str(thread_id))
        response = self._rest.POST(url, **kwargs)
        return response

    @deprecated_in_version(version="12.0.0")
    def cancel_all_running(self, **kwargs) -> list:
        running_threads = self.get_all(**kwargs)
        canceled_threads = list()
        for thread in running_threads:
            if thread["State"] == "Idle":
                continue
            if thread["Type"] == "System":
                continue
            if thread["Name"] == "Pseudo":
                continue
            if thread["Function"] == "GET /Threads":
                continue
            if thread["Function"] == "GET /api/v1/Threads":
                continue
            self.cancel(thread["ID"], **kwargs)
            canceled_threads.append(thread)
        return canceled_threads
