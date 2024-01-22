import pytz
from warnings import warn

from datetime import datetime
from typing import Dict, Iterable, Optional

from TM1py.Objects.Process import Process
from TM1py import ObjectService, RestService
from TM1py.Utils import verify_version, deprecated_in_version, odata_track_changes_header, require_admin, format_url, \
    CaseAndSpaceInsensitiveDict, CaseAndSpaceInsensitiveSet


class MessageLogService(ObjectService):

    def __init__(self, rest: RestService):
        if verify_version(required_version="12.0.0", version=self.version):
            # warn only due to use in Monitoring Service
            warn("Message Logs are not available in this version of TM1, removed as of 12.0.0", DeprecationWarning,
                 2)

        super().__init__(rest)
        self.last_delta_request = None

    @deprecated_in_version(version="12.0.0")
    @odata_track_changes_header
    def initialize_delta_requests(self, filter=None, **kwargs):
        url = "/TailMessageLog()"
        if filter:
            url += "?$filter={}".format(filter)
        response = self._rest.GET(url=url, **kwargs)
        # Read the next delta-request-url from the response
        self.last_delta_request = response.text[response.text.rfind(
            "MessageLogEntries/!delta('"):-2]

    @deprecated_in_version(version="12.0.0")
    @odata_track_changes_header
    def execute_delta_request(self, **kwargs) -> Dict:
        response = self._rest.GET(
            url="/" + self.last_delta_request, **kwargs)
        self.last_delta_request = response.text[response.text.rfind(
            "MessageLogEntries/!delta('"):-2]
        return response.json()['value']

    @deprecated_in_version(version="12.0.0")
    @require_admin
    def get_entries(self, reverse: bool = True, since: datetime = None,
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

    @require_admin
    def create_entry(self, level: str, message: str, **kwargs) -> None:
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

    @require_admin
    @deprecated_in_version(version="12.0.0")
    def get_last_process_message(self, process_name: str, **kwargs) -> Optional[str]:
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