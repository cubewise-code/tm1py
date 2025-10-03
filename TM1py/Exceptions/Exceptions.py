# -*- coding: utf-8 -*-

# TM1py Exceptions are defined here
from typing import List, Mapping


class TM1pyTimeout(Exception):
    def __init__(self, method: str, url: str, timeout: float):
        self.method = method
        self.url = url
        self.timeout = timeout

    def __str__(self):
        return f"Timeout after {self.timeout} seconds for '{self.method}' request with url :'{self.url}'"


class TM1pyVersionException(Exception):
    def __init__(self, function: str, required_version, feature: str = None):
        self.function = function
        self.required_version = required_version
        self.feature = feature

    def __str__(self):
        require_string = f"requires TM1 server version >= '{self.required_version}'"
        if self.feature:
            return f"'{self.feature}' feature of function '{self.function}' {require_string}"
        else:
            return f"Function '{self.function}' {require_string}"


class TM1pyVersionDeprecationException(Exception):
    def __init__(self, function: str, deprecated_in_version):
        self.function = function
        self.deprecated_in_version = deprecated_in_version

    def __str__(self):
        return f"Function '{self.function}' has been deprecated in TM1 server version >= '{self.deprecated_in_version}'"


class TM1pyNotAdminException(Exception):
    def __init__(self, function: str):
        self.function = function

    def __str__(self):
        return f"Function '{self.function}' requires admin permissions"


class TM1pyNotDataAdminException(Exception):
    def __init__(self, function: str):
        self.function = function

    def __str__(self):
        return f"Function '{self.function}' requires DataAdmin permissions"


class TM1pyNotSecurityAdminException(Exception):
    def __init__(self, function: str):
        self.function = function

    def __str__(self):
        return f"Function '{self.function}' requires SecurityAdmin permissions"


class TM1pyNotOpsAdminException(Exception):
    def __init__(self, function: str):
        self.function = function

    def __str__(self):
        return f"Function '{self.function}' requires OperationsAdmin permissions"


class TM1pyException(Exception):
    """The default exception for TM1py"""

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


class TM1pyRestException(TM1pyException):
    """Exception for failing REST operations"""

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
            self.message, self._status_code, self._reason, self._headers
        )


class TM1pyWriteFailureException(TM1pyException):

    def __init__(self, statuses: List[str], error_log_files: List[str]):
        self.statuses = statuses
        self.error_log_files = error_log_files

        message = f"All {len(self.statuses)} write operations failed. Details: {self.error_log_files}"
        super(TM1pyWriteFailureException, self).__init__(message)


class TM1pyWritePartialFailureException(TM1pyException):

    def __init__(self, statuses: List[str], error_log_files: List[str], attempts: int):
        self.statuses = statuses
        self.error_log_files = error_log_files
        self.attempts = attempts

        message = (
            f"{len(self.statuses)} out of {self.attempts} write operations failed partially. "
            f"Details: {self.error_log_files}"
        )
        super(TM1pyWritePartialFailureException, self).__init__(message)
