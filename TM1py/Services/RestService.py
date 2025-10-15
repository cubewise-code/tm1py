# -*- coding: utf-8 -*-
import json
import re
import socket
import time
import warnings
from ast import literal_eval
from base64 import b64decode, b64encode
from enum import Enum
from http.client import HTTPResponse
from http.cookies import SimpleCookie
from io import BytesIO
from json import JSONDecodeError
from typing import Dict, Optional, Tuple, Union

import requests
import urllib3
from requests import ConnectionError, Response, Session, Timeout
from requests.adapters import HTTPAdapter
from requests.auth import HTTPBasicAuth
from urllib3._collections import HTTPHeaderDict

from TM1py.Exceptions.Exceptions import TM1pyTimeout, TM1pyVersionDeprecationException
from TM1py.Utils import (
    CaseAndSpaceInsensitiveSet,
    HTTPAdapterWithSocketOptions,
    case_and_space_insensitive_equals,
    verify_version,
)

try:
    from requests_negotiate_sspi import HttpNegotiateAuth
except ImportError:
    warnings.warn("requests_negotiate_sspi failed to import. SSO will not work", ImportWarning)

import http.client as http_client

from TM1py.Exceptions import TM1pyRestException


class AuthenticationMode(Enum):
    BASIC = 1
    WIA = 2
    CAM = 3
    CAM_SSO = 4
    # 5 is legacy early-release of v12. Deprecate with next major release
    IBM_CLOUD_API_KEY = 5
    SERVICE_TO_SERVICE = 6
    PA_PROXY = 7
    BASIC_API_KEY = 8
    ACCESS_TOKEN = 9

    @property
    def use_v12_auth(self):
        if self.value < 5:
            return False
        return True


