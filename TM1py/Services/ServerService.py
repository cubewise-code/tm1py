# -*- coding: utf-8 -*-

import functools
import json

import pytz

from TM1py.Services.ObjectService import ObjectService


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

    def __init__(self, rest):
        super().__init__(rest)
        self.tlog_last_delta_request = None
        self.mlog_last_delta_request = None

    @odata_track_changes_header
    def initialize_transaction_log_delta_requests(self, filter=None):
        request = "/api/v1/TransactionLogEntries"
        if filter:
            request += "?$filter={}".format(filter)
        response = self._rest.GET(request=request)
        # Read the next delta-request-url from the response
        self.tlog_last_delta_request = response.text[response.text.rfind("TransactionLogEntries/!delta('"):-2]

    @odata_track_changes_header
    def execute_transaction_log_delta_request(self):
        response = self._rest.GET(request="/api/v1/" + self.tlog_last_delta_request)
        self.tlog_last_delta_request = response.text[response.text.rfind("TransactionLogEntries/!delta('"):-2]
        return response.json()['value']

    @odata_track_changes_header
    def initialize_message_log_delta_requests(self, filter=None):
        request = "/api/v1/MessageLogEntries"
        if filter:
            request += "?$filter={}".format(filter)
        response = self._rest.GET(request=request)
        # Read the next delta-request-url from the response
        self.mlog_last_delta_request = response.text[response.text.rfind("MessageLogEntries/!delta('"):-2]

    @odata_track_changes_header
    def execute_message_log_delta_request(self):
        response = self._rest.GET(request="/api/v1/" + self.mlog_last_delta_request)
        self.mlog_last_delta_request = response.text[response.text.rfind("MessageLogEntries/!delta('"):-2]
        return response.json()['value']

    def get_message_log_entries(self, reverse=True, top=None):
        reverse = 'true' if reverse else 'false'
        request = '/api/v1/MessageLog(Reverse={})'.format(reverse)
        if top:
            request += '?$top={}'.format(top)
        response = self._rest.GET(request, '')
        return response.json()['value']

    def get_transaction_log_entries(self, reverse=True, user=None, cube=None, since=None, top=None):
        """
        
        :param reverse: 
        :param user: 
        :param cube: 
        :param since: of type datetime. If it doesn't have tz information, UTC is assumed.
        :param top: 
        :return: 
        """
        reverse = 'desc' if reverse else 'asc'
        request = '/api/v1/TransactionLogEntries?$orderby=TimeStamp {} '.format(reverse)
        # filter on user, cube and time
        if user or cube or since:
            log_filters = []
            if user:
                log_filters.append("User eq '{}'".format(user))
            if cube:
                log_filters.append("Cube eq '{}'".format(cube))
            if since:
                # If since doesn't have tz information, UTC is assumed
                if not since.tzinfo:
                    since = pytz.utc.localize(since)
                # TM1 REST API expects %Y-%m-%dT%H:%M:%SZ Format with UTC time !
                since_utc = since.astimezone(pytz.utc)
                log_filters.append("TimeStamp ge {}".format(since_utc.strftime("%Y-%m-%dT%H:%M:%SZ")))
            request += "&$filter={}".format(" and ".join(log_filters))
        # top limit
        if top:
            request += '&$top={}'.format(top)
        response = self._rest.GET(request, '')
        return response.json()['value']

    def get_last_process_message_from_messagelog(self, process_name):
        """ Get the latest messagelog entry for a process

            :param process_name: name of the process
            :return: String - the message, for instance: "Ausführung normal beendet, verstrichene Zeit 0.03  Sekunden"
        """
        request = "/api/v1/MessageLog()?$orderby='TimeStamp'&$filter=Logger eq 'TM1.Process' " \
                  "and contains( Message, '" + process_name + "')"
        response = self._rest.GET(request=request)
        response_as_list = response.json()['value']
        if len(response_as_list) > 0:
            message_log_entry = response_as_list[0]
            return message_log_entry['Message']

    def get_server_name(self):
        """ Ask TM1 Server for its name

        :Returns:
            String, the server name
        """
        request = '/api/v1/Configuration/ServerName/$value'
        return self._rest.GET(request, '').text

    def get_product_version(self):
        """ Ask TM1 Server for its version

        :Returns:
            String, the version
        """
        request = '/api/v1/Configuration/ProductVersion/$value'
        return self._rest.GET(request, '').text

    def get_admin_host(self):
        request = '/api/v1/Configuration/AdminHost/$value'
        return self._rest.GET(request, '').text

    def get_data_directory(self):
        request = '/api/v1/Configuration/DataBaseDirectory/$value'
        return self._rest.GET(request, '').text

    def get_configuration(self):
        request = '/api/v1/Configuration'
        config = self._rest.GET(request, '').json()
        del config["@odata.context"]
        return config

    def get_static_configuration(self):
        """ Read current applied (!) TM1 config settings as dictionary from TM1 Server

        :return: config as dictionary
        """
        request = '/api/v1/StaticConfiguration'
        config = self._rest.GET(request, '').json()
        del config["@odata.context"]
        return config

    def get_active_configuration(self):
        """ Read current effective(!) TM1 config settings as dictionary from TM1 Server

        :return: config as dictionary
        """
        request = '/api/v1/ActiveConfiguration'
        config = self._rest.GET(request, '').json()
        del config["@odata.context"]
        return config

    def update_static_configuration(self, configuration):
        """ Update the .cfg file and triggers TM1 to re-read the file.

        :param configuration:
        :return: Response
        """
        request = '/api/v1/StaticConfiguration'
        return self._rest.PATCH(request, json.dumps(configuration))

    def save_data(self):
        from TM1py.Services import ProcessService
        ti = "SaveDataAll;"
        process_service = ProcessService(self._rest)
        process_service.execute_ti_code(ti)
