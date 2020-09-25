from typing import List, Iterable
from requests import Response
import json

from TM1py.Exceptions.Exceptions import TM1pyRestException
from TM1py.Services.ObjectService import ObjectService
from TM1py.Services.RestService import RestService
from TM1py.Utils import format_url
from TM1py.Objects.Sandbox import Sandbox


class SandboxService(ObjectService):
    """ Service to handle sandboxes in TM1
    
    """

    def __init__(self, rest: RestService):
        super().__init__(rest)

    def get(self, sandbox_name: str, **kwargs) -> Sandbox:
        """ get sandbox from TM1 Server

        :param cube_name:
        :return: instance of TM1py.Sandbox
        """
        url = format_url("/api/v1/Sandboxes('{}')", sandbox_name)
        response = self._rest.GET(url=url, **kwargs)
        sandbox = Sandbox.from_json(response.text)
        return sandbox

    def create(self, sandbox: Sandbox, **kwargs) -> Response:
        """ create a new sandbox in TM1 Server

        :param sandbox: Sandbox
        :return: response
        """
        url = format_url("/api/v1/Sandboxes")
        return self._rest.POST(url=url, data=sandbox.body, **kwargs)

    def delete(self, sandbox_name: str, **kwargs) -> Response:
        """ Delete a sandbox in TM1

        :param sandbox_name:
        :return: response
        """
        url = format_url("/api/v1/Sandboxes('{}')", sandbox_name)
        return self._rest.DELETE(url, **kwargs)

    def publish(self, sandbox_name: str, **kwargs) -> Response:
        """ publish existing sandbox to base

        :param sandbox_name: str
        :return: response
        """
        url = format_url("/api/v1/Sandboxes('{}')/tm1.Publish", sandbox_name)
        return self._rest.POST(url=url, **kwargs)

    def reset(self, sandbox_name: str, **kwargs) -> Response:
        """ reset all changes in specified sandbox

        :param sandbox_name: str
        :return: response
        """
        url = format_url("/api/v1/Sandboxes('{}')/tm1.DiscardChanges", sandbox_name)
        return self._rest.POST(url=url, **kwargs)

    def merge(
        self,
        source_sandbox_name: str,
        target_sandbox_name: str,
        clean_after: bool = False,
        **kwargs
    ) -> Response:
        """ merge one sandbox into another

        :param source_sandbox_name: str
        :param target_sandbox_name: str
        :param clean_after: bool: Reset source sandbox after merging
        :return: response
        """
        url = format_url("/api/v1/Sandboxes('{}')/tm1.Merge", source_sandbox_name)
        payload = dict()
        payload["Target@odata.bind"] = format_url(
            "Sandboxes('{}')", target_sandbox_name
        )
        payload["CleanAfter"] = clean_after
        return self._rest.POST(url=url, data=json.dumps(payload), **kwargs)

    def get_all(self, **kwargs) -> List[Sandbox]:
        """ get all sandboxes from TM1 Server

        :return: List of TM1py.Sandbox instances
        """
        url = "/api/v1/Sandboxes?$select=Name,IncludeInSandboxDimension"
        response = self._rest.GET(url, **kwargs)
        sandboxes = [
            Sandbox.from_dict(sandbox_as_dict=sandbox)
            for sandbox in response.json()["value"]
        ]
        return sandboxes

    def exists(self, sandbox_name: str, **kwargs) -> bool:
        """ checks if the sandbox exists in TM1

        :param cube_name: String
        :return: bool
        """
        url = format_url("/api/v1/Sandboxes('{}')", sandbox_name)
        return self._exists(url, **kwargs)

    def set_sandbox(self, sandbox_name: str) -> str:
        """ set sandbox parameter on Rest service, which will be applied to all requests to TM1

        :param sandbox_name: String - name of existing sandbox in TM1
        :return: text
        """
        self._rest._sandbox = sandbox_name
        return sandbox_name

    def set_base(self) -> str:
        """ use base version of TM1 data

        :return: text
        """
        self._rest._sandbox = None
        return "[Base]"

    def current_sandbox(self) -> str:
        """ returns name of the sandbox which is currently set on Rest service

        :return: text
        """
        current_sandbox = self._rest._sandbox
        return current_sandbox
