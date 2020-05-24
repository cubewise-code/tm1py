import configparser
import unittest
from pathlib import Path

from requests import Response

from TM1py import TM1Service
from TM1py.Services.RestService import RestService

config = configparser.ConfigParser()
config.read(Path(__file__).parent.joinpath('config.ini'))


class TestRestServiceMethods(unittest.TestCase):
    tm1 = None

    @classmethod
    def setUpClass(cls):
        cls.tm1 = TM1Service(**config['tm1srv01'])

    def test_wait_time_generator_with_timeout(self):
        self.assertEqual(
            [0.1, 0.3, 0.6, 1, 1, 1, 1, 1, 1, 1, 1, 1],
            list(self.tm1._tm1_rest.wait_time_generator(10)))
        self.assertEqual(sum(self.tm1._tm1_rest.wait_time_generator(10)), 10)

    def test_wait_time_generator_without_timeout(self):
        generator = self.tm1._tm1_rest.wait_time_generator(None)
        self.assertEqual(0.1, next(generator))
        self.assertEqual(0.3, next(generator))
        self.assertEqual(0.6, next(generator))
        self.assertEqual(1, next(generator))
        self.assertEqual(1, next(generator))

    def test_build_response_from_async_response_ok(self):
        response = Response()
        response._content = b'HTTP/1.1 200 OK\r\nContent-Length: 32\r\nConnection: keep-alive\r\nContent-Encoding: ' \
                            b'gzip\r\nCache-Control: no-cache\r\nContent-Type: text/plain; charset=utf-8\r\n' \
                            b'OData-Version: 4.0\r\n\r\n\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x0b34\xd43\xd730000' \
                            b'\xd23\x04\x00\xf4\x1c\xa0j\x0c\x00\x00\x00'
        response = RestService.build_response_from_async_response(response=response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("Content-Length"), "32")
        self.assertEqual(response.headers.get("Connection"), "keep-alive")
        self.assertEqual(response.headers.get("Content-Encoding"), "gzip")
        self.assertEqual(response.headers.get("Cache-Control"), "no-cache")
        self.assertEqual(response.headers.get("Content-Type"), "text/plain; charset=utf-8")
        self.assertEqual(response.headers.get("OData-Version"), "4.0")
        self.assertEqual(response.text, "11.7.00002.1")

    def test_build_response_from_async_response_not_found(self):
        response = Response()
        response._content = b'HTTP/1.1 404 Not Found\r\nContent-Length: 105\r\nConnection: keep-alive\r\n' \
                            b'Content-Encoding: gzip\r\nCache-Control: no-cache\r\n' \
                            b'Content-Type: application/json; charset=utf-8\r\nOData-Version: 4.0\r\n' \
                            b'\r\n\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x0b\x15\xc71\n\x800\x0c\x05\xd0\xab|\xb2t\x11' \
                            b'\x07\x17\xc5Sx\x05M\xa3\x14\xdaD\xda:\x94\xe2\xdd\xc5\xb7\xbdN\x92\xb3eZ;\xb1y\xa1\x95' \
                            b'\xa6y\xa1\x81\x92\x94\xb2_\xff\x9d\x7fRj\x0e\xbc+\xd4*\x0e\xc1i\x8fz\x04\x05[\x8c\xc25' \
                            b'\x98\xc2N\xd4v\x0b\xdc\x96\x8d\xa5\x147\xd2\xfb~Od\xf8E^\x00\x00\x00'
        response = RestService.build_response_from_async_response(response=response)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.headers.get("Content-Length"), "105")
        self.assertEqual(response.headers.get("Connection"), "keep-alive")
        self.assertEqual(response.headers.get("Content-Encoding"), "gzip")
        self.assertEqual(response.headers.get("Cache-Control"), "no-cache")
        self.assertEqual(response.headers.get("Content-Type"), "application/json; charset=utf-8")
        self.assertEqual(response.headers.get("OData-Version"), "4.0")
        self.assertEqual(
            response.text,
            "{\"error\":{\"code\":\"278\",\"message\":\"\'dummy\' can not be found in collection of type \'Process\'.\"}}")

    @classmethod
    def tearDownClass(cls):
        cls.tm1.logout()
