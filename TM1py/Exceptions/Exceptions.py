# -*- coding: utf-8 -*-

# TM1py Exceptions are defined here
from typing import Mapping


class TM1pyTimeout(Exception):
    def __init__(self, method: str, url: str, timeout: float):
        self.method = method
        self.url = url
        self.timeout = timeout

    def __str__(self):
        return f"Timeout after {self.timeout} seconds for '{self.method}' request with url :'{self.url}'"


class TM1pyException(Exception):
    """ The default exception for TM1py

    """

    def __init__(self, response: str, status_code: int, reason: str, headers: Mapping):
        self._response = response
        self._status_code = status_code
        self._reason = reason
        self._headers = headers

    @property
    def status_code(self):
        return self._status_code

    @property
    def reason(self):
        return self.reason

    @property
    def response(self):
        return self._response

    @property
    def headers(self):
        return self._headers

    def __str__(self):
        return "Text: {} Status Code: {} Reason: {} Headers: {}".format(
            self._response,
            self._status_code,
            self._reason,
            self._headers)
