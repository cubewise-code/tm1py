"""Interactive OAuth sign-in for Planning Analytics Workspace (PAW).

``PawOAuthSession`` runs the OAuth 2.0 authorization-code flow with PKCE against a
PAW deployment, holds the resulting tokens, and refreshes the access token on demand.
It is deliberately kept outside ``RestService``: the flow is interactive (it opens a
browser), so the calling application decides when an interactive sign-in is
acceptable, and TM1py itself stays usable headless.

Typical use::

    from TM1py import TM1Service
    from TM1py.Utils.PawOAuth import PawOAuthSession

    oauth = PawOAuthSession(
        auth_url="https://<host>/oauth2/authorize",
        token_url="https://<host>/oauth2/token",
        client_id="<client id>",
        client_secret=keyring.get_password("paw", "client_secret"),  # caller supplies
        redirect_uri="http://127.0.0.1:8080/callback",
    )
    oauth.login()  # opens a browser once

    with TM1Service(
        base_url="https://<host>/api/v1/tm1/<database>",  # see base URLs below
        access_token=oauth.access_token,  # a callable: resolved on every (re)connect
        keep_authorization_header=True,  # the PAW gateway checks every request
    ) as tm1:
        print(tm1.whoami)

``<host>`` is the host you sign in to PAW on. The ``base_url`` must be PAW's API
route, which accepts the bearer token, not TM1's own REST endpoint:

* TM1 11 on IBM Cloud (``<env>.planning-analytics.cloud.ibm.com``):
  ``https://<host>/api/v1/tm1/<database>``. The ``/tm1/api/<database>`` route only
  accepts CAM authentication.
* TM1 12 Planning Analytics as a Service (``<region>.planninganalytics.saas.ibm.com``):
  ``https://<host>/api/<tenant>/v0/tm1/<database>``.

Design notes:

* PKCE is always sent. Servers that enforce it require it; servers that ignore it
  are unaffected, so it never needs per-server configuration.
* The client secret is a parameter, not fetched here. The caller reads it (e.g. from
  ``keyring``) or passes ``None`` for a public client.
* Refresh-token caching is pluggable and defaults to in-memory. Pass a ``TokenCache``
  to keep the refresh token between processes.
* Standard library only, apart from ``requests`` for the token calls.
"""

from __future__ import annotations

import base64
import hashlib
import http.server
import os
import secrets
import socket
import threading
import time
import webbrowser
from typing import Optional, Tuple
from urllib.parse import parse_qs, urlencode, urlparse

import requests

__all__ = ["PawOAuthSession", "TokenCache", "InMemoryTokenCache", "OAuthError"]

DEFAULT_SCOPE = "v0userContext"
# Refresh a little before the token actually expires, to absorb clock skew and the
# round-trip of the request the token is about to be used on.
EXPIRY_SKEW_SECONDS = 60


class OAuthError(RuntimeError):
    """Raised when the authorization or token exchange fails."""


class TokenCache:
    """Persistence interface for the refresh token.

    Subclass this (or provide an object with the same two methods) to keep the refresh
    token between processes, for example backed by ``keyring``.
    """

    def load_refresh_token(self) -> Optional[str]:
        """Return the stored refresh token, or None if none is stored."""
        raise NotImplementedError

    def save_refresh_token(self, refresh_token: Optional[str]) -> None:
        """Store the refresh token, or clear it when given None."""
        raise NotImplementedError


class InMemoryTokenCache(TokenCache):
    """Default cache: holds the refresh token in memory for this process only."""

    def __init__(self) -> None:
        self._refresh_token: Optional[str] = None

    def load_refresh_token(self) -> Optional[str]:
        return self._refresh_token

    def save_refresh_token(self, refresh_token: Optional[str]) -> None:
        self._refresh_token = refresh_token


class _RedirectHandler(http.server.BaseHTTPRequestHandler):
    """One-shot handler that captures the authorization redirect's query parameters."""

    # Browsers open speculative connections that send nothing. Requests are handled
    # one at a time, so without a read timeout one of those would block the listener.
    timeout = 5

    def do_GET(self):  # name fixed by BaseHTTPRequestHandler
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        if parsed.path == self.server.expected_path and ("code" in params or "error" in params):
            self.server.captured = params
            body = b"Sign-in received. You can close this tab and return to the application."
        else:
            body = b"Waiting for the sign-in redirect..."
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"<html><body>" + body + b"</body></html>")

    def log_message(self, *args):  # silence default logging
        return