class RestService:
    """Low level communication with TM1 instance through HTTP.
    Allows to execute HTTP Methods
        - GET
        - POST
        - PATCH
        - DELETE
    Takes Care of
        - Encodings
        - TM1 User-Login
        - HTTP Headers
        - HTTP Session Management
        - Response Handling
    Based on requests module
    """

    HEADERS = {
        "Connection": "keep-alive",
        "User-Agent": "TM1py",
        "Content-Type": "application/json; odata.streaming=true; charset=utf-8",
        "Accept": "application/json;odata.metadata=none,text/plain",
        "TM1-SessionContext": "TM1py",
    }

    DEFAULT_CONNECTION_POOL_SIZE = 10
    DEFAULT_POOL_CONNECTIONS = 1

    def __init__(self, **kwargs):
        """Create an instance of RESTService
        :param address: String - address of the TM1 instance
        :param port: Int - HTTPPortNumber as specified in the tm1s.cfg
        :param ssl: boolean -  as specified in the tm1s.cfg
        :param instance: string -  planing analytics engine (v12) instance name
        :param database: string -  planing analytics engine (v12) database name
        :param base_url - base url
        :param auth_url - auth url for planning analytics engine (v12)
        :param user: String - name of the user
        :param password String - password of the user
        :param decode_b64 - whether password argument is b64 encoded
        :param namespace String - optional CAM namespace
        :param cam_passport: String - the cam passport
        :param session_id: String - TM1SessionId e.g. q7O6e1w49AixeuLVxJ1GZg
        :param application_client_id - planning analytics engine (v12) named application client ID created via manage service
        :param application_client_secret - planning analytics engine (v12) named application secret created via manage service
        :param api_key: String - planing analytics engine (v12) API Key from https://cloud.ibm.com/iam/apikeys
        :param iam_url: String - planing analytics engine (v12) IBM Cloud IAM URL. Default: "https://iam.cloud.ibm.com"
        :param pa_url: String - planing analytics engine (v12) PA URL e.g., "https://us-east-2.aws.planninganalytics.ibm.com"
        :param cpd_url: String - cloud pack for data url (aka ZEN) CPD URL e.g., "https://cpd-zen.apps.cp4dpa-test11.cp.fyre.ibm.com"
        :param tenant: String - planing analytics engine (v12) Tenant e.g., YC4B2M1AG2Y6
        :param session_context: String - Name of the Application. Controls "Context" column in Arc / TM1top.
                If None, use default: TM1py
        :param verify: path to .cer file or 'True' / True / 'False' / False (if no ssl verification is required)
        :param logging: boolean - switch on/off verbose http logging into sys.stdout
        :param timeout: Float - Number of seconds that the client will wait to receive the first byte.
        :param cancel_at_timeout: Abort operation in TM1 when timeout is reached
        :param async_requests_mode: changes internal REST execution mode to avoid 60s timeout on IBM cloud
        :param connection_pool_size - Maximum number of connections to save in the pool (default: 10).
                In a multi threaded environment, you should set this value to a higher number, such as the number of threads
        :param pool_connections: Number of connection pools to cache (default: 1 for a single TM1 instance)
        :param integrated_login: True for IntegratedSecurityMode3
        :param integrated_login_domain: NT Domain name.
                Default: '.' for local account.
        :param integrated_login_service: Kerberos Service type for remote Service Principal Name.
                Default: 'HTTP'
        :param integrated_login_host: Host name for Service Principal Name.
                Default: Extracted from request URI
        :param integrated_login_delegate: Indicates that the user's credentials are to be delegated to the server.
                Default: False
        :param impersonate: Name of user to impersonate
        :param re_connect_on_session_timeout: attempt to reconnect once if session is timed out
        :param re_connect_on_remote_disconnect: attempt to reconnect once if connection is aborted by remote end
        :param proxies: pass a dictionary with proxies e.g.
                {'http': 'http://proxy.example.com:8080', 'https': 'http://secureproxy.example.com:8090'}
        :param ssl_context: Pass a user defined ssl context
        :param cert: (optional) If String, path to SSL client cert file (.pem).
                If Tuple, ('cert', 'key') pair
        """
        # store kwargs for future use e.g. re_connect on 401 session timeout
        self._kwargs = kwargs

        # core arguments for connection
        self._ssl = self.translate_to_boolean(kwargs.get("ssl", True))
        self._address = kwargs.get("address", None)
        self._port = kwargs.get("port", None)
        self._base_url = kwargs.get("base_url", None)
        self._auth_url = kwargs.get("auth_url", None)
        self._instance = kwargs.get("instance", None)
        self._database = kwargs.get("database", None)
        self._api_key = kwargs.get("api_key", None)
        self._iam_url = kwargs.get("iam_url", None)
        self._pa_url = kwargs.get("pa_url", None)
        self._cpd_url = kwargs.get("cpd_url", None)
        self._tenant = kwargs.get("tenant", None)
        self._user = kwargs.get("user", kwargs.get("username", None))

        # other arguments
        self._auth_mode = self._determine_auth_mode()
        self._timeout = None if kwargs.get("timeout", None) is None else float(kwargs.get("timeout"))
        self._cancel_at_timeout = kwargs.get("cancel_at_timeout", False)
        self._async_requests_mode = self.translate_to_boolean(kwargs.get("async_requests_mode", False))
        self._connection_pool_size = int(kwargs.get("connection_pool_size", self.DEFAULT_CONNECTION_POOL_SIZE))
        self._pool_connections = int(kwargs.get("pool_connections", self.DEFAULT_POOL_CONNECTIONS))
        self._re_connect_on_session_timeout = kwargs.get("re_connect_on_session_timeout", True)
        self._re_connect_on_remote_disconnect = kwargs.get("re_connect_on_remote_disconnect", True)
        # is retrieved on demand and then cached
        self._sandboxing_disabled = None
        # optional verbose logging to stdout
        self.handle_logging(kwargs.get("logging", False))

        self._proxies = self._handle_proxies(kwargs.get("proxies", None))
        self._is_admin = None
        self._is_data_admin = None
        self._is_security_admin = None
        self._is_ops_admin = None
        self._ssl_context = kwargs.get("ssl_context", None)

        # populated later on the fly for users with the name different from 'Admin'
        if self._user and case_and_space_insensitive_equals(self._user, "ADMIN"):
            self._is_admin = True
            self._is_data_admin = True
            self._is_security_admin = True
            self._is_ops_admin = True

        self._verify = self._determine_verify(kwargs.get("verify", None))

        self._base_url, self._auth_url = self._construct_service_and_auth_root()

        self._version = None
        self._headers = self.HEADERS.copy()
        if "session_context" in kwargs:
            self._headers["TM1-SessionContext"] = kwargs["session_context"]

        self.disable_http_warnings()

        self._s = Session()
        self._manage_http_adapter()

        self._cert = kwargs.get("cert")
        self._s.cert = self._cert

        if self._proxies:
            self._s.proxies = self._proxies

        # First contact with TM1
        self.connect()
        if not self._version:
            self.set_version()

    def _determine_verify(self, verify: [bool, str] = None) -> [bool, str]:
        if verify is None:
            # Default SSL verification in v12 is True
            if self._auth_mode in [
                AuthenticationMode.IBM_CLOUD_API_KEY,
                AuthenticationMode.SERVICE_TO_SERVICE,
                AuthenticationMode.BASIC_API_KEY,
                AuthenticationMode.ACCESS_TOKEN,
            ]:
                return True
            else:
                return False

        if isinstance(verify, str):
            if verify.upper() == "FALSE":
                return False
            elif verify.upper() == "TRUE":
                return True

            # path to .cer file
            else:
                return verify

        elif isinstance(verify, bool):
            return verify

        raise ValueError("'verify' argument must be of type str or bool")

    def handle_logging(self, logging: Union[str, bool]):
        if logging:
            if self.translate_to_boolean(value=logging):
                http_client.HTTPConnection.debuglevel = 1

    def _handle_proxies(self, proxies: Union[Dict, str]):
        if proxies is None or isinstance(proxies, dict):
            return proxies

        elif isinstance(proxies, str):
            try:
                return json.loads(proxies)
            except JSONDecodeError:
                raise ValueError("Invalid JSON passed for argument 'proxies': %s", proxies)

        # handle invalid type
        raise ValueError("Argument of 'proxies' must be None, dictionary or JSON string")

    def request(
        self,
        method: str,
        url: str,
        data: str = "",
        encoding="utf-8",
        async_requests_mode: Optional[bool] = None,
        return_async_id=False,
        timeout: float = None,
        cancel_at_timeout: bool = False,
        idempotent: bool = False,
        verify_response: bool = True,
        **kwargs,
    ):
        """
        Execute a request to TM1 REST API
        """
        url, data = self._url_and_body(url=url, data=data, encoding=encoding)

        timeout = timeout if timeout else self._timeout

        try:
            # Determine async mode
            if return_async_id:
                async_requests_mode = True
            elif async_requests_mode is None:
                async_requests_mode = self._async_requests_mode

            # Execute request based on mode
            if not async_requests_mode:
                response = self._execute_sync_request(method=method, url=url, data=data, timeout=timeout, **kwargs)
            else:
                response = self._execute_async_request(
                    method=method,
                    url=url,
                    data=data,
                    timeout=timeout,
                    cancel_at_timeout=cancel_at_timeout,
                    return_async_id=return_async_id,
                    **kwargs,
                )

            # If async_id is returned as string, return it directly
            if return_async_id and isinstance(response, str):
                return response

            # Verify and encode response
            if verify_response:
                self.verify_response(response=response)
            response.encoding = encoding
            return response

        except Timeout:
            if cancel_at_timeout or (cancel_at_timeout is None and self._cancel_at_timeout):
                self.cancel_running_operation()
            raise TM1pyTimeout(method=method, url=url, timeout=timeout)

        except ConnectionError as e:
            # Handle read timeout issue in requests library
            if re.search("Read timed out", str(e), re.IGNORECASE):
                if cancel_at_timeout or (cancel_at_timeout is None and self._cancel_at_timeout):
                    self.cancel_running_operation()
                raise TM1pyTimeout(method=method, url=url, timeout=timeout)

            # Handle RemoteDisconnected errors
            elif re.search("RemoteDisconnected|Connection aborted", str(e), re.IGNORECASE):
                if self._re_connect_on_remote_disconnect:
                    return self._handle_remote_disconnect(
                        e,
                        method,
                        url,
                        data,
                        timeout,
                        idempotent,
                        async_requests_mode,
                        cancel_at_timeout,
                        return_async_id,
                        encoding,
                        **kwargs,
                    )
                else:
                    raise e

            # Other connection errors
            raise e

    def _execute_sync_request(self, method: str, url: str, data: str, timeout: float, **kwargs):
        """
        Execute a synchronous request with session timeout handling
        """
        response = self._s.request(method=method, url=url, data=data, verify=self._verify, timeout=timeout, **kwargs)

        # Handle session timeout
        if self._re_connect_on_session_timeout and response.status_code == 401:
            self.connect()
            response = self._s.request(
                method=method, url=url, data=data, verify=self._verify, timeout=timeout, **kwargs
            )

        return response

    def _execute_async_request(
        self, method: str, url: str, data: str, timeout: float, cancel_at_timeout: bool, return_async_id: bool, **kwargs
    ):
        """
        Execute an asynchronous request with response polling
        """
        # Add async header
        http_headers = kwargs.get("headers", dict())
        http_headers.update({"Prefer": "respond-async"})
        kwargs["headers"] = http_headers

        # Make initial request
        response = self._s.request(method=method, url=url, data=data, verify=self._verify, timeout=timeout, **kwargs)

        # Handle session timeout
        if self._re_connect_on_session_timeout and response.status_code == 401:
            self.connect()
            response = self._s.request(
                method=method, url=url, data=data, verify=self._verify, timeout=timeout, **kwargs
            )

        self.verify_response(response=response)

        # Handle async response
        if "Location" in response.headers and "'" in response.headers.get("Location", ""):
            async_id = response.headers.get("Location").split("'")[1]
            if return_async_id:
                return async_id

            # Poll for async result
            response = self._poll_async_response(async_id, timeout, cancel_at_timeout, method, url)

            # Transform response if needed
            response = self._transform_async_response(response)

        return response

    def _poll_async_response(self, async_id: str, timeout: float, cancel_at_timeout: bool, method: str, url: str):
        """
        Poll for async operation completion
        """
        for wait in RestService.wait_time_generator(timeout):
            response = self.retrieve_async_response(async_id)
            if response.status_code in [200, 201]:
                return response
            time.sleep(wait)

        # Timeout reached
        if cancel_at_timeout or (cancel_at_timeout is None and self._cancel_at_timeout):
            self.cancel_async_operation(async_id)
        raise TM1pyTimeout(method=method, url=url, timeout=timeout)

    def _transform_async_response(self, response):
        """
        Transform async response for TM1 version compatibility
        """
        # Response transformation necessary in TM1 < v11
        if response.content.startswith(b"HTTP/"):
            return self.build_response_from_binary_response(response.content)
        else:
            # In v12 status_code must be set explicitly
            if "asyncresult" in response.headers:
                async_result = response.headers["asyncresult"]
                response.status_code = int(async_result.split()[0])

        return response

    def _handle_remote_disconnect(
        self,
        original_error,
        method: str,
        url: str,
        data: str,
        timeout: float,
        idempotent: bool,
        async_requests_mode: bool,
        cancel_at_timeout: bool,
        return_async_id: bool,
        encoding: str,
        **kwargs,
    ):
        """
        Handle remote disconnect errors with reconnection and retry logic
        """
        warnings.warn(f"Connection aborted due to remote disconnect. Attempting to reconnect: {original_error}")

        try:
            # Reconnect
            self._manage_http_adapter()
            self.connect()

            # Only retry if idempotent
            if not idempotent:
                warnings.warn(
                    f"Successfully reconnected but not retrying {method.upper()} request (idempotent={idempotent})"
                )
                raise original_error

            warnings.warn(f"Successfully reconnected. Retrying {method.upper()} request...")

            # Retry the request using the same execution path
            if not async_requests_mode:
                response = self._execute_sync_request(method=method, url=url, data=data, timeout=timeout, **kwargs)
            else:
                response = self._execute_async_request(
                    method=method,
                    url=url,
                    data=data,
                    timeout=timeout,
                    cancel_at_timeout=cancel_at_timeout,
                    return_async_id=return_async_id,
                    **kwargs,
                )

            # Verify and encode response
            self.verify_response(response=response)
            response.encoding = encoding
            return response

        except TM1pyTimeout:
            # Re-raise timeout exceptions as-is
            raise
        except TM1pyRestException:
            # Re-raise TM1 exceptions as-is
            raise
        except Exception as retry_error:
            warnings.warn(f"Failed to reconnect or retry after remote disconnect: {retry_error}")
            raise original_error

    def connect(self):
        if "session_id" in self._kwargs:
            self._set_session_id_cookie()
        else:
            self._start_session(
                user=self._kwargs.get("user", None),
                password=self._kwargs.get("password", None),
                namespace=self._kwargs.get("namespace", None),
                gateway=self._kwargs.get("gateway", None),
                cam_passport=self._kwargs.get("cam_passport", None),
                decode_b64=self.translate_to_boolean(self._kwargs.get("decode_b64", False)),
                integrated_login=self.translate_to_boolean(self._kwargs.get("integrated_login", False)),
                integrated_login_domain=self._kwargs.get("integrated_login_domain"),
                integrated_login_service=self._kwargs.get("integrated_login_service"),
                integrated_login_host=self._kwargs.get("integrated_login_host"),
                integrated_login_delegate=self._kwargs.get("integrated_login_delegate"),
                impersonate=self._kwargs.get("impersonate", None),
                application_client_id=self._kwargs.get("application_client_id", None),
                application_client_secret=self._kwargs.get("application_client_secret", None),
            )

    def _set_session_id_cookie(self):
        if self._auth_mode.use_v12_auth:
            self._s.cookies.set("paSession", self._kwargs["session_id"])
        else:
            self._s.cookies.set("TM1SessionId", self._kwargs["session_id"])

    def _construct_ibm_cloud_service_and_auth_root(self):
        if not all([self._address, self._tenant, self._database]):
            raise ValueError("'address', 'tenant' and 'database' must be provided to connect to TM1 > v12 in IBM Cloud")

        if not self._ssl:
            raise ValueError("'ssl' must be True to connect to TM1 > v12 in IBM Cloud")

        base_url = f"https://{self._address}/api/{self._tenant}/v0/tm1/{self._database}"
        auth_url = f"{base_url}/Configuration/ProductVersion/$value"

        return base_url, auth_url

    def _construct_pa_proxy_service_and_auth_root(self) -> Tuple[str, str]:
        if not all([self._address, self._database]):
            raise ValueError("'address' and 'database' must be provided to connect to TM1 > v12 using PA Proxy")

        base_url = "http{}://{}/tm1/{}/api/v1".format("s" if self._ssl else "", self._address, self._database)

        auth_url = "http{}://{}/login".format("s" if self._ssl else "", self._address)

        return base_url, auth_url

    def _construct_s2s_service_and_auth_root(self) -> Tuple[str, str]:
        if not all([self._instance, self._database]):
            raise ValueError("'Instance' and 'Database' arguments are required for v12 authentication with 'address'")

        # URL Format: http{ssl}://{address}:{port}/{instance}/api/v1/Databases('{database}')
        base_url = "http{}://{}{}/{}/api/v1/Databases('{}')".format(
            "s" if self._ssl else "",
            "localhost" if len(self._address) == 0 else self._address,
            f":{self._port}" if self._port is not None else "",
            self._instance,
            self._database,
        )

        auth_url = "http{}://{}{}/{}/auth/v1/session".format(
            "s" if self._ssl else "",
            "localhost" if len(self._address) == 0 else self._address,
            f":{self._port}" if self._port is not None else "",
            self._instance,
        )

        return base_url, auth_url

    def _construct_v11_service_and_auth_root(self) -> Tuple[str, str]:
        # URL Format: http{ssl}://{address}:{port}/api/v1
        base_url = "http{}://{}{}/api/v1".format(
            "s" if self._ssl else "", "localhost" if len(self._address) == 0 else self._address, f":{self._port}"
        )
        auth_url = f"{base_url}/Configuration/ProductVersion/$value"

        return base_url, auth_url

    def _construct_all_version_service_and_auth_root_from_base_url(self) -> Tuple[str, str]:
        if self._address is not None:
            raise ValueError("Base URL and Address can not be specified at the same time")

        # v12 requires an auth URL be provided if a base URL is specified
        elif "api/v1/Databases" in self._base_url:
            if not self._auth_url:
                raise ValueError(
                    "Auth_url missing, when connecting to planning analytics engine and using the "
                    "base_url"
                    " you must specify a corresponding auth url"
                )

        elif self._base_url.endswith("/api/v1"):
            self._auth_url = f"{self._base_url}/Configuration/ProductVersion/$value"

        else:
            self._base_url += "/api/v1"
            self._auth_url = f"{self._base_url}/Configuration/ProductVersion/$value"

        return self._base_url, self._auth_url

    def _construct_service_and_auth_root(self) -> Tuple[str, str]:
        """Create the service root URL (base_url) for all versions of TM1
        If a base_url is passed then it is assumed to be the complete service root
        for accessing the API
        """
        if not self._auth_mode.use_v12_auth:
            if self._base_url is None:
                return self._construct_v11_service_and_auth_root()
            else:
                # if the base URL is provided when the REST service is created
                return self._construct_all_version_service_and_auth_root_from_base_url()

        if self._auth_mode is AuthenticationMode.IBM_CLOUD_API_KEY:
            return self._construct_ibm_cloud_service_and_auth_root()

        if self._auth_mode is AuthenticationMode.PA_PROXY:
            return self._construct_pa_proxy_service_and_auth_root()

        # If an address and database and instances are specified then we create a CP4D connection
        elif self._auth_mode is AuthenticationMode.SERVICE_TO_SERVICE:
            return self._construct_s2s_service_and_auth_root()

        if self._auth_mode in [AuthenticationMode.BASIC_API_KEY, AuthenticationMode.ACCESS_TOKEN]:
            return self._construct_all_version_service_and_auth_root_from_base_url()

    def _manage_http_adapter(self):
        adapter = HTTPAdapterWithSocketOptions(
            pool_connections=self._pool_connections,
            pool_maxsize=self._connection_pool_size,
            ssl_context=self._ssl_context,
            socket_options=[
                (socket.SOL_TCP, socket.TCP_NODELAY, 1),
                (socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1),
                (socket.SOL_SOCKET, socket.SO_REUSEADDR, 1),
            ],
        )

        self._s.mount(self._base_url, adapter)

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        try:
            self.logout()
        except Exception as e:
            warnings.warn(f"Logout Failed due to Exception: {e}")

    def GET(
        self,
        url: str,
        data: Union[str, bytes, BytesIO] = "",
        headers: Dict = None,
        async_requests_mode: bool = None,
        return_async_id: bool = False,
        timeout: float = None,
        cancel_at_timeout: bool = False,
        encoding: str = "utf-8",
        idempotent: bool = True,
        verify_response: bool = True,
        **kwargs,
    ):
        """Perform a GET request against TM1 instance
        :param url:
        :param data: the payload
        :param headers: custom headers
        :param async_requests_mode changes internal REST execution mode to avoid 60s timeout on IBM cloud
        :param return_async_id: If True function will return async_id after initiation and not await the execution
        :param timeout: Number of seconds that the client will wait to receive the first byte.
        :param cancel_at_timeout: Abort operation in TM1 when timeout is reached
        :param encoding:
        :return: response object or async_id
        """

        return self.request(
            method="get",
            headers={**self._headers, **headers} if headers else dict(self._headers),
            url=url,
            data=data,
            async_requests_mode=async_requests_mode,
            return_async_id=return_async_id,
            timeout=timeout if timeout else self._timeout,
            cancel_at_timeout=cancel_at_timeout,
            encoding=encoding,
            idempotent=idempotent,
            verify_response=verify_response,
        )

    def POST(
        self,
        url: str,
        data: Union[str, bytes, BytesIO] = "",
        headers: Dict = None,
        async_requests_mode: bool = None,
        return_async_id: bool = False,
        timeout: float = None,
        cancel_at_timeout: bool = False,
        encoding: str = "utf-8",
        idempotent: bool = False,
        verify_response: bool = True,
        **kwargs,
    ):
        """Perform a POST request against TM1 instance
        :param url:
        :param data: the payload
        :param headers: custom headers
        :param async_requests_mode changes internal REST execution mode to avoid 60s timeout on IBM cloud
        :param return_async_id: If True function will return async_id after initiation and not await the execution
        :param timeout: Number of seconds that the client will wait to receive the first byte.
        :param cancel_at_timeout: Abort operation in TM1 when timeout is reached
        :param encoding:
        :return: response object or async_id
        """

        response = self.request(
            method="post",
            headers={**self._headers, **headers} if headers else dict(self._headers),
            url=url,
            data=data,
            async_requests_mode=async_requests_mode,
            return_async_id=return_async_id,
            timeout=timeout if timeout else self._timeout,
            cancel_at_timeout=cancel_at_timeout,
            encoding=encoding,
            idempotent=idempotent,
            verify_response=verify_response,
        )

        return response

    def PATCH(
        self,
        url: str,
        data: Union[str, bytes, BytesIO] = "",
        headers: Dict = None,
        async_requests_mode: bool = None,
        return_async_id: bool = False,
        timeout: float = None,
        cancel_at_timeout: bool = False,
        encoding: str = "utf-8",
        idempotent: bool = False,
        verify_response: bool = True,
        **kwargs,
    ):
        """Perform a PATCH request against TM1 instance
        :param url:
        :param data: the payload
        :param headers: custom headers
        :param async_requests_mode changes internal REST execution mode to avoid 60s timeout on IBM cloud
        :param return_async_id: If True function will return async_id after initiation and not await the execution
        :param timeout: Number of seconds that the client will wait to receive the first byte.
        :param cancel_at_timeout: Abort operation in TM1 when timeout is reached
        :param encoding:
        :return: response object or async_id
        """

        return self.request(
            method="patch",
            headers={**self._headers, **headers} if headers else dict(self._headers),
            url=url,
            data=data,
            async_requests_mode=async_requests_mode,
            return_async_id=return_async_id,
            timeout=timeout if timeout else self._timeout,
            cancel_at_timeout=cancel_at_timeout,
            encoding=encoding,
            idempotent=idempotent,
            verify_response=verify_response,
        )

    def PUT(
        self,
        url: str,
        data: Union[str, bytes, BytesIO] = "",
        headers: Dict = None,
        async_requests_mode: bool = None,
        return_async_id: bool = False,
        timeout: float = None,
        cancel_at_timeout: bool = False,
        encoding: str = "utf-8",
        idempotent: bool = False,
        verify_response: bool = True,
        **kwargs,
    ):
        """Perform a PUT request against TM1 instance
        :param url:
        :param data: the payload
        :param headers: custom headers
        :param async_requests_mode changes internal REST execution mode to avoid 60s timeout on IBM cloud
        :param return_async_id: If True function will return async_id after initiation and not await the execution
        :param timeout: Number of seconds that the client will wait to receive the first byte.
        :param cancel_at_timeout: Abort operation in TM1 when timeout is reached
        :param encoding:
        :return: response object or async_id
        """

        return self.request(
            method="put",
            headers={**self._headers, **headers} if headers else dict(self._headers),
            url=url,
            data=data,
            async_requests_mode=async_requests_mode,
            return_async_id=return_async_id,
            timeout=timeout if timeout else self._timeout,
            cancel_at_timeout=cancel_at_timeout,
            encoding=encoding,
            idempotent=idempotent,
            verify_response=verify_response,
        )

    def DELETE(
        self,
        url: str,
        data: Union[str, bytes, BytesIO] = "",
        headers: Dict = None,
        async_requests_mode: bool = None,
        return_async_id: bool = False,
        timeout: float = None,
        cancel_at_timeout: bool = False,
        encoding: str = "utf-8",
        idempotent: bool = False,
        verify_response: bool = True,
        **kwargs,
    ):
        """Perform a DELETE request against TM1 instance
        :param url:
        :param data: the payload
        :param headers: custom headers
        :param async_requests_mode changes internal REST execution mode to avoid 60s timeout on IBM cloud
        :param return_async_id: If True function will return async_id after initiation and not await the execution
        :param timeout: Number of seconds that the client will wait to receive the first byte.
        :param cancel_at_timeout: Abort operation in TM1 when timeout is reached
        :param encoding:
        :return: response object or async_id
        """

        return self.request(
            method="delete",
            headers={**self._headers, **headers} if headers else dict(self._headers),
            url=url,
            data=data,
            async_requests_mode=async_requests_mode,
            return_async_id=return_async_id,
            timeout=timeout if timeout else self._timeout,
            cancel_at_timeout=cancel_at_timeout,
            encoding=encoding,
            idempotent=idempotent,
            verify_response=verify_response,
        )

    def logout(self, timeout: float = None, **kwargs):
        """End TM1 Session and HTTP session"""

        try:
            self.POST(
                "/ActiveSession/tm1.Close",
                "",
                headers={"Connection": "close"},
                timeout=timeout,
                async_requests_mode=False,
                **kwargs,
            )
        finally:
            self._s.close()

    @staticmethod
    def _extract_tm1_session_id_from_set_cookie_header(auth_response_headers: object) -> str:
        if auth_response_headers["set-cookie"]:
            cookie = SimpleCookie()
            # remove invalid domain from cookie
            cookie.load(auth_response_headers["set-cookie"].split(";")[0])
            tm1_session_id = cookie["TM1SessionId"].value
            return tm1_session_id
        else:
            return None

    def _start_session(
        self,
        user: str,
        password: str,
        decode_b64: bool = False,
        namespace: str = None,
        gateway: str = None,
        cam_passport: str = None,
        integrated_login: bool = None,
        integrated_login_domain: str = None,
        integrated_login_service: str = None,
        integrated_login_host: str = None,
        integrated_login_delegate: bool = None,
        impersonate: str = None,
        application_client_id: str = None,
        application_client_secret: str = None,
    ):
        """perform a simple GET request (Ask for the TM1 Version) to start a session"""
        # Authorization with integrated_login
        if self._auth_mode == AuthenticationMode.WIA:
            self._s.auth = HttpNegotiateAuth(
                domain=integrated_login_domain,
                service=integrated_login_service,
                host=integrated_login_host,
                delegate=integrated_login_delegate,
            )

        elif self._auth_mode == AuthenticationMode.SERVICE_TO_SERVICE:
            application_auth = HTTPBasicAuth(application_client_id, application_client_secret)
            self._s.auth = application_auth

        # Get the JWT token from the CPD URL
        elif self._auth_mode == AuthenticationMode.PA_PROXY:
            credentials = {"username": user, "password": password}
            jwt = self._generate_cpd_access_token(credentials)

        elif self._auth_mode == AuthenticationMode.IBM_CLOUD_API_KEY:
            access_token = self._generate_ibm_iam_cloud_access_token()
            self.add_http_header("Authorization", "Bearer " + access_token)

        elif self._auth_mode == AuthenticationMode.ACCESS_TOKEN:
            self.add_http_header("Authorization", "Bearer " + self._kwargs.get("access_token"))

        # v11 authorization (Basic, CAM) through Headers
        else:
            token = self._build_authorization_token(
                user,
                self.b64_decode_password(password) if decode_b64 else password,
                namespace,
                gateway,
                cam_passport,
                self._verify,
                self._cert,
            )
            self.add_http_header("Authorization", token)

        # process additional headers
        if impersonate:
            if self._auth_mode.use_v12_auth:
                raise TM1pyVersionDeprecationException("User Impersonation", "12")
            else:
                self.add_http_header("TM1-Impersonate", impersonate)

        try:
            # skip re_connect to avoid infinite recursion in case of invalid credentials
            original_value = self._re_connect_on_session_timeout
            try:
                self._re_connect_on_session_timeout = False
                if self._auth_mode == AuthenticationMode.SERVICE_TO_SERVICE:
                    payload = {"User": user}
                    response = self._s.post(
                        url=self._auth_url,
                        headers=self._headers,
                        verify=self._verify,
                        timeout=self._timeout,
                        json=payload,
                    )
                    self.verify_response(response)
                    if "TM1SessionId" not in self._s.cookies:
                        # if session had incorrect domain due to CP4D extract it and add it to cookie jar
                        self._s.cookies.set(
                            "TM1SessionId",
                            self._extract_tm1_session_id_from_set_cookie_header(auth_response_headers=response.headers),
                        )
                        warnings.warn(
                            "TM1SessionId has failed to be automatically added to the session cookies, future requests "
                            "using this TM1Service will use the session id extracted from the first response "
                            "Check the tm1-gateway domain settings are correct"
                            "in the container orchestrator "
                        )
                elif self._auth_mode == AuthenticationMode.PA_PROXY:
                    header = {"Content-Type": "application/x-www-form-urlencoded"}
                    payload = f"jwt={jwt}"
                    response = self._s.post(
                        url=self._auth_url, headers=header, verify=self._verify, timeout=self._timeout, data=payload
                    )
                    self.verify_response(response)
                    csrf_cookie = response.cookies.get_dict(self._address, "/")["ba-sso-csrf"]
                    self.add_http_header("ba-sso-authenticity", csrf_cookie)
                else:
                    response = self._s.get(
                        url=self._auth_url, headers=self._headers, verify=self._verify, timeout=self._timeout
                    )
                    self.verify_response(response)
                    self._version = response.text

            finally:
                self._re_connect_on_session_timeout = original_value

            if response is None:
                raise ValueError(
                    f"No response returned from URL: '{self._auth_url}'. "
                    f"Please double check your address and port number in the URL."
                )

        finally:
            # If the TM1 REST API is routed through a reverse proxy that alters the expected URL,
            # we explicitly re-set the 'TM1SessionId' cookie to maintain session continuity.
            session_id = self._s.cookies.pop("TM1SessionId", None)
            if session_id is not None:
                self._s.cookies.set("TM1SessionId", session_id)

            # After we have session cookie, drop the Authorization Header
            self.remove_http_header("Authorization")

    def _url_and_body(self, url: str, data: str, encoding: str = "utf-8") -> Tuple[str, bytes]:
        """create proper url and payload"""
        # drop leading '/api/v1' from URL for backwards compatibility
        url = self._base_url + (url[len("/api/v1") :] if url.startswith("/api/v1") else url)
        url = url.replace(" ", "%20")
        if isinstance(data, str):
            data = data.encode(encoding)
        return url, data

    def is_connected(self) -> bool:
        """Check if Connection to TM1 Server is established.
        :Returns:
            Boolean
        """
        try:
            self.GET("/Configuration/ServerName/$value")
            return True
        except Exception:
            return False

    def set_version(self):
        url = "/Configuration/ProductVersion/$value"
        response = self.GET(url=url)
        self._version = response.text

    def get_api_metadata(self) -> dict:
        """Get API Metadata

        :return: Dictionary
        """
        url = "/$metadata"
        metadata = self.GET(url=url).content.decode("utf-8")
        return json.loads(metadata)

    @property
    def version(self) -> str:
        return self._version

    @property
    def is_admin(self) -> bool:
        if self._is_admin is None:
            response = self.GET("/ActiveUser/Groups")
            self._is_admin = "ADMIN" in CaseAndSpaceInsensitiveSet(
                *[group["Name"] for group in response.json()["value"]]
            )

        return self._is_admin

    @property
    def is_data_admin(self) -> bool:
        if self._is_data_admin is None:
            response = self.GET("/ActiveUser/Groups")
            self._is_data_admin = any(
                g in CaseAndSpaceInsensitiveSet(*[group["Name"] for group in response.json()["value"]])
                for g in ["Admin", "DataAdmin"]
            )

        return self._is_data_admin

    @property
    def is_security_admin(self) -> bool:
        if self._is_security_admin is None:
            response = self.GET("/ActiveUser/Groups")
            self._is_security_admin = any(
                g in CaseAndSpaceInsensitiveSet(*[group["Name"] for group in response.json()["value"]])
                for g in ["Admin", "SecurityAdmin"]
            )

        return self._is_security_admin

    @property
    def is_ops_admin(self) -> bool:
        if self._is_ops_admin is None:
            response = self.GET("/ActiveUser/Groups")
            self._is_ops_admin = any(
                g in CaseAndSpaceInsensitiveSet(*[group["Name"] for group in response.json()["value"]])
                for g in ["Admin", "OperationsAdmin"]
            )

        return self._is_ops_admin

    @property
    def sandboxing_disabled(self):
        if verify_version(required_version="12", version=self.version):
            self._sandboxing_disabled = False

        elif self._sandboxing_disabled is None:
            response = self.GET("/ActiveConfiguration/Administration/DisableSandboxing")
            self._sandboxing_disabled = response.json().get("value", False)

        return self._sandboxing_disabled

    @property
    def session_id(self) -> str:
        try:
            return self._s.cookies["TM1SessionId"]
        # case v12
        except KeyError:
            return self._s.cookies["paSession"]

    @staticmethod
    def translate_to_boolean(value) -> bool:
        """Takes a boolean or string (eg. true, True, FALSE, etc.) value and returns (boolean) True or False
        :param value: True, 'true', 'false' or 'False' ...
        :return:
        """
        if isinstance(value, bool) or isinstance(value, int):
            return bool(value)
        elif isinstance(value, str):
            return value.replace(" ", "").lower() == "true"
        else:
            raise ValueError("Invalid argument: '" + value + "'. Must be to be of type 'bool' or 'str'")

    @staticmethod
    def b64_decode_password(encrypted_password: str) -> str:
        """b64 decoding
        :param encrypted_password: encrypted password with b64
        :return: password in plain text
        """
        return b64decode(encrypted_password).decode("UTF-8")

    @staticmethod
    def verify_response(response: Response):
        """check if Status Code is OK
        :Parameters:
            `response`: String
                the response that is returned from a method call
        :Exceptions:
            TM1pyException, raises TM1pyException when Code is not 200, 204 etc.
        """
        if not response.ok:
            raise TM1pyRestException(
                response.text, status_code=response.status_code, reason=response.reason, headers=response.headers
            )

    @staticmethod
    def _build_authorization_token(
        user: str,
        password: str,
        namespace: str = None,
        gateway: str = None,
        cam_passport: str = None,
        verify: bool = False,
        cert: Optional[Union[str, Tuple[str, str]]] = None,
    ) -> str:
        """Build the Authorization Header for CAM and Native Security"""
        if cam_passport:
            return "CAMPassport " + cam_passport
        elif namespace:
            return RestService._build_authorization_token_cam(user, password, namespace, gateway, verify, cert)
        else:
            return RestService._build_authorization_token_basic(user, password)

    @staticmethod
    def _build_authorization_token_cam(
        user: str = None,
        password: str = None,
        namespace: str = None,
        gateway: str = None,
        verify: bool = False,
        cert: Optional[Union[str, Tuple[str, str]]] = None,
    ) -> str:
        if gateway:
            try:
                HttpNegotiateAuth
            except NameError:
                raise RuntimeError(
                    "SSO failed due to missing dependency requests_negotiate_sspi.HttpNegotiateAuth. "
                    "SSO only supported for Windows"
                )
            response = requests.get(
                gateway, auth=HttpNegotiateAuth(), verify=verify, cert=cert, params={"CAMNamespace": namespace}
            )
            if not response.status_code == 200:
                raise RuntimeError(
                    "Failed to authenticate through CAM. Expected status_code 200, received status_code: "
                    + str(response.status_code)
                )
            elif "cam_passport" not in response.cookies:
                raise RuntimeError(
                    "Failed to authenticate through CAM. HTTP response does not contain 'cam_passport' cookie"
                )
            else:
                return "CAMPassport " + response.cookies["cam_passport"]
        else:
            return "CAMNamespace " + b64encode(str.encode("{}:{}:{}".format(user, password, namespace))).decode("ascii")

    @staticmethod
    def _build_authorization_token_basic(user: str, password: str) -> str:
        return "Basic " + b64encode(str.encode("{}:{}".format(user, password))).decode("ascii")

    @staticmethod
    def disable_http_warnings():
        # disable HTTP verification warnings from requests library
        requests.packages.urllib3.disable_warnings()

    def get_http_header(self, key: str) -> str:
        return self._headers[key]

    def add_http_header(self, key: str, value: str):
        self._headers[key] = value

    def remove_http_header(self, key: str):
        if key in self._headers:
            self._headers.pop(key)

    def add_compact_json_header(self) -> str:
        original_header = self.get_http_header("Accept")
        parts = original_header.split(";")

        # Point of insertion is important. Needs to come after application/json
        parts.insert(1, "tm1.compact=v0")
        modified_header = ";".join(parts)
        self.add_http_header("Accept", modified_header)

        return original_header

    def retrieve_async_response(self, async_id: str, **kwargs) -> Response:
        url = f"/_async('{async_id}')"
        # Use GET method which includes reconnect logic, but force sync mode
        return self.GET(url, async_requests_mode=False, **kwargs)

    def cancel_async_operation(self, async_id: str, **kwargs):
        url = f"/_async('{async_id}')"
        # Use DELETE method which includes reconnect logic, but force sync mode
        response = self.DELETE(url, async_requests_mode=False, **kwargs)
        self.verify_response(response)

    def cancel_running_operation(self):
        monitoring_service = self.get_monitoring_service()
        threads = monitoring_service.get_active_session_threads(exclude_idle=True)

        # if more than one thread is running in session, operation can not be identified unambiguously
        if not len(threads) == 1:
            return

        monitoring_service.cancel_thread(threads[0]["ID"])

    def get_monitoring_service(self):
        from TM1py.Services import MonitoringService

        return MonitoringService(self)

    @staticmethod
    def urllib3_response_from_bytes(data: bytes) -> HTTPResponse:
        """Build urllib3.HTTPResponse based on raw bytes string"""
        sock = BytesIOSocket(data)

        response = HTTPResponse(sock)
        response.begin()

        headers = response.msg
        if not isinstance(headers, HTTPHeaderDict):
            headers = HTTPHeaderDict(headers.items())

        urllib3_http_response = urllib3.HTTPResponse(
            body=response,
            headers=headers,
            status=response.status,
            version=response.version,
            reason=response.reason,
            original_response=response,
        )
        return urllib3_http_response

    @staticmethod
    def build_response_from_binary_response(data: bytes) -> Response:
        urllib_response = RestService.urllib3_response_from_bytes(data)

        adapter = HTTPAdapter()
        requests_response = adapter.build_response(requests.PreparedRequest(), urllib_response)
        # actual content of response needs to be set explicitly
        requests_response._content = urllib_response.data

        return requests_response

    @staticmethod
    def wait_time_generator(timeout: int):
        yield 0.1
        yield 0.3
        yield 0.6
        if timeout:
            for _ in range(1, int(timeout)):
                yield 1
        else:
            while True:
                yield 1

    def _determine_ssl_based_on_base_url(self) -> bool:
        if self._base_url.startswith("https"):
            return True
        elif self._base_url.startswith("http"):
            return False
        else:
            raise ValueError(f"Invalid base_url: '{self._base_url}'")

    def _determine_auth_mode(self) -> AuthenticationMode:
        if not any(
            [self._auth_url, self._instance, self._database, self._api_key, self._iam_url, self._pa_url, self._tenant]
        ):
            if not any(
                [
                    self._kwargs.get("namespace", None),
                    self._kwargs.get("gateway", None),
                    self._kwargs.get("integrated_login", None),
                ]
            ):
                if self._kwargs.get("user", None) == "apikey" and "planninganalytics.saas.ibm.com" in self._base_url:
                    return AuthenticationMode.BASIC_API_KEY
                elif self._kwargs.get("access_token"):
                    return AuthenticationMode.ACCESS_TOKEN
                return AuthenticationMode.BASIC

            if self._kwargs.get("gateway", None):
                return AuthenticationMode.CAM_SSO

            if self._kwargs.get("integrated_login", False):
                return AuthenticationMode.WIA

            return AuthenticationMode.CAM

        # v12
        if self._iam_url:
            return AuthenticationMode.IBM_CLOUD_API_KEY

        if self._address and self._user and not self._instance:
            return AuthenticationMode.PA_PROXY

        return AuthenticationMode.SERVICE_TO_SERVICE

    def _generate_cpd_access_token(self, credentials) -> str:
        if not all([self._cpd_url]):
            raise ValueError("cpd_url must be provided to authenticate via PA Proxy")
        url = f"{self._cpd_url}/v1/preauth/signin"
        headers = {"Content-Type": "application/json;charset=UTF-8"}
        response = requests.request("POST", url, headers=headers, json=credentials, verify=self._verify)
        jwt = literal_eval(response.content.decode("utf8"))
        return jwt["token"]

    def _generate_ibm_iam_cloud_access_token(self) -> str:
        if not all([self._iam_url, self._api_key]):
            raise ValueError("'iam_url' and 'api_key' must be provided to generate access token from IBM Cloud")

        payload = f"grant_type=urn%3Aibm%3Aparams%3Aoauth%3Agrant-type%3Aapikey&apikey={self._api_key}"
        headers = {"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"}
        response = requests.request("POST", self._iam_url, headers=headers, data=payload)
        if "access_token" not in response.json():
            raise RuntimeError(f"Failed to generate access_token from URL: '{self._iam_url}'")
        return response.json()["access_token"]


class BytesIOSocket:
    """used in urllib3_response_from_bytes method to construct urllib3 response from raw bytes"""

    def __init__(self, content: bytes):
        self.handle = BytesIO(content)

    def makefile(self, mode) -> BytesIO:
        return self.handle
