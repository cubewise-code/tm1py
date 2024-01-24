# -*- coding: utf-8 -*-
import json
from collections.abc import Iterable
from datetime import datetime
from enum import Enum
from typing import Dict, Optional, List
from typing import Dict, Optional
from warnings import warn
import pytz

from requests import Response

from TM1py.Services.AuditLogService import AuditLogService
from TM1py.Services.ConfigurationService import ConfigurationService
from TM1py.Services.MessageLogService import MessageLogService
from TM1py.Services.ObjectService import ObjectService
from TM1py.Services.RestService import RestService
from TM1py.Utils.Utils import require_admin, require_ops_admin, require_data_admin, deprecated_in_version
from TM1py.Services.TransactionLogService import TransactionLogService
from TM1py.Utils.Utils import require_admin, require_version, \
    deprecated_in_version
from TM1py.Utils.Utils import require_data_admin, \
    require_ops_admin


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
        self.audit_logs = AuditLogService(rest)

    def initialize_transaction_log_delta_requests(self, filter=None, **kwargs):
        self.transaction_logs.initialize_delta_requests(filter, **kwargs)

    def execute_transaction_log_delta_request(self, **kwargs) -> Dict:
        self.transaction_logs.execute_delta_request(**kwargs)

    def initialize_audit_log_delta_requests(self, filter=None, **kwargs):
        return self.audit_logs.initialize_audit_log_delta_requests(filter, **kwargs)

    def execute_audit_log_delta_request(self, **kwargs) -> Dict:
        return self.audit_logs.execute_delta_request(**kwargs)

    def initialize_message_log_delta_requests(self, filter=None, **kwargs):
        return self.message_logs.initialize_delta_requests(filter, **kwargs)

    def execute_message_log_delta_request(self, **kwargs) -> Dict:
        return self.message_logs.execute_delta_request(**kwargs)

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

        return self.message_logs.get_entries(reverse=reverse,
                                             since=since,
                                             until=until,
                                             top=top,
                                             logger=logger,
                                             level=level,
                                             msg_contains=msg_contains,
                                             msg_contains_operator=msg_contains_operator,
                                             **kwargs)

    @require_data_admin
    def write_to_message_log(self, level: str, message: str, **kwargs) -> None:
        """
        :param level: string, FATAL, ERROR, WARN, INFO, DEBUG
        :param message: string
        :return:
        """

        return self.message_logs.create_entry(level=level,
                                              message=message,
                                              **kwargs)

    @staticmethod
    def utc_localize_time(timestamp):
        timestamp = pytz.utc.localize(timestamp)
        timestamp_utc = timestamp.astimezone(pytz.utc)
        return timestamp_utc

    @deprecated_in_version(version="12.0.0")
    @require_admin
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
        return self.audit_logs.get_entries(user=user,
                                           object_type=object_type,
                                           object_name=object_name,
                                           since=since,
                                           until=until,
                                           top=top,
                                           **kwargs)

    @require_ops_admin
    @deprecated_in_version(version="12.0.0")
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

    def get_admin_host(self, **kwargs) -> str:
        return self.configuration.get_admin_host()

    def get_data_directory(self, **kwargs) -> str:
        return self.configuration.get_data_directory()

    def get_configuration(self, **kwargs) -> Dict:
        return self.configuration.get()

    @require_ops_admin
    def get_static_configuration(self, **kwargs) -> Dict:
        return self.configuration.get_static()

    @require_ops_admin
    def get_active_configuration(self, **kwargs) -> Dict:
        """ Read effective(!) TM1 config settings as dictionary from TM1 Server

        :return: config as dictionary
        """
        return self.configuration.get_active()

    def get_api_metadata(self):
        """ Read effective(!) TM1 config settings as dictionary from TM1 Server

        :return: config as dictionary
        """
        return self._rest.get_api_metadata()

    @require_ops_admin
    def update_static_configuration(self, configuration: Dict) -> Response:
        """ Update the .cfg file and triggers TM1 to re-read the file.

        :param configuration:
        :return: Response
        """
        return self.configuration.update_static_configuration(configuration)

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

