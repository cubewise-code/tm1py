# -*- coding: utf-8 -*-
import json

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

        url = format_url(
            "/Contents('{version_content_path}')/Contents?$select=Name",
            version_content_path=self.version_content_path)

        return self._rest.GET(url, **kwargs).content

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

        return self._rest.PUT(url, file_content, headers=self.BINARY_HTTP_HEADER, **kwargs)

    def update(self, file_name: str, file_content: bytes, **kwargs):
        url = format_url(
            "/Contents('{version_content_path}')/Contents('{name}')/Content",
            name=file_name,
            version_content_path=self.version_content_path)

        return self._rest.PUT(url, file_content, headers=self.BINARY_HTTP_HEADER, **kwargs)

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
