# -*- coding: utf-8 -*-
import concurrent.futures
import itertools
import json
import time
import warnings
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from typing import Iterable, Iterator, List, Optional, Tuple, Union

from TM1py.Exceptions import (
    TM1pyFileTransferException,
    TM1pyRestException,
    TM1pyVersionException,
)
from TM1py.Services import RestService
from TM1py.Services.ObjectService import ObjectService
from TM1py.Utils import format_url
from TM1py.Utils.BlobProcessBuilder import ti_file_name as _ti_file_name
from TM1py.Utils.Utils import is_streamed_body, require_version, verify_version

UTF8_BOM = b"\xef\xbb\xbf"

FileContent = Union[bytes, BytesIO, Iterable[bytes]]


class _SizedIterable:
    """An iterable body that reports its length, so `requests` sends `Content-Length` instead of a chunked body
    (v11 rejects chunked uploads)."""

    def __init__(self, iterable: Iterable[bytes], length: int):
        self._iterable = iterable
        self._length = length

    def __iter__(self):
        return iter(self._iterable)

    def __len__(self):
        return self._length


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
            self.version_content_path = "Files"
        else:
            self.version_content_path = "Blobs"

    @require_version(version="11.4")
    def get_names(self, **kwargs) -> bytes:
        warnings.warn(
            "Function get_names will be deprecated. Use get_all_names instead", DeprecationWarning, stacklevel=2
        )

        url = format_url(
            "/Contents('{version_content_path}')/Contents?$select=Name", version_content_path=self.version_content_path
        )

        return self._rest.GET(url, **kwargs).content

    @require_version(version="11.4")
    def get_all_names(self, path: Union[str, Path] = "", **kwargs) -> List[str]:
        """return list of blob file names

        :param path: path to folder. When empty searches in root
        """
        path = Path(path)
        url = self._construct_content_url(path, exclude_path_end=False, extension="Contents")

        response = self._rest.GET(url, **kwargs).content
        return [file["Name"] for file in json.loads(response)["value"]]

    @require_version(version="11.4")
    def get(self, file_name: str, **kwargs) -> bytes:
        """Get file

        :param file_name: file name in root or path to file
        """
        path = Path(file_name)
        self._check_subfolder_support(path=path, function="FileService.get")

        url = self._construct_content_url(path=path, exclude_path_end=False, extension="Content")

        return self._rest.GET(url, **kwargs).content

    @require_version(version="11.4")
    def get_size(self, file_name: Union[str, Path], **kwargs) -> int:
        """Size of a file in bytes, read from the document's metadata

        v11 sends large downloads without a length, so read the size here before streaming a file.

        :param file_name: file name in root or path to file
        """
        path = Path(file_name)
        self._check_subfolder_support(path=path, function="FileService.get_size")

        url = self._construct_content_url(path=path, exclude_path_end=False, extension="") + "?$select=Size"
        return int(self._rest.GET(url, **kwargs).json()["Size"])

    @require_version(version="11.4")
    @contextmanager
    def get_stream(
        self, file_name: Union[str, Path], chunk_size: int = 8 * 1024 * 1024, **kwargs
    ) -> Iterator[Iterator[bytes]]:
        """Stream a file's content in chunks, holding about one chunk in memory

        Use as a context manager, so the connection is released when done:
            with tm1.files.get_stream("export.csv") as chunks:
                for chunk in chunks:
                    ...

        :param file_name: file name in root or path to file
        :param chunk_size: maximum bytes per chunk
        """
        path = Path(file_name)
        self._check_subfolder_support(path=path, function="FileService.get_stream")

        url = self._construct_content_url(path=path, exclude_path_end=False, extension="Content")
        # identity: the chunks add up to the file's size (see get_size)
        response = self._rest.GET(url, headers={"Accept-Encoding": "identity"}, stream=True, **kwargs)
        try:
            yield response.iter_content(chunk_size=chunk_size)
        finally:
            response.close()

    def ti_file_name(self, file_name: Union[str, Path]) -> str:
        """The name a TI process must use for a file in the file store (v11 adds a `.blb` extension)

        :param file_name: file name in root or path to file
        """
        return _ti_file_name(Path(file_name).as_posix(), verify_version("12", self.version))

    @require_version(version="11.4")
    def transfer_from(
        self,
        source: "FileService",
        file_name: Union[str, Path],
        target_file_name: Union[str, Path] = None,
        remove_source: bool = False,
        chunk_size: int = 8 * 1024 * 1024,
        multi_part_upload: bool = None,
        max_mb_per_part: float = 50,
        **kwargs,
    ) -> int:
        """Copy a file from another instance's file store (`source`) into this one, streamed

        Called on the target. Client memory stays at about one chunk (one part with multipart upload),
        whatever the file size. A UTF-8 BOM at the start of the source file is not copied.
        An existing target file is overwritten. If the target's session has expired, the copy runs once more after
        reconnecting, with a new stream from the source (a streamed upload can't be resent).

        :param source: FileService of the source instance (may be this instance)
        :param file_name: file name in root or path to file on the source
        :param target_file_name: name on the target. Defaults to `file_name`
        :param remove_source: delete the source file after a successful copy
        :param chunk_size: bytes per chunk read from the source
        :param multi_part_upload: use multipart upload on the target. By default used on v12 and not on v11,
        where the file is sent as one sized upload
        :param max_mb_per_part: megabytes per part with multipart upload
        :return: number of bytes sent to the target
        :raises TM1pyFileTransferException: when the bytes sent differ from the source file's size
        """
        target_file_name = file_name if target_file_name is None else target_file_name
        size = source.get_size(file_name, **kwargs)

        def copy() -> Tuple[int, int]:
            return self._copy_stream(
                source, file_name, target_file_name, size, chunk_size, multi_part_upload, max_mb_per_part, **kwargs
            )

        try:
            sent, length = copy()
        except TM1pyRestException as e:
            # A streamed upload can't be resent, so a 401 from an expired session on the target is returned after
            # RestService reconnects. The source can be read again, so the copy is run once more with a new stream
            if e.status_code != 401:
                raise
            sent, length = copy()

        if sent != length:
            raise TM1pyFileTransferException(str(file_name), sent, length)

        if remove_source:
            source.delete(file_name, **kwargs)

        return sent

    def _copy_stream(
        self,
        source: "FileService",
        file_name: Union[str, Path],
        target_file_name: Union[str, Path],
        size: int,
        chunk_size: int,
        multi_part_upload: Optional[bool],
        max_mb_per_part: float,
        **kwargs,
    ) -> Tuple[int, int]:
        """Stream one file from `source` into this file store. Returns the bytes sent and the bytes expected."""
        sent = 0
        with source.get_stream(file_name, chunk_size=chunk_size, **kwargs) as chunks:
            chunks, has_bom = self._strip_bom(chunks)
            length = size - len(UTF8_BOM) if has_bom else size

            def counted() -> Iterator[bytes]:
                nonlocal sent
                for chunk in chunks:
                    sent += len(chunk)
                    yield chunk

            self.update_or_create(
                target_file_name,
                counted(),
                multi_part_upload=multi_part_upload,
                max_mb_per_part=max_mb_per_part,
                content_length=length,
                **kwargs,
            )
        return sent, length

    @staticmethod
    def _strip_bom(chunks: Iterable[bytes]) -> Tuple[Iterator[bytes], bool]:
        """Drop a UTF-8 BOM from the start of a stream of chunks. Returns the chunks and whether a BOM was found."""
        chunks = iter(chunks)
        head = b""
        for chunk in chunks:
            head += chunk
            if len(head) >= len(UTF8_BOM):
                break

        has_bom = head.startswith(UTF8_BOM)
        if has_bom:
            head = head[len(UTF8_BOM) :]

        return itertools.chain([head] if head else [], chunks), has_bom

    def _create_folder(self, folder_name: Union[str, Path], **kwargs):
        """Create folder

        Can only create 1 folder at a time.
        To create nested folder structures it must be called in an iterative fashion.

        :param folder_name: path to folder (e.g. folderA, folderA/folderB)
        """
        path = Path(folder_name)
        url = self._construct_content_url(path, exclude_path_end=True, extension="Contents")

        body = {"@odata.type": "#ibm.tm1.api.v1.Folder", "Name": path.name}
        self._rest.POST(url, json.dumps(body), **kwargs)

    @require_version(version="12")
    def create_folder(self, folder_name: Union[str, Path], **kwargs):
        """Create folder(s)

        Supports recursive creation (e.g., 'folderA/folderB/folderC')

        :param folder_name: folder name or path to nested folders
        :return: None
        """
        path = Path(folder_name)
        folder_path = Path()
        for part in path.parts:
            folder_path = folder_path.joinpath(part)
            if not self.exists(folder_path, **kwargs):
                self._create_folder(folder_name=folder_path, **kwargs)

    def _construct_content_url(self, path: Path, exclude_path_end: bool = True, extension: str = "Contents") -> str:
        """Dynamically construct URL to use in FileService functions

        :param path: file name in root or path to file
        :param exclude_path_end: Some functions require complete URL to file (e.g. exists),
        while others require URL to parent folder (e.g., create)
        :param extension: Final piece of the URL e.g. ('Contents', 'Content', or 'Contents?$select=Name')

        """
        parent_folders = {
            f"level{str(n).zfill(4)}": parent
            for n, parent in enumerate(path.parts[:-1] if exclude_path_end else path.parts, 1)
        }

        url = format_url(
            "".join(
                [
                    "/Contents('{version_content_path}')/",
                    "/".join(f"Contents('{{{folder}}}')" for folder in parent_folders) + "/" if parent_folders else "",
                    extension,
                ]
            ),
            version_content_path=self.version_content_path,
            **parent_folders,
        )

        return url.rstrip("/")

    def _check_subfolder_support(self, path: Path, function: str) -> None:
        if not len(path.parts) > 1:
            return

        if not verify_version(required_version=self.SUBFOLDER_REQUIRED_VERSION, version=self.version):
            raise TM1pyVersionException(
                function=function, required_version=self.SUBFOLDER_REQUIRED_VERSION, feature="Subfolder"
            )

    def _check_mpu_support(self, function: str) -> None:
        if not verify_version(required_version=self.MPU_REQUIRED_VERSION, version=self.version):
            raise TM1pyVersionException(
                function=function, required_version=self.MPU_REQUIRED_VERSION, feature="MultiProcessUpload"
            )

    def _upload_file_content(
        self,
        path: Path,
        file_content: FileContent,
        multi_part_upload: bool = None,
        max_mb_per_part: float = 200,
        max_workers: int = 1,
        content_length: Optional[int] = None,
        **kwargs,
    ):
        """
        :param path: file name in root or path to file
        :param file_content: file_content as bytes, BytesIO or an iterable of bytes
        :param multi_part_upload: boolean use multipart upload or not (only available from TM1 12 onwards)
        By default, multi_part_upload is used for TM1 v12 and not used for TM1 v11
        :param max_mb_per_part: max megabyte per part in multipart upload (only available from TM1 12 onwards)
        :param max_workers: max parallel workers for multipart upload (only available from TM1 12 onwards)
        :param content_length: total bytes of an iterable file_content
        """

        url = self._construct_content_url(path, exclude_path_end=False, extension="Content")

        if is_streamed_body(file_content):
            return self._upload_iterable_content(
                url, file_content, multi_part_upload, max_mb_per_part, content_length, **kwargs
            )

        # empty files must be created without MPU
        if self._file_content_is_empty(file_content):
            return self._upload_file_content_without_mpu(url, file_content, **kwargs)

        if multi_part_upload is None:
            multi_part_upload = self.version.startswith("12.")

        if multi_part_upload:
            return self._upload_file_content_with_mpu(url, file_content, max_mb_per_part, max_workers, **kwargs)

        return self._upload_file_content_without_mpu(url, file_content, **kwargs)

    def _upload_iterable_content(
        self,
        url: str,
        file_content: Iterable[bytes],
        multi_part_upload: Optional[bool],
        max_mb_per_part: float,
        content_length: Optional[int],
        **kwargs,
    ):
        """Upload an iterable of bytes, holding at most one part in memory

        Without multipart upload the content is sent as one sized upload, because v11 rejects chunked uploads.
        With multipart upload the iterable is regrouped into parts, uploaded one at a time.
        """
        if multi_part_upload is None:
            multi_part_upload = verify_version("12", self.version)

        if content_length is None and hasattr(file_content, "__len__"):
            content_length = len(file_content)
        if not multi_part_upload and content_length is None and not verify_version("12", self.version):
            raise ValueError("'content_length' is required to upload an iterable to TM1 v11 without multipart upload")

        blocks = iter(file_content)
        first = next((block for block in blocks if block), None)
        # empty files must be created without MPU
        if first is None:
            return self._upload_file_content_without_mpu(url, b"", **kwargs)
        blocks = itertools.chain([first], blocks)

        if multi_part_upload:
            parts = self._regroup_into_parts(blocks, max_chunk_size=int(max_mb_per_part * 1024 * 1024))
            return self._upload_file_content_with_mpu(url, parts, max_mb_per_part, max_workers=1, **kwargs)

        body = blocks if content_length is None else _SizedIterable(blocks, content_length)
        return self._upload_file_content_without_mpu(url, body, **kwargs)

    def _upload_file_content_without_mpu(self, url, file_content, **kwargs):
        return self._rest.PUT(url=url, data=file_content, headers=self.binary_http_header, **kwargs)

    def _upload_file_content_with_mpu(
        self,
        content_url: str,
        file_content: Union[bytes, BytesIO, Iterator[bytes]],
        max_mb_per_part: float,
        max_workers: int = 1,
        **kwargs,
    ):
        """:param file_content: bytes or BytesIO, split here into parts, or an iterator of ready-made parts"""

        # Initiate multipart upload
        response = self._rest.POST(
            url=content_url + "/mpu.CreateMultipartUpload", data="{}", async_requests_mode=False, **kwargs
        )
        upload_id = response.json()["UploadID"]

        # Split the file content into parts
        if isinstance(file_content, (bytes, BytesIO)):
            parts_to_upload = self._split_into_parts(
                data=file_content, max_chunk_size=int(max_mb_per_part * 1024 * 1024)
            )
        else:
            parts_to_upload = file_content

        part_numbers_and_etags = []

        # helper function for uploading each part
        def upload_part_with_retry(index: int, data: bytes, retries: int = 3) -> Tuple[int, int, str]:
            for attempt in range(retries):
                try:
                    part_response = self._rest.POST(
                        url=content_url + f"/!uploads('{upload_id}')/Parts",
                        data=data,
                        headers={**self.binary_http_header, "Accept": "application/json,text/plain"},
                        async_requests_mode=False,
                        **kwargs,
                    )
                    return index, part_response.json()["PartNumber"], part_response.json()["@odata.etag"]
                except Exception as e:
                    if attempt < retries - 1:
                        time.sleep(2**attempt)  # Exponential backoff
                    else:
                        raise e from None

        if max_workers > 1:
            # upload parts concurrently
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:

                futures = {
                    executor.submit(upload_part_with_retry, i, part, 3): i for i, part in enumerate(parts_to_upload)
                }

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
                {
                    "Parts": [
                        {"PartNumber": part_number, "ETag": etag}
                        for _, part_number, etag in sorted(part_numbers_and_etags)
                    ]
                }
            ),
        )

    @require_version(version="11.4")
    def create(
        self,
        file_name: Union[str, Path],
        file_content: FileContent,
        multi_part_upload: bool = None,
        max_mb_per_part: float = 200,
        max_workers: int = 1,
        content_length: Optional[int] = None,
        **kwargs,
    ):
        """Create file

        Folders in file_name (e.g. folderA/folderB/file.csv) will be created implicitly

        :param file_name: file name in root or path to file
        :param file_content: file_content as bytes, BytesIO or an iterable of bytes (streamed, one part at a time)
        :param multi_part_upload: boolean use multipart upload or not (only available from TM1 12 onwards)
        By default, multi_part_upload is used for TM1 v12 and not used for TM1 v11
        :param max_mb_per_part: max megabyte per part in multipart upload (only available from TM1 12 onwards)
        :param max_workers: max parallel workers for multipart upload (only available from TM1 12 onwards).
        Ignored for an iterable file_content
        :param content_length: total bytes of an iterable file_content. Required on v11, which only accepts a
        sized upload, unless the iterable implements `__len__`
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
        body = {"@odata.type": "#ibm.tm1.api.v1.Document", "ID": path.name, "Name": path.name}
        self._rest.POST(url, json.dumps(body), **kwargs)

        return self._upload_file_content(
            path, file_content, multi_part_upload, max_mb_per_part, max_workers, content_length, **kwargs
        )

    @require_version(version="11.4")
    def update(
        self,
        file_name: Union[str, Path],
        file_content: FileContent,
        multi_part_upload: bool = None,
        max_mb_per_part: float = 200,
        max_workers: int = 1,
        content_length: Optional[int] = None,
        **kwargs,
    ):
        """Update existing file

        :param file_name: file name in root or path to file
        :param file_content: file_content as bytes, BytesIO or an iterable of bytes (streamed, one part at a time)
        :param multi_part_upload: boolean use multipart upload or not (only available from TM1 12 onwards)
        By default, multi_part_upload is used for TM1 v12 and not used for TM1 v11
        :param max_mb_per_part: max megabyte per part in multipart upload (only available from TM1 12 onwards)
        :param max_workers: max parallel workers for multipart upload (only available from TM1 12 onwards).
        Ignored for an iterable file_content
        :param content_length: total bytes of an iterable file_content. Required on v11, which only accepts a
        sized upload, unless the iterable implements `__len__`
        """
        path = Path(file_name)
        self._check_subfolder_support(path=path, function="FileService.update")
        if multi_part_upload:
            self._check_mpu_support(function="FileService.create")

        return self._upload_file_content(
            path, file_content, multi_part_upload, max_mb_per_part, max_workers, content_length, **kwargs
        )

    @require_version(version="11.4")
    def update_or_create(
        self,
        file_name: Union[str, Path],
        file_content: FileContent,
        multi_part_upload: bool = None,
        max_mb_per_part: float = 200,
        max_workers: int = 1,
        content_length: Optional[int] = None,
        **kwargs,
    ):
        """Create file or update file if it already exists

        :param file_name: file name in root or path to file
        :param file_content: file_content as bytes, BytesIO or an iterable of bytes (streamed, one part at a time)
        :param multi_part_upload: boolean use multipart upload or not (only available from TM1 12 onwards).
        By default, multi_part_upload is used for TM1 v12 and not used for TM1 v11
        :param max_mb_per_part: max megabyte per part in multipart upload (only available from TM1 12 onwards)
        :param max_workers: max parallel workers for multipart upload (only available from TM1 12 onwards)
        :param content_length: total bytes of an iterable file_content (see create)
        """
        if self.exists(file_name, **kwargs):
            return self.update(
                file_name, file_content, multi_part_upload, max_mb_per_part, max_workers, content_length, **kwargs
            )

        return self.create(
            file_name, file_content, multi_part_upload, max_mb_per_part, max_workers, content_length, **kwargs
        )

    @require_version(version="11.4")
    def exists(self, file_name: Union[str, Path], **kwargs):
        """Check if file exists

        :param file_name: file name in root or path to file
        """
        url = self._construct_content_url(path=Path(file_name), exclude_path_end=False, extension="")

        return self._exists(url, **kwargs)

    @require_version(version="11.4")
    def delete(self, file_name: Union[str, Path], **kwargs):
        """Delete file

        :param file_name: file name in root or path to file
        """
        path = Path(file_name)
        self._check_subfolder_support(path=path, function="FileService.delete")

        url = self._construct_content_url(path=path, exclude_path_end=False, extension="")

        return self._rest.DELETE(url, **kwargs)

    @require_version(version="11.4")
    def search_string_in_name(
        self,
        name_startswith: str = None,
        name_contains: Iterable = None,
        name_contains_operator: str = "and",
        path: Union[Path, str] = "",
        **kwargs,
    ) -> List[str]:
        """Return list of blob files that match search critera

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
                name_contains_filters = [
                    format_url("contains(tolower(Name),tolower('{}'))", wildcard) for wildcard in name_contains
                ]
                name_filters.append("({})".format(f" {name_contains_operator} ".join(name_contains_filters)))

            else:
                raise ValueError("'name_contains' must be str or iterable")

        path = Path(path)
        self._check_subfolder_support(path=path, function="FileService.search_string_in_name")

        url = self._construct_content_url(
            path=Path(path),
            exclude_path_end=False,
            extension="Contents?$select=Name&$filter={}".format(" and ".join(name_filters)),
        )
        response = self._rest.GET(url, **kwargs).content

        return list(file["Name"] for file in json.loads(response)["value"])

    @staticmethod
    def _split_into_parts(data: Union[bytes, BytesIO], max_chunk_size: int = 200 * 1024 * 1024):
        # Convert data to bytes if it's a BytesIO object
        if isinstance(data, BytesIO):
            data = data.getvalue()

        # List to store chunks
        parts = []

        # Split data into chunks
        for i in range(0, len(data), max_chunk_size):
            part = data[i : i + max_chunk_size]
            parts.append(part)

        return parts

    @staticmethod
    def _regroup_into_parts(blocks: Iterable[bytes], max_chunk_size: int) -> Iterator[bytes]:
        """Regroup an iterable of bytes into parts of `max_chunk_size` bytes (the last may be smaller)"""
        buffer = bytearray()
        for block in blocks:
            buffer += block
            while len(buffer) >= max_chunk_size:
                yield bytes(buffer[:max_chunk_size])
                del buffer[:max_chunk_size]
        if buffer:
            yield bytes(buffer)

    @staticmethod
    def _file_content_is_empty(file_content: Union[bytes, BytesIO]):
        if isinstance(file_content, bytes):
            return not file_content  # Empty bytes are falsy

        elif isinstance(file_content, BytesIO):
            return file_content.getbuffer().nbytes == 0  # Check buffer size

        else:
            raise TypeError("Expected 'bytes' or 'BytesIO'.")
