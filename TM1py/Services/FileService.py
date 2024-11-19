# -*- coding: utf-8 -*-
import concurrent.futures
import json
import time
import warnings
from io import BytesIO
from pathlib import Path
from typing import List, Iterable, Union, Tuple

from TM1py.Exceptions import TM1pyVersionException
from TM1py.Services import RestService
from TM1py.Services.ObjectService import ObjectService
from TM1py.Utils import format_url
from TM1py.Utils.Utils import verify_version, require_version


class FileService(ObjectService):
    SUBFOLDER_REQUIRED_VERSION = "12"
    MPU_REQUIRED_VERSION = "12"

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

    @require_version(version="11.4")
    def get_names(self, **kwargs) -> bytes:
        warnings.warn(
            "Function get_names will be deprecated. Use get_all_names instead",
            DeprecationWarning,
            stacklevel=2)

        url = format_url(
            "/Contents('{version_content_path}')/Contents?$select=Name",
            version_content_path=self.version_content_path)

        return self._rest.GET(url, **kwargs).content

    @require_version(version="11.4")
    def get_all_names(self, path: Union[str, Path] = "", **kwargs) -> List[str]:
        """ return list of blob file names

        :param path: path to folder. When empty searches in root
        """
        path = Path(path)
        url = self._construct_content_url(path, exclude_path_end=False, extension="Contents")

        response = self._rest.GET(url, **kwargs).content
        return [file['Name'] for file in json.loads(response)['value']]

    @require_version(version="11.4")
    def get(self, file_name: str, **kwargs) -> bytes:
        """ Get file

        :param file_name: file name in root or path to file
        """
        path = Path(file_name)
        self._check_subfolder_support(path=path, function="FileService.get")

        url = self._construct_content_url(
            path=path,
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

    def _check_subfolder_support(self, path: Path, function: str) -> None:
        if not len(path.parts) > 1:
            return

        if not verify_version(required_version=self.SUBFOLDER_REQUIRED_VERSION, version=self.version):
            raise TM1pyVersionException(
                function=function,
                required_version=self.SUBFOLDER_REQUIRED_VERSION,
                feature='Subfolder')

    def _check_mpu_support(self, function: str) -> None:
        if not verify_version(required_version=self.MPU_REQUIRED_VERSION, version=self.version):
            raise TM1pyVersionException(
                function=function,
                required_version=self.MPU_REQUIRED_VERSION,
                feature='MultiProcessUpload')

    def _upload_file_content(
            self,
            path: Path,
            file_content: Union[bytes, BytesIO],
            multi_part_upload: bool = None,
            max_mb_per_part: float = 200,
            max_workers: int = 1,
            **kwargs):
        """
        :param path: file name in root or path to file
        :param file_content: file_content as bytes or BytesIO
        :param multi_part_upload: boolean use multipart upload or not (only available from TM1 12 onwards)
        By default, multi_part_upload is used for TM1 v12 and not used for TM1 v11
        :param max_mb_per_part: max megabyte per part in multipart upload (only available from TM1 12 onwards)
        :param max_workers: max parallel workers for multipart upload (only available from TM1 12 onwards)
        """

        url = self._construct_content_url(path, exclude_path_end=False, extension="Content")

        # empty files must be created without MPU
        if self._file_content_is_empty(file_content):
            return self._upload_file_content_without_mpu(url, file_content, **kwargs)

        if multi_part_upload is None:
            multi_part_upload = self.version.startswith("12.")

        if multi_part_upload:
            return self._upload_file_content_with_mpu(url, file_content, max_mb_per_part, max_workers, **kwargs)

        return self._upload_file_content_without_mpu(url, file_content, **kwargs)

    def _upload_file_content_without_mpu(self, url, file_content, **kwargs):
        return self._rest.PUT(
            url=url,
            data=file_content,
            headers=self.binary_http_header,
            **kwargs)

    def _upload_file_content_with_mpu(self, content_url: str, file_content: Union[bytes, BytesIO], 
                                      max_mb_per_part: float, max_workers: int = 1, **kwargs):


        # Initiate multipart upload
        response = self._rest.POST(
            url=content_url + "/mpu.CreateMultipartUpload",
            data="{}",
            async_requests_mode=False,
            **kwargs)
        upload_id = response.json()['UploadID']

        # Split the file content into parts
        parts_to_upload = self._split_into_parts(
            data=file_content,
            max_chunk_size=int(max_mb_per_part * 1024 * 1024)
        )

        part_numbers_and_etags = []

        # helper function for uploading each part
        def upload_part_with_retry(index: int, data: bytes, retries: int = 3) -> Tuple[int, int, str]:
            for attempt in range(retries):
                try:
                    part_response = self._rest.POST(
                        url=content_url + f"/!uploads('{upload_id}')/Parts",
                        data=data,
                        headers={**self.binary_http_header, 'Accept': 'application/json,text/plain'},
                        async_requests_mode=False,
                        **kwargs)
                    return index, part_response.json()["PartNumber"], part_response.json()["@odata.etag"]
                except Exception as e:
                    if attempt < retries - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                    else:
                        raise e from None

        if max_workers > 1:
            # upload parts concurrently
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:

                futures = {
                    executor.submit(upload_part_with_retry, i, part, 3): i
                    for i, part
                    in enumerate(parts_to_upload)}

                for future in concurrent.futures.as_completed(futures):
                    part_index, part_number, odata_etag = future.result()
                    part_numbers_and_etags.append((part_index, part_number, odata_etag))

        else:
            # Sequential upload
            for i, bytes_part in enumerate(parts_to_upload):
                part_index, part_number, odata_etag = upload_part_with_retry(i, bytes_part)
                part_numbers_and_etags.append((part_index, part_number, odata_etag))

        # Complete the multipart upload
        self._rest.POST(
            url=content_url + f"/!uploads('{upload_id}')/mpu.Complete",
            data=json.dumps(
                {"Parts": [
                    {"PartNumber": part_number, "ETag": etag}
                    for _, part_number, etag in sorted(part_numbers_and_etags)
                ]}
            )
        )

    @require_version(version="11.4")
    def create(self, file_name: Union[str, Path], file_content: Union[bytes, BytesIO], multi_part_upload: bool = None,
               max_mb_per_part: float = 200, max_workers: int = 1, **kwargs):
        """ Create file

        Folders in file_name (e.g. folderA/folderB/file.csv) will be created implicitly

        :param file_name: file name in root or path to file
        :param file_content: file_content as bytes or BytesIO
        :param multi_part_upload: boolean use multipart upload or not (only available from TM1 12 onwards)
        By default, multi_part_upload is used for TM1 v12 and not used for TM1 v11
        :param max_mb_per_part: max megabyte per part in multipart upload (only available from TM1 12 onwards)
        :param max_workers: max parallel workers for multipart upload (only available from TM1 12 onwards)
        """
        path = Path(file_name)
        self._check_subfolder_support(path=path, function="FileService.create")
        if multi_part_upload:
            self._check_mpu_support(function="FileService.create")

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

        return self._upload_file_content(path, file_content, multi_part_upload, max_mb_per_part, max_workers, **kwargs)

    @require_version(version="11.4")
    def update(self, file_name: Union[str, Path], file_content: Union[bytes, BytesIO], multi_part_upload: bool = None,
               max_mb_per_part: float = 200, max_workers: int = 1, **kwargs):
        """ Update existing file

        :param file_name: file name in root or path to file
        :param file_content: file_content as bytes or BytesIO
        :param multi_part_upload: boolean use multipart upload or not (only available from TM1 12 onwards)
        By default, multi_part_upload is used for TM1 v12 and not used for TM1 v11
        :param max_mb_per_part: max megabyte per part in multipart upload (only available from TM1 12 onwards)
        :param max_workers: max parallel workers for multipart upload (only available from TM1 12 onwards)
        """
        path = Path(file_name)
        self._check_subfolder_support(path=path, function="FileService.update")
        if multi_part_upload:
            self._check_mpu_support(function="FileService.create")

        return self._upload_file_content(path, file_content, multi_part_upload, max_mb_per_part, max_workers, **kwargs)

    @require_version(version="11.4")
    def update_or_create(self, file_name: Union[str, Path], file_content: bytes, multi_part_upload: bool = None,
                         max_mb_per_part: float = 200, max_workers: int = 1, **kwargs):
        """ Create file or update file if it already exists

        :param file_name: file name in root or path to file
        :param file_content: file_content as bytes or BytesIO
        :param multi_part_upload: boolean use multipart upload or not (only available from TM1 12 onwards).
        By default, multi_part_upload is used for TM1 v12 and not used for TM1 v11
        :param max_mb_per_part: max megabyte per part in multipart upload (only available from TM1 12 onwards)
        :param max_workers: max parallel workers for multipart upload (only available from TM1 12 onwards)
        """
        if self.exists(file_name, **kwargs):
            return self.update(file_name, file_content, multi_part_upload, max_mb_per_part, max_workers, **kwargs)

        return self.create(file_name, file_content, multi_part_upload, max_mb_per_part, max_workers, **kwargs)

    @require_version(version="11.4")
    def exists(self, file_name: Union[str, Path], **kwargs):
        """ Check if file exists

        :param file_name: file name in root or path to file
        """
        url = self._construct_content_url(
            path=Path(file_name),
            exclude_path_end=False,
            extension="")

        return self._exists(url, **kwargs)

    @require_version(version="11.4")
    def delete(self, file_name: Union[str, Path], **kwargs):
        """ Delete file

        :param file_name: file name in root or path to file
        """
        path = Path(file_name)
        self._check_subfolder_support(path=path, function="FileService.delete")

        url = self._construct_content_url(
            path=path,
            exclude_path_end=False,
            extension="")

        return self._rest.DELETE(url, **kwargs)

    @require_version(version="11.4")
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

        path = Path(path)
        self._check_subfolder_support(path=path, function="FileService.search_string_in_name")

        url = self._construct_content_url(
            path=Path(path),
            exclude_path_end=False,
            extension="Contents?$select=Name&$filter={}".format(" and ".join(name_filters)))
        response = self._rest.GET(url, **kwargs).content

        return list(file['Name'] for file in json.loads(response)['value'])

    @staticmethod
    def _split_into_parts(data: Union[bytes, BytesIO], max_chunk_size: int = 200 * 1024 * 1024):
        # Convert data to bytes if it's a BytesIO object
        if isinstance(data, BytesIO):
            data = data.getvalue()

        # List to store chunks
        parts = []

        # Split data into chunks
        for i in range(0, len(data), max_chunk_size):
            part = data[i:i + max_chunk_size]
            parts.append(part)

        return parts

    @staticmethod
    def _file_content_is_empty(file_content: Union[bytes, BytesIO]):
        if isinstance(file_content, bytes):
            return not file_content  # Empty bytes are falsy

        elif isinstance(file_content, BytesIO):
            return file_content.getbuffer().nbytes == 0  # Check buffer size

        else:
            raise TypeError("Expected 'bytes' or 'BytesIO'.")
