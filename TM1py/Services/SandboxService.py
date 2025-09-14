from typing import List
from requests import Response
import json

from TM1py.Services.ObjectService import ObjectService
from TM1py.Services.RestService import RestService
from TM1py.Utils import format_url
from TM1py.Objects.Sandbox import Sandbox


class SandboxService(ObjectService):
    """Service to handle sandboxes in TM1"""

    def __init__(self, rest: RestService):
        super().__init__(rest)

    def get(self, sandbox_name: str, **kwargs) -> Sandbox:
        """get a sandbox from TM1 Server

        :param sandbox_name: str
        :return: instance of TM1py.Sandbox
        """
        url = format_url("/Sandboxes('{}')", sandbox_name)
        response = self._rest.GET(url=url, **kwargs)
        sandbox = Sandbox.from_json(response.text)
        return sandbox

    def get_all(self, **kwargs) -> List[Sandbox]:
        """get all sandboxes from TM1 Server

        :return: List of TM1py.Sandbox instances
        """
        url = "/Sandboxes?$select=Name,IncludeInSandboxDimension,IsLoaded,IsActive,IsQueued"
        response = self._rest.GET(url, **kwargs)
        sandboxes = [Sandbox.from_dict(sandbox_as_dict=sandbox) for sandbox in response.json()["value"]]
        return sandboxes

    def get_all_names(self, **kwargs) -> List[str]:
        """get all sandbox names

        :param kwargs:
        :return:
        """
        url = "/Sandboxes?$select=Name"
        response = self._rest.GET(url, **kwargs)
        return [entry["Name"] for entry in response.json()["value"]]

    def create(self, sandbox: Sandbox, **kwargs) -> Response:
        """create a new sandbox in TM1 Server

        :param sandbox: Sandbox
        :return: response
        """
        url = "/Sandboxes"
        return self._rest.POST(url=url, data=sandbox.body, **kwargs)

    def update(self, sandbox: Sandbox, **kwargs) -> Response:
        """update a sandbox in TM1

        :param sandbox:
        :return: response
        """
        url = format_url("/Sandboxes('{}')", sandbox.name)
        return self._rest.PATCH(url=url, data=sandbox.body, **kwargs)

    def delete(self, sandbox_name: str, **kwargs) -> Response:
        """delete a sandbox in TM1

        :param sandbox_name:
        :return: response
        """
        url = format_url("/Sandboxes('{}')", sandbox_name)
        return self._rest.DELETE(url, **kwargs)

    def publish(self, sandbox_name: str, **kwargs) -> Response:
        """publish existing sandbox to base

        :param sandbox_name: str
        :return: response
        """
        url = format_url("/Sandboxes('{}')/tm1.Publish", sandbox_name)
        return self._rest.POST(url=url, **kwargs)

    def reset(self, sandbox_name: str, **kwargs) -> Response:
        """reset all changes in specified sandbox

        :param sandbox_name: str
        :return: response
        """
        url = format_url("/Sandboxes('{}')/tm1.DiscardChanges", sandbox_name)
        return self._rest.POST(url=url, **kwargs)

    def merge(
        self, source_sandbox_name: str, target_sandbox_name: str, clean_after: bool = False, **kwargs
    ) -> Response:
        """merge one sandbox into another

        :param source_sandbox_name: str
        :param target_sandbox_name: str
        :param clean_after: bool: Reset source sandbox after merging
        :return: response
        """
        url = format_url("/Sandboxes('{}')/tm1.Merge", source_sandbox_name)
        payload = dict()
        payload["Target@odata.bind"] = format_url("Sandboxes('{}')", target_sandbox_name)
        payload["CleanAfter"] = clean_after
        return self._rest.POST(url=url, data=json.dumps(payload), **kwargs)

    def exists(self, sandbox_name: str, **kwargs) -> bool:
        """check if the sandbox exists in TM1

        :param sandbox_name: String
        :return: bool
        """
        url = format_url("/Sandboxes('{}')", sandbox_name)
        return self._exists(url, **kwargs)

    def load(self, sandbox_name: str, **kwargs) -> Response:
        """load sandbox into memory

        :param sandbox_name: str
        :return: response
        """
        url = format_url("/Sandboxes('{}')/tm1.Load", sandbox_name)
        return self._rest.POST(url=url, **kwargs)

    def unload(self, sandbox_name: str, **kwargs) -> Response:
        """unload sandbox from memory

        :param sandbox_name: str
        :return: response
        """
        url = format_url("/Sandboxes('{}')/tm1.Unload", sandbox_name)
        return self._rest.POST(url=url, **kwargs)
