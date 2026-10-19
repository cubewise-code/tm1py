import unittest
from unittest.mock import patch

import requests

from TM1py.Services.RestService import AuthenticationMode, RestService

BASE_URL = "https://tm1.example.com/api/v1/tm1/CONS"


def _ok_response():
    response = requests.Response()
    response.status_code = 200
    response._content = b"12.0.0"
    return response


class TestRestServiceAuthorizationHeader(unittest.TestCase):
    """Bearer-token session start: keep_authorization_header and callable access_token.

    Builds a real RestService with connect() and set_version() patched out, then runs the real
    _start_session against a stubbed HTTP GET, so no TM1 server is needed.
    """

    def _rest(self, **kwargs):
        with patch.object(RestService, "connect"), patch.object(RestService, "set_version"):
            rest = RestService(base_url=BASE_URL, **kwargs)
        self.assertEqual(rest._auth_mode, AuthenticationMode.ACCESS_TOKEN)
        self.sent_authorization = []

        def get(url, headers, **_):
            self.sent_authorization.append(headers.get("Authorization"))
            return _ok_response()

        rest._s.get = get
        return rest

    def _start_session(self, rest):
        rest._start_session(user=None, password=None)

    def test_header_removed_by_default(self):
        rest = self._rest(access_token="abc")
        self._start_session(rest)

        self.assertEqual(self.sent_authorization, ["Bearer abc"])
        self.assertNotIn("Authorization", rest._headers)

    def test_header_kept_when_flag_on(self):
        rest = self._rest(access_token="abc", keep_authorization_header=True)
        self._start_session(rest)

        self.assertEqual(rest._headers["Authorization"], "Bearer abc")

    def test_flag_given_as_false_string_stays_off(self):
        """config.ini values arrive as strings; "False" must not switch the option on."""
        rest = self._rest(access_token="abc", keep_authorization_header="False")
        self._start_session(rest)

        self.assertNotIn("Authorization", rest._headers)

    def test_callable_token_is_resolved_on_every_session_start(self):
        tokens = iter(["first", "second"])
        rest = self._rest(access_token=lambda: next(tokens), keep_authorization_header=True)

        self._start_session(rest)
        self._start_session(rest)

        self.assertEqual(self.sent_authorization, ["Bearer first", "Bearer second"])
        self.assertEqual(rest._headers["Authorization"], "Bearer second")

    def test_callable_returning_empty_token_raises(self):
        rest = self._rest(access_token=lambda: "")

        with self.assertRaises(ValueError):
            self._start_session(rest)


if __name__ == "__main__":
    unittest.main()
