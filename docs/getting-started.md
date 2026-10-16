# Getting Started with TM1py

TM1py is a Python library for interacting with **IBM Planning Analytics / TM1** via the REST API.

---

## Requirements

- [Python](https://www.python.org/downloads/) (3.7 or higher)
- [TM1/Planning Analytics](https://www.ibm.com/products/planning-analytics) (v11 or higher)

## Optional Python Packages

To fully unlock TM1py's potential, these two packages are optional.

- pandas
- networkx

## Installation

TM1py only

```bash
pip install TM1py
```

Or TM1py with pandas dataframe support

```bash
pip install "tm1py[pandas]"
```

## Connect and print version

### TM1 11 on-premise

```python
from TM1py.Services import TM1Service

with TM1Service(address='localhost', port=8001, user='admin', password='apple', ssl=True) as tm1:
    print(tm1.server.get_product_version())
```

### TM1 11 on IBM cloud

```python
with TM1Service(
        base_url='https://mycompany.planning-analytics.ibmcloud.com/tm1/api/tm1/',
        user="non_interactive_user",
        namespace="LDAP",
        password="U3lSn5QLwoQZY2",
        ssl=True,
        verify=True,
        async_requests_mode=True) as tm1:
    print(tm1.server.get_product_version())
```

### TM1 12 PAaaS

```python
from TM1py import TM1Service

params = {
    "base_url": "https://us-east-1.planninganalytics.saas.ibm.com/api/<TenantId>/v0/tm1/<DatabaseName>/",
    "user": "apikey",
    "password": "<TheActualApiKey>",
    "async_requests_mode": True,
    "ssl": True,
    "verify": True
}

with TM1Service(**params) as tm1:
    print(tm1.server.get_product_version())
```

### TM1 12 on-premise & Cloud Pak For Data

```python
with TM1Service(
        address="tm1-ibm-operands-services.apps.cluster.your-cluster.company.com",
        instance="your instance name",
        database="your database name",
        application_client_id="client id",
        application_client_secret="client secret",
        user="admin",
        ssl=True) as tm1:

    print(tm1.server.get_product_version())
```

### TM1 12 on-premise with access token

```python
params = {
    "base_url": "https://pa12.dev.net/api/<InstanceId>/v0/tm1/<DatabaseName>",
    "user": "8643fd6....8a6b",
    "access_token":"<TheActualAccessToken>",
    "async_requests_mode": True,
    "ssl": True,
    "verify": True
}

with TM1Service(**params) as tm1:
    print(tm1.server.get_product_version())
```

### Planning Analytics Workspace with OAuth sign-in

`access_token` also accepts a zero-argument callable. TM1py calls it on every connect and reconnect, so a token
that has expired is replaced after a session timeout. `PawOAuthSession` signs the user in through the browser
once (OAuth authorization code with PKCE) and refreshes the token from then on. The redirect URI must be a
loopback address (`127.0.0.1` or `[::1]`, not `localhost`) registered on the OAuth client.

```python
from TM1py import TM1Service
from TM1py.Utils.PawOAuth import PawOAuthSession

oauth = PawOAuthSession(
    auth_url="https://<paw-host>/oauth2/authorize",
    token_url="https://<paw-host>/oauth2/token",
    client_id="<ClientId>",
    client_secret="<ClientSecret>",  # or None for a public client
    redirect_uri="http://127.0.0.1:8080/callback",
)
oauth.login()  # opens the browser once

with TM1Service(
        base_url="https://<paw-host>/api/v1/tm1/<DatabaseName>",  # TM1 11; see below for TM1 12
        access_token=oauth.access_token,  # the method itself, not its result
        keep_authorization_header=True) as tm1:
    print(tm1.server.get_product_version())
```

The `base_url` must be PAW's API route, which accepts the bearer token:

| Environment | `<paw-host>` | `base_url` |
|---|---|---|
| TM1 11 on IBM Cloud | `<env>.planning-analytics.cloud.ibm.com` | `https://<paw-host>/api/v1/tm1/<DatabaseName>` |
| TM1 12 PAaaS | `<region>.planninganalytics.saas.ibm.com` | `https://<paw-host>/api/<TenantId>/v0/tm1/<DatabaseName>` |

On TM1 11, `/tm1/api/<DatabaseName>` is TM1's own REST endpoint and only accepts CAM authentication, so it rejects
the token. `keep_authorization_header=True` is required on both: the gateway checks the token on every request,
not only when the session starts.

By default the refresh token is kept in memory, so every new process opens the browser again. To sign in once and
refresh silently in later runs, keep it in the operating system's credential store (Windows Credential Manager,
macOS Keychain) with the optional `keyring` package:

```bash
pip install TM1py[keyring]
```

```python
from TM1py.Utils.PawOAuth import KeyringTokenCache, PawOAuthSession

oauth = PawOAuthSession(
    ...,  # as above
    cache=KeyringTokenCache("my-env"),  # one key per environment and OAuth client
)
oauth.login()  # silent refresh if the stored token still works, browser otherwise
```
