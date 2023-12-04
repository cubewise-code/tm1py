# -*- coding: utf-8 -*-
import functools
import json
import re
import socket
import time
import warnings
from base64 import b64encode, b64decode
from enum import Enum
from http.client import HTTPResponse
from http.cookies import SimpleCookie
from io import BytesIO
from json import JSONDecodeError
from typing import Union, Dict, Tuple, Optional

import requests
import urllib3
from requests import Timeout, Response, ConnectionError, Session
from requests.adapters import HTTPAdapter
from requests.auth import HTTPBasicAuth
from urllib3._collections import HTTPHeaderDict

# SSO not supported for Linux
from TM1py.Exceptions.Exceptions import TM1pyTimeout, TM1pyVersionDeprecationException
from TM1py.Utils import case_and_space_insensitive_equals, CaseAndSpaceInsensitiveSet, HTTPAdapterWithSocketOptions, \
    decohints

try:
    from requests_negotiate_sspi import HttpNegotiateAuth
except ImportError:
    warnings.warn("requests_negotiate_sspi failed to import. SSO will not work", ImportWarning)

from TM1py.Exceptions import TM1pyRestException, TM1pyException

import http.client as http_client


@decohints
def httpmethod(func):
    """ Higher Order Function to wrap the GET, POST, PATCH, PUT, DELETE methods
        Takes care of:
        - encoding of url and payload
        - verifying response. Throws TM1pyException if StatusCode of Response is not OK
    """

    @functools.wraps(func)
    def wrapper(self, url: str, data: str = '', encoding='utf-8', async_requests_mode: Optional[bool] = None, **kwargs):
        # url encoding
        url, data = self._url_and_body(
            url=url,
            data=data,
            encoding=encoding)

        # execute request
        try:
            # determine async_requests_mode
            if async_requests_mode is None:
                async_requests_mode = self._async_requests_mode

            if not async_requests_mode:
                response = func(self, url, data, **kwargs)
                if self._re_connect_on_session_timeout and response.status_code == 401:
                    self.connect()
                    response = func(self, url, data, **kwargs)

            else:
                additional_header = {'Prefer': 'respond-async'}
                http_headers = kwargs.get('headers', dict())
                http_headers.update(additional_header)
                kwargs['headers'] = http_headers
                response = func(self, url, data, **kwargs)
                # reconnect in case of session timeout
                if self._re_connect_on_session_timeout and response.status_code == 401:
                    self.connect()
                    response = func(self, url, data, **kwargs)
                self.verify_response(response=response)

                if 'Location' not in response.headers or "'" not in response.headers['Location']:
                    raise ValueError(f"Failed to retrieve async_id from request {func.__name__} '{url}'")
                async_id = response.headers.get('Location').split("'")[1]

                for wait in RestService.wait_time_generator(kwargs.get('timeout', self._timeout)):
                    response = self.retrieve_async_response(async_id)
                    if response.status_code in [200, 201]:
                        break
                    time.sleep(wait)

                # all wait times consumed and still no 200
                if response.status_code not in [200, 201]:
                    if kwargs.get("cancel_at_timeout", self._cancel_at_timeout):
                        self.cancel_async_operation(async_id)
                    raise TM1pyTimeout(method=func.__name__, url=url, timeout=kwargs['timeout'])

                # response transformation necessary in TM1 < v11. Not required for v12
                if response.content.startswith(b"HTTP/"):
                    response = self.build_response_from_binary_response(response.content)

            # verify
            self.verify_response(response=response)

            # response encoding
            response.encoding = encoding
            return response

        except Timeout:
            if kwargs.get("cancel_at_timeout", self._cancel_at_timeout):
                self.cancel_running_operation()
            raise TM1pyTimeout(method=func.__name__, url=url, timeout=kwargs.get('timeout', self._timeout))

        except ConnectionError as e:
            # cater for issue in requests library: https://github.com/psf/requests/issues/5430
            if re.search('Read timed out', str(e), re.IGNORECASE):
                if kwargs.get("cancel_at_timeout", False):
                    self.cancel_running_operation()
                raise TM1pyTimeout(method=func.__name__, url=url, timeout=kwargs.get('timeout', self._timeout))

    return wrapper


