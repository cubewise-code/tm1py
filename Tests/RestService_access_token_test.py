import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from http.client import HTTPMessage
from types import SimpleNamespace
from unittest.mock import patch

import requests
from requests.adapters import HTTPAdapter

from TM1py.Exceptions import TM1pyRestException
from TM1py.Services.RestService import BearerTokenAuth, RestService

BASE_URL = "https://paw.example.com/api/v1/tm1/Planning Sample"

# login replies of a server that starts a cookie-based session
PA_SESSION = (200, {"Set-Cookie": "paSession=abc123; Path=/"})
TM1_SESSION = (200, {"Set-Cookie": "TM1SessionId=q7O6e1w49AixeuLVxJ1GZg; Path=/"})


class FakeTransport:
    """Stands in for the HTTP adapter: records the headers of every request and replies from a
    queue of statuses, each a status code or a (status code, headers) pair (200 once the queue is
    empty). A 'Set-Cookie' header in a reply is stored in the session's cookie jar, as it is for
    a real response."""

    def __init__(self, statuses=()):
        self.statuses = list(statuses)
        self.sent = []

    def send(self, adapter, request, **kwargs):
        self.sent.append((request.method, request.url, dict(request.headers)))
        status = self.statuses.pop(0) if self.statuses else 200
        status, headers = status if isinstance(status, tuple) else (status, {})
        response = requests.Response()
        response.status_code = status
        response.headers.update(headers)
        response._content = b"12.6.4"
        response.url = request.url
        response.request = request
        if "Set-Cookie" in headers:
            # requests reads cookies from the raw urllib3 response, not from response.headers
            message = HTTPMessage()
            message["Set-Cookie"] = headers["Set-Cookie"]
            response.raw = SimpleNamespace(_original_response=SimpleNamespace(msg=message))
        return response

    def authorization(self, n):
        return self.sent[n][2].get("Authorization")


class TokenSequence:
    """A thread-safe token provider returning 'token-1', 'token-2', ... and counting its calls."""

    def __init__(self):
        self.calls = 0
        self._lock = threading.Lock()

    def __call__(self):
        with self._lock:
            self.calls += 1
            return f"token-{self.calls}"


