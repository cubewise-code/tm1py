from warnings import warn

from datetime import datetime
from typing import Dict


from TM1py.Services.ObjectService import ObjectService
from TM1py.Services.RestService import RestService
from TM1py.Utils import (
    verify_version,
    deprecated_in_version,
    odata_track_changes_header,
    require_data_admin,
    format_url,
    require_version,
    require_ops_admin,
    utc_localize_time,
)
from TM1py.Services.ConfigurationService import ConfigurationService


class AuditLogService(ObjectService):

    def __init__(self, rest: RestService):
        super().__init__(rest)
        if verify_version(required_version="12.0.0", version=rest.version):
            # warn only due to use in Monitoring Service
            warn("Audit Logs are not available in this version of TM1, removed as of 12.0.0", DeprecationWarning, 2)
        self.last_delta_request = None
        self.configuration = ConfigurationService(rest)

    @deprecated_in_version(version="12.0.0")
    @odata_track_changes_header
    def initialize_delta_requests(self, filter=None, **kwargs):
        url = "/TailAuditLog()"
        if filter:
            url += "?$filter={}".format(filter)
        response = self._rest.GET(url=url, **kwargs)
        # Read the next delta-request-url from the response
        self.last_delta_request = response.text[response.text.rfind("AuditLogEntries/!delta('") : -2]

    @deprecated_in_version(version="12.0.0")
    @odata_track_changes_header
    def execute_delta_request(self, **kwargs) -> Dict:
        response = self._rest.GET(url="/" + self.last_delta_request, **kwargs)
        self.last_delta_request = response.text[response.text.rfind("AuditLogEntries/!delta('") : -2]
        return response.json()["value"]

    @require_data_admin
    @deprecated_in_version(version="12.0.0")
    @require_version(version="11.6")
    def get_entries(
        self,
        user: str = None,
        object_type: str = None,
        object_name: str = None,
        since: datetime = None,
        until: datetime = None,
        top: int = None,
        **kwargs,
    ) -> Dict:
        """
        :param user: UserName
        :param object_type: ObjectType
        :param object_name: ObjectName
        :param since: of type datetime. If it doesn't have tz information, UTC is assumed.
        :param until: of type datetime. If it doesn't have tz information, UTC is assumed.
        :param top: int
        :return:
        """

        url = "/AuditLogEntries?$expand=AuditDetails"
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
                    since = utc_localize_time(since)
                log_filters.append(format_url("TimeStamp ge {}", since.strftime("%Y-%m-%dT%H:%M:%SZ")))
            if until:
                # If until doesn't have tz information, UTC is assumed
                if not until.tzinfo:
                    until = utc_localize_time(until)
                log_filters.append(format_url("TimeStamp le {}", until.strftime("%Y-%m-%dT%H:%M:%SZ")))
            url += "&$filter={}".format(" and ".join(log_filters))
        # top limit
        if top:
            url += "&$top={}".format(top)
        response = self._rest.GET(url, **kwargs)
        return response.json()["value"]

    @require_ops_admin
    def activate(self):
        config = {"Administration": {"AuditLog": {"Enable": True}}}
        self.configuration.update_static(config)
