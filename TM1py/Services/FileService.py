# -*- coding: utf-8 -*-
import json
import warnings
from pathlib import Path
from typing import List, Iterable, Union

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

    def get_all_names(self, path: Union[str, Path] = "", **kwargs) -> List[str]:
        """ return list of blob file names

        :param path: path to folder. When empty searches in root
        """
        path = Path(path)
        url = self._construct_content_url(path, exclude_path_end=False, extension="Contents")

        response = self._rest.GET(url, **kwargs).content
        return [file['Name'] for file in json.loads(response)['value']]

    def get(self, file_name: str, **kwargs) -> bytes:
        """ Get file

        :param file_name: file name in root or path to file
        """
        url = self._construct_content_url(
            path=Path(file_name),
            exclude_path_end=False,
            extension="Content")

        return self._rest.GET(url, **kwargs).content

    def _create_folder(self, folder_name: Union[str, Path], **kwargs):
        """ Create folder

        Can only create 1 folder at a time.
        To create nested folder structures it must be called in an iterative fashion.

        :param folder_name: path to folder (e.g. folderA, folderA/folderB)
        """
        path = Path(folder_name)
        url = self._construct_content_url(path, exclude_path_end=True, extension="Contents")

        body = {
            "@odata.type": "#ibm.tm1.api.v1.Folder",
            "Name": folder_name.name
        }
        self._rest.POST(url, json.dumps(body), **kwargs)

    def _construct_content_url(self, path: Path, exclude_path_end: bool = True, extension: str = 'Contents') -> str:
        """ Dynamically construct URL to use in FileService functions

        :param path: file name in root or path to file
        :param exclude_path_end: Some functions require complete URL to file (e.g. exists),
        while others require URL to parent folder (e.g., create)
        :param extension: Final piece of the URL e.g. ('Contents', 'Content', or 'Contents?$select=Name')

        """
        parent_folders = {
            f"level{str(n).zfill(4)}": parent
            for n, parent
            in enumerate(path.parts[:-1] if exclude_path_end else path.parts, 1)
        }

        url = format_url(
            "".join([
                "/Contents('{version_content_path}')/",
                "/".join(f"Contents('{{{folder}}}')" for folder in parent_folders) + "/" if parent_folders else "",
                extension
            ]),
            version_content_path=self.version_content_path,
            **parent_folders)

        return url.rstrip("/")

    def create(self, file_name: Union[str, Path], file_content: bytes, **kwargs):
        """ Create file

        Folders in file_name (e.g. folderA/folderB/file.csv) will be created implicitly

        :param file_name: file name in root or path to file
        :param file_content: file_content as bytes or BytesIO
        """
        path = Path(file_name)

        # Create folder structure iteratively
        if path.parents:
            folder_path = Path()
            for parent_folder in path.parts[:-1]:
                folder_path = folder_path.joinpath(parent_folder)
                self._create_folder(folder_name=folder_path)

        url = self._construct_content_url(path, exclude_path_end=True, extension="Contents")
        body = {
            "@odata.type": "#ibm.tm1.api.v1.Document",
            "ID": path.name,
            "Name": path.name
        }
        self._rest.POST(url, json.dumps(body), **kwargs)

        url = self._construct_content_url(path, exclude_path_end=False, extension="Content")
        return self._rest.PUT(
            url=url,
            data=file_content,
            headers=self.binary_http_header,
            **kwargs)

    def update(self, file_name: Union[str, Path], file_content: bytes, **kwargs):
        """ Update existing file

        :param file_name: file name in root or path to file
        :param file_content: file_content as bytes or BytesIO
        """
        url = self._construct_content_url(
            path=Path(file_name),
            exclude_path_end=False,
            extension="Content")

        return self._rest.PUT(
            url=url,
            data=file_content,
            headers=self.binary_http_header,
            **kwargs)

    def update_or_create(self, file_name: Union[str, Path], file_content: bytes, **kwargs):
        """ Create file or update file if it already exists

        :param file_name: file name in root or path to file
        :param file_content: file_content as bytes or BytesIO
        """
        if self.exists(file_name, **kwargs):
            return self.update(file_name, file_content, **kwargs)

        return self.create(file_name, file_content, **kwargs)

    def exists(self, file_name: Union[str, Path], **kwargs):
        """ Check if file exists

        :param file_name: file name in root or path to file
        """
        url = self._construct_content_url(
            path=Path(file_name),
            exclude_path_end=False,
            extension="")

        return self._exists(url, **kwargs)

    def delete(self, file_name: Union[str, Path], **kwargs):
        """ Delete file

        :param file_name: file name in root or path to file
        """
        url = self._construct_content_url(
            path=Path(file_name),
            exclude_path_end=False,
            extension="")

        return self._rest.DELETE(url, **kwargs)

    def search_string_in_name(self, name_startswith: str = None, name_contains: Iterable = None,
                              name_contains_operator: str = 'and', path: Union[Path, str] = "",
                              **kwargs) -> List[str]:
        """ Return list of blob files that match search critera

        :param name_startswith: str, file name begins with (case insensitive)
        :param name_contains: iterable, found anywhere in name (case insensitive)
        :param name_contains_operator: 'and' or 'or'
        :param path: search in given path or root
        """

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

        url = self._construct_content_url(
            path=Path(path),
            exclude_path_end=False,
            extension="Contents?$select=Name&$filter={}".format(f" and ".join(name_filters)))
        response = self._rest.GET(url, **kwargs).content

        return list(file['Name'] for file in json.loads(response)['value'])
