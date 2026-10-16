import base64
import hashlib
import json
import socket
import threading
import time
import unittest
import urllib.request
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import requests

from TM1py.Utils import PawOAuth
from TM1py.Utils.PawOAuth import InMemoryTokenCache, OAuthError, PawOAuthSession


def _free_port(host="127.0.0.1"):
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    with socket.socket(family) as s:
        s.bind((host, 0))
        return s.getsockname()[1]


def _ipv6_available():
    try:
        _free_port("::1")
        return True
    except OSError:
        return False


def _session(redirect_uri=None, **kwargs):
    redirect_uri = redirect_uri or f"http://127.0.0.1:{_free_port()}/callback"
    return PawOAuthSession(
        auth_url="https://paw.example.com/oauth2/authorize",
        token_url="https://paw.example.com/oauth2/token",
        client_id="cid",
        redirect_uri=redirect_uri,
        **kwargs,
    )


def _token_response(status=200, **body):
    response = requests.Response()
    response.status_code = status
    response._content = json.dumps(body).encode("utf-8")
    return response


class _FakeBrowser:
    """Stands in for webbrowser.open: follows the redirect back to the listener at once."""

    def __init__(self, preconnect=False, query=None):
        self.preconnect = preconnect
        self.query = query

    def __call__(self, url):
        params = parse_qs(urlparse(url).query)
        redirect = params["redirect_uri"][0]
        query = self.query or f"code=abc&state={params['state'][0]}"
        target = urlparse(redirect)

        def follow():
            idle = None
            if self.preconnect:  # a speculative connection that never sends anything
                idle = socket.create_connection((target.hostname, target.port))
            urllib.request.urlopen(f"{redirect}?{query}", timeout=30).read()
            if idle:
                idle.close()

        # No delay: the listener must already be bound when the browser opens.
        threading.Thread(target=follow, daemon=True).start()
        return True


class TestRedirectValidation(unittest.TestCase):
    def test_localhost_rejected(self):
        with self.assertRaises(ValueError):
            _session("http://localhost:8080/callback")

    def test_https_rejected(self):
        with self.assertRaises(ValueError):
            _session("https://127.0.0.1:8080/callback")

    def test_port_required(self):
        with self.assertRaises(ValueError):
            _session("http://127.0.0.1/callback")

    def test_missing_client_id_rejected(self):
        with self.assertRaises(ValueError):
            PawOAuthSession("https://a", "https://t", "", "http://127.0.0.1:8080/callback")


class TestRedirectListener(unittest.TestCase):
    def _authorize(self, oauth, browser, listener_timeout=10):
        with patch.object(PawOAuth.webbrowser, "open", browser):
            return oauth._authorize(open_browser=True, listener_timeout=listener_timeout)

    def test_instant_redirect_is_captured(self):
        code, verifier = self._authorize(_session(), _FakeBrowser())
        self.assertEqual(code, "abc")
        self.assertTrue(verifier)

    def test_idle_browser_connection_does_not_block_listener(self):
        start = time.monotonic()
        code, _ = self._authorize(_session(), _FakeBrowser(preconnect=True), listener_timeout=30)
        self.assertEqual(code, "abc")
        self.assertLess(time.monotonic() - start, 10)

    @unittest.skipUnless(_ipv6_available(), "IPv6 loopback not available")
    def test_ipv6_loopback(self):
        oauth = _session(f"http://[::1]:{_free_port('::1')}/callback")
        code, _ = self._authorize(oauth, _FakeBrowser())
        self.assertEqual(code, "abc")

    def test_port_in_use_raises_oauth_error(self):
        with socket.socket() as busy:
            busy.bind(("127.0.0.1", 0))
            busy.listen()
            port = busy.getsockname()[1]
            with self.assertRaisesRegex(OAuthError, str(port)):
                _session(f"http://127.0.0.1:{port}/callback")._open_listener()

    def test_no_redirect_times_out(self):
        with self.assertRaisesRegex(OAuthError, "No redirect received"):
            self._authorize(_session(), lambda url: True, listener_timeout=2)

    def test_state_mismatch_rejected(self):
        with self.assertRaisesRegex(OAuthError, "State"):
            self._authorize(_session(), _FakeBrowser(query="code=abc&state=forged"))

    def test_authorization_error_reported(self):
        with self.assertRaisesRegex(OAuthError, "access_denied"):
            self._authorize(_session(), _FakeBrowser(query="error=access_denied"))


class TestTokens(unittest.TestCase):
    def test_pkce_challenge_matches_verifier(self):
        verifier, challenge = PawOAuthSession._make_verifier_and_challenge()
        expected = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
        self.assertEqual(challenge, expected)
        self.assertTrue(43 <= len(verifier) <= 128)

    def test_access_token_without_login_raises(self):
        with self.assertRaises(OAuthError):
            _session().access_token()

    def test_login_with_cached_refresh_token_skips_browser(self):
        cache = InMemoryTokenCache()
        cache.save_refresh_token("r1")
        oauth = _session(cache=cache)
        response = _token_response(access_token="a1", refresh_token="r2", expires_in=3600)

        with patch.object(PawOAuth.requests, "post", return_value=response) as post, patch.object(
            PawOAuth.webbrowser, "open"
        ) as browser:
            oauth.login()

        browser.assert_not_called()
        self.assertEqual(post.call_args[1]["data"]["grant_type"], "refresh_token")
        self.assertEqual(oauth.access_token(), "a1")
        self.assertEqual(cache.load_refresh_token(), "r2")

    def test_expired_access_token_is_refreshed(self):
        cache = InMemoryTokenCache()
        cache.save_refresh_token("r1")
        oauth = _session(cache=cache)
        responses = [
            _token_response(access_token="short", refresh_token="r2", expires_in=1),
            _token_response(access_token="fresh", expires_in=3600),
        ]

        with patch.object(PawOAuth.requests, "post", side_effect=responses):
            oauth.login()
            # expires_in=1 is inside the refresh margin, so the next call refreshes
            self.assertEqual(oauth.access_token(), "fresh")

        self.assertEqual(cache.load_refresh_token(), "r2")

    def test_public_client_sends_client_id_in_body(self):
        oauth = _session()
        with patch.object(PawOAuth.requests, "post", return_value=_token_response(access_token="a")) as post:
            oauth._exchange_code("abc", "verifier")

        self.assertIsNone(post.call_args[1]["auth"])
        self.assertEqual(post.call_args[1]["data"]["client_id"], "cid")

    def test_confidential_client_uses_basic_auth(self):
        oauth = _session(client_secret="s3cret")
        with patch.object(PawOAuth.requests, "post", return_value=_token_response(access_token="a")) as post:
            oauth._exchange_code("abc", "verifier")

        self.assertEqual(post.call_args[1]["auth"], ("cid", "s3cret"))
        self.assertNotIn("client_id", post.call_args[1]["data"])

    def test_token_error_raises_oauth_error(self):
        oauth = _session()
        response = _token_response(status=400, error="invalid_grant")
        with patch.object(PawOAuth.requests, "post", return_value=response):
            with self.assertRaisesRegex(OAuthError, "invalid_grant"):
                oauth._exchange_code("abc", "verifier")

    def test_non_object_json_raises_oauth_error(self):
        oauth = _session()
        response = requests.Response()
        response.status_code = 200
        response._content = b"[]"
        with patch.object(PawOAuth.requests, "post", return_value=response):
            with self.assertRaises(OAuthError):
                oauth._exchange_code("abc", "verifier")


if __name__ == "__main__":
    unittest.main()
