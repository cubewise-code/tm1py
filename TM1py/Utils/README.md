# OAuth sign-in to Planning Analytics Workspace (TM1py PR #1494)

This document explains how OAuth is used in [cubewise-code/tm1py#1494](https://github.com/cubewise-code/tm1py/pull/1494), *"Add PawOAuthSession for interactive OAuth sign-in to PAW"*.

> **Status:** the PR is a draft and unmerged. Names, defaults and file locations below reflect its latest commits and may change in review.

## What the PR does

It lets a user sign in to **Planning Analytics Workspace (PAW)** through their browser once, then lets `TM1Service` talk to TM1 through PAW's OAuth-protected API route, with tokens refreshed automatically.

It has two parts:

| Part | Location | Role |
|---|---|---|
| `PawOAuthSession` | `TM1py/Utils/PawOAuth.py` (new) | Runs the OAuth flow, holds the tokens, refreshes the access token |
| Changes to `RestService` | `TM1py/Services/RestService.py` | Accepts a *callable* `access_token`, and adds `keep_authorization_header` |

`PawOAuthSession` deliberately lives **outside** `RestService`. The flow opens a browser, so the calling application decides when an interactive sign-in is acceptable, and TM1py itself stays usable headless. Nothing in `TM1py/__init__.py` imports it, so existing connections are unaffected.

## The OAuth flow

It uses the **OAuth 2.0 authorization-code grant with PKCE** (S256).

```
App              PawOAuthSession        Browser          PAW /oauth2          TM1py
 |  login()            |                    |                 |                  |
 |-------------------->| bind 127.0.0.1     |                 |                  |
 |                     | listener           |                 |                  |
 |                     |-- open /authorize (PKCE, state) ---->|                  |
 |                     |<-- redirect with code ---------------|                  |
 |                     |-- exchange code -> access + refresh token ->            |
 |  TM1Service(access_token=oauth.access_token,                                  |
 |             keep_authorization_header=True) ------------------------------->  |
 |                     |<-- access_token() on connect / 401 reconnect ----------|
 |                     |-- refresh if expired -->                                |
```

Step by step:

1. **`login()`** first checks the token cache. If a refresh token is stored, it tries a silent refresh and returns. Only if that fails does it go interactive.
2. **A PKCE verifier and challenge are generated**, plus a random `state` value. PKCE is always sent: servers that enforce it need it, and servers that ignore it are unaffected.
3. **A temporary loopback listener is bound *before* the browser opens**, so an already signed-in user who is redirected back instantly is not refused.
4. **The browser opens `/oauth2/authorize`.** The user signs in to PAW.
5. **PAW redirects to the loopback URI** with `code` and `state`. The listener captures them, and `state` is checked against the request.
6. **The code is exchanged** at `/oauth2/token` for an access token and refresh token.
7. **From then on, `access_token()` is the hook TM1py uses.** It returns the cached token while it is still valid (with a 60 second safety margin) and otherwise refreshes it using the refresh token.

## How it plugs into TM1py

Two small changes to `RestService` make the integration work.

### 1. `access_token` can be a callable

`access_token` previously had to be a string. It can now also be a **zero-argument callable**, resolved on **every connect and reconnect**. This matters because TM1py reconnects when a session times out. With a plain string it would reuse a stale token. With `oauth.access_token` it gets a freshly refreshed one.

If the callable returns an empty value, a `ValueError` is raised.

### 2. `keep_authorization_header`

Normally TM1py sends the `Authorization` header on the session-start request, receives a session cookie, then **drops the header**. PAW's OAuth gateway validates the token on **every** request, so the header must stay. Set `keep_authorization_header=True` for this route.

It is parsed with `translate_to_boolean`, so a `"False"` string from `config.ini` no longer switches the option on by accident.

## Usage

```python
import os

from TM1py import TM1Service
from TM1py.Utils.PawOAuth import PawOAuthSession


def main(
    paw_host: str = "",
    database: str = "",
    client_id: str = "",
    client_secret_env: str = "PAW_CLIENT_SECRET",
    redirect_uri: str = "http://127.0.0.1:8080/callback",
    cache: str = "in_memory",
) -> None:
    """Sign in to PAW via OAuth and print the current TM1 user.

    :param paw_host: PAW host name, e.g. "myenv.planning-analytics.cloud.ibm.com".
    :param database: TM1 database name.
    :param client_id: OAuth client ID registered in PAW.
    :param client_secret_env: Name of the environment variable holding the client
        secret. If the variable is unset, a public client is assumed.
    :param redirect_uri: Loopback redirect registered on the client. Must use
        127.0.0.1 or [::1] and include an explicit port.
    :param cache: "in_memory" (browser sign-in every process) or "keyring"
        (refresh silently across processes; needs TM1py[keyring]).
    :raises ValueError: If paw_host, database or client_id is empty.
    """
    for name, value in (("paw_host", paw_host), ("database", database), ("client_id", client_id)):
        if not value:
            raise ValueError(f"{name} is required")

    oauth = PawOAuthSession(
        auth_url=f"https://{paw_host}/oauth2/authorize",
        token_url=f"https://{paw_host}/oauth2/token",
        client_id=client_id,
        client_secret=os.environ.get(client_secret_env),
        redirect_uri=redirect_uri,
        cache=cache,
    )
    oauth.login()  # opens a browser unless a cached refresh token still works

    with TM1Service(
        base_url=f"https://{paw_host}/api/v1/tm1/{database}",
        access_token=oauth.access_token,  # callable: resolved on every (re)connect
        keep_authorization_header=True,  # the PAW gateway checks every request
    ) as tm1:
        print(tm1.whoami)


if __name__ == "__main__":
    args = {
        "paw_host": "myenv.planning-analytics.cloud.ibm.com",
        "database": "MyDatabase",
        "client_id": "my-client-id",
        "client_secret_env": "PAW_CLIENT_SECRET",
        "redirect_uri": "http://127.0.0.1:8080/callback",
        "cache": "in_memory",
    }
    main(**args)
```

### Choosing the `base_url`

The endpoint matters. The PR author confirmed against real instances that the OAuth token is accepted on PAW's API route but **not** on TM1 11's `/tm1/api/<db>` endpoint, which only accepts CAM authentication.

| Environment | `base_url` |
|---|---|
| TM1 11 on IBM Cloud | `https://<env>.planning-analytics.cloud.ibm.com/api/v1/tm1/<db>` |
| TM1 12 (PAaaS) | `https://<region>.planninganalytics.saas.ibm.com/api/<tenant>/v0/tm1/<db>` |

Both used `scope=v0userContext` (the default) and a confidential client with the secret sent as HTTP Basic auth.

## `PawOAuthSession` reference

**Constructor parameters**

| Parameter | Default | Notes |
|---|---|---|
| `auth_url` | required | The deployment's `/oauth2/authorize` endpoint |
| `token_url` | required | The deployment's `/oauth2/token` endpoint |
| `client_id` | required | OAuth client ID |
| `redirect_uri` | required | `http://` loopback on `127.0.0.1` or `[::1]` with an explicit port. `localhost` is rejected |
| `client_secret` | `None` | Sent as HTTP Basic. `None` means a public client (`client_id` goes in the body) |
| `scope` | `"v0userContext"` | OAuth scope |
| `cache` | `"in_memory"` | `"in_memory"`, `"keyring"`, or a `TokenCache` instance |
| `timeout` | `30` | Seconds per token HTTP request |

**Methods and properties**

- `login(open_browser=True, listener_timeout=180)` runs the interactive flow, trying a silent refresh first. With `open_browser=False` it prints the URL instead.
- `access_token()` returns a valid token, refreshing if needed. Raises `OAuthError` if there is no token and no refresh token, so call `login()` first. Pass this method (uncalled) to TM1py.
- `has_refresh_token` reports whether a refresh token is cached.

**Errors:** `ValueError` for bad configuration (missing values, non-loopback redirect, unknown cache name). `OAuthError` for runtime failures (port in use, no redirect received, `state` mismatch, token endpoint errors). `ImportError` if `cache="keyring"` is used without the `keyring` package.

## Token caching

By default the refresh token lives in memory, so every new process opens the browser again. Two alternatives:

- **`cache="keyring"`** stores the refresh token in the OS credential store (Windows Credential Manager, macOS Keychain, and so on), so later runs sign in silently. Install the optional extra: `pip install TM1py[keyring]`. The `keyring` package is imported only when this cache is created.
  - The entry key is derived from the token endpoint host, client ID and scope, with unsafe characters replaced and a short hash appended so similar sign-ins stay separate.
  - **The client secret is never part of the key.** Key names are visible in the credential store, and a rotated secret should keep the stored token.
  - Windows Credential Manager rejects values over 1280 UTF-16 characters, which refresh tokens can exceed. The token is therefore stored in 1000-character chunks plus a count entry written last.
- **A custom `TokenCache`** subclass implementing `load_refresh_token()` and `save_refresh_token()`, for any other store. To pick your own keyring key or service name, pass `KeyringTokenCache("my-key")` directly.

## Security design

- **PKCE (S256) and a `state` check** protect the authorization code exchange.
- **Loopback IP literals only** (RFC 8252 section 8.3). `localhost` may resolve to the other address family than the listener binds to.
- **Windows port safety:** address reuse is disabled on Windows, where it would let the listener share a port with another process that could intercept the redirect. A busy port raises `OAuthError`.
- **Read timeouts on the listener** (5 seconds), so a browser's idle speculative connection cannot block the single-threaded listener.
- **The client secret is supplied by the caller**, never read from storage by `PawOAuthSession`.

## Dependencies and tests

- The module needs only the standard library plus `requests`. `keyring` is an optional extra.
- Offline unit tests live in `Tests/PawOAuth_test.py` (36 tests, with `keyring` faked so CI does not need it) and `Tests/RestService_authorization_header_test.py`.
- Real-instance checks (TM1 11.8 on IBM Cloud and TM1 12.5.9 PAaaS) were run manually and are not committed. They covered `whoami`, a forced `re_connect()` with a new token, and the `keep_authorization_header=False` failure case.

## Caveats

- This README is based on the PR page and its commit diffs as of the date above. Check the PR itself for anything that changed during review.
- Because the feature is not yet released, the public names (`PawOAuthSession`, `TM1py.Utils.PawOAuth`) are still open to change.