class AuthenticationMode(Enum):
    BASIC = 1
    WIA = 2
    CAM = 3
    CAM_SSO = 4
    IBM_CLOUD_API_KEY = 5
    CP4D = 6

    @property
    def use_v12_auth(self):
        if self.value < 5:
            return False
        return True


class RestService:
    """ Low level communication with TM1 instance through HTTP.
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
        'Connection': 'keep-alive',
        'User-Agent': 'TM1py',
        'Content-Type': 'application/json; odata.streaming=true; charset=utf-8',
        'Accept': 'application/json;odata.metadata=none,text/plain',
        'TM1-SessionContext': 'TM1py'
    }

    # You can reset the following TCP socket options based on your own use cases when tcp_keepalive is eanbled
    # TCP_KEEPIDLE: Time in seconds until the first keepalive is sent
    # TCP_KEEPINTVL: How often should the keepalive packet be sent
    # TCP_KEEPCNT: The max number of keepalive packets to send
    TCP_SOCKET_OPTIONS = {
        'TCP_KEEPIDLE': 30,
        'TCP_KEEPINTVL': 15,
        'TCP_KEEPCNT': 60
    }

    def __init__(self, **kwargs):
        """ Create an instance of RESTService
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
        :param tenant: String - planing analytics engine (v12) Tenant e.g., YC4B2M1AG2Y6
        :param session_context: String - Name of the Application. Controls "Context" column in Arc / TM1top.
                If None, use default: TM1py
        :param verify: path to .cer file or 'True' / True / 'False' / False (if no ssl verification is required)
        :param logging: boolean - switch on/off verbose http logging into sys.stdout
        :param timeout: Float - Number of seconds that the client will wait to receive the first byte.
        :param cancel_at_timeout: Abort operation in TM1 when timeout is reached
        :param async_requests_mode: changes internal REST execution mode to avoid 60s timeout on IBM cloud
        :param tcp_keepalive: maintain the TCP connection all the time, users should choose either async_requests_mode or tcp_keepalive to run a long-run request
                If both are True, use async_requests_mode by default
        :param connection_pool_size - In a multi threaded environment, you should set this value to a
                higher number, such as the number of threads
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
        :param proxies: pass a dictionary with proxies e.g.
                {'http': 'http://proxy.example.com:8080', 'https': 'http://secureproxy.example.com:8090'}
        """
        # store kwargs for future use e.g. re_connect on 401 session timeout
        self._kwargs = kwargs

        # core arguments for connection
        self._ssl = self.translate_to_boolean(kwargs.get('ssl', True))
        self._address = kwargs.get('address', None)
        self._port = kwargs.get('port', None)
        self._base_url = kwargs.get('base_url', None)
        self._auth_url = kwargs.get('auth_url', None)
        self._instance = kwargs.get('instance', None)
        self._database = kwargs.get('database', None)
        self._api_key = kwargs.get('api_key', None)
        self._iam_url = kwargs.get('iam_url', None)
        self._pa_url = kwargs.get('pa_url', None)
        self._tenant = kwargs.get('tenant', None)

        # other arguments
        self._auth_mode = self._determine_auth_mode()
        self._timeout = None if kwargs.get('timeout', None) is None else float(kwargs.get('timeout'))
        self._cancel_at_timeout = kwargs.get('cancel_at_timeout', False)
        self._async_requests_mode = self.translate_to_boolean(kwargs.get('async_requests_mode', False))
        # Set tcp_keepalive to False explicitly to turn it off when async_requests_mode is enabled
        self._tcp_keepalive = self._determine_tcp_keepalive(kwargs.get('tcp_keepalive', False))
        self._connection_pool_size = kwargs.get('connection_pool_size', None)
        self._re_connect_on_session_timeout = kwargs.get('re_connect_on_session_timeout', True)
        # is retrieved on demand and then cached
        self._sandboxing_disabled = None
        # optional verbose logging to stdout
        self.handle_logging(kwargs.get('logging', False))

        self._proxies = self._handle_proxies(kwargs.get('proxies', None))

        # populated later on the fly for users with the name different from 'Admin'
        self._is_admin = self._determine_is_admin(kwargs.get('user', None))

        self._verify = self._determine_verify(kwargs.get('verify', None))

        self._base_url, self._auth_url = self._construct_service_and_auth_root()

        self._version = None
        self._headers = self.HEADERS.copy()
        if "session_context" in kwargs:
            self._headers["TM1-SessionContext"] = kwargs["session_context"]

        self.disable_http_warnings()

        self._s = Session()
        if self._proxies:
            self._s.proxies = self._proxies

        # First contact with TM1
        self.connect()
        if not self._version:
            self.set_version()

        if self._tcp_keepalive or self._connection_pool_size is not None:
            self._manage_http_adapter()

    def _determine_is_admin(self, user: [None, str]) -> [None, bool]:
        if user is None:
            return None

        return True if case_and_space_insensitive_equals(user, 'ADMIN') else None

    def _determine_tcp_keepalive(self, tcp_keepalive: bool):
        return self.translate_to_boolean(tcp_keepalive) if self._async_requests_mode is not True else False

    def _determine_verify(self, verify: [bool, str] = None) -> [bool, str]:
        if verify is None:
            # Default SSL verification in v12 is True
            if self._auth_mode in [AuthenticationMode.IBM_CLOUD_API_KEY, AuthenticationMode.CP4D]:
                return True
            else:
                return False

        if isinstance(verify, str):
            if verify.upper() == 'FALSE':
                return False
            elif verify.upper() == 'TRUE':
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

    def connect(self):
        if "session_id" in self._kwargs:
            self._s.cookies.set("TM1SessionId", self._kwargs["session_id"])
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
                application_client_secret=self._kwargs.get("application_client_secret", None))

    def _construct_ibm_cloud_service_and_auth_root(self):
        if not all([self._address, self._tenant, self._database]):
            raise ValueError("'address', 'tenant' and 'database' must be provided to connect to TM1 > v12 in IBM Cloud")

        if not self._ssl:
            raise ValueError("'ssl' must be True to connect to TM1 > v12 in IBM Cloud")

        base_url = f"https://{self._address}/api/{self._tenant}/v0/tm1/{self._database}"
        auth_url = f"{base_url}/Configuration/ProductVersion/$value"

        return base_url, auth_url

    def _construct_cp4d_service_and_auth_root(self) -> Tuple[str, str]:
        if not all([self._instance, self._database]):
            raise ValueError("'Instance' and 'Database' arguments are required for v12 authentication with 'address'")

        # URL Format: http{ssl}://{address}:{port}/{instance}/api/v1/Databases('{database}')
        base_url = "http{}://{}{}/{}/api/v1/Databases('{}')".format(
            's' if self._ssl else '',
            'localhost' if len(self._address) == 0 else self._address,
            f':{self._port}' if self._port is not None else '',
            self._instance,
            self._database)

        auth_url = 'http{}://{}{}/{}/auth/v1/session'.format(
            's' if self._ssl else '',
            'localhost' if len(self._address) == 0 else self._address,
            f':{self._port}' if self._port is not None else '',
            self._instance)

        return base_url, auth_url

    def _construct_v11_service_and_auth_root(self) -> Tuple[str, str]:
        # URL Format: http{ssl}://{address}:{port}/api/v1
        base_url = "http{}://{}{}/api/v1".format(
            's' if self._ssl else '',
            'localhost' if len(self._address) == 0 else self._address,
            f':{self._port}')
        auth_url = f"{base_url}/Configuration/ProductVersion/$value"

        return base_url, auth_url

    def _construct_all_version_service_and_auth_root_from_base_url(self):
        if self._address is not None:
            raise ValueError('Base URL and Address can not be specified at the same time')

        # v12 requires an auth URL be provided if a base URL is specified
        elif "api/v1/Databases" in self._base_url:
            if not self._auth_url:
                raise ValueError("Auth_url missing, when connecting to planning analytics engine and using the "
                                 "base_url"
                                 " you must specify a corresponding auth url")

        elif self._base_url.endswith("/api/v1"):
            self._auth_url = f"{self._base_url}/Configuration/ProductVersion/$value"

        else:
            self._base_url += "/api/v1"
            self._auth_url = f"{self._base_url}/Configuration/ProductVersion/$value"

    def _construct_service_and_auth_root(self) -> Tuple[str, str]:
        """  Create the service root URL (base_url) for all versions of TM1
        If a base_url is passed then it is assumed to be the complete service root
        for accessing the API
        """
        if not self._auth_mode.use_v12_auth:
            if self._base_url is None:
                return self._construct_v11_service_and_auth_root()
            else:
                # if the base URL is provided when the REST service is created
                return self._construct_all_version_service_and_auth_root_from_base_url()

        if self._auth_mode.IBM_CLOUD_API_KEY:
            return self._construct_ibm_cloud_service_and_auth_root()

        # If an address and database and instances are specified then we create a CP4D connection
        elif self._auth_mode.CP4D:
            return self._construct_cp4d_service_and_auth_root()

    def _manage_http_adapter(self):
        if self._tcp_keepalive:
            # SO_KEEPALIVE: set 1 to enable TCP keepalive
            socket_options = urllib3.connection.HTTPConnection.default_socket_options + [
                (socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1),
                (socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, self.TCP_SOCKET_OPTIONS['TCP_KEEPIDLE']),
                (socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, self.TCP_SOCKET_OPTIONS['TCP_KEEPINTVL']),
                (socket.IPPROTO_TCP, socket.TCP_KEEPCNT, self.TCP_SOCKET_OPTIONS['TCP_KEEPCNT'])]

            if self._connection_pool_size is not None:
                adapter = HTTPAdapterWithSocketOptions(
                    pool_connections=int(self._connection_pool_size),
                    pool_maxsize=int(self._connection_pool_size),
                    socket_options=socket_options)
            else:
                adapter = HTTPAdapterWithSocketOptions(socket_options=socket_options)

        else:
            adapter = HTTPAdapterWithSocketOptions(
                pool_connections=int(self._connection_pool_size),
                pool_maxsize=int(self._connection_pool_size))

        self._s.mount(self._base_url, adapter)

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.logout()

    @httpmethod
    def GET(self, url: str, data: Union[str, bytes] = '', headers: Dict = None, timeout: float = None, **kwargs):
        """ Perform a GET request against TM1 instance
        :param url:
        :param data: the payload
        :param headers: custom headers
        :param timeout: Number of seconds that the client will wait to receive the first byte.
        :return: response object
        """
        return self._s.get(
            url=url,
            headers={**self._headers, **headers} if headers else self._headers,
            data=data,
            verify=self._verify,
            timeout=timeout if timeout else self._timeout)

    @httpmethod
    def POST(self, url: str, data: Union[str, bytes], headers: Dict = None, timeout: float = None, **kwargs):
        """ POST request against the TM1 instance
        :param url:
        :param data: the payload
        :param headers: custom headers
        :param timeout: Number of seconds that the client will wait to receive the first byte.
        :return: response object
        """
        return self._s.post(
            url=url,
            headers={**self._headers, **headers} if headers else self._headers,
            data=data,
            verify=self._verify,
            timeout=timeout if timeout else self._timeout)

    @httpmethod
    def PATCH(self, url: str, data: Union[str, bytes], headers: Dict = None, timeout: float = None, **kwargs):
        """ PATCH request against the TM1 instance
        :param url: String, for instance : /Dimensions('plan_business_unit')
        :param data: the payload
        :param headers: custom headers
        :param timeout: Number of seconds that the client will wait to receive the first byte.
        :return: response object
        """
        return self._s.patch(
            url=url,
            headers={**self._headers, **headers} if headers else self._headers,
            data=data,
            verify=self._verify,
            timeout=timeout if timeout else self._timeout)

    @httpmethod
    def PUT(self, url: str, data: Union[str, bytes], headers: Dict = None, timeout: float = None, **kwargs):
        """ PUT request against the TM1 instance
        :param url: String, for instance : /Dimensions('plan_business_unit')
        :param data: the payload
        :param headers: custom headers
        :param timeout: Number of seconds that the client will wait to receive the first byte.
        :return: response object
        """
        return self._s.put(
            url=url,
            headers={**self._headers, **headers} if headers else self._headers,
            data=data,
            verify=self._verify,
            timeout=timeout if timeout else self._timeout)

    @httpmethod
    def DELETE(self, url: str, data: Union[str, bytes], headers: Dict = None, timeout: float = None, **kwargs):
        """ Delete request against TM1 instance
        :param url:  String, for instance : /Dimensions('plan_business_unit')
        :param data: the payload
        :param headers: custom headers
        :param timeout: Number of seconds that the client will wait to receive the first byte.
        :return: response object
        """
        return self._s.delete(
            url=url,
            headers={**self._headers, **headers} if headers else self._headers,
            data=data,
            verify=self._verify,
            timeout=timeout if timeout else self._timeout)

    def logout(self, timeout: float = None, **kwargs):
        """ End TM1 Session and HTTP session
        """
        # Easier to ask for forgiveness than permission
        try:
            # ProductVersion >= TM1 10.2.2 FP 6
            self.POST('/ActiveSession/tm1.Close', '', headers={"Connection": "close"}, timeout=timeout,
                      async_requests_mode=False, **kwargs)
        except TM1pyRestException:
            # ProductVersion < TM1 10.2.2 FP 6
            self.POST('/api/logout', '', headers={"Connection": "close"}, timeout=timeout, **kwargs)
        finally:
            self._s.close()

    @staticmethod
    def _extract_tm1_session_id_from_set_cookie_header(auth_response_headers: object) -> str:
        if auth_response_headers["set-cookie"]:
            cookie = SimpleCookie()
            # remove invalid domain from cookie
            cookie.load(auth_response_headers["set-cookie"].split(";")[0])
            tm1_session_id = cookie['TM1SessionId'].value
            return tm1_session_id
        else:
            return None

    def _start_session(self, user: str, password: str, decode_b64: bool = False, namespace: str = None,
                       gateway: str = None, cam_passport: str = None, integrated_login: bool = None,
                       integrated_login_domain: str = None, integrated_login_service: str = None,
                       integrated_login_host: str = None, integrated_login_delegate: bool = None,
                       impersonate: str = None,
                       application_client_id: str = None, application_client_secret: str = None):
        """ perform a simple GET request (Ask for the TM1 Version) to start a session
        """
        # Authorization with integrated_login
        if self._auth_mode == AuthenticationMode.WIA:
            self._s.auth = HttpNegotiateAuth(
                domain=integrated_login_domain,
                service=integrated_login_service,
                host=integrated_login_host,
                delegate=integrated_login_delegate)

        elif self._auth_mode == AuthenticationMode.CP4D:
            application_auth = HTTPBasicAuth(application_client_id, application_client_secret)
            self._s.auth = application_auth

        elif self._auth_mode == AuthenticationMode.IBM_CLOUD_API_KEY:
            access_token = self._generate_ibm_iam_cloud_access_token()
            self.add_http_header('Authorization', "Bearer " + access_token)

        # v11 authorization (Basic, CAM) through Headers
        else:
            token = self._build_authorization_token(
                user,
                self.b64_decode_password(password) if decode_b64 else password,
                namespace,
                gateway,
                cam_passport,
                self._verify)
            self.add_http_header('Authorization', token)

        # process additional headers
        if impersonate:
            if self._auth_mode.use_v12_auth:
                raise TM1pyVersionDeprecationException('User Impersonation', '12')
            else:
                self.add_http_header('TM1-Impersonate', impersonate)

        try:
            # skip re_connect to avoid infinite recursion in case of invalid credentials
            original_value = self._re_connect_on_session_timeout
            try:
                self._re_connect_on_session_timeout = False
                if self._auth_mode == AuthenticationMode.CP4D:
                    payload = {"User": user}
                    response = self._s.post(
                        url=self._auth_url,
                        headers=self._headers,
                        verify=self._verify,
                        timeout=self._timeout,
                        json=payload)
                    self.verify_response(response)
                    if 'TM1SessionId' not in self._s.cookies:
                        raise TM1pyException(
                            f"TM1SessionId has failed to be automatically added to the session cookies, future requests "
                            "using this TM1Service instance will fail due to authentication. "
                            "Check the tm1-gateway domain settings are correct "
                            "in the container orchestrator ")

                        # ToDo: fix unreachable code
                        # if session had incorrect domain due to CP4D extract it and add it to cookie jar
                        self._s.cookies.set(
                            "TM1SessionId",
                            self._extract_tm1_session_id_from_set_cookie_header(auth_response_headers=response.headers))

                else:
                    response = self._s.get(
                        url=self._auth_url,
                        headers=self._headers,
                        verify=self._verify,
                        timeout=self._timeout)
                    self.verify_response(response)
                    self._version = response.text

            finally:
                self._re_connect_on_session_timeout = original_value

            if response is None:
                raise ValueError(f"No response returned from URL: '{self._auth_url}'. "
                                 f"Please double check your address and port number in the URL.")


        finally:
            # After we have session cookie, drop the Authorization Header
            self.remove_http_header('Authorization')

    def _url_and_body(self, url: str, data: str, encoding: str = 'utf-8') -> Tuple[str, bytes]:
        """ create proper url and payload
        """
        url = self._base_url + url
        url = url.replace(' ', '%20')
        if isinstance(data, str):
            data = data.encode(encoding)
        return url, data

    def is_connected(self) -> bool:
        """ Check if Connection to TM1 Server is established.
        :Returns:
            Boolean
        """
        try:
            self.GET('/Configuration/ServerName/$value')
            return True
        except:
            return False

    def set_version(self):
        url = '/Configuration/ProductVersion/$value'
        response = self.GET(url=url)
        self._version = response.text

    @property
    def version(self) -> str:
        return self._version

    @property
    def is_admin(self) -> bool:
        if self._is_admin is None:
            response = self.GET("/ActiveUser/Groups")
            self._is_admin = "ADMIN" in CaseAndSpaceInsensitiveSet(
                *[group["Name"] for group in response.json()["value"]])

        return self._is_admin

    @property
    def sandboxing_disabled(self):
        if self._sandboxing_disabled is None:
            value = self.GET("/ActiveConfiguration/Administration/DisableSandboxing/$value")
            self._sandboxing_disabled = value

        return self._sandboxing_disabled

    @property
    def session_id(self) -> str:
        try:
            return self._s.cookies['TM1SessionId']
        # case v12
        except KeyError:
            return self._s.cookies['paSession']

    @staticmethod
    def translate_to_boolean(value) -> bool:
        """ Takes a boolean or string (eg. true, True, FALSE, etc.) value and returns (boolean) True or False
        :param value: True, 'true', 'false' or 'False' ...
        :return:
        """
        if isinstance(value, bool) or isinstance(value, int):
            return bool(value)
        elif isinstance(value, str):
            return value.replace(" ", "").lower() == 'true'
        else:
            raise ValueError("Invalid argument: '" + value + "'. Must be to be of type 'bool' or 'str'")

    @staticmethod
    def b64_decode_password(encrypted_password: str) -> str:
        """ b64 decoding
        :param encrypted_password: encrypted password with b64
        :return: password in plain text
        """
        return b64decode(encrypted_password).decode("UTF-8")

    @staticmethod
    def verify_response(response: Response):
        """ check if Status Code is OK
        :Parameters:
            `response`: String
                the response that is returned from a method call
        :Exceptions:
            TM1pyException, raises TM1pyException when Code is not 200, 204 etc.
        """
        if not response.ok:
            raise TM1pyRestException(response.text,
                                     status_code=response.status_code,
                                     reason=response.reason,
                                     headers=response.headers)

    @staticmethod
    def _build_authorization_token(user: str, password: str, namespace: str = None, gateway: str = None,
                                   cam_passport: str = None, verify: bool = False) -> str:
        """ Build the Authorization Header for CAM and Native Security
        """
        if cam_passport:
            return 'CAMPassport ' + cam_passport
        elif namespace:
            return RestService._build_authorization_token_cam(user, password, namespace, gateway, verify)
        else:
            return RestService._build_authorization_token_basic(user, password)

    @staticmethod
    def _build_authorization_token_cam(user: str = None, password: str = None, namespace: str = None,
                                       gateway: str = None, verify: bool = False) -> str:
        if gateway:
            try:
                HttpNegotiateAuth
            except NameError:
                raise RuntimeError(
                    "SSO failed due to missing dependency requests_negotiate_sspi.HttpNegotiateAuth. "
                    "SSO only supported for Windows")
            response = requests.get(gateway, auth=HttpNegotiateAuth(), verify=verify,
                                    params={"CAMNamespace": namespace})
            if not response.status_code == 200:
                raise RuntimeError(
                    "Failed to authenticate through CAM. Expected status_code 200, received status_code: "
                    + str(response.status_code))
            elif 'cam_passport' not in response.cookies:
                raise RuntimeError(
                    "Failed to authenticate through CAM. HTTP response does not contain 'cam_passport' cookie")
            else:
                return 'CAMPassport ' + response.cookies['cam_passport']
        else:
            return 'CAMNamespace ' + b64encode(str.encode("{}:{}:{}".format(user, password, namespace))).decode("ascii")

    @staticmethod
    def _build_authorization_token_basic(user: str, password: str) -> str:
        return 'Basic ' + b64encode(str.encode("{}:{}".format(user, password))).decode("ascii")

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
        original_header = self.get_http_header('Accept')
        parts = original_header.split(';')

        # Point of insertion is important. Needs to come after application/json
        parts.insert(1, 'tm1.compact=v0')
        modified_header = ";".join(parts)
        self.add_http_header('Accept', modified_header)

        return original_header

    def retrieve_async_response(self, async_id: str, **kwargs) -> Response:
        url = self._base_url + f"/_async('{async_id}')"
        return self._s.get(url, **kwargs)

    def cancel_async_operation(self, async_id: str, **kwargs):
        url = self._base_url + f"/_async('{async_id}')"
        response = self._s.delete(url, **kwargs)
        self.verify_response(response)

    def cancel_running_operation(self):
        monitoring_service = self.get_monitoring_service()
        threads = monitoring_service.get_active_session_threads(exclude_idle=True)

        # if more than one thread is running in session, operation can not be identified unambiguously
        if not len(threads) == 1:
            return

        monitoring_service.cancel_thread(threads[0]['ID'])

    def get_monitoring_service(self):
        from TM1py.Services import MonitoringService
        return MonitoringService(self)

    @staticmethod
    def urllib3_response_from_bytes(data: bytes) -> HTTPResponse:
        """ Build urllib3.HTTPResponse based on raw bytes string

        """
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
            original_response=response
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
        if not any([
            self._auth_url,
            self._instance,
            self._database,
            self._api_key,
            self._iam_url,
            self._pa_url,
            self._tenant
        ]):
            # v11
            if not any([self._kwargs.get('namespace', None), self._kwargs.get('gateway', None)]):
                return AuthenticationMode.BASIC

            if self._kwargs.get('gateway', None):
                return AuthenticationMode.CAM_SSO

            if self._kwargs.get("integrated_login", False):
                return AuthenticationMode.WIA

            return AuthenticationMode.CAM

        # v12
        if self._iam_url:
            return AuthenticationMode.IBM_CLOUD_API_KEY

        return AuthenticationMode.CP4D

    def _generate_ibm_iam_cloud_access_token(self) -> str:
        if not all([self._iam_url, self._api_key]):
            raise ValueError("'iam_url' and 'api_key' must be provided to generate access token from IBM Cloud")

        payload = f'grant_type=urn%3Aibm%3Aparams%3Aoauth%3Agrant-type%3Aapikey&apikey={self._api_key}'
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        response = requests.request("POST", self._iam_url, headers=headers, data=payload)
        if 'access_token' not in response.json():
            raise RuntimeError(f"Failed to generate access_token from URL: '{self._iam_url}'")
        return response.json()["access_token"]


class BytesIOSocket:
    """ used in urllib3_response_from_bytes method to construct urllib3 response from raw bytes

    """

    def __init__(self, content: bytes):
        self.handle = BytesIO(content)

    def makefile(self, mode) -> BytesIO:
        return self.handle