class TestRestServiceAccessToken(unittest.TestCase):
    def connect(self, transport, **kwargs):
        with patch.object(HTTPAdapter, "send", autospec=True, side_effect=transport.send):
            rest = RestService(base_url=BASE_URL, **kwargs)
            rest.GET("/Cubes")
            return rest

    def test_string_token_is_dropped_once_a_session_cookie_is_returned(self):
        for login in (PA_SESSION, TM1_SESSION):
            with self.subTest(login=login):
                transport = FakeTransport([login])
                self.connect(transport, access_token="abc")

                self.assertEqual(transport.authorization(0), "Bearer abc")
                self.assertIsNone(transport.authorization(-1))
                self.assertIn("Cookie", transport.sent[-1][2])

    def test_string_token_is_sent_on_every_request_when_no_session_cookie_is_returned(self):
        transport = FakeTransport()
        rest = self.connect(transport, access_token="abc")
        with self.patched(transport):
            rest.GET("/Dimensions")

        self.assertGreaterEqual(len(transport.sent), 3)
        self.assertEqual({transport.authorization(n) for n in range(len(transport.sent))}, {"Bearer abc"})

    def test_string_token_is_kept_when_only_other_cookies_are_returned(self):
        transport = FakeTransport([(200, {"Set-Cookie": "route=node-3; Path=/"})])
        self.connect(transport, access_token="abc")

        self.assertEqual(transport.authorization(-1), "Bearer abc")

    def test_basic_credentials_are_sent_on_every_request_when_no_session_cookie_is_returned(self):
        transport = FakeTransport()
        self.connect(transport, user="apikey", password="secret")

        login, request = transport.authorization(0), transport.authorization(-1)
        self.assertTrue(login.startswith("Basic "))
        self.assertEqual(request, login)

    def test_basic_credentials_are_dropped_once_a_session_cookie_is_returned(self):
        transport = FakeTransport([TM1_SESSION])
        self.connect(transport, user="admin", password="apple")

        self.assertTrue(transport.authorization(0).startswith("Basic "))
        self.assertIsNone(transport.authorization(-1))

    def test_rejected_string_token_without_session_cookie_raises_401(self):
        transport = FakeTransport()
        rest = self.connect(transport, access_token="abc")

        transport.statuses = [401, 401]  # the request, then the login of the reconnect
        with self.patched(transport), self.assertRaises(TM1pyRestException) as context:
            rest.GET("/Dimensions")

        self.assertEqual(context.exception.status_code, 401)
        self.assertEqual(len(transport.sent), 4, "one reconnect attempt, no retry loop")

    def test_callable_token_is_sent_on_every_request(self):
        transport = FakeTransport()
        provider = TokenSequence()
        rest = self.connect(transport, access_token=provider)

        self.assertIsInstance(rest._s.auth, BearerTokenAuth)
        self.assertEqual(provider.calls, len(transport.sent))
        self.assertEqual(
            [transport.authorization(n) for n in range(len(transport.sent))],
            [f"Bearer token-{n + 1}" for n in range(len(transport.sent))],
        )

    def test_callable_token_change_needs_no_reconnect(self):
        transport = FakeTransport()
        token = {"value": "first"}
        rest = self.connect(transport, access_token=lambda: token["value"])
        session_starts = sum(1 for _, url, _ in transport.sent if url.endswith("ProductVersion/$value"))

        token["value"] = "second"  # what a provider does when it refreshes
        with patch.object(HTTPAdapter, "send", autospec=True, side_effect=transport.send):
            rest.GET("/Dimensions")

        self.assertEqual(transport.authorization(-1), "Bearer second")
        self.assertEqual(
            sum(1 for _, url, _ in transport.sent if url.endswith("ProductVersion/$value")), session_starts
        )

    def test_401_retries_with_a_fresh_token(self):
        provider = TokenSequence()
        transport = FakeTransport()
        rest = self.connect(transport, access_token=provider)
        sent_before = len(transport.sent)

        transport.statuses = [401]
        with patch.object(HTTPAdapter, "send", autospec=True, side_effect=transport.send):
            response = rest.GET("/Dimensions")

        self.assertEqual(response.status_code, 200)
        retried = transport.sent[sent_before:]
        tokens = [headers["Authorization"] for _, _, headers in retried]
        self.assertEqual(len(tokens), len(set(tokens)), "each attempt asks the provider again")

    def test_callable_returning_empty_token_raises(self):
        with self.assertRaisesRegex(ValueError, "access_token"):
            self.connect(FakeTransport(), access_token=lambda: "")

    @staticmethod
    def patched(transport):
        return patch.object(HTTPAdapter, "send", autospec=True, side_effect=transport.send)

    def test_bearer_token_auth_sets_header_on_prepared_request(self):
        prepared = requests.Request("GET", "https://paw.example.com/", auth=BearerTokenAuth(lambda: "abc")).prepare()

        self.assertEqual(prepared.headers["Authorization"], "Bearer abc")

    def test_token_overrides_an_authorization_header_set_on_the_service(self):
        transport = FakeTransport()
        rest = self.connect(transport, access_token=lambda: "fresh")

        rest.add_http_header("Authorization", "Bearer stale")
        with self.patched(transport):
            rest.GET("/Dimensions")

        self.assertEqual(transport.authorization(-1), "Bearer fresh")

    def test_string_token_is_sent_again_when_reconnecting_after_401(self):
        transport = FakeTransport([PA_SESSION])
        rest = self.connect(transport, access_token="abc")
        sent_before = len(transport.sent)

        transport.statuses = [401]
        with self.patched(transport):
            rest.GET("/Dimensions")

        sent = transport.sent[sent_before:]
        session_starts = [headers.get("Authorization") for _, url, headers in sent if url.endswith("$value")]
        self.assertEqual(session_starts, ["Bearer abc"])
        self.assertIsNone(transport.authorization(-1), "the retried request relies on the session cookie")

    def test_async_request_and_its_polling_carry_the_token(self):
        transport = FakeTransport()
        rest = self.connect(transport, access_token=TokenSequence(), async_requests_mode=True)
        sent_before = len(transport.sent)

        transport.statuses = [(202, {"Location": "_async('abc')"}), (200, {"asyncresult": "200 OK"})]
        with self.patched(transport):
            response = rest.GET("/Cubes")

        self.assertEqual(response.status_code, 200)
        sent = transport.sent[sent_before:]
        self.assertEqual(len(sent), 2)
        self.assertIn("_async('abc')", sent[1][1])
        tokens = [headers.get("Authorization") for _, _, headers in sent]
        self.assertTrue(all(token and token.startswith("Bearer token-") for token in tokens))
        self.assertEqual(len(set(tokens)), 2, "the polling request asks the provider again")

    def test_provider_is_called_for_every_request_from_several_threads(self):
        transport = FakeTransport()
        rest = self.connect(transport, access_token=TokenSequence())
        sent_before = len(transport.sent)

        with self.patched(transport), ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(lambda _: rest.GET("/Cubes"), range(40)))

        tokens = [headers.get("Authorization") for _, _, headers in transport.sent[sent_before:]]
        self.assertEqual(len(tokens), 40)
        self.assertEqual(len(set(tokens)), 40)

    def test_provider_error_reaches_the_caller(self):
        state = {"signed_in": True}

        def provider():
            if not state["signed_in"]:
                raise RuntimeError("sign-in required")
            return "abc"

        transport = FakeTransport()
        rest = self.connect(transport, access_token=provider)

        state["signed_in"] = False
        with self.patched(transport), self.assertRaisesRegex(RuntimeError, "sign-in required"):
            rest.GET("/Dimensions")

    def test_callable_token_is_sent_when_reusing_a_session_id(self):
        transport = FakeTransport()
        rest = self.connect(transport, access_token=TokenSequence(), session_id="q7O6e1w49AixeuLVxJ1GZg")

        self.assertIsInstance(rest._s.auth, BearerTokenAuth)
        self.assertTrue(transport.sent)
        self.assertTrue(
            all(headers.get("Authorization", "").startswith("Bearer token-") for _, _, headers in transport.sent)
        )

    def test_re_authenticate_keeps_a_single_token_hook(self):
        transport = FakeTransport()
        provider = TokenSequence()
        rest = self.connect(transport, access_token=provider)

        with self.patched(transport):
            rest.connect()
            calls_before = provider.calls
            rest.GET("/Dimensions")

        self.assertIsInstance(rest._s.auth, BearerTokenAuth)
        self.assertEqual(provider.calls, calls_before + 1, "one provider call per request, not one per hook")


if __name__ == "__main__":
    unittest.main()
