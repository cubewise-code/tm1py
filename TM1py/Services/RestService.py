# -*- coding: utf-8 -*-
import functools
import re
import time
import warnings
from base64 import b64encode, b64decode
from http.client import HTTPResponse
from io import BytesIO
from typing import Union, Dict, Tuple, Optional

import requests
import urllib3
from requests import Timeout, Response, ConnectionError
from requests.adapters import HTTPAdapter

# SSO not supported for Linux
from TM1py.Exceptions.Exceptions import TM1pyTimeout
from TM1py.Utils import case_and_space_insensitive_equals, CaseAndSpaceInsensitiveSet

try:
    from requests_negotiate_sspi import HttpNegotiateAuth
except ImportError:
    warnings.warn("requests_negotiate_sspi failed to import. SSO will not work", ImportWarning)

from TM1py.Exceptions import TM1pyRestException

import http.client as http_client


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

            else:
                additional_header = {'Prefer': 'respond-async'}
                http_headers = kwargs.get('headers', dict())
                http_headers.update(additional_header)
                kwargs['headers'] = http_headers
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
                    if kwargs.get("cancel_at_timeout", False):
                        self.cancel_async_operation(async_id)
                    raise TM1pyTimeout(method=func.__name__, url=url, timeout=kwargs['timeout'])

                response = self.build_response_from_raw_bytes(response.content)

            # verify
            self.verify_response(response=response)

            # response encoding
            response.encoding = encoding
            return response

        except Timeout:
            if kwargs.get("cancel_at_timeout", False):
                self.cancel_running_operation()
            raise TM1pyTimeout(method=func.__name__, url=url, timeout=kwargs['timeout'])

        except ConnectionError as e:
            # cater for issue in requests library: https://github.com/psf/requests/issues/5430
            if re.search('Read timed out', str(e), re.IGNORECASE):
                if kwargs.get("cancel_at_timeout", False):
                    self.cancel_running_operation()
                raise TM1pyTimeout(method=func.__name__, url=url, timeout=kwargs['timeout'])

    return wrapper


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

    HEADERS = {'Connection': 'keep-alive',
               'User-Agent': 'TM1py',
               'Content-Type': 'application/json; odata.streaming=true; charset=utf-8',
               'Accept': 'application/json;odata.metadata=none,text/plain',
               'TM1-SessionContext': 'TM1py'}

    def __init__(self, **kwargs):
        """ Create an instance of RESTService
        :param address: String - address of the TM1 instance
        :param port: Int - HTTPPortNumber as specified in the tm1s.cfg
        :param base_url - base url e.g. https://localhost:12354/api/v1
        :param user: String - name of the user
        :param password String - password of the user
        :param decode_b64 - whether password argument is b64 encoded
        :param namespace String - optional CAM namespace
        :param ssl: boolean -  as specified in the tm1s.cfg
        :param cam_passport: String - the cam passport
        :param session_id: String - TM1SessionId e.g. q7O6e1w49AixeuLVxJ1GZg
        :param session_context: String - Name of the Application. Controls "Context" column in Arc / TM1top.
        If None, use default: TM1py
        :param verify: path to .cer file or 'True' / True / 'False' / False (if no ssl verification is required)
        :param logging: boolean - switch on/off verbose http logging into sys.stdout
        :param timeout: Float - Number of seconds that the client will wait to receive the first byte.
        :param async_requests_mode: changes internal REST execution mode to avoid 60s timeout on IBM cloud
        :param connection_pool_size - In a multithreaded environment, you should set this value to a
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
        """
        self._kwargs = kwargs
        self._ssl = self.translate_to_boolean(kwargs['ssl'])
        self._address = kwargs.get('address', None)
        self._port = kwargs.get('port', None)
        self._verify = False
        self._timeout = None if kwargs.get('timeout', None) is None else float(kwargs.get('timeout'))
        self._async_requests_mode = self.translate_to_boolean(kwargs.get('async_requests_mode', False))
        # populated on the fly
        if kwargs.get('user'):
            self._is_admin = True if case_and_space_insensitive_equals(kwargs.get('user'), 'ADMIN') else None
        else:
            self._is_admin = None

        if 'verify' in kwargs:
            if isinstance(kwargs['verify'], str):
                if kwargs['verify'].upper() == 'FALSE':
                    self._verify = False
                elif kwargs['verify'].upper() == 'TRUE':
                    self._verify = True
                # path to .cer file
                else:
                    self._verify = kwargs.get('verify')
            elif isinstance(kwargs['verify'], bool):
                self._verify = kwargs['verify']
            else:
                raise ValueError("verify argument must be of type str or bool")

        if 'base_url' in kwargs:
            self._base_url = kwargs['base_url']
        else:
            self._base_url = "http{}://{}:{}".format(
                's' if self._ssl else '',
                'localhost' if len(self._address) == 0 else self._address,
                self._port)

        self._version = None
        self._headers = self.HEADERS.copy()
        if "session_context" in kwargs:
            self._headers["TM1-SessionContext"] = kwargs["session_context"]

        self.disable_http_warnings()
        # re-use or create tm1 http session
        self._s = requests.session()
        if "session_id" in kwargs:
            self._s.cookies.set("TM1SessionId", kwargs["session_id"])
        else:
            self._start_session(
                user=kwargs.get("user", None),
                password=kwargs.get("password", None),
                namespace=kwargs.get("namespace", None),
                gateway=kwargs.get("gateway", None),
                cam_passport=kwargs.get("cam_passport", None),
                decode_b64=self.translate_to_boolean(kwargs.get("decode_b64", False)),
                integrated_login=self.translate_to_boolean(kwargs.get("integrated_login", False)),
                integrated_login_domain=kwargs.get("integrated_login_domain"),
                integrated_login_service=kwargs.get("integrated_login_service"),
                integrated_login_host=kwargs.get("integrated_login_host"),
                integrated_login_delegate=kwargs.get("integrated_login_delegate"),
                impersonate=kwargs.get("impersonate", None))

        if not self._version:
            self.set_version()

        self._sandboxing_disabled = None

        # manage connection pool
        if "connection_pool_size" in kwargs:
            self._manage_http_connection_pool(kwargs.get("connection_pool_size"))

        # Logging
        if 'logging' in kwargs:
            if self.translate_to_boolean(value=kwargs['logging']):
                http_client.HTTPConnection.debuglevel = 1

    def _manage_http_connection_pool(self, connection_pool_size: Union[str, int]):
        self._s.mount(
            self._base_url,
            HTTPAdapter(
                pool_connections=int(connection_pool_size),
                pool_maxsize=int(connection_pool_size)))

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
        :param url: String, for instance : /api/v1/Dimensions('plan_business_unit')
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
        :param url: String, for instance : /api/v1/Dimensions('plan_business_unit')
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
        :param url:  String, for instance : /api/v1/Dimensions('plan_business_unit')
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
            self.POST('/api/v1/ActiveSession/tm1.Close', '', headers={"Connection": "close"}, timeout=timeout,
                      async_requests_mode=False, **kwargs)
        except TM1pyRestException:
            # ProductVersion < TM1 10.2.2 FP 6
            self.POST('/api/logout', '', headers={"Connection": "close"}, timeout=timeout, **kwargs)
        finally:
            self._s.close()

    def _start_session(self, user: str, password: str, decode_b64: bool = False, namespace: str = None,
                       gateway: str = None, cam_passport: str = None, integrated_login: bool = None,
                       integrated_login_domain: str = None, integrated_login_service: str = None,
                       integrated_login_host: str = None, integrated_login_delegate: bool = None,
                       impersonate: str = None):
        """ perform a simple GET request (Ask for the TM1 Version) to start a session
        """
        # Authorization with integrated_login
        if integrated_login:
            self._s.auth = HttpNegotiateAuth(
                domain=integrated_login_domain,
                service=integrated_login_service,
                host=integrated_login_host,
                delegate=integrated_login_delegate)

        # Authorization [Basic, CAM] through Headers
        else:
            token = self._build_authorization_token(
                user,
                self.b64_decode_password(password) if decode_b64 else password,
                namespace,
                gateway,
                cam_passport,
                self._verify)
            self.add_http_header('Authorization', token)

        url = '/api/v1/Configuration/ProductVersion/$value'
        try:
            additional_headers = dict()
            if impersonate:
                additional_headers["TM1-Impersonate"] = impersonate

            response = self.GET(url=url, headers=additional_headers)
            if response is None:
                raise ValueError(f"No response returned from URL: '{self._base_url + url}'. "
                                 f"Please double check your address and port number in the URL.")
                
            self._version = response.text
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
            self.GET('/api/v1/Configuration/ServerName/$value')
            return True
        except:
            return False

    def set_version(self):
        url = '/api/v1/Configuration/ProductVersion/$value'
        response = self.GET(url=url)
        self._version = response.text

    @property
    def version(self) -> str:
        return self._version

    @property
    def is_admin(self) -> bool:
        if self._is_admin is None:
            response = self.GET("/api/v1/ActiveUser/Groups")
            self._is_admin = "ADMIN" in CaseAndSpaceInsensitiveSet(
                *[group["Name"] for group in response.json()["value"]])

        return self._is_admin

    @property
    def sandboxing_disabled(self):
        if self._sandboxing_disabled is None:
            value = self.GET("/api/v1/ActiveConfiguration/Administration/DisableSandboxing/$value")
            self._sandboxing_disabled = value

        return self._sandboxing_disabled

    @property
    def session_id(self) -> str:
        return self._s.cookies["TM1SessionId"]

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

    def retrieve_async_response(self, async_id: str, **kwargs) -> Response:
        url = self._base_url + f"/api/v1/_async('{async_id}')"
        return self._s.get(url, **kwargs)

    def cancel_async_operation(self, async_id: str, **kwargs):
        url = self._base_url + f"/api/v1/_async('{async_id}')"
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
        sock = BytesIOSocket(data)

        response = HTTPResponse(sock)
        response.begin()

        return urllib3.HTTPResponse.from_httplib(response)

    @staticmethod
    def build_response_from_raw_bytes(data: bytes) -> Response:
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


class BytesIOSocket:
    """ used in urllib3_response_from_bytes method to construct urllib3 response from raw bytes

    """

    def __init__(self, content: bytes):
        self.handle = BytesIO(content)

    def makefile(self, mode) -> BytesIO:
        return self.handle
