# -*- coding: utf-8 -*-

import functools
import json
from datetime import datetime
from typing import Dict, Optional

import pytz
from requests import Response

from TM1py.Services.ObjectService import ObjectService
from TM1py.Services.RestService import RestService
from TM1py.Utils import format_url


def odata_track_changes_header(func):
    """ Higher Order function to handle addition and removal of odata.track-changes HTTP Header

    :param func: 
    :return: 
    """

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        # Add header
        self._rest.add_http_header("Prefer", "odata.track-changes")
        # Do stuff
        response = func(self, *args, **kwargs)
        # Remove Header
        self._rest.remove_http_header("Prefer")
        return response

    return wrapper


class ServerService(ObjectService):
    """ Service to query common information from the TM1 Server
    
    """

    def __init__(self, rest: RestService):
        super().__init__(rest)
        self.tlog_last_delta_request = None
        self.mlog_last_delta_request = None

    @odata_track_changes_header
    def initialize_transaction_log_delta_requests(self, filter=None, **kwargs):
        url = "/api/v1/TransactionLogEntries"
        if filter:
            url += "?$filter={}".format(filter)
        response = self._rest.GET(url=url, **kwargs)
        # Read the next delta-request-url from the response
        self.tlog_last_delta_request = response.text[response.text.rfind("TransactionLogEntries/!delta('"):-2]

    @odata_track_changes_header
    def execute_transaction_log_delta_request(self, **kwargs) -> Dict:
        response = self._rest.GET(url="/api/v1/" + self.tlog_last_delta_request, **kwargs)
        self.tlog_last_delta_request = response.text[response.text.rfind("TransactionLogEntries/!delta('"):-2]
        return response.json()['value']

    @odata_track_changes_header
    def initialize_message_log_delta_requests(self, filter=None, **kwargs):
        url = "/api/v1/MessageLogEntries"
        if filter:
            url += "?$filter={}".format(filter)
        response = self._rest.GET(url=url, **kwargs)
        # Read the next delta-request-url from the response
        self.mlog_last_delta_request = response.text[response.text.rfind("MessageLogEntries/!delta('"):-2]

    @odata_track_changes_header
    def execute_message_log_delta_request(self, **kwargs) -> Dict:
        response = self._rest.GET(url="/api/v1/" + self.mlog_last_delta_request, **kwargs)
        self.mlog_last_delta_request = response.text[response.text.rfind("MessageLogEntries/!delta('"):-2]
        return response.json()['value']

    def get_message_log_entries(self, reverse: bool = True, since: datetime = None, top: int = None, **kwargs) -> Dict:
        """

        :param reverse: Boolean
        :param since: of type datetime. If it doesn't have tz information, UTC is assumed.
        :param top: Integer
        :param kwargs:
        :return: Dict of server log
        """
        reverse = 'desc' if reverse else 'asc'
        url = '/api/v1/MessageLogEntries?$orderby=TimeStamp {} '.format(reverse)
        if since:
            # If since doesn't have tz information, UTC is assumed
            if not since.tzinfo:
                since = pytz.utc.localize(since)
            # TM1 REST API expects %Y-%m-%dT%H:%M:%SZ Format with UTC time !
            since_utc = since.astimezone(pytz.utc)
            url += "&$filter={}".format(format_url("TimeStamp ge {}", since_utc.strftime("%Y-%m-%dT%H:%M:%SZ")))
        if top:
            url += '&$top={}'.format(top)
        response = self._rest.GET(url, **kwargs)
        return response.json()['value']

    def get_transaction_log_entries(self, reverse: bool = True, user: str = None, cube: str = None,
                                    since: datetime = None, top: int = None, **kwargs) -> Dict:
        """
        
        :param reverse: 
        :param user: 
        :param cube: 
        :param since: of type datetime. If it doesn't have tz information, UTC is assumed.
        :param top: 
        :return: 
        """
        reverse = 'desc' if reverse else 'asc'
        url = '/api/v1/TransactionLogEntries?$orderby=TimeStamp {} '.format(reverse)
        # filter on user, cube and time
        if user or cube or since:
            log_filters = []
            if user:
                log_filters.append(format_url("User eq '{}'", user))
            if cube:
                log_filters.append(format_url("Cube eq '{}'", cube))
            if since:
                # If since doesn't have tz information, UTC is assumed
                if not since.tzinfo:
                    since = pytz.utc.localize(since)
                # TM1 REST API expects %Y-%m-%dT%H:%M:%SZ Format with UTC time !
                since_utc = since.astimezone(pytz.utc)
                log_filters.append(format_url("TimeStamp ge {}", since_utc.strftime("%Y-%m-%dT%H:%M:%SZ")))
            url += "&$filter={}".format(" and ".join(log_filters))
        # top limit
        if top:
            url += '&$top={}'.format(top)
        response = self._rest.GET(url, **kwargs)
        return response.json()['value']

    def get_last_process_message_from_messagelog(self, process_name: str, **kwargs) -> Optional[str]:
        """ Get the latest message log entry for a process

            :param process_name: name of the process
            :return: String - the message, for instance: "Ausführung normal beendet, verstrichene Zeit 0.03  Sekunden"
        """
        url = format_url(
            "/api/v1/MessageLog()?$orderby='TimeStamp'&$filter=Logger eq 'TM1.Process' and contains(Message, '{}')",
            process_name)
        response = self._rest.GET(url=url, **kwargs)
        response_as_list = response.json()['value']
        if len(response_as_list) > 0:
            message_log_entry = response_as_list[0]
            return message_log_entry['Message']

    def get_server_name(self, **kwargs) -> str:
        """ Ask TM1 Server for its name

        :Returns:
            String, the server name
        """
        url = '/api/v1/Configuration/ServerName/$value'
        return self._rest.GET(url, **kwargs).text

    def get_product_version(self, **kwargs) -> str:
        """ Ask TM1 Server for its version

        :Returns:
            String, the version
        """
        url = '/api/v1/Configuration/ProductVersion/$value'
        return self._rest.GET(url, **kwargs).text

    def get_admin_host(self, **kwargs) -> str:
        url = '/api/v1/Configuration/AdminHost/$value'
        return self._rest.GET(url, **kwargs).text

    def get_data_directory(self, **kwargs) -> str:
        url = '/api/v1/Configuration/DataBaseDirectory/$value'
        return self._rest.GET(url, **kwargs).text

    def get_configuration(self, **kwargs) -> Dict:
        url = '/api/v1/Configuration'
        config = self._rest.GET(url, **kwargs).json()
        del config["@odata.context"]
        return config

    def get_static_configuration(self, **kwargs) -> Dict:
        """ Read TM1 config settings as dictionary from TM1 Server

        :return: config as dictionary
        """
        url = '/api/v1/StaticConfiguration'
        config = self._rest.GET(url, **kwargs).json()
        del config["@odata.context"]
        return config

    def get_active_configuration(self, **kwargs) -> Dict:
        """ Read effective(!) TM1 config settings as dictionary from TM1 Server

        :return: config as dictionary
        """
        url = '/api/v1/ActiveConfiguration'
        config = self._rest.GET(url, **kwargs).json()
        del config["@odata.context"]
        return config

    def update_static_configuration(self, configuration: Dict) -> Response:
        """ Update the .cfg file and triggers TM1 to re-read the file.

        :param configuration:
        :return: Response
        """
        url = '/api/v1/StaticConfiguration'
        return self._rest.PATCH(url, json.dumps(configuration))

    def save_data(self, **kwargs) -> Response:
        from TM1py.Services import ProcessService
        ti = "SaveDataAll;"
        process_service = ProcessService(self._rest)
        return process_service.execute_ti_code(ti, **kwargs)
