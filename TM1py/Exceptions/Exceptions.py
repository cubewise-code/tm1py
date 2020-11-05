# -*- coding: utf-8 -*-

# TM1py Exceptions are defined here
from typing import Mapping


class TM1pyTimeout(Exception):
    def __init__(self, method: str, url: str, timeout: float):
        """
        Initialize a method.

        Args:
            self: (todo): write your description
            method: (str): write your description
            url: (str): write your description
            timeout: (int): write your description
        """
        self.method = method
        self.url = url
        self.timeout = timeout

    def __str__(self):
        """
        Return a string representation of this object.

        Args:
            self: (todo): write your description
        """
        return f"Timeout after {self.timeout} seconds for '{self.method}' request with url :'{self.url}'"


class TM1pyVersionException(Exception):
    def __init__(self, function, required_version):
        """
        Initialize a function.

        Args:
            self: (todo): write your description
            function: (callable): write your description
            required_version: (str): write your description
        """
        self.function = function
        self.required_version = required_version

    def __str__(self):
        """
        Return a string representation of this object.

        Args:
            self: (todo): write your description
        """
        return f"Function '{self.function}' requires TM1 server version >= '{self.required_version}'"


class TM1pyException(Exception):
    """ The default exception for TM1py

    """

    def __init__(self, message):
        """
        Initialize the message

        Args:
            self: (todo): write your description
            message: (str): write your description
        """
        self.message = message

    def __str__(self):
        """
        Return the string representation of the message.

        Args:
            self: (todo): write your description
        """
        return self.message


class TM1pyRestException(TM1pyException):
    """ Exception for failing REST operations

    """

    def __init__(self, response: str, status_code: int, reason: str, headers: Mapping):
        """
        Initialize the http response.

        Args:
            self: (todo): write your description
            response: (list): write your description
            status_code: (int): write your description
            reason: (str): write your description
            headers: (list): write your description
        """
        super(TM1pyRestException, self).__init__(response)
        self._status_code = status_code
        self._reason = reason
        self._headers = headers

    @property
    def status_code(self):
        """
        Return the status code.

        Args:
            self: (todo): write your description
        """
        return self._status_code

    @property
    def reason(self):
        """
        Returns the reason.

        Args:
            self: (todo): write your description
        """
        return self._reason

    @property
    def response(self):
        """
        Return the response

        Args:
            self: (todo): write your description
        """
        return self.message

    @property
    def headers(self):
        """
        Returns the headers.

        Args:
            self: (todo): write your description
        """
        return self._headers

    def __str__(self):
        """
        Return a string representation of the request.

        Args:
            self: (todo): write your description
        """
        return "Text: {} Status Code: {} Reason: {} Headers: {}".format(
            self.message,
            self._status_code,
            self._reason,
            self._headers)
