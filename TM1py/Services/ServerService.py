# -*- coding: utf-8 -*-

import functools
import json
from collections.abc import Iterable
from datetime import datetime
from typing import Dict, Optional

import pytz
from requests import Response

from TM1py.Services.ObjectService import ObjectService
from TM1py.Services.RestService import RestService
from TM1py.Utils import format_url
from TM1py.Utils.Utils import CaseAndSpaceInsensitiveDict, require_admin, require_version


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
        self.alog_last_delta_request = None

    @odata_track_changes_header
    def initialize_transaction_log_delta_requests(self, filter=None, **kwargs):
        url = "/api/v1/TailTransactionLog()"
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
    def initialize_audit_log_delta_requests(self, filter=None, **kwargs):
        url = "/api/v1/TailAuditLog()"
        if filter:
            url += "?$filter={}".format(filter)
        response = self._rest.GET(url=url, **kwargs)
        # Read the next delta-request-url from the response
        self.alog_last_delta_request = response.text[response.text.rfind("AuditLogEntries/!delta('"):-2]

    @odata_track_changes_header
    def execute_audit_log_delta_request(self, **kwargs) -> Dict:
        response = self._rest.GET(url="/api/v1/" + self.alog_last_delta_request, **kwargs)
        self.alog_last_delta_request = response.text[response.text.rfind("AuditLogEntries/!delta('"):-2]
        return response.json()['value']

    @odata_track_changes_header
    def initialize_message_log_delta_requests(self, filter=None, **kwargs):
        url = "/api/v1/TailMessageLog()"
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

    @require_admin
    def get_message_log_entries(self, reverse: bool = True, since: datetime = None,
                                until: datetime = None, top: int = None, logger: str = None,
                                level: str = None, msg_contains: Iterable = None, msg_contains_operator: str = 'and',
                                **kwargs) -> Dict:
        """
        :param reverse: Boolean
        :param since: of type datetime. If it doesn't have tz information, UTC is assumed.
        :param until: of type datetime. If it doesn't have tz information, UTC is assumed.
        :param top: Integer
        :param logger: string, eg TM1.Server, TM1.Chore, TM1.Mdx.Interface, TM1.Process
        :param level: string, ERROR, WARNING, INFO, DEBUG, UNKNOWN
        :param msg_contains: iterable, find substring in log message; list of substrings will be queried as AND statement
        :param msg_contains_operator: 'and' or 'or'

        :param kwargs:
        :return: Dict of server log
        """
        msg_contains_operator = msg_contains_operator.strip().lower()
        if msg_contains_operator not in ("and", "or"):
            raise ValueError("'msg_contains_operator' must be either 'AND' or 'OR'")

        reverse = 'desc' if reverse else 'asc'
        url = '/api/v1/MessageLogEntries?$orderby=TimeStamp {}'.format(reverse)

        if since or until or logger or level or msg_contains:
            log_filters = []

            if since:
                # If since doesn't have tz information, UTC is assumed
                if not since.tzinfo:
                    since = self.utc_localize_time(since)
                log_filters.append(format_url("TimeStamp ge {}", since.strftime("%Y-%m-%dT%H:%M:%SZ")))

            if until:
                # If until doesn't have tz information, UTC is assumed
                if not until.tzinfo:
                    until = self.utc_localize_time(until)
                log_filters.append(format_url("TimeStamp le {}", until.strftime("%Y-%m-%dT%H:%M:%SZ")))

            if logger:
                log_filters.append(format_url("Logger eq '{}'", logger))

            if level:
                level_dict = CaseAndSpaceInsensitiveDict(
                    {'ERROR': 1, 'WARNING': 2, 'INFO': 3, 'DEBUG': 4, 'UNKNOWN': 5})
                level_index = level_dict.get(level)
                if level_index:
                    log_filters.append("Level eq {}".format(level_index))

            if msg_contains:
                if isinstance(msg_contains, str):
                    log_filters.append(format_url("contains(toupper(Message),toupper('{}'))", msg_contains))
                else:
                    msg_filters = [format_url("contains(toupper(Message),toupper('{}'))", wildcard)
                                   for wildcard in msg_contains]
                    log_filters.append("({})".format(f" {msg_contains_operator} ".join(msg_filters)))

            url += "&$filter={}".format(" and ".join(log_filters))

        if top:
            url += '&$top={}'.format(top)

        response = self._rest.GET(url, **kwargs)
        return response.json()['value']

    @require_admin
    def write_to_messsage_log(self, level: str = "INFO", message: str):
        from TM1py.Services import ProcessService
        process_service = ProcessService(self._rest)
        ti="LogOutput('{}', '{}')".format(level, messsage)
        return process_service.execute_ti_code(prolog=ti)

    @staticmethod
    def utc_localize_time(timestamp):
        timestamp = pytz.utc.localize(timestamp)
        timestamp_utc = timestamp.astimezone(pytz.utc)
        return timestamp_utc

    @require_admin
    def get_transaction_log_entries(self, reverse: bool = True, user: str = None, cube: str = None,
                                    since: datetime = None, until: datetime = None, top: int = None, **kwargs) -> Dict:
        """
        :param reverse: Boolean
        :param user: UserName
        :param cube: CubeName
        :param since: of type datetime. If it doesn't have tz information, UTC is assumed.
        :param until: of type datetime. If it doesn't have tz information, UTC is assumed.
        :param top: int
        :return:
        """
        reverse = 'desc' if reverse else 'asc'
        url = '/api/v1/TransactionLogEntries?$orderby=TimeStamp {} '.format(reverse)
        # filter on user, cube and time
        if user or cube or since or until:
            log_filters = []
            if user:
                log_filters.append(format_url("User eq '{}'", user))
            if cube:
                log_filters.append(format_url("Cube eq '{}'", cube))
            if since:
                # If since doesn't have tz information, UTC is assumed
                if not since.tzinfo:
                    since = self.utc_localize_time(since)
                log_filters.append(format_url("TimeStamp ge {}", since.strftime("%Y-%m-%dT%H:%M:%SZ")))
            if until:
                # If until doesn't have tz information, UTC is assumed
                if not until.tzinfo:
                    until = self.utc_localize_time(until)
                log_filters.append(format_url("TimeStamp le {}", until.strftime("%Y-%m-%dT%H:%M:%SZ")))
            url += "&$filter={}".format(" and ".join(log_filters))
        # top limit
        if top:
            url += '&$top={}'.format(top)
        response = self._rest.GET(url, **kwargs)
        return response.json()['value']

    @require_admin
    @require_version(version="11.6")
    def get_audit_log_entries(self, user: str = None, object_type: str = None, object_name: str = None,
                              since: datetime = None, until: datetime = None, top: int = None, **kwargs) -> Dict:
        """
        :param user: UserName
        :param object_type: ObjectType
        :param object_name: ObjectName
        :param since: of type datetime. If it doesn't have tz information, UTC is assumed.
        :param until: of type datetime. If it doesn't have tz information, UTC is assumed.
        :param top: int
        :return:
        """

        url = '/api/v1/AuditLogEntries?$expand=AuditDetails'
        # filter on user, object_type, object_name  and time
        if any([user, object_type, object_name, since, until]):
            log_filters = []
            if user:
                log_filters.append(format_url("UserName eq '{}'", user))
            if object_type:
                log_filters.append(format_url("ObjectType eq '{}'", object_type))
            if object_name:
                log_filters.append(format_url("ObjectName eq '{}'", object_name))
            if since:
                # If since doesn't have tz information, UTC is assumed
                if not since.tzinfo:
                    since = self.utc_localize_time(since)
                log_filters.append(format_url("TimeStamp ge {}", since.strftime("%Y-%m-%dT%H:%M:%SZ")))
            if until:
                # If until doesn't have tz information, UTC is assumed
                if not until.tzinfo:
                    until = self.utc_localize_time(until)
                log_filters.append(format_url("TimeStamp le {}", until.strftime("%Y-%m-%dT%H:%M:%SZ")))
            url += "&$filter={}".format(" and ".join(log_filters))
        # top limit
        if top:
            url += '&$top={}'.format(top)
        response = self._rest.GET(url, **kwargs)
        return response.json()['value']

    @require_admin
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

    @require_admin
    def get_static_configuration(self, **kwargs) -> Dict:
        """ Read TM1 config settings as dictionary from TM1 Server

        :return: config as dictionary
        """
        url = '/api/v1/StaticConfiguration'
        config = self._rest.GET(url, **kwargs).json()
        del config["@odata.context"]
        return config

    @require_admin
    def get_active_configuration(self, **kwargs) -> Dict:
        """ Read effective(!) TM1 config settings as dictionary from TM1 Server

        :return: config as dictionary
        """
        url = '/api/v1/ActiveConfiguration'
        config = self._rest.GET(url, **kwargs).json()
        del config["@odata.context"]
        return config

    @require_admin
    def update_static_configuration(self, configuration: Dict) -> Response:
        """ Update the .cfg file and triggers TM1 to re-read the file.

        :param configuration:
        :return: Response
        """
        url = '/api/v1/StaticConfiguration'
        return self._rest.PATCH(url, json.dumps(configuration))

    @require_admin
    def save_data(self, **kwargs) -> Response:
        from TM1py.Services import ProcessService
        ti = "SaveDataAll;"
        process_service = ProcessService(self._rest)
        return process_service.execute_ti_code(ti, **kwargs)

    @require_admin
    def start_performance_monitor(self):
        config = {
            "Administration": {"PerformanceMonitorOn": True}
        }
        self.update_static_configuration(config)

    @require_admin
    def stop_performance_monitor(self):
        config = {
            "Administration": {"PerformanceMonitorOn": False}
        }
        self.update_static_configuration(config)

    @require_admin
    def activate_audit_log(self):
        config = {'Administration': {'AuditLog': {'Enable': True}}}
        self.update_static_configuration(config)

    @require_admin
    def deactivate_audit_log(self):
        config = {'Administration': {'AuditLog': {'Enable': False}}}
        self.update_static_configuration(config)
