"""Streaming in FileService: get_size, get_stream, create/update from an iterable, transfer_from.

Live tests. Same-instance cases run on tm1srv01; cross-instance and v12 cases run when tm1srv02 / tm1srv03 are
configured in config.ini and are skipped otherwise.
"""

import configparser
import hashlib
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from TM1py import TM1Service
from TM1py.Exceptions import TM1pyFileTransferException, TM1pyRestException
from TM1py.Services.FileService import FileService
from TM1py.Utils import verify_version

BOM = b"\xef\xbb\xbf"
CONFIG = configparser.ConfigParser()
CONFIG.read(Path(__file__).parent.joinpath("config.ini"))

SOURCE_FILE = "TM1py_unittest_stream_source.csv"
TARGET_FILE = "TM1py_unittest_stream_target.csv"
LARGE_FILE = "TM1py_unittest_stream_large.csv"

# > 100 MB, as the spec asks for at least one large streamed file in each direction
LARGE_SIZE = 110 * 1024 * 1024
LARGE_BLOCK = (b"0123456789,Region\xc3\xa9,Product 'A',\"1e-07\"\r\n" * 4096)[: 1024 * 1024]


def large_content(size: int = LARGE_SIZE):
    """Deterministic generator of `size` bytes, starting with a BOM like a v11 export."""
    yield BOM
    remaining = size - len(BOM)
    while remaining > 0:
        block = LARGE_BLOCK[:remaining]
        remaining -= len(block)
        yield block


def large_content_digest(size: int = LARGE_SIZE) -> str:
    """sha256 of the large content without its BOM: what must arrive on the target."""
    digest = hashlib.sha256()
    blocks = large_content(size)
    assert next(blocks) == BOM
    for block in blocks:
        digest.update(block)
    return digest.hexdigest()


def stream_digest(tm1: TM1Service, file_name: str) -> tuple:
    digest = hashlib.sha256()
    size = 0
    with tm1.files.get_stream(file_name) as chunks:
        for chunk in chunks:
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def connect(section: str) -> TM1Service:
    if section not in CONFIG:
        raise unittest.SkipTest(f"{section} not configured in config.ini")
    return TM1Service(**CONFIG[section])


def delete_if_exists(tm1: TM1Service, *file_names):
    for file_name in file_names:
        if tm1.files.exists(file_name):
            tm1.files.delete(file_name)


class TestTransferFromChecks(unittest.TestCase):
    """Server-free: transfer_from on a FileService wired to a mocked REST layer."""

    @staticmethod
    def file_service() -> FileService:
        rest = MagicMock()
        rest.version = "11.8.02300.1"
        return FileService(rest)

    def test_transfer_onto_the_same_file_raises_before_any_request(self):
        files = self.file_service()

        with self.assertRaises(ValueError):
            files.transfer_from(files, SOURCE_FILE)

        files._rest.GET.assert_not_called()

    def test_byte_mismatch_removes_the_target_file(self):
        source, target = self.file_service(), self.file_service()

        with patch.object(source, "get_size", return_value=10), patch.object(
            target, "_copy_stream", return_value=(5, 10)
        ), patch.object(target, "delete") as delete:
            with self.assertRaises(TM1pyFileTransferException):
                target.transfer_from(source, SOURCE_FILE, target_file_name=TARGET_FILE)

        delete.assert_called_once_with(TARGET_FILE)


