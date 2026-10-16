import sys
import unittest
from unittest.mock import patch

import requests

from TM1py.Services.RestService import AuthenticationMode, RestService
from TM1py.Utils.PawOAuth import (
    DEFAULT_REDIRECT_URI,
    InMemoryTokenCache,
    KeyringTokenCache,
    PawOAuthSession,
)

V11_BASE_URL = "https://env.planning-analytics.cloud.ibm.com/api/v1/tm1/CONS"
V12_BASE_URL = "https://us-east-1.planninganalytics.saas.ibm.com/api/TENANT/v0/tm1/db"


def _ok_response():
    response = requests.Response()
    response.status_code = 200
    response._content = b"12.0.0"
    return response


class TestRestServicePawOAuth(unittest.TestCase):
    """use_paw_oauth: endpoints derived from base_url, login before connect, token wired in.

    The browser sign-in is replaced by a stub that hands out numbered tokens, and
    connect()/set_version() are patched out, so no PAW or TM1 server is needed.
    """

    def setUp(self):
        self.logins = 0
        self.tokens = iter(f"token{n}" for n in range(1, 100))

        def login(oauth, **_):
            self.logins += 1
            oauth._access_token = next(self.tokens)
            oauth._expires_at = float("inf")

        for patcher in (
            patch.object(PawOAuthSession, "login", login),
            patch.object(RestService, "connect"),
            patch.object(RestService, "set_version"),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def _rest(self, base_url=V11_BASE_URL, **kwargs):
        kwargs.setdefault("use_paw_oauth", True)
        kwargs.setdefault("paw_client_id", "cid")
        return RestService(base_url=base_url, **kwargs)

    def test_endpoints_derived_from_v11_base_url(self):
        oauth = self._rest()._paw_oauth

        self.assertEqual(oauth._auth_url, "https://env.planning-analytics.cloud.ibm.com/oauth2/authorize")
        self.assertEqual(oauth._token_url, "https://env.planning-analytics.cloud.ibm.com/oauth2/token")

    def test_endpoints_derived_from_v12_base_url(self):
        oauth = self._rest(V12_BASE_URL)._paw_oauth

        self.assertEqual(oauth._auth_url, "https://us-east-1.planninganalytics.saas.ibm.com/oauth2/authorize")
        self.assertEqual(oauth._token_url, "https://us-east-1.planninganalytics.saas.ibm.com/oauth2/token")

    def test_signs_in_and_uses_access_token_mode(self):
        rest = self._rest(paw_client_secret="s3cret")

        self.assertEqual(self.logins, 1)
        self.assertEqual(rest._auth_mode, AuthenticationMode.ACCESS_TOKEN)
        self.assertTrue(rest._keep_authorization_header)
        self.assertEqual(rest._paw_oauth._client_secret, "s3cret")
        self.assertEqual(rest._paw_oauth._redirect_uri, DEFAULT_REDIRECT_URI)

    def test_session_start_sends_the_oauth_token(self):
        rest = self._rest()
        sent = []

        def get(url, headers, **_):
            sent.append(headers.get("Authorization"))
            return _ok_response()

        rest._s.get = get
        rest._start_session(user=None, password=None)

        self.assertEqual(sent, ["Bearer token1"])
        self.assertEqual(rest._headers["Authorization"], "Bearer token1")  # kept for the gateway

    def test_redirect_uri_can_be_overridden(self):
        rest = self._rest(paw_redirect_uri="http://127.0.0.1:9123/cb")
        self.assertEqual(rest._paw_oauth._redirect_uri, "http://127.0.0.1:9123/cb")

    def test_explicit_keep_authorization_header_is_respected(self):
        self.assertFalse(self._rest(keep_authorization_header=False)._keep_authorization_header)

    def test_cache_choices(self):
        self.assertIsInstance(self._rest(use_paw_oauth=True)._paw_oauth._cache, InMemoryTokenCache)
        self.assertIsInstance(self._rest(use_paw_oauth="in_memory")._paw_oauth._cache, InMemoryTokenCache)
        self.assertIsInstance(self._rest(use_paw_oauth="True")._paw_oauth._cache, InMemoryTokenCache)
        cache = InMemoryTokenCache()
        self.assertIs(self._rest(use_paw_oauth=cache)._paw_oauth._cache, cache)

    def test_keyring_choice(self):
        fake = type(sys)("keyring")
        fake.errors = type(sys)("keyring.errors")
        fake.errors.PasswordDeleteError = Exception
        fake.get_password = lambda service, key: None
        with patch.dict(sys.modules, {"keyring": fake, "keyring.errors": fake.errors}):
            cache = self._rest(use_paw_oauth="keyring")._paw_oauth._cache

        self.assertIsInstance(cache, KeyringTokenCache)

    def test_off_values_do_not_sign_in(self):
        for value in (False, None, "False", "false", ""):
            with self.subTest(value=value):
                rest = RestService(base_url=V11_BASE_URL, user="admin", password="apple", use_paw_oauth=value)
                self.assertIsNone(rest._paw_oauth)
        self.assertEqual(self.logins, 0)

    def test_invalid_combinations_rejected(self):
        cases = [
            dict(use_paw_oauth="memory"),
            dict(paw_client_id=None),
            dict(access_token="abc"),
            dict(base_url=None),
            dict(base_url="not-a-url"),
        ]
        for overrides in cases:
            with self.subTest(**{k: str(v) for k, v in overrides.items()}):
                kwargs = dict(base_url=V11_BASE_URL, use_paw_oauth=True, paw_client_id="cid")
                kwargs.update(overrides)
                with self.assertRaises(ValueError):
                    RestService(**kwargs)
        self.assertEqual(self.logins, 0)


if __name__ == "__main__":
    unittest.main()
