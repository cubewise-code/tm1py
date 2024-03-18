# -*- coding: utf-8 -*-
import json
import warnings
from typing import List, Iterable

from TM1py.Services import RestService
from TM1py.Services.ObjectService import ObjectService
from TM1py.Utils import format_url
from TM1py.Utils.Utils import verify_version


class FileService(ObjectService):

    def __init__(self, tm1_rest: RestService):
        """

        :param tm1_rest:
        """
        super().__init__(tm1_rest)
        self._rest = tm1_rest
        if verify_version(required_version="12", version=self.version):
            self.version_content_path = 'Files'
        else:
            self.version_content_path = 'Blobs'

    def get_names(self, **kwargs) -> bytes:
        warnings.warn(
            f"Function get_names will be deprecated. Use get_all_names instead",
            DeprecationWarning,
            stacklevel=2)

        url = format_url(
            "/Contents('{version_content_path}')/Contents?$select=Name",
            version_content_path=self.version_content_path)

        return self._rest.GET(url, **kwargs).content

    def get_all_names(self, **kwargs) -> List[str]:
        """ return list of blob file names

        """

        url = format_url(
            "/Contents('{version_content_path}')/Contents?$select=Name",
            version_content_path=self.version_content_path)

        response = self._rest.GET(url, **kwargs).content

        return [file['Name'] for file in json.loads(response)['value']]

    def get(self, file_name: str, **kwargs) -> bytes:

        url = format_url(
            "/Contents('{version_content_path}')/Contents('{name}')/Content",
            name=file_name,
            version_content_path=self.version_content_path)

        return self._rest.GET(url, **kwargs).content

    def create(self, file_name: str, file_content: bytes, **kwargs):
        url = format_url(
            "/Contents('{version_content_path}')/Contents",
            version_content_path=self.version_content_path)
        body = {
            "@odata.type": "#ibm.tm1.api.v1.Document",
            "ID": file_name,
            "Name": file_name
        }
        self._rest.POST(url, json.dumps(body), **kwargs)

        url = format_url(
            "/Contents('{version_content_path}')/Contents('{name}')/Content",
            name=file_name,
            version_content_path=self.version_content_path)

        return self._rest.PUT(url, file_content, headers=self.binary_http_header, **kwargs)

    def update(self, file_name: str, file_content: bytes, **kwargs):
        url = format_url(
            "/Contents('{version_content_path}')/Contents('{name}')/Content",
            name=file_name,
            version_content_path=self.version_content_path)

        return self._rest.PUT(url, file_content, headers=self.binary_http_header, **kwargs)

    def update_or_create(self, file_name: str, file_content: bytes, **kwargs):
        if self.exists(file_name, **kwargs):
            return self.update(file_name, file_content, **kwargs)

        return self.create(file_name, file_content, **kwargs)

    def exists(self, file_name: str, **kwargs):
        url = format_url(
            "/Contents('{version_content_path}')/Contents('{name}')",
            name=file_name,
            version_content_path=self.version_content_path)

        return self._exists(url, **kwargs)

    def delete(self, file_name: str, **kwargs):
        url = format_url(
            "/Contents('{version_content_path}')/Contents('{name}')",
            name=file_name,
            version_content_path=self.version_content_path)

        return self._rest.DELETE(url, **kwargs)

    def search_string_in_name(self, name_startswith: str = None, name_contains: Iterable = None,
                              name_contains_operator: str = 'and', **kwargs) -> List[str]:
        """ Return list of blob files that match search critera

        :param name_startswith: str, file name begins with (case insensitive)
        :param name_contains: iterable, found anywhere in name (case insensitive)
        :param name_contains_operator: 'and' or 'or'
        """

        url = format_url(
            "/Contents('{version_content_path}')/Contents?$select=Name",
            version_content_path=self.version_content_path)

        name_contains_operator = name_contains_operator.strip().lower()
        if name_contains_operator not in ("and", "or"):
            raise ValueError("'name_contains_operator' must be either 'AND' or 'OR'")

        name_filters = []

        if name_startswith:
            name_filters.append(format_url("startswith(tolower(Name),tolower('{}'))", name_startswith))

        if name_contains:
            if isinstance(name_contains, str):
                name_filters.append(format_url("contains(tolower(Name),tolower('{}'))", name_contains))

            elif isinstance(name_contains, Iterable):
                name_contains_filters = [format_url("contains(tolower(Name),tolower('{}'))", wildcard)
                                         for wildcard in name_contains]
                name_filters.append("({})".format(f" {name_contains_operator} ".join(name_contains_filters)))

            else:
                raise ValueError("'name_contains' must be str or iterable")

        url += "&$filter={}".format(f" and ".join(name_filters))

        response = self._rest.GET(url, **kwargs).content

        return list(file['Name'] for file in json.loads(response)['value'])
