# -*- coding: utf-8 -*-

# TM1py Exceptions are defined here


class TM1pyException(Exception):
    """ The default exception for TM1py

    """
    def __init__(self, response, status_code, reason):
        self._response = response
        self._status_code = status_code
        self._reason = reason

    def __str__(self):
        return "Text: {} Status Code: {} Reason: {}".format(self._response, self._status_code, self._reason)