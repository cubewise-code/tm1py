# -*- coding: utf-8 -*-

# TM1py Exceptions are defined here
from typing import Mapping, List


class TM1pyTimeout(Exception):
    def __init__(self, method: str, url: str, timeout: float):
        self.method = method
        self.url = url
        self.timeout = timeout

    def __str__(self):
        return f"Timeout after {self.timeout} seconds for '{self.method}' request with url :'{self.url}'"


class TM1pyVersionException(Exception):
    def __init__(self, function: str, required_version):
        self.function = function
        self.required_version = required_version

    def __str__(self):
        return f"Function '{self.function}' requires TM1 server version >= '{self.required_version}'"


class TM1pyNotAdminException(Exception):
    def __init__(self, function: str):
        self.function = function

    def __str__(self):
        return f"Function '{self.function}' requires admin permissions"


class TM1pyException(Exception):
    """ The default exception for TM1py

    """

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


class TM1pyRestException(TM1pyException):
    """ Exception for failing REST operations

    """

    def __init__(self, response: str, status_code: int, reason: str, headers: Mapping):
        super(TM1pyRestException, self).__init__(response)
        self._status_code = status_code
        self._reason = reason
        self._headers = headers

    @property
    def status_code(self):
        return self._status_code

    @property
    def reason(self):
        return self._reason

    @property
    def response(self):
        return self.message

    @property
    def headers(self):
        return self._headers

    def __str__(self):
        return "Text: '{}' - Status Code: {} - Reason: '{}' - Headers: {}".format(
            self.message,
            self._status_code,
            self._reason,
            self._headers)


class TM1pyWriteFailureException(TM1pyException):

    def __init__(self, error_log_files: List[str]):
        self.error_log_files = error_log_files

        message = f"Write operation failed. Details: '{self.error_log_files}'"
        super(TM1pyWriteFailureException, self).__init__([message])


class TM1pyWritePartialFailureException(TM1pyException):

    def __init__(self, error_log_files: List[str]):
        self.error_log_files = error_log_files

        message = f"Write operations failed partially. Details: '{self.error_log_files}'"
        super(TM1pyWritePartialFailureException, self).__init__(message)
