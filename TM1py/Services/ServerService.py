# -*- coding: utf-8 -*-

import functools
import json
from collections.abc import Iterable
from datetime import datetime
from enum import Enum
from typing import Dict, Optional, List

import pytz
from requests import Response

from TM1py.Objects.Process import Process
from TM1py.Services.ObjectService import ObjectService
from TM1py.Services.RestService import RestService
from TM1py.Utils import format_url
from TM1py.Utils.Utils import CaseAndSpaceInsensitiveDict, CaseAndSpaceInsensitiveSet, require_data_admin, \
    require_ops_admin, require_version, decohints, deprecated_in_version, require_admin


class LogLevel(Enum):
    FATAL = "fatal"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    DEBUG = "debug"
    OFF = "off"


@decohints
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

    @deprecated_in_version(version="12.0.0")
    @odata_track_changes_header
    def initialize_transaction_log_delta_requests(self, filter=None, **kwargs):
        url = "/TailTransactionLog()"
        if filter:
            url += "?$filter={}".format(filter)
        response = self._rest.GET(url=url, **kwargs)
        # Read the next delta-request-url from the response
        self.tlog_last_delta_request = response.text[response.text.rfind(
            "TransactionLogEntries/!delta('"):-2]

    @deprecated_in_version(version="12.0.0")
    @odata_track_changes_header
    def execute_transaction_log_delta_request(self, **kwargs) -> Dict:
        response = self._rest.GET(
            url="/" + self.tlog_last_delta_request, **kwargs)
        self.tlog_last_delta_request = response.text[response.text.rfind(
            "TransactionLogEntries/!delta('"):-2]
        return response.json()['value']

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

    @deprecated_in_version(version="12.0.0")
    @odata_track_changes_header
    def initialize_message_log_delta_requests(self, filter=None, **kwargs):
        url = "/TailMessageLog()"
        if filter:
            url += "?$filter={}".format(filter)
        response = self._rest.GET(url=url, **kwargs)
        # Read the next delta-request-url from the response
        self.mlog_last_delta_request = response.text[response.text.rfind(
            "MessageLogEntries/!delta('"):-2]

    @deprecated_in_version(version="12.0.0")
    @odata_track_changes_header
    def execute_message_log_delta_request(self, **kwargs) -> Dict:
        response = self._rest.GET(
            url="/" + self.mlog_last_delta_request, **kwargs)
        self.mlog_last_delta_request = response.text[response.text.rfind(
            "MessageLogEntries/!delta('"):-2]
        return response.json()['value']

    @deprecated_in_version(version="12.0.0")
    @require_ops_admin
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
            raise ValueError(
                "'msg_contains_operator' must be either 'AND' or 'OR'")

        reverse = 'desc' if reverse else 'asc'
        url = '/MessageLogEntries?$orderby=TimeStamp {}'.format(reverse)

        if since or until or logger or level or msg_contains:
            log_filters = []

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
                    log_filters.append(format_url(
                        "contains(toupper(Message),toupper('{}'))", msg_contains))
                else:
                    msg_filters = [format_url("contains(toupper(Message),toupper('{}'))", wildcard)
                                   for wildcard in msg_contains]
                    log_filters.append("({})".format(
                        f" {msg_contains_operator} ".join(msg_filters)))

            url += "&$filter={}".format(" and ".join(log_filters))

        if top:
            url += '&$top={}'.format(top)

        response = self._rest.GET(url, **kwargs)
        return response.json()['value']

    @require_data_admin
    def write_to_message_log(self, level: str, message: str, **kwargs) -> None:
        """
        :param level: string, FATAL, ERROR, WARN, INFO, DEBUG
        :param message: string
        :return:
        """

        valid_levels = CaseAndSpaceInsensitiveSet(
            {'FATAL', 'ERROR', 'WARN', 'INFO', 'DEBUG'})
        if level not in valid_levels:
            raise ValueError(f"Invalid level: '{level}'")

        from TM1py.Services import ProcessService
        process_service = ProcessService(self._rest)
        process = Process(
            name="", prolog_procedure="LogOutput('{}', '{}');".format(level, message))
        success, status, _ = process_service.execute_process_with_return(
            process, **kwargs)

        if not success:
            raise RuntimeError(
                f"Failed to write to TM1 Message Log through unbound process. Status: '{status}'")

    @staticmethod
    def utc_localize_time(timestamp):
        timestamp = pytz.utc.localize(timestamp)
        timestamp_utc = timestamp.astimezone(pytz.utc)
        return timestamp_utc

    @deprecated_in_version(version="12.0.0")
    @require_data_admin
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
        if element_position_filter:
            raise NotImplementedError("Feature expected in upcoming releases of TM1, TM1py")

        reverse = 'desc' if reverse else 'asc'
        url = '/TransactionLogEntries?$orderby=TimeStamp {} '.format(reverse)

        # filter on user, cube, time and elements
        if any([user, cube, since, until, element_tuple_filter, element_position_filter]):
            log_filters = []
            if user:
                log_filters.append(format_url("User eq '{}'", user))
            if cube:
                log_filters.append(format_url("Cube eq '{}'", cube))
            if element_tuple_filter:
                log_filters.append(format_url(
                    "Tuple/any(e: {})".format(" or ".join([f"e {v} '{k}'" for k, v in element_tuple_filter.items()]))))
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

    @require_data_admin
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

    @require_ops_admin
    @deprecated_in_version(version="12.0.0")
    def get_last_process_message_from_messagelog(self, process_name: str, **kwargs) -> Optional[str]:
        """ Get the latest message log entry for a process

            :param process_name: name of the process
            :return: String - the message, for instance: "Ausführung normal beendet, verstrichene Zeit 0.03  Sekunden"
        """
        url = format_url(
            "/MessageLog()?$orderby='TimeStamp'&$filter=Logger eq 'TM1.Process' and contains(Message, '{}')",
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
        url = '/Configuration/ServerName/$value'
        return self._rest.GET(url, **kwargs).text

    def get_product_version(self, **kwargs) -> str:
        """ Ask TM1 Server for its version

        :Returns:
            String, the version
        """
        url = '/Configuration/ProductVersion/$value'
        return self._rest.GET(url, **kwargs).text

    @deprecated_in_version(version="12.0.0")
    def get_admin_host(self, **kwargs) -> str:
        url = '/Configuration/AdminHost/$value'
        return self._rest.GET(url, **kwargs).text

    @deprecated_in_version(version="12.0.0")
    def get_data_directory(self, **kwargs) -> str:
        url = '/Configuration/DataBaseDirectory/$value'
        return self._rest.GET(url, **kwargs).text

    def get_configuration(self, **kwargs) -> Dict:
        url = '/Configuration'
        config = self._rest.GET(url, **kwargs).json()
        del config["@odata.context"]
        return config

    @require_ops_admin
    def get_static_configuration(self, **kwargs) -> Dict:
        """ Read TM1 config settings as dictionary from TM1 Server

        :return: config as dictionary
        """
        url = '/StaticConfiguration'
        config = self._rest.GET(url, **kwargs).json()
        del config["@odata.context"]
        return config

    @require_ops_admin
    def get_active_configuration(self, **kwargs) -> Dict:
        """ Read effective(!) TM1 config settings as dictionary from TM1 Server

        :return: config as dictionary
        """
        url = '/ActiveConfiguration'
        config = self._rest.GET(url, **kwargs).json()
        del config["@odata.context"]
        return config

    def get_api_metadata(self, **kwargs):
        """ Read effective(!) TM1 config settings as dictionary from TM1 Server

        :return: config as dictionary
        """
        url = '/$metadata'
        metadata = self._rest.GET(url, **kwargs).content.decode("utf-8")
        return json.loads(metadata)

    @require_ops_admin
    def update_static_configuration(self, configuration: Dict) -> Response:
        """ Update the .cfg file and triggers TM1 to re-read the file.

        :param configuration:
        :return: Response
        """
        url = '/StaticConfiguration'
        return self._rest.PATCH(url, json.dumps(configuration))

    @deprecated_in_version(version="12.0.0")
    @require_data_admin
    def save_data(self, **kwargs) -> Response:
        from TM1py.Services import ProcessService
        ti = "SaveDataAll;"
        process_service = ProcessService(self._rest)
        return process_service.execute_ti_code(ti, **kwargs)

    @require_data_admin
    def delete_persistent_feeders(self, **kwargs) -> Response:
        from TM1py.Services import ProcessService
        ti = "DeleteAllPersistentFeeders;"
        process_service = ProcessService(self._rest)
        return process_service.execute_ti_code(ti, **kwargs)

    @require_ops_admin
    def start_performance_monitor(self):
        config = {
            "Administration": {"PerformanceMonitorOn": True}
        }
        self.update_static_configuration(config)

    @require_ops_admin
    def stop_performance_monitor(self):
        config = {
            "Administration": {"PerformanceMonitorOn": False}
        }
        self.update_static_configuration(config)

    @require_ops_admin
    def activate_audit_log(self):
        config = {'Administration': {'AuditLog': {'Enable': True}}}
        self.update_static_configuration(config)

    @require_ops_admin
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

    @require_ops_admin
    def logger_get_all(self, **kwargs) -> Dict:
        url = f"/Loggers"
        loggers = self._rest.GET(url, **kwargs).json()
        return loggers['value']

    @require_ops_admin
    def logger_get_all_names(self, **kwargs) -> List[str]:
        url = f"/Loggers"
        loggers = self._rest.GET(url, **kwargs).json()
        return [logger['Name'] for logger in loggers['value']]

    @require_ops_admin
    def logger_get(self, logger: str, **kwargs) -> Dict:
        """ Get level for specified logger

        :param logger: string name of logger
        :return: Dict of logger and level
        """
        url = format_url("/Loggers('{}')", logger)
        logger = self._rest.GET(url, **kwargs).json()
        del logger["@odata.context"]
        return logger

    @require_ops_admin
    def logger_search(self, wildcard: str='', level: str='', **kwargs) -> Dict:
        """ Searches logger names by wildcard or by level. Combining wildcard and level will filter via AND and not OR

        :param wildcard: string to match in logger name
        :param level: string e.g. FATAL, ERROR, WARNING, INFO, DEBUG, UNKOWN, OFF
        :return: Dict of matching loggers and levels
        """
        url = f"/Loggers"

        logger_filters = []

        if level:
            level_dict = CaseAndSpaceInsensitiveDict(
                {'FATAL': 0, 'ERROR': 1, 'WARNING': 2, 'INFO': 3, 'DEBUG': 4, 'UNKNOWN': 5, 'OFF': 6}
            )
            level_index = level_dict.get(level)
            if level_index:
                logger_filters.append("Level eq {}".format(level_index))

        if wildcard:
            logger_filters.append("contains(tolower(Name), tolower('{}'))".format(wildcard))

        url += "?$filter={}".format(" and ".join(logger_filters))

        loggers = self._rest.GET(url, **kwargs).json()
        return loggers['value']

    @require_ops_admin
    def logger_exists(self, logger: str, **kwargs) -> bool:
        """ Test if logger exists
        :param logger: string name of logger
        :return: bool
        """
        url = format_url("/Loggers('{}')", logger)
        return self._exists(url, **kwargs)

    @require_ops_admin
    def logger_set_level(self, logger: str, level: str, **kwargs):
        """ Set logger level
        :param logger: string name of logger
        :param level: string e.g. FATAL, ERROR, WARNING, INFO, DEBUG, UNKOWN, OFF
        :return: response
        """
        url = format_url("/Loggers('{}')", logger)

        if not self.logger_exists(logger=logger, **kwargs):
            raise ValueError('{} is not a valid logger'.format(logger))
        
        level_dict = CaseAndSpaceInsensitiveDict(
            {'FATAL': 0, 'ERROR': 1, 'WARNING': 2, 'INFO': 3, 'DEBUG': 4, 'UNKNOWN': 5, 'OFF': 6}
        )
        level_index = level_dict.get(level)
        if level_index:
            logger = {'Level': level_index}
        else:
            raise ValueError('{} is not a valid level'.format(level))
        
        return self._rest.PATCH(url, json.dumps(logger))