class _RedirectServer(http.server.HTTPServer):
    """Temporary loopback listener for the authorization redirect."""

    # On Windows, SO_REUSEADDR lets this bind a port another process is already
    # listening on, so the redirect could go to that process instead. Only reuse
    # the address elsewhere, where it just avoids TIME_WAIT on a quick re-login.
    allow_reuse_address = os.name != "nt"

    def __init__(self, host: str, port: int, expected_path: str) -> None:
        if ":" in host:
            self.address_family = socket.AF_INET6
        super().__init__((host, port), _RedirectHandler)
        self.expected_path = expected_path
        self.captured: dict = {}
        self.timeout = 1


class PawOAuthSession:
    """Runs the PAW OAuth authorization-code + PKCE flow and supplies access tokens."""

    def __init__(
        self,
        auth_url: str,
        token_url: str,
        client_id: str,
        redirect_uri: str,
        client_secret: Optional[str] = None,
        scope: str = DEFAULT_SCOPE,
        cache: Optional[TokenCache] = None,
        timeout: int = 30,
    ) -> None:
        """Create a session.

        :param auth_url: The deployment's /oauth2/authorize endpoint.
        :param token_url: The deployment's /oauth2/token endpoint.
        :param client_id: The OAuth client ID.
        :param redirect_uri: A loopback redirect registered on the client, e.g.
            "http://127.0.0.1:8080/callback". Its host must be 127.0.0.1 or [::1]
            (not localhost); its port is where the temporary listener binds.
        :param client_secret: The client secret, or None for a public client. The caller
            supplies this (e.g. from keyring); it is never read from storage here.
        :param scope: OAuth scope.
        :param cache: A TokenCache for the refresh token. Defaults to in-memory only.
        :param timeout: Seconds to wait for each token HTTP request.
        :raises ValueError: If a required value is missing or the redirect is not a loopback URL.
        """
        for name, value in (
            ("auth_url", auth_url),
            ("token_url", token_url),
            ("client_id", client_id),
            ("redirect_uri", redirect_uri),
        ):
            if not value:
                raise ValueError(f"{name} is required")
        parsed = urlparse(redirect_uri)
        # Loopback IP literals only (RFC 8252 section 8.3): "localhost" may resolve to
        # ::1 in the browser while the listener is on 127.0.0.1, or vice versa.
        if parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "::1"):
            raise ValueError(
                "redirect_uri must be an http loopback URL using 127.0.0.1 or [::1], "
                "not localhost; register that URI on the client"
            )
        if not parsed.port:
            raise ValueError("redirect_uri must include an explicit port, e.g. 127.0.0.1:8080")

        self._auth_url = auth_url
        self._token_url = token_url
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri
        self._scope = scope
        self._cache = cache or InMemoryTokenCache()
        self._timeout = timeout

        self._lock = threading.Lock()
        self._access_token: Optional[str] = None
        self._expires_at: float = 0.0

    # -- public API ---------------------------------------------------------------

    def login(self, open_browser: bool = True, listener_timeout: int = 180) -> None:
        """Run the interactive browser flow and obtain the first tokens.

        If a refresh token is already cached, this tries a silent refresh first and
        only opens a browser if that fails.

        :param open_browser: Open the authorize URL automatically. If False, the URL is
            printed for the user to open manually.
        :param listener_timeout: Seconds to wait for the browser redirect.
        :raises OAuthError: If authorization or the token exchange fails.
        """
        cached_refresh = self._cache.load_refresh_token()
        if cached_refresh:
            try:
                self._refresh(cached_refresh)
                return
            except OAuthError:
                pass  # cached refresh token stale; fall back to interactive login
        code, verifier = self._authorize(open_browser, listener_timeout)
        self._exchange_code(code, verifier)

    def access_token(self) -> str:
        """Return a currently valid access token, refreshing if necessary.

        This is the callable to pass as TM1py's ``access_token``: TM1py calls it on
        every connect and reconnect, so a reconnect after a session timeout picks up
        a freshly refreshed token rather than a stale one.

        :raises OAuthError: If no token is available and none can be refreshed. Call
            ``login()`` first.
        """
        with self._lock:
            if self._access_token and time.monotonic() < self._expires_at - EXPIRY_SKEW_SECONDS:
                return self._access_token
            refresh_token = self._cache.load_refresh_token()
            if not refresh_token:
                raise OAuthError("No valid access token and no refresh token; call login() first.")
            self._refresh(refresh_token, _already_locked=True)
            return self._access_token

    @property
    def has_refresh_token(self) -> bool:
        """Whether a refresh token is currently cached."""
        return bool(self._cache.load_refresh_token())

    # -- internals ----------------------------------------------------------------

    @staticmethod
    def _make_verifier_and_challenge() -> Tuple[str, str]:
        verifier = secrets.token_urlsafe(64)
        digest = hashlib.sha256(verifier.encode("ascii")).digest()
        challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
        return verifier, challenge

    def _authorize(self, open_browser: bool, listener_timeout: int) -> Tuple[str, str]:
        verifier, challenge = self._make_verifier_and_challenge()
        state = secrets.token_urlsafe(16)
        params = {
            "response_type": "code",
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "scope": self._scope,
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
        url = f"{self._auth_url}?{urlencode(params)}"

        # Listen before opening the browser: an already signed-in user can be
        # redirected back almost instantly, before a late listener would be bound.
        server = self._open_listener()
        try:
            if open_browser:
                webbrowser.open(url)
            else:
                print(f"Open this URL to sign in:\n{url}")
            captured = self._wait_for_redirect(server, listener_timeout)
        finally:
            server.server_close()

        if not captured:
            raise OAuthError(
                f"No redirect received within {listener_timeout}s on "
                f"{self._redirect_uri}. Is the URI registered on the client?"
            )
        if "error" in captured:
            raise OAuthError(
                f"Authorization failed: {captured['error'][0]} " f"{captured.get('error_description', [''])[0]}".strip()
            )
        if captured.get("state", [None])[0] != state:
            raise OAuthError("State in the redirect did not match the request; aborting.")
        return captured["code"][0], verifier

    def _open_listener(self) -> _RedirectServer:
        parsed = urlparse(self._redirect_uri)
        try:
            return _RedirectServer(parsed.hostname, parsed.port, parsed.path or "/")
        except OSError as error:
            raise OAuthError(
                f"Could not listen on {self._redirect_uri} ({error}). Is another process using port {parsed.port}?"
            ) from error

    @staticmethod
    def _wait_for_redirect(server: _RedirectServer, listener_timeout: int) -> dict:
        deadline = time.monotonic() + listener_timeout
        while not server.captured and time.monotonic() < deadline:
            server.handle_request()
        return server.captured

    def _token_request(self, data: dict) -> dict:
        auth = None
        if self._client_secret is not None:
            auth = (self._client_id, self._client_secret)
        else:
            data = {**data, "client_id": self._client_id}
        try:
            response = requests.post(
                self._token_url,
                data=data,
                auth=auth,
                timeout=self._timeout,
                headers={"Accept": "application/json"},
            )
        except requests.RequestException as error:
            raise OAuthError(f"Token request to {self._token_url} failed: {error}") from error
        try:
            body = response.json()
        except ValueError:
            body = {}
        if not isinstance(body, dict):
            body = {}
        if not response.ok or "access_token" not in body:
            raise OAuthError(
                f"Token endpoint returned HTTP {response.status_code}: "
                f"{body.get('error', response.text[:200])!r} "
                f"{body.get('error_description', '')!r}".strip()
            )
        return body

    def _store(self, body: dict, _already_locked: bool = False) -> None:
        def apply():
            self._access_token = body["access_token"]
            # Treat expires_in as seconds from now; default to one hour if absent.
            self._expires_at = time.monotonic() + float(body.get("expires_in", 3600))
            if body.get("refresh_token"):
                self._cache.save_refresh_token(body["refresh_token"])

        if _already_locked:
            apply()
        else:
            with self._lock:
                apply()

    def _exchange_code(self, code: str, verifier: str) -> None:
        body = self._token_request(
            {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self._redirect_uri,
                "code_verifier": verifier,
            }
        )
        self._store(body)

    def _refresh(self, refresh_token: str, _already_locked: bool = False) -> None:
        body = self._token_request(
            {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            }
        )
        self._store(body, _already_locked=_already_locked)
