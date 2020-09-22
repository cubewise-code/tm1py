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

    def sandbox_exists(self, sandbox_name: str, **kwargs):
        """ checks if the sandbox exists in TM1

        :param cube_name: String
        :return: bool
        """
        url = format_url("/api/v1/Sandboxes('{}')", sandbox_name)
        response = self._rest.GET(url=url, **kwargs)
        sandbox = Sandbox.from_json(response.text)
        return sandbox

    def set_sandbox(self, sandbox_name: str):
        """ set sandbox parameter on Rest service, which will be applied to all requests to TM1

        :param sandbox_name: String - name of existing sandbox in TM1
        :return: text
        """
        self._rest._sandbox = sandbox_name
        return sandbox_name

    def set_base(self):
        """ use base version of TM1 data

        :return: text
        """
        self._rest._sandbox = None
        return "[Base]"

    def current_sandbox(self):
        """ returns name of sandbox which is currently set on Rest service

        :return: text
        """
        current_sandbox = self._rest._sandbox
        return current_sandbox
