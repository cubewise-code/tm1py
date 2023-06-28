import json
import requests
from requests.auth import HTTPBasicAuth


class ManageService:
    """ Manage service to interact with the manage endpoint.
    The manage endpoint uses basic auth using the root client and secret

    """

    def __init__(self, domain, root_client, root_secret):
        self._domain = domain
        self._root_client = root_client
        self._root_secret = root_secret
        self._auth_header = HTTPBasicAuth(self._root_client, self._root_secret)
        self._root_url = f"{self._domain}/manage/v1"

    def get_instances(self, **kwargs):
        url = f"{self._root_url}/Instances"
        response = requests.get(url=url, auth=self._auth_header)
        return json.loads(response.content).get('value')

    def get_instance(self, instance_name, **kwargs):
        url = f"{self._root_url}/Instances('{instance_name}')"
        response = requests.get(url=url, auth=self._auth_header)
        return json.loads(response.content)

    def create_instance(self, instance_name, **kwargs):
        url = f"{self._root_url}/Instances"
        payload = {"Name": instance_name}
        response = requests.post(url=url, json=payload, auth=self._auth_header)
        return response

    def delete_instance(self, instance_name, **kwargs):
        url = f"{self._root_url}/Instances('{instance_name}')"
        response = requests.delete(url=url, auth=self._auth_header)
        return response

    def instance_exists(self, instance_name, **kwargs):
        url = f"{self._root_url}/Instances('{instance_name}')"
        response = requests.get(url=url, auth=self._auth_header)
        if response.ok:
            return True
        else:
            return False

    def get_databases(self, instance_name, **kwargs):
        url = f"{self._root_url}/Instances('{instance_name}')/Databases"
        response = requests.get(url=url, auth=self._auth_header)
        return json.loads(response.content).get('value')

    def get_database(self, instance_name, database_name, **kwargs):
        url = f"{self._root_url}/Instances('{instance_name}')/Databases('{database_name}')"
        response = requests.get(url=url, auth=self._auth_header)
        return json.loads(response.content)

    def create_database(self,
                        instance_name,
                        database_name,
                        number_replicas,
                        product_version="12.0.0-alpha.1",
                        cpu_requests="1000m",
                        cpu_limits="2000m",
                        memory_requests="1G",
                        memory_limits="2G",
                        storage_size="20Gi",
                        **kwargs):

        url = f"{self._root_url}/Instances('{instance_name}')/Databases"

        payload = {"Name": database_name,
                   "Replicas": number_replicas,
                   "ProductVersion": product_version,
                   "Resources": {
                       "Replica": {
                           "CPU": {
                               "Requests": cpu_requests,
                               "Limits": cpu_limits
                           },
                           "Memory": {
                               "Requests": memory_requests,
                               "Limits": memory_limits
                           }
                       },
                       "Storage": {
                           "Size": storage_size
                       }
                   }
                   }
        response = requests.post(url=url, json=payload, auth=self._auth_header)

        return response

    def delete_database(self, instance_name, database_name, **kwargs):
        url = f"{self._root_url}/Instances('{instance_name}')/Databases('{database_name}')"
        response = requests.delete(url=url, auth=self._auth_header)
        return response

    def database_exists(self, instance_name, database_name, **kwargs):
        url = f"{self._root_url}/Instances('{instance_name}')/Databases('{database_name}')"
        response = requests.get(url=url, auth=self._auth_header)
        if response.ok:
            return True
        else:
            return False

    def get_applications(self, instance_name, **kwargs):
        url = f"{self._root_url}/Instances('{instance_name}')/Applications"
        response = requests.get(url=url, auth=self._auth_header)
        return json.loads(response.content)

    def create_application(self, instance_name, application_name, **kwargs):
        url = f"{self._root_url}/Instances('{instance_name}')/Applications"
        payload = {"Name": application_name}
        response = requests.post(url=url, json=payload, auth=self._auth_header)
        response_json = json.loads(response.content)
        return response_json['ClientID'], response_json['ClientSecret']




