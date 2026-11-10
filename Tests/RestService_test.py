import configparser
import gzip
import unittest
import uuid
from io import BytesIO
from pathlib import Path

from TM1py import TM1Service
from TM1py.Objects import Process
from TM1py.Services.RestService import RestService


class TestRestService(unittest.TestCase):
    tm1: TM1Service

    @classmethod
    def setUpClass(cls):
        """
        Establishes a connection to TM1 and creates TM! objects to use across all tests
        """

        # Connection to TM1
        cls.config = configparser.ConfigParser()
        cls.config.read(Path(__file__).parent.joinpath("config.ini"))
        cls.tm1 = TM1Service(**cls.config["tm1srv01"])

    def test_is_connected(self):
        self.assertTrue(self.tm1._tm1_rest.is_connected())

    def test_wait_time_generator_with_float_timeout(self):
        # Use fixed known values to test the generator logic deterministically
        original_initial = self.tm1._tm1_rest._async_polling_initial_delay
        original_max = self.tm1._tm1_rest._async_polling_max_delay
        original_factor = self.tm1._tm1_rest._async_polling_backoff_factor
        try:
            self.tm1._tm1_rest._async_polling_initial_delay = 0.1
            self.tm1._tm1_rest._async_polling_max_delay = 1.0
            self.tm1._tm1_rest._async_polling_backoff_factor = 2.0
            # With 0.1s initial, 1.0s max, 2x factor: 0.1 -> 0.2 -> 0.4 -> 0.8 -> 1.0 -> 1.0...
            expected = [0.1, 0.2, 0.4, 0.8, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
            self.assertEqual(expected, list(self.tm1._tm1_rest.wait_time_generator(10.0)))
            self.assertEqual(10.5, sum(self.tm1._tm1_rest.wait_time_generator(10.0)))
        finally:
            self.tm1._tm1_rest._async_polling_initial_delay = original_initial
            self.tm1._tm1_rest._async_polling_max_delay = original_max
            self.tm1._tm1_rest._async_polling_backoff_factor = original_factor

    def test_wait_time_generator_with_timeout(self):
        # Use fixed known values to test the generator logic deterministically
        original_initial = self.tm1._tm1_rest._async_polling_initial_delay
        original_max = self.tm1._tm1_rest._async_polling_max_delay
        original_factor = self.tm1._tm1_rest._async_polling_backoff_factor
        try:
            self.tm1._tm1_rest._async_polling_initial_delay = 0.1
            self.tm1._tm1_rest._async_polling_max_delay = 1.0
            self.tm1._tm1_rest._async_polling_backoff_factor = 2.0
            # With 0.1s initial, 1.0s max, 2x factor: 0.1 -> 0.2 -> 0.4 -> 0.8 -> 1.0 -> 1.0...
            expected = [0.1, 0.2, 0.4, 0.8, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
            self.assertEqual(expected, list(self.tm1._tm1_rest.wait_time_generator(10)))
            self.assertEqual(10.5, sum(self.tm1._tm1_rest.wait_time_generator(10)))
        finally:
            self.tm1._tm1_rest._async_polling_initial_delay = original_initial
            self.tm1._tm1_rest._async_polling_max_delay = original_max
            self.tm1._tm1_rest._async_polling_backoff_factor = original_factor

    def test_wait_time_generator_without_timeout(self):
        # Use fixed known values to test the generator logic deterministically
        original_initial = self.tm1._tm1_rest._async_polling_initial_delay
        original_max = self.tm1._tm1_rest._async_polling_max_delay
        original_factor = self.tm1._tm1_rest._async_polling_backoff_factor
        try:
            self.tm1._tm1_rest._async_polling_initial_delay = 0.1
            self.tm1._tm1_rest._async_polling_max_delay = 1.0
            self.tm1._tm1_rest._async_polling_backoff_factor = 2.0
            generator = self.tm1._tm1_rest.wait_time_generator(None)
            self.assertEqual(0.1, next(generator))
            self.assertEqual(0.2, next(generator))
            self.assertEqual(0.4, next(generator))
            self.assertEqual(0.8, next(generator))
            self.assertEqual(1.0, next(generator))
            self.assertEqual(1.0, next(generator))
        finally:
            self.tm1._tm1_rest._async_polling_initial_delay = original_initial
            self.tm1._tm1_rest._async_polling_max_delay = original_max
            self.tm1._tm1_rest._async_polling_backoff_factor = original_factor

    def test_wait_time_generator_custom_max_delay(self):
        # Test with custom max_delay for long-running operations
        original_initial = self.tm1._tm1_rest._async_polling_initial_delay
        original_max_delay = self.tm1._tm1_rest._async_polling_max_delay
        original_factor = self.tm1._tm1_rest._async_polling_backoff_factor
        try:
            self.tm1._tm1_rest._async_polling_initial_delay = 0.1
            self.tm1._tm1_rest._async_polling_max_delay = 30.0
            self.tm1._tm1_rest._async_polling_backoff_factor = 2.0
            # With 0.1s initial, 30s max, 2x factor: 0.1 -> 0.2 -> 0.4 -> 0.8 -> 1.6 -> 3.2 -> 6.4 -> 12.8 -> 25.6 -> 30.0...
            generator = self.tm1._tm1_rest.wait_time_generator(None)
            self.assertEqual(0.1, next(generator))
            self.assertEqual(0.2, next(generator))
            self.assertEqual(0.4, next(generator))
            self.assertEqual(0.8, next(generator))
            self.assertEqual(1.6, next(generator))
            self.assertEqual(3.2, next(generator))
            self.assertEqual(6.4, next(generator))
            self.assertEqual(12.8, next(generator))
            self.assertEqual(25.6, next(generator))
            self.assertEqual(30.0, next(generator))
            self.assertEqual(30.0, next(generator))
        finally:
            self.tm1._tm1_rest._async_polling_initial_delay = original_initial
            self.tm1._tm1_rest._async_polling_max_delay = original_max_delay
            self.tm1._tm1_rest._async_polling_backoff_factor = original_factor

    def test_wait_time_generator_custom_backoff_factor(self):
        # Test with custom backoff factor (3x instead of 2x)
        original_initial = self.tm1._tm1_rest._async_polling_initial_delay
        original_max = self.tm1._tm1_rest._async_polling_max_delay
        original_factor = self.tm1._tm1_rest._async_polling_backoff_factor
        try:
            self.tm1._tm1_rest._async_polling_initial_delay = 0.1
            self.tm1._tm1_rest._async_polling_max_delay = 1.0
            self.tm1._tm1_rest._async_polling_backoff_factor = 3.0
            # With 0.1s initial, 1.0s max, 3x factor: 0.1 -> 0.3 -> 0.9 -> 1.0 -> 1.0...
            generator = self.tm1._tm1_rest.wait_time_generator(None)
            self.assertEqual(0.1, next(generator))
            self.assertAlmostEqual(0.3, next(generator), places=5)
            self.assertAlmostEqual(0.9, next(generator), places=5)
            self.assertEqual(1.0, next(generator))
            self.assertEqual(1.0, next(generator))
        finally:
            self.tm1._tm1_rest._async_polling_initial_delay = original_initial
            self.tm1._tm1_rest._async_polling_max_delay = original_max
            self.tm1._tm1_rest._async_polling_backoff_factor = original_factor

    def test_wait_time_generator_custom_initial_delay(self):
        # Test with custom initial delay
        original_initial = self.tm1._tm1_rest._async_polling_initial_delay
        original_max = self.tm1._tm1_rest._async_polling_max_delay
        original_factor = self.tm1._tm1_rest._async_polling_backoff_factor
        try:
            self.tm1._tm1_rest._async_polling_initial_delay = 0.5
            self.tm1._tm1_rest._async_polling_max_delay = 1.0
            self.tm1._tm1_rest._async_polling_backoff_factor = 2.0
            # With 0.5s initial, 1.0s max, 2x factor: 0.5 -> 1.0 -> 1.0...
            generator = self.tm1._tm1_rest.wait_time_generator(None)
            self.assertEqual(0.5, next(generator))
            self.assertEqual(1.0, next(generator))
            self.assertEqual(1.0, next(generator))
        finally:
            self.tm1._tm1_rest._async_polling_initial_delay = original_initial
            self.tm1._tm1_rest._async_polling_max_delay = original_max
            self.tm1._tm1_rest._async_polling_backoff_factor = original_factor

    def test_default_remote_disconnect_parameters(self):
        # Verify values for remote disconnect retry parameters match config or defaults
        expected_max_retries = int(self.config["tm1srv01"].get("remote_disconnect_max_retries", 5))
        expected_retry_delay = float(self.config["tm1srv01"].get("remote_disconnect_retry_delay", 1.0))
        expected_max_delay = float(self.config["tm1srv01"].get("remote_disconnect_max_delay", 30.0))
        expected_backoff_factor = float(self.config["tm1srv01"].get("remote_disconnect_backoff_factor", 2.0))
        self.assertEqual(expected_max_retries, self.tm1._tm1_rest._remote_disconnect_max_retries)
        self.assertEqual(expected_retry_delay, self.tm1._tm1_rest._remote_disconnect_retry_delay)
        self.assertEqual(expected_max_delay, self.tm1._tm1_rest._remote_disconnect_max_delay)
        self.assertEqual(expected_backoff_factor, self.tm1._tm1_rest._remote_disconnect_backoff_factor)

    def test_default_async_polling_parameters(self):
        # Verify values for async polling parameters match config or defaults
        expected_initial_delay = float(self.config["tm1srv01"].get("async_polling_initial_delay", 0.1))
        expected_max_delay = float(self.config["tm1srv01"].get("async_polling_max_delay", 1.0))
        expected_backoff_factor = float(self.config["tm1srv01"].get("async_polling_backoff_factor", 2.0))
        self.assertEqual(expected_initial_delay, self.tm1._tm1_rest._async_polling_initial_delay)
        self.assertEqual(expected_max_delay, self.tm1._tm1_rest._async_polling_max_delay)
        self.assertEqual(expected_backoff_factor, self.tm1._tm1_rest._async_polling_backoff_factor)

    def test_build_response_from_async_response_ok(self):
        response_content = (
            b"HTTP/1.1 200 OK\r\nContent-Length: 32\r\nConnection: keep-alive\r\nContent-Encoding: "
            b"gzip\r\nCache-Control: no-cache\r\nContent-Type: text/plain; charset=utf-8\r\n"
            b"OData-Version: 4.0\r\n\r\n\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x0b34\xd43\xd730000"
            b"\xd23\x04\x00\xf4\x1c\xa0j\x0c\x00\x00\x00"
        )
        response = RestService.build_response_from_binary_response(response_content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("Content-Length"), "32")
        self.assertEqual(response.headers.get("Connection"), "keep-alive")
        self.assertEqual(response.headers.get("Content-Encoding"), "gzip")
        self.assertEqual(response.headers.get("Cache-Control"), "no-cache")
        self.assertEqual(response.headers.get("Content-Type"), "text/plain; charset=utf-8")
        self.assertEqual(response.headers.get("OData-Version"), "4.0")
        self.assertEqual(response.text, "11.7.00002.1")

    def test_build_response_from_async_response_not_found(self):
        response_content = (
            b"HTTP/1.1 404 Not Found\r\nContent-Length: 105\r\nConnection: keep-alive\r\n"
            b"Content-Encoding: gzip\r\nCache-Control: no-cache\r\n"
            b"Content-Type: application/json; charset=utf-8\r\nOData-Version: 4.0\r\n"
            b"\r\n\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x0b\x15\xc71\n\x800\x0c\x05\xd0\xab|\xb2t\x11"
            b"\x07\x17\xc5Sx\x05M\xa3\x14\xdaD\xda:\x94\xe2\xdd\xc5\xb7\xbdN\x92\xb3eZ;\xb1y\xa1\x95"
            b"\xa6y\xa1\x81\x92\x94\xb2_\xff\x9d\x7fRj\x0e\xbc+\xd4*\x0e\xc1i\x8fz\x04\x05[\x8c\xc25"
            b"\x98\xc2N\xd4v\x0b\xdc\x96\x8d\xa5\x147\xd2\xfb~Od\xf8E^\x00\x00\x00"
        )
        response = RestService.build_response_from_binary_response(response_content)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.headers.get("Content-Length"), "105")
        self.assertEqual(response.headers.get("Connection"), "keep-alive")
        self.assertEqual(response.headers.get("Content-Encoding"), "gzip")
        self.assertEqual(response.headers.get("Cache-Control"), "no-cache")
        self.assertEqual(response.headers.get("Content-Type"), "application/json; charset=utf-8")
        self.assertEqual(response.headers.get("OData-Version"), "4.0")
        self.assertEqual(
            response.text,
            '{"error":{"code":"278","message":"\'dummy\' ' "can not be found in collection of type 'Process'.\"}}",
        )

    def test_live_request_body_compression_roundtrip(self):
        """End-to-end: a gzip-compressed request body is accepted by the live server and
        round-trips correctly. Creates a process with a body well above the default threshold,
        reads it back, and confirms our marker survived server-side decompression."""
        config = dict(self.config["tm1srv01"])
        config["compress_request_body"] = "True"
        config["gzip_min_bytes"] = "1"

        process_name = "TM1py_Tests_gzip_" + str(uuid.uuid4()).replace("-", "")
        marker = "sMarker = '" + process_name + "';"
        # build a prolog comfortably larger than the default 1024-byte threshold
        prolog = marker + "\r\n" + "\r\n".join(f"sFiller{i} = '{i}';" for i in range(300))

        with TM1Service(**config) as tm1:
            self.assertTrue(tm1._tm1_rest._compress_request_body)
            process = Process(name=process_name, datasource_type="None", prolog_procedure=prolog)
            try:
                tm1.processes.create(process)
                retrieved = tm1.processes.get(process_name)
                self.assertEqual(process_name, retrieved.name)
                self.assertIn(marker, retrieved.prolog_procedure)
            finally:
                if tm1.processes.exists(process_name):
                    tm1.processes.delete(process_name)

    @classmethod
    def tearDownClass(cls):
        cls.tm1.logout()


class _FakeResponse:
    """Minimal stand-in for a requests.Response used by the seam-level unit tests."""

    def __init__(self, status_code: int, headers: dict = None, text: str = ""):
        self.status_code = status_code
        self.ok = 200 <= status_code < 300
        self.headers = headers or {}
        self.text = text
        self.reason = "OK" if self.ok else "ERROR"
        self.encoding = None
        self.content = text.encode("utf-8") if isinstance(text, str) else text


class _RecordingSession:
    """Captures the (data, headers) handed to the transport so tests can assert on the wire bytes."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def request(self, method, url, data=None, verify=None, timeout=None, **kwargs):
        self.calls.append({"method": method, "url": url, "data": data, "headers": kwargs.get("headers")})
        return self._responses.pop(0)

    def close(self):
        pass


class TestRequestBodyCompressionHelper(unittest.TestCase):
    """Unit tests for RestService._maybe_compress_body (no server connection)."""

    @staticmethod
    def _rest(min_bytes: int = 1024, level: int = 6) -> RestService:
        rest = object.__new__(RestService)
        rest._compress_request_body = True
        rest._gzip_min_bytes = min_bytes
        rest._gzip_compress_level = level
        return rest

    def test_compress_roundtrip_sets_header(self):
        rest = self._rest(min_bytes=1)
        body = b'{"value": "' + b"x" * 2000 + b'"}'
        data, headers = rest._maybe_compress_body(body, {"Content-Type": "application/json"})
        self.assertEqual(headers["Content-Encoding"], "gzip")
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertEqual(gzip.decompress(data), body)
        self.assertLess(len(data), len(body))

    def test_below_threshold_not_compressed(self):
        rest = self._rest(min_bytes=1024)
        body = b'{"a": 1}'
        data, headers = rest._maybe_compress_body(body, {"Content-Type": "application/json"})
        self.assertEqual(data, body)
        self.assertNotIn("Content-Encoding", headers)

    def test_empty_body_not_compressed(self):
        rest = self._rest(min_bytes=1)
        data, headers = rest._maybe_compress_body(b"", {})
        self.assertEqual(data, b"")
        self.assertNotIn("Content-Encoding", headers)

    def test_bytes_path_compressed(self):
        rest = self._rest(min_bytes=1)
        body = b"binary-content-" + b"\x00\x01\x02" * 1000
        data, headers = rest._maybe_compress_body(body, {})
        self.assertEqual(headers["Content-Encoding"], "gzip")
        self.assertEqual(gzip.decompress(data), body)

    def test_bytesio_path_compressed_and_not_consumed(self):
        rest = self._rest(min_bytes=1)
        raw = b"stream-content-" + b"abc" * 1000
        stream = BytesIO(raw)
        data, headers = rest._maybe_compress_body(stream, {})
        self.assertEqual(headers["Content-Encoding"], "gzip")
        self.assertEqual(gzip.decompress(data), raw)
        # the original BytesIO must remain intact (reading it does not consume it)
        self.assertEqual(stream.getvalue(), raw)

    def test_bytesio_path_reads_from_current_position(self):
        # a caller may hand in a partially-read stream; we must compress exactly what the
        # transport would otherwise upload (current position -> EOF) and leave the pointer put
        rest = self._rest(min_bytes=1)
        raw = b"header-to-skip-" + b"payload" * 1000
        offset = len(b"header-to-skip-")
        stream = BytesIO(raw)
        stream.seek(offset)
        data, headers = rest._maybe_compress_body(stream, {})
        self.assertEqual(headers["Content-Encoding"], "gzip")
        # only the bytes from the current position onward are compressed
        self.assertEqual(gzip.decompress(data), raw[offset:])
        # the stream pointer is restored so the original stays usable
        self.assertEqual(stream.tell(), offset)

    def test_preexisting_content_encoding_not_recompressed(self):
        rest = self._rest(min_bytes=1)
        already = gzip.compress(b"x" * 2000)
        data, headers = rest._maybe_compress_body(already, {"Content-Encoding": "gzip"})
        self.assertEqual(data, already)
        # body is returned untouched - not gzipped a second time
        self.assertEqual(gzip.decompress(data), b"x" * 2000)

    def test_preexisting_content_encoding_case_insensitive(self):
        rest = self._rest(min_bytes=1)
        body = b"y" * 2000
        data, headers = rest._maybe_compress_body(body, {"content-encoding": "identity"})
        self.assertEqual(data, body)

    def test_content_length_dropped_on_compression(self):
        rest = self._rest(min_bytes=1)
        body = b"z" * 2000
        data, headers = rest._maybe_compress_body(body, {"Content-Length": "2000", "Content-Type": "text/plain"})
        self.assertEqual(headers["Content-Encoding"], "gzip")
        self.assertNotIn("Content-Length", headers)
        self.assertEqual(headers["Content-Type"], "text/plain")


class TestRequestBodyCompressionSeam(unittest.TestCase):
    """Tests that compression is applied once at request() and survives the retry path."""

    @staticmethod
    def _rest(responses, compress=True, min_bytes=1) -> RestService:
        rest = object.__new__(RestService)
        rest._base_url = "https://tm1.example/api/v1"
        rest._headers = {"Content-Type": "application/json; charset=utf-8"}
        rest._compress_request_body = compress
        rest._gzip_min_bytes = min_bytes
        rest._gzip_compress_level = 6
        rest._timeout = None
        rest._cancel_at_timeout = False
        rest._async_requests_mode = False
        rest._re_connect_on_session_timeout = True
        rest._verify = False
        rest._s = _RecordingSession(responses)
        rest.connect = lambda: None
        return rest

    def test_post_stamps_content_encoding_and_compresses(self):
        rest = self._rest([_FakeResponse(200)])
        body = '{"value": "' + "x" * 2000 + '"}'
        rest.POST(url="/Cubes", data=body)

        self.assertEqual(len(rest._s.calls), 1)
        call = rest._s.calls[0]
        self.assertEqual(call["headers"]["Content-Encoding"], "gzip")
        self.assertEqual(gzip.decompress(call["data"]), body.encode("utf-8"))

    def test_default_off_sends_raw_body(self):
        rest = self._rest([_FakeResponse(200)], compress=False)
        body = '{"value": "' + "x" * 2000 + '"}'
        rest.POST(url="/Cubes", data=body)

        call = rest._s.calls[0]
        self.assertNotIn("Content-Encoding", call["headers"])
        self.assertEqual(call["data"], body.encode("utf-8"))

    def test_retry_after_401_not_double_compressed(self):
        rest = self._rest([_FakeResponse(401), _FakeResponse(200)])
        body = '{"value": "' + "x" * 2000 + '"}'
        rest.POST(url="/Cubes", data=body)

        # initial send + one retry after reconnect
        self.assertEqual(len(rest._s.calls), 2)
        first, second = rest._s.calls
        # both sends carry the identical, single-member gzip body and exactly one Content-Encoding
        self.assertEqual(first["data"], second["data"])
        self.assertEqual(gzip.decompress(second["data"]), body.encode("utf-8"))
        self.assertEqual(first["headers"]["Content-Encoding"], "gzip")
        self.assertEqual(second["headers"]["Content-Encoding"], "gzip")


class TestRequestBodyCompressionInitValidation(unittest.TestCase):
    """gzip_compress_level is validated at construction, before any network call."""

    def test_out_of_range_level_raises_value_error(self):
        # values outside 1..9 would otherwise raise a zlib.error deep inside gzip.compress
        # at request time; we fail fast in __init__ with a clear message instead. The check
        # runs before connect(), so no live server is required.
        for level in (0, 10, -1):
            with self.subTest(level=level):
                with self.assertRaises(ValueError) as ctx:
                    RestService(gzip_compress_level=level)
                self.assertIn("gzip_compress_level", str(ctx.exception))
