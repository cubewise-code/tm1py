from TM1py.Exceptions.Exceptions import TM1pyRestException
from TM1py.Services.ObjectService import ObjectService
from TM1py.Services.RestService import RestService
from TM1py.Utils import format_url


class SandboxService(ObjectService):
    """ Service to handle sandboxes in TM1
    
    """

    def __init__(self, rest: RestService):
        super().__init__(rest)

    def get(self, sandbox_name: str, **kwargs):
        """ get sandbox from TM1 Server

        :param cube_name:
        :return: instance of TM1py.Sandbox
        """
        url = format_url("/api/v1/Sandboxes('{}')", sandbox_name)
        response = self._rest.GET(url=url, **kwargs)
        sandbox = response.text
        return sandbox

