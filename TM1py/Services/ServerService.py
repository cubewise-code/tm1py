# -*- coding: utf-8 -*-

import json


from TM1py.Services.ObjectService import ObjectService


class ServerService(ObjectService):
    """ Service to query common information from the TM1 Server
    
    """
    def __init__(self, rest):
        super().__init__(rest)

    def get_message_log_entries(self, reverse=True, top=None):
        reverse = 'true' if reverse else 'false'
        request = '/api/v1/MessageLog(Reverse={})'.format(reverse)
        if top:
            request += '?$top={}'.format(top)
        response = self._rest.GET(request, '')
        return json.loads(response)['value']

    def get_transaction_log_entries(self, reverse=True, user=None, cube=None, since=None, top=None):
        """
        
        :param reverse: 
        :param user: 
        :param cube: 
        :param since: of type datetime
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
                log_filters.append("TimeStamp ge datetimeoffset'{}'".format(since.isoformat()))
            request += "&$filter={}".format(" and ".join(log_filters))
        # top limit
        if top:
            request += '&$top={}'.format(top)
        response = self._rest.GET(request, '')
        return json.loads(response)['value']

    def get_last_process_message_from_messagelog(self, process_name):
        """ Get the latest messagelog entry for a process

            :param process_name: name of the process
            :return: String - the message, for instance: "Ausführung normal beendet, verstrichene Zeit 0.03  Sekunden"
        """
        request = "/api/v1/MessageLog()?$orderby='TimeStamp'&$filter=Logger eq 'TM1.Process' " \
                  "and contains( Message, '" + process_name + "')"
        response = self._rest.GET(request=request)
        response_as_list = json.loads(response)['value']
        if len(response_as_list) > 0:
            message_log_entry = response_as_list[0]
            return message_log_entry['Message']

    def get_server_name(self):
        """ Ask TM1 Server for its name

        :Returns:
            String, the server name
        """
        request = '/api/v1/Configuration/ServerName/$value'
        return self._rest.GET(request, '')

    def get_product_version(self):
        """ Ask TM1 Server for its version

        :Returns:
            String, the version
        """
        request = '/api/v1/Configuration/ProductVersion/$value'
        return self._rest.GET(request, '')
