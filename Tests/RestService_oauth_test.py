"""Live tests for a callable access_token against a TM1 route that authenticates every request with
an OAuth bearer token, such as Planning Analytics Workspace's /api/v1/tm1/<DatabaseName>.

Needs an [oauth] section in Tests/config.ini; skipped without one. Either a fixed access token
(valid about an hour; the refresh test is skipped):

    [oauth]
    base_url=https://<PawHost>/api/v1/tm1/<DatabaseName>
    access_token=<access token>

or refresh settings, which cover all tests and win if both are given:

    [oauth]
    base_url=https://<PawHost>/api/v1/tm1/<DatabaseName>
    token_url=https://<PawHost>/oauth2/token
    client_id=<OAuth client id>
    client_secret=<OAuth client secret>
    refresh_token_file=<path to a file holding a refresh token>

PAW replaces the refresh token on every refresh and the old one stops working, so the tests write
the new one back to refresh_token_file. Each run refreshes twice.
"""

import configparser
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional
from unittest.mock import patch

import requests

from TM1py import TM1Service
from TM1py.Exceptions import TM1pyRestException
from TM1py.Services.RestService import BearerTokenAuth

CONFIG = configparser.ConfigParser()
CONFIG.read(Path(__file__).parent.joinpath("config.ini"))

REFRESH_SETTINGS = ("token_url", "client_id", "client_secret", "refresh_token_file")


class TokenProvider:
    """A minimal caller-side token provider: hands out the current access token and counts how often
    TM1py asks for it. With refresh settings, it can also refresh the token and saves the replaced
    refresh token."""

    def __init__(
        self,
        access_token: Optional[str] = None,
        token_url: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        refresh_token_file: Optional[str] = None,
    ):
        self._access_token = access_token
        self._token_url = token_url
        self._client_id = client_id
        self._client_secret = client_secret
        self._refresh_token_file = Path(refresh_token_file) if refresh_token_file else None
        self._lock = threading.Lock()
        self.calls = 0

    @property
    def can_refresh(self) -> bool:
        return self._refresh_token_file is not None

    def __call__(self) -> str:
        with self._lock:
            self.calls += 1
            return self._access_token

    def refresh(self) -> str:
        with self._lock:
            response = requests.post(
                self._token_url,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self._refresh_token_file.read_text(encoding="utf-8").strip(),
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
                timeout=30,
            )
            response.raise_for_status()
            body = response.json()
            if body.get("refresh_token"):
                self._refresh_token_file.write_text(body["refresh_token"], encoding="utf-8")
            self._access_token = body["access_token"]
            return self._access_token


@unittest.skipUnless(CONFIG.has_section("oauth"), "requires an [oauth] section in Tests/config.ini")
class TestRestServiceOAuth(unittest.TestCase):
    tm1: TM1Service
    provider: TokenProvider

    @classmethod
    def setUpClass(cls):
        oauth = CONFIG["oauth"]
        cls.base_url = oauth["base_url"]
        if all(oauth.get(key) for key in REFRESH_SETTINGS):
            cls.provider = TokenProvider(**{key: oauth[key] for key in REFRESH_SETTINGS})
            cls.provider.refresh()
        elif oauth.get("access_token"):
            cls.provider = TokenProvider(access_token=oauth["access_token"])
        else:
            raise unittest.SkipTest(
                "[oauth] needs access_token, or token_url, client_id, client_secret and refresh_token_file"
            )
        cls.tm1 = TM1Service(base_url=cls.base_url, access_token=cls.provider)

    @classmethod
    def tearDownClass(cls):
        cls.tm1.logout()

    def session_id(self):
        return self.tm1._tm1_rest.GET("/ActiveSession?$select=ID").json()["ID"]

    def test_connects_with_callable_access_token(self):
        self.assertIsInstance(self.tm1._tm1_rest._s.auth, BearerTokenAuth)
        self.assertTrue(self.tm1._tm1_rest.is_connected())
        self.assertTrue(self.tm1.whoami.name)

    def test_provider_is_asked_once_per_request(self):
        calls_before = self.provider.calls

        for _ in range(3):
            self.tm1.server.get_product_version()

        self.assertEqual(self.provider.calls - calls_before, 3)

    def test_refresh_mid_session_needs_no_reconnect(self):
        if not self.provider.can_refresh:
            self.skipTest("requires refresh settings in [oauth]")
        rest = self.tm1._tm1_rest
        session_before = self.session_id()

        # wraps= keeps the real connect working while recording any call to it
        with patch.object(rest, "connect", wraps=rest.connect) as connect:
            new_token = self.provider.refresh()
            response = rest.GET("/ActiveSession?$select=ID")

        # PAW keeps accepting the old access token after a refresh, so only the sent header
        # shows that the request picked up the new token
        self.assertEqual(response.request.headers["Authorization"], f"Bearer {new_token}")
        connect.assert_not_called()
        self.assertEqual(response.json()["ID"], session_before)

    def test_concurrent_requests(self):
        calls_before = self.provider.calls

        with ThreadPoolExecutor(max_workers=4) as pool:
            versions = list(pool.map(lambda _: self.tm1.server.get_product_version(), range(8)))

        self.assertEqual(len(set(versions)), 1)
        self.assertEqual(self.provider.calls - calls_before, 8)

    def test_async_requests_mode(self):
        with TM1Service(base_url=self.base_url, access_token=self.provider, async_requests_mode=True) as tm1:
            self.assertEqual(tm1.server.get_product_version(), self.tm1.server.get_product_version())

    def test_invalid_token_is_rejected(self):
        with self.assertRaises(TM1pyRestException) as context:
            TM1Service(base_url=self.base_url, access_token=lambda: "not-a-token")

        self.assertEqual(context.exception.status_code, 401)


if __name__ == "__main__":
    unittest.main()
