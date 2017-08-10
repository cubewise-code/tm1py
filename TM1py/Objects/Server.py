# -*- coding: utf-8 -*-

class Server:
    """ Abstraction of the TM1 Server

        :Notes:
            contains the information you get from http://localhost:5895/api/v1/Servers
            no methods so far
    """
    def __init__(self, server_as_dict):
        self.name = server_as_dict['Name']
        self.ip_address = server_as_dict['IPAddress']
        self.ip_v6_address = server_as_dict['IPv6Address']
        self.port_number = server_as_dict['PortNumber']
        self.client_message_port_number = server_as_dict['ClientMessagePortNumber']
        self.http_port_number = server_as_dict['HTTPPortNumber']
        self.using_ssl = server_as_dict['UsingSSL']
        self.accepting_clients = server_as_dict['AcceptingClients']