class TestFileServiceStream(unittest.TestCase):
    """Same-instance streaming on tm1srv01."""

    tm1: TM1Service

    CONTENT = BOM + 'Région,Product \'A\',"x"\r\nNorth,"1,5",1e-07\r\n'.encode("utf-8") * 50

    @classmethod
    def setUpClass(cls):
        cls.tm1 = connect("tm1srv01")

    @classmethod
    def tearDownClass(cls):
        delete_if_exists(cls.tm1, SOURCE_FILE, TARGET_FILE)
        cls.tm1.logout()

    def setUp(self):
        delete_if_exists(self.tm1, SOURCE_FILE, TARGET_FILE)
        self.tm1.files.create(SOURCE_FILE, self.CONTENT)

    def test_get_size(self):
        self.assertEqual(len(self.CONTENT), self.tm1.files.get_size(SOURCE_FILE))

    def test_get_stream(self):
        with self.tm1.files.get_stream(SOURCE_FILE, chunk_size=100) as chunks:
            received = b"".join(chunks)
        self.assertEqual(self.CONTENT, received)

    def test_ti_file_name(self):
        expected = SOURCE_FILE if verify_version("12", self.tm1.version) else SOURCE_FILE + ".blb"
        self.assertEqual(expected, self.tm1.files.ti_file_name(SOURCE_FILE))

    def test_create_from_iterable_with_length(self):
        delete_if_exists(self.tm1, TARGET_FILE)
        blocks = [self.CONTENT[i : i + 7] for i in range(0, len(self.CONTENT), 7)]

        self.tm1.files.create(TARGET_FILE, iter(blocks), content_length=len(self.CONTENT))

        self.assertEqual(self.CONTENT, self.tm1.files.get(TARGET_FILE))

    def test_update_from_iterable_with_length(self):
        blocks = [b"new,", b"content\r\n"]

        self.tm1.files.update(SOURCE_FILE, iter(blocks), content_length=13)

        self.assertEqual(b"new,content\r\n", self.tm1.files.get(SOURCE_FILE))

    def test_create_from_empty_iterable(self):
        self.tm1.files.create(TARGET_FILE, iter([]), content_length=0)

        self.assertEqual(b"", self.tm1.files.get(TARGET_FILE))

    def test_create_from_iterable_without_length_v11_raises(self):
        if verify_version("12", self.tm1.version):
            self.skipTest("v11 only")
        with self.assertRaises(ValueError):
            self.tm1.files.create(TARGET_FILE, iter([b"a", b"b"]))

    def test_transfer_from_strips_bom(self):
        sent = self.tm1.files.transfer_from(self.tm1.files, SOURCE_FILE, target_file_name=TARGET_FILE)

        expected = self.CONTENT[len(BOM) :]
        self.assertEqual(len(expected), sent)
        self.assertEqual(expected, self.tm1.files.get(TARGET_FILE))
        self.assertTrue(self.tm1.files.exists(SOURCE_FILE))

    def test_transfer_from_retries_once_after_expired_session(self):
        files = self.tm1.files
        update_or_create = files.update_or_create
        attempts = []

        def expire_first_upload(file_name, file_content, **kwargs):
            attempts.append(file_name)
            if len(attempts) == 1:
                # the streamed body is consumed, then the target answers 401
                b"".join(file_content)
                raise TM1pyRestException("session expired", 401, "Unauthorized", {})
            return update_or_create(file_name, file_content, **kwargs)

        with patch.object(files, "update_or_create", side_effect=expire_first_upload):
            sent = files.transfer_from(files, SOURCE_FILE, target_file_name=TARGET_FILE)

        expected = self.CONTENT[len(BOM) :]
        self.assertEqual(2, len(attempts))
        self.assertEqual(len(expected), sent)
        self.assertEqual(expected, files.get(TARGET_FILE))

    def test_transfer_from_does_not_retry_other_errors(self):
        files = self.tm1.files
        error = TM1pyRestException("bad request", 400, "Bad Request", {})
        with patch.object(files, "update_or_create", side_effect=error) as upload:
            with self.assertRaises(TM1pyRestException):
                files.transfer_from(files, SOURCE_FILE, target_file_name=TARGET_FILE)
        self.assertEqual(1, upload.call_count)

    def test_transfer_from_without_bom(self):
        content = self.CONTENT[len(BOM) :]
        self.tm1.files.update(SOURCE_FILE, content)

        sent = self.tm1.files.transfer_from(self.tm1.files, SOURCE_FILE, target_file_name=TARGET_FILE)

        self.assertEqual(len(content), sent)
        self.assertEqual(content, self.tm1.files.get(TARGET_FILE))

    def test_transfer_from_small_chunks(self):
        sent = self.tm1.files.transfer_from(self.tm1.files, SOURCE_FILE, target_file_name=TARGET_FILE, chunk_size=2)

        self.assertEqual(len(self.CONTENT) - len(BOM), sent)
        self.assertEqual(self.CONTENT[len(BOM) :], self.tm1.files.get(TARGET_FILE))

    def test_transfer_from_overwrites_existing_target(self):
        self.tm1.files.create(TARGET_FILE, b"old content that is longer than nothing")

        self.tm1.files.transfer_from(self.tm1.files, SOURCE_FILE, target_file_name=TARGET_FILE)

        self.assertEqual(self.CONTENT[len(BOM) :], self.tm1.files.get(TARGET_FILE))

    def test_transfer_from_remove_source(self):
        self.tm1.files.transfer_from(self.tm1.files, SOURCE_FILE, target_file_name=TARGET_FILE, remove_source=True)

        self.assertFalse(self.tm1.files.exists(SOURCE_FILE))
        self.assertEqual(self.CONTENT[len(BOM) :], self.tm1.files.get(TARGET_FILE))

    def test_transfer_from_empty_file(self):
        self.tm1.files.update(SOURCE_FILE, b"")

        sent = self.tm1.files.transfer_from(self.tm1.files, SOURCE_FILE, target_file_name=TARGET_FILE)

        self.assertEqual(0, sent)
        self.assertEqual(b"", self.tm1.files.get(TARGET_FILE))

    def test_transfer_from_bom_only_file(self):
        self.tm1.files.update(SOURCE_FILE, BOM)

        sent = self.tm1.files.transfer_from(self.tm1.files, SOURCE_FILE, target_file_name=TARGET_FILE)

        self.assertEqual(0, sent)
        self.assertEqual(b"", self.tm1.files.get(TARGET_FILE))


