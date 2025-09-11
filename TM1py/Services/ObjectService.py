# -*- coding: utf-8 -*-
import hashlib
import random
import threading

from TM1py.Exceptions import TM1pyRestException
from TM1py.Services import RestService
from TM1py.Utils import format_url, verify_version


class ObjectService:
    """Parent class for all Object Services"""

    ELEMENT_ATTRIBUTES_PREFIX = "}ElementAttributes_"
    SANDBOX_DIMENSION = "Sandboxes"

    BINARY_HTTP_HEADER_PRE_V12 = {"Content-Type": "application/octet-stream; odata.streaming=true"}
    BINARY_HTTP_HEADER = {"Content-Type": "application/json;charset=UTF-8"}

    def __init__(self, rest_service: RestService):
        """Constructor, Create an instance of ObjectService

        :param rest_service:
        """
        self._rest = rest_service
        if verify_version("12", self.version):
            self.binary_http_header = self.BINARY_HTTP_HEADER
        else:
            self.binary_http_header = self.BINARY_HTTP_HEADER_PRE_V12

    def suggest_unique_object_name(self, random_seed: float = None) -> str:
        """
        Generate hash based on tm1-session-id, local-thread-id and random id to guarantee unique name
        avoids name conflicts in multithreading operations
        """
        if not random_seed:
            random_seed = random.random()
        unique_string = f"{self._rest.session_id}{threading.get_ident()}{random_seed}"
        unique_hash = "tm1py." + hashlib.sha256(unique_string.encode("utf-8")).hexdigest()[:12]
        return unique_hash

    def determine_actual_object_name(self, object_class: str, object_name: str, **kwargs) -> str:
        url = format_url(
            "/{}?$filter=tolower(replace(Name, ' ', '')) eq '{}'", object_class, object_name.replace(" ", "").lower()
        )
        response = self._rest.GET(url, **kwargs)

        if len(response.json()["value"]) == 0:
            raise ValueError("Object '{}' of type '{}' doesn't exist".format(object_name, object_class))

        return response.json()["value"][0]["Name"]

    def _exists(self, url: str, **kwargs) -> bool:
        """Check if resource exists in the TM1 Server

        :param url:
        :return:
        """
        try:
            self._rest.GET(url, **kwargs)
            return True
        except TM1pyRestException as e:
            if e.status_code == 404:
                return False
            raise e

    @property
    def version(self) -> str:
        return self._rest.version

    @property
    def is_admin(self) -> bool:
        return self._rest.is_admin

    @property
    def is_data_admin(self) -> bool:
        return self._rest.is_data_admin

    @property
    def is_security_admin(self) -> bool:
        return self._rest.is_security_admin

    @property
    def is_ops_admin(self) -> bool:
        return self._rest.is_ops_admin
