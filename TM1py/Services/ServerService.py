# -*- coding: utf-8 -*-
from warnings import warn

import functools
import json
from collections.abc import Iterable
from datetime import datetime
from enum import Enum
from typing import Dict, Optional

import pytz
from requests import Response

from TM1py.Objects.Process import Process
from TM1py.Services.ObjectService import ObjectService
from TM1py.Services.RestService import RestService
from TM1py.Utils import format_url, odata_track_changes_header
from TM1py.Utils.Utils import CaseAndSpaceInsensitiveDict, CaseAndSpaceInsensitiveSet, require_admin, require_version, \
    decohints, deprecated_in_version
from TM1py.Services.TransactionLogService import TransactionLogService
from TM1py.Services.MessageLogService import MessageLogService
from TM1py.Services.ConfigurationService import ConfigurationService


class LogLevel(Enum):
    FATAL = "fatal"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    DEBUG = "debug"
    OFF = "off"


class ServerService(ObjectService):
    """ Service to query common information from the TM1 Server

    """

    def __init__(self, rest: RestService):
        super().__init__(rest)
        warn("Server Service will be moved to a new location in a future version", DeprecationWarning, 2)
        self.transaction_logs = TransactionLogService(rest)
        self.message_logs = MessageLogService(rest)
        self.configuration = ConfigurationService(rest)
        self.mlog_last_delta_request = None
        self.alog_last_delta_request = None

    def initialize_transaction_log_delta_requests(self, filter=None, **kwargs):
        self.transaction_logs.initialize_delta_requests(filter, **kwargs)

    def execute_transaction_log_delta_request(self, **kwargs) -> Dict:
        self.transaction_logs.execute_delta_request(**kwargs)

    @deprecated_in_version(version="12.0.0")
    @odata_track_changes_header
    def initialize_audit_log_delta_requests(self, filter=None, **kwargs):
        url = "/TailAuditLog()"
        if filter:
            url += "?$filter={}".format(filter)
        response = self._rest.GET(url=url, **kwargs)
        # Read the next delta-request-url from the response
        self.alog_last_delta_request = response.text[response.text.rfind(
            "AuditLogEntries/!delta('"):-2]

    @deprecated_in_version(version="12.0.0")
    @odata_track_changes_header
    def execute_audit_log_delta_request(self, **kwargs) -> Dict:
        response = self._rest.GET(
            url="/" + self.alog_last_delta_request, **kwargs)
        self.alog_last_delta_request = response.text[response.text.rfind(
            "AuditLogEntries/!delta('"):-2]
        return response.json()['value']

    def initialize_message_log_delta_requests(self, filter=None, **kwargs):
        return self.message_logs.initialize_delta_requests(filter, **kwargs)

    def execute_message_log_delta_request(self, **kwargs) -> Dict:
        return self.message_logs.execute_delta_request(**kwargs)


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

        return self.message_logs.get_entries(reverse=reverse,
                                             since=since,
                                             until=until,
                                             top=top,
                                             logger=logger,
                                             level=level,
                                             msg_contains=msg_contains,
                                             msg_contains_operator=msg_contains_operator,
                                             **kwargs)

    @require_admin
    def write_to_message_log(self, level: str, message: str, **kwargs) -> None:
        """
        :param level: string, FATAL, ERROR, WARN, INFO, DEBUG
        :param message: string
        :return:
        """

        return self.message_logs.create_entry(level=level,
                                              message=message,
                                              **kwargs)

    def get_transaction_log_entries(self, reverse: bool = True, user: str = None, cube: str = None,
                                    since: datetime = None, until: datetime = None, top: int = None,
                                    element_tuple_filter: Dict[str, str] = None,
                                    element_position_filter: Dict[int, Dict[str, str]] = None, **kwargs) -> Dict:
        """
        :param reverse: Boolean
        :param user: UserName
        :param cube: CubeName
        :param since: of type datetime. If it doesn't have tz information, UTC is assumed.
        :param until: of type datetime. If it doesn't have tz information, UTC is assumed.
        :param top: int
        :param element_tuple_filter: of type dict. Element name as key and comparison operator as value
        :param element_position_filter: not yet implemented
        tuple={'Actual':'eq','2020': 'ge'}
        :return:
        """
        return self.transaction_logs.get_entries(reverse=reverse,
                                                 user=user,
                                                 cube=cube,
                                                 since=since,
                                                 until=until,
                                                 top=top,
                                                 element_tuple_filter=element_tuple_filter,
                                                 element_position_filter=element_position_filter,
                                                 **kwargs)

    @require_admin
    @deprecated_in_version(version="12.0.0")
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

        url = '/AuditLogEntries?$expand=AuditDetails'
        # filter on user, object_type, object_name  and time
        if any([user, object_type, object_name, since, until]):
            log_filters = []
            if user:
                log_filters.append(format_url("UserName eq '{}'", user))
            if object_type:
                log_filters.append(format_url(
                    "ObjectType eq '{}'", object_type))
            if object_name:
                log_filters.append(format_url(
                    "ObjectName eq '{}'", object_name))
            if since:
                # If since doesn't have tz information, UTC is assumed
                if not since.tzinfo:
                    since = self.utc_localize_time(since)
                log_filters.append(format_url(
                    "TimeStamp ge {}", since.strftime("%Y-%m-%dT%H:%M:%SZ")))
            if until:
                # If until doesn't have tz information, UTC is assumed
                if not until.tzinfo:
                    until = self.utc_localize_time(until)
                log_filters.append(format_url(
                    "TimeStamp le {}", until.strftime("%Y-%m-%dT%H:%M:%SZ")))
            url += "&$filter={}".format(" and ".join(log_filters))
        # top limit
        if top:
            url += '&$top={}'.format(top)
        response = self._rest.GET(url, **kwargs)
        return response.json()['value']

    def get_last_process_message_from_message_log(self, process_name: str, **kwargs) -> Optional[str]:
        """ Get the latest message log entry for a process

            :param process_name: name of the process
            :return: String - the message, for instance: "Ausführung normal beendet, verstrichene Zeit 0.03  Sekunden"
        """
        self.message_logs.get_last_process_message(process_name, **kwargs)

    def get_server_name(self, **kwargs) -> str:
        """ Ask TM1 Server for its name

        :Returns:
            String, the server name
        """
        return self.configuration.get_server_name()

    def get_product_version(self, **kwargs) -> str:
        """ Ask TM1 Server for its version

        :Returns:
            String, the version
        """
        return self.configuration.get_product_version()

    @deprecated_in_version(version="12.0.0")
    def get_admin_host(self, **kwargs) -> str:
        return self.configuration.get_admin_host

    @deprecated_in_version(version="12.0.0")
    def get_data_directory(self, **kwargs) -> str:
        return self.configuration.get_data_directory

    def get_configuration(self, **kwargs) -> Dict:
        return self.configuration.get()

    @require_admin
    def get_static_configuration(self, **kwargs) -> Dict:
        return self.configuration.get_static()

    @require_admin
    def get_active_configuration(self, **kwargs) -> Dict:
        """ Read effective(!) TM1 config settings as dictionary from TM1 Server

        :return: config as dictionary
        """
        return self.configuration.get_active()

    def get_api_metadata(self, **kwargs):
        """ Read effective(!) TM1 config settings as dictionary from TM1 Server

        :return: config as dictionary
        """
        url = '/$metadata'
        metadata = self._rest.GET(url, **kwargs).content.decode("utf-8")
        return json.loads(metadata)

    @require_admin
    def update_static_configuration(self, configuration: Dict) -> Response:
        """ Update the .cfg file and triggers TM1 to re-read the file.

        :param configuration:
        :return: Response
        """
        url = '/StaticConfiguration'
        return self._rest.PATCH(url, json.dumps(configuration))

    @deprecated_in_version(version="12.0.0")
    @require_admin
    def save_data(self, **kwargs) -> Response:
        from TM1py.Services import ProcessService
        ti = "SaveDataAll;"
        process_service = ProcessService(self._rest)
        return process_service.execute_ti_code(ti, **kwargs)

    @require_admin
    def delete_persistent_feeders(self, **kwargs) -> Response:
        from TM1py.Services import ProcessService
        ti = "DeleteAllPersistentFeeders;"
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

    @require_admin
    def update_message_logger_level(self, logger, level):
        '''
        Updates tm1 message log levels
        :param logger:
        :param level:
        :return:
        '''

        payload = {"Level": level}
        url = f"/Loggers('{logger}')"
        return self._rest.PATCH(url, json.dumps(payload))

    @require_admin
    def get_all_message_logger_level(self):
        '''
        Get tm1 message log levels
        :param logger:
        :param level:
        :return:
        '''
        url = f"/Loggers"
        return self._rest.GET(url).content
