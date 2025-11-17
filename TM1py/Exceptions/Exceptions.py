# -*- coding: utf-8 -*-

# TM1py Exceptions are defined here
from typing import List, Mapping


class TM1pyTimeout(Exception):
    """Exception for timeout during a REST request."""

    def __init__(self, method: str, url: str, timeout: float):
        """
        :param method: HTTP method used
        :param url: URL of the request
        :param timeout: Timeout in seconds
        """
        self.method = method
        self.url = url
        self.timeout = timeout

    def __str__(self):
        return f"Timeout after {self.timeout} seconds for '{self.method}' request with url :'{self.url}'"


class TM1pyVersionException(Exception):
    """Exception for usage of a feature requiring a higher TM1 server version."""

    def __init__(self, function: str, required_version, feature: str = None):
        """
        :param function: Name of the function
        :param required_version: Required TM1 server version
        :param feature: Optional feature name
        """
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
    """Exception for usage of a deprecated feature."""

    def __init__(self, function: str, deprecated_in_version):
        """
        :param function: Name of the function
        :param deprecated_in_version: Version in which the function was deprecated
        """
        self.function = function
        self.deprecated_in_version = deprecated_in_version

    def __str__(self):
        return f"Function '{self.function}' has been deprecated in TM1 server version >= '{self.deprecated_in_version}'"


class TM1pyPermissionException(Exception):
    """Exception for missing permissions."""

    def __init__(self, function: str, required_permission: str):
        """
        :param function: Name of the function
        :param permission: Name of Permission, e.g.
        """
        self.function = function
        self.required_permission = required_permission

    def __str__(self):
        return f"Function '{self.function}' requires {self.required_permission} permissions"


class TM1pyNotAdminException(TM1pyPermissionException):
    """Exception for missing admin permissions."""

    def __init__(self, function: str):
        """
        :param function: Name of the function
        """
        super().__init__(function, "admin")


class TM1pyNotDataAdminException(TM1pyPermissionException):
    """Exception for missing DataAdmin permissions."""

    def __init__(self, function: str):
        """
        :param function: Name of the function
        """
        super().__init__(function, "DataAdmin")


class TM1pyNotSecurityAdminException(TM1pyPermissionException):
    """Exception for missing SecurityAdmin permissions."""

    def __init__(self, function: str):
        """
        :param function: Name of the function
        """
        super().__init__(function, "SecurityAdmin")


class TM1pyNotOpsAdminException(TM1pyPermissionException):
    """Exception for missing OperationsAdmin permissions."""

    def __init__(self, function: str):
        """
        :param function: Name of the function
        """
        super().__init__(function, "OperationsAdmin")


class TM1pyException(Exception):
    """The default exception for TM1py."""

    def __init__(self, message):
        """
        :param message: Exception message
        """
        self.message = message

    def __str__(self):
        return self.message


class TM1pyRestException(TM1pyException):
    """Exception for failing REST operations."""

    def __init__(self, response: str, status_code: int, reason: str, headers: Mapping):
        """
        :param response: Response text
        :param status_code: HTTP status code
        :param reason: Reason phrase
        :param headers: HTTP headers
        """
        super(TM1pyRestException, self).__init__(response)
        self._status_code = status_code
        self._reason = reason
        self._headers = headers

    @property
    def status_code(self):
        """HTTP status code."""
        return self._status_code

    @property
    def reason(self):
        """Reason phrase."""
        return self._reason

    @property
    def response(self):
        """Response text."""
        return self.message

    @property
    def headers(self):
        """HTTP headers."""
        return self._headers

    def __str__(self):
        return "Text: '{}' - Status Code: {} - Reason: '{}' - Headers: {}".format(
            self.message, self._status_code, self._reason, self._headers
        )


class TM1pyWriteFailureException(TM1pyException):
    """Exception for complete failure of write operations."""

    def __init__(self, statuses: List[str], error_log_files: List[str]):
        """
        :param statuses: List of failed statuses
        :param error_log_files: List of error log file paths
        """
        self.statuses = statuses
        self.error_log_files = error_log_files

        message = f"All {len(self.statuses)} write operations failed. Details: {self.error_log_files}"
        super(TM1pyWriteFailureException, self).__init__(message)


class TM1pyWritePartialFailureException(TM1pyException):
    """Exception for partial failure of write operations."""

    def __init__(self, statuses: List[str], error_log_files: List[str], attempts: int):
        """
        :param statuses: List of failed statuses
        :param error_log_files: List of error log file paths
        :param attempts: Total number of attempts
        """
        self.statuses = statuses
        self.error_log_files = error_log_files
        self.attempts = attempts

        message = (
            f"{len(self.statuses)} out of {self.attempts} write operations failed partially. "
            f"Details: {self.error_log_files}"
        )
        super(TM1pyWritePartialFailureException, self).__init__(message)
