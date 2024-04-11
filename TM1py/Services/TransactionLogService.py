from warnings import warn

from datetime import datetime
from typing import Dict

from TM1py.Services.ObjectService import ObjectService
from TM1py.Services.RestService import RestService
from TM1py.Utils import verify_version, deprecated_in_version, odata_track_changes_header, require_data_admin, format_url, utc_localize_time


class TransactionLogService(ObjectService):

    def __init__(self, rest: RestService):
        super().__init__(rest)
        if verify_version(required_version="12.0.0", version=rest.version):
            # warn only due to use in Monitoring Service
            warn("Transaction Logs are not available in this version of TM1, removed as of 12.0.0", DeprecationWarning,
                 2)
        self.last_delta_request = None

    @deprecated_in_version(version="12.0.0")
    @odata_track_changes_header
    def initialize_delta_requests(self, filter=None, **kwargs):
        url = "/TailTransactionLog()"
        if filter:
            url += "?$filter={}".format(filter)
        response = self._rest.GET(url=url, **kwargs)
        # Read the next delta-request-url from the response
        self.last_delta_request = response.text[response.text.rfind(
            "TransactionLogEntries/!delta('"):-2]

    @deprecated_in_version(version="12.0.0")
    @odata_track_changes_header
    def execute_delta_request(self, **kwargs) -> Dict:
        response = self._rest.GET(
            url="/" + self.last_delta_request, **kwargs)
        self.last_delta_request = response.text[response.text.rfind(
            "TransactionLogEntries/!delta('"):-2]
        return response.json()['value']

    @deprecated_in_version(version="12.0.0")
    @require_data_admin
    def get_entries(self, reverse: bool = True, user: str = None, cube: str = None,
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
                    since = utc_localize_time(since)
                log_filters.append(format_url(
                    "TimeStamp ge {}", since.strftime("%Y-%m-%dT%H:%M:%SZ")))
            if until:
                # If until doesn't have tz information, UTC is assumed
                if not until.tzinfo:
                    until = utc_localize_time(until)
                log_filters.append(format_url(
                    "TimeStamp le {}", until.strftime("%Y-%m-%dT%H:%M:%SZ")))
            url += "&$filter={}".format(" and ".join(log_filters))
        # top limit
        if top:
            url += '&$top={}'.format(top)
        response = self._rest.GET(url, **kwargs)
        return response.json()['value']