class TestFileServiceStreamCrossInstance(unittest.TestCase):
    """A file over 100 MB in each direction: v11 sized upload and v12 multipart upload."""

    source_v11: TM1Service

    @classmethod
    def setUpClass(cls):
        cls.source_v11 = connect("tm1srv01")
        cls.expected_digest = large_content_digest()
        cls.expected_size = LARGE_SIZE - len(BOM)

    @classmethod
    def tearDownClass(cls):
        delete_if_exists(cls.source_v11, LARGE_FILE, TARGET_FILE)
        cls.source_v11.logout()

    def run_transfer(self, source: TM1Service, target: TM1Service, **kwargs):
        try:
            delete_if_exists(target, TARGET_FILE)
            delete_if_exists(source, LARGE_FILE)
            source.files.create(LARGE_FILE, large_content(), content_length=LARGE_SIZE)
            self.assertEqual(LARGE_SIZE, source.files.get_size(LARGE_FILE))

            sent = target.files.transfer_from(
                source.files, LARGE_FILE, target_file_name=TARGET_FILE, remove_source=True, **kwargs
            )

            self.assertEqual(self.expected_size, sent)
            self.assertFalse(source.files.exists(LARGE_FILE))
            self.assertEqual(self.expected_size, target.files.get_size(TARGET_FILE))
            self.assertEqual((self.expected_digest, self.expected_size), stream_digest(target, TARGET_FILE))
        finally:
            delete_if_exists(source, LARGE_FILE)
            delete_if_exists(target, TARGET_FILE)

    def test_large_v11_to_v11_sized_upload(self):
        self.run_transfer(self.source_v11, self.source_v11)

    def test_large_v11_to_v12_multipart(self):
        target = connect("tm1srv02")
        try:
            self.run_transfer(self.source_v11, target)
        finally:
            target.logout()

    def test_large_v12_to_v11_sized_upload(self):
        source = connect("tm1srv02")
        try:
            self.run_transfer(source, self.source_v11)
        finally:
            source.logout()

    def test_large_v11_to_paoc_sized_upload(self):
        target = connect("tm1srv03")
        try:
            self.run_transfer(self.source_v11, target)
        finally:
            target.logout()


if __name__ == "__main__":
    unittest.main()
