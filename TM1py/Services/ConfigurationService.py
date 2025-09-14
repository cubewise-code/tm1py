import json
from typing import Dict

from requests import Response

from TM1py.Services.ObjectService import ObjectService
from TM1py.Services.RestService import RestService
from TM1py.Utils import deprecated_in_version, require_ops_admin


class ConfigurationService(ObjectService):

    def __init__(self, rest: RestService):
        super().__init__(rest)

    def get_all(self, **kwargs) -> Dict:
        url = "/Configuration"
        config = self._rest.GET(url, **kwargs).json()
        del config["@odata.context"]
        return config

    def get_server_name(self, **kwargs) -> str:
        """Ask TM1 Server for its name

        :Returns:
            String, the server name
        """
        url = "/Configuration/ServerName/$value"
        return self._rest.GET(url, **kwargs).text

    def get_product_version(self, **kwargs) -> str:
        """Ask TM1 Server for its version

        :Returns:
            String, the version
        """
        url = "/Configuration/ProductVersion/$value"
        return self._rest.GET(url, **kwargs).text

    @deprecated_in_version(version="12.0.0")
    def get_admin_host(self, **kwargs) -> str:
        url = "/Configuration/AdminHost/$value"
        return self._rest.GET(url, **kwargs).text

    @deprecated_in_version(version="12.0.0")
    def get_data_directory(self, **kwargs) -> str:
        url = "/Configuration/DataBaseDirectory/$value"
        return self._rest.GET(url, **kwargs).text

    @require_ops_admin
    def get_static(self, **kwargs) -> Dict:
        """Read TM1 config settings as dictionary from TM1 Server

        :return: config as dictionary
        """
        url = "/StaticConfiguration"
        config = self._rest.GET(url, **kwargs).json()
        del config["@odata.context"]
        return config

    @require_ops_admin
    def get_active(self, **kwargs) -> Dict:
        """Read effective(!) TM1 config settings as dictionary from TM1 Server

        :return: config as dictionary
        """
        url = "/ActiveConfiguration"
        config = self._rest.GET(url, **kwargs).json()
        del config["@odata.context"]
        return config

    @require_ops_admin
    def update_static(self, configuration: Dict) -> Response:
        """Update the .cfg file and triggers TM1 to re-read the file.

        :param configuration:
        :return: Response
        """
        url = "/StaticConfiguration"
        return self._rest.PATCH(url, json.dumps(configuration))
