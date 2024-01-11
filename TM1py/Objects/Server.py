# -*- coding: utf-8 -*-
from typing import Dict


class Server:
    """ Abstraction of the TM1 Server

        :Notes:
            contains the information you get from http://localhost:5895/Servers
            no methods so far
    """
    def __init__(self, server_as_dict: Dict):
        self.name = server_as_dict['Name']
        self.ip_address = server_as_dict['IPAddress']
        self.ip_v6_address = server_as_dict['IPv6Address']
        self.port_number = server_as_dict['PortNumber']
        self.client_message_port_number = server_as_dict['ClientMessagePortNumber']
        self.http_port_number = server_as_dict['HTTPPortNumber']
        self.using_ssl = server_as_dict['UsingSSL']
        self.accepting_clients = server_as_dict['AcceptingClients']
        self.self_registered = server_as_dict['SelfRegistered'] 
        self.host = server_as_dict['Host'] 
        self.is_local = server_as_dict['IsLocal'] 
        self.ssl_certificate_id = server_as_dict['SSLCertificateID'] 
        self.ssl_certificate_authority = server_as_dict['SSLCertificateAuthority'] 
        self.ssl_certificate_revocation_list = server_as_dict['SSLCertificateRevocationList'] 
        self.client_export_ssl_server_keyid = server_as_dict['ClientExportSSLSvrKeyID'] 
        self.client_export_ssl_server_cert = server_as_dict['ClientExportSSLSvrCert'] 
        self.last_updated = server_as_dict['LastUpdated']