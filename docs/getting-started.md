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

`use_paw_oauth` signs the user in to PAW through the browser (OAuth authorization code with PKCE) and connects
through PAW's API route. The OAuth endpoints are derived from `base_url`, and the token is refreshed automatically
from then on, including when TM1py reconnects after a session timeout.

```python
import os

from TM1py import TM1Service

with TM1Service(
        base_url="https://<paw-host>/api/v1/tm1/<DatabaseName>",  # TM1 11; see below for TM1 12
        use_paw_oauth=True,
        paw_client_id="<ClientId>",
        paw_client_secret=os.environ["PAW_CLIENT_SECRET"]) as tm1:  # omit for a public client
    print(tm1.server.get_product_version())
```

The `base_url` must be PAW's API route, which accepts the bearer token:

| Environment | `<paw-host>` | `base_url` |
|---|---|---|
| TM1 11 on IBM Cloud | `<env>.planning-analytics.cloud.ibm.com` | `https://<paw-host>/api/v1/tm1/<DatabaseName>` |
| TM1 12 PAaaS | `<region>.planninganalytics.saas.ibm.com` | `https://<paw-host>/api/<TenantId>/v0/tm1/<DatabaseName>` |

On TM1 11, `/tm1/api/<DatabaseName>` is TM1's own REST endpoint and only accepts CAM authentication, so it rejects
the token. `use_paw_oauth` also turns on `keep_authorization_header`, because the gateway checks the token on every
request, not only when the session starts.

The OAuth client must have `http://127.0.0.1:8000/oauth/paw/callback` registered as a redirect URI. To use another
loopback address (`127.0.0.1` or `[::1]`, not `localhost`), for example if port 8000 is in use, pass
`paw_redirect_uri`. `paw_client_id` is the PAW OAuth client; it is unrelated to `application_client_id`, which is a
TM1 12 engine application client.

#### Signing in once across runs

With `use_paw_oauth=True` the refresh token is kept in memory, so every new process opens the browser again. To
sign in once and refresh silently in later runs, keep it in the operating system's credential store (Windows
Credential Manager, macOS Keychain) with the optional `keyring` package:

```bash
pip install TM1py[keyring]
```

```python
with TM1Service(..., use_paw_oauth="keyring") as tm1:  # instead of True
    ...
```

The entry is keyed on the token endpoint, client ID and scope, so each environment and OAuth client gets its own.
To choose the key yourself, pass `use_paw_oauth=KeyringTokenCache("my-key")`; any other store can be used by
passing your own `TokenCache` subclass.

#### Using `PawOAuthSession` directly

`access_token` also accepts a zero-argument callable, which TM1py calls on every connect and reconnect. For full
control over the sign-in, for example to sign in before creating several `TM1Service` instances, create the session
yourself and pass its `access_token` method:

```python
import os

from TM1py import TM1Service
from TM1py.Utils.PawOAuth import PawOAuthSession

oauth = PawOAuthSession.from_base_url(
    "https://<paw-host>/api/v1/tm1/<DatabaseName>",
    client_id="<ClientId>",
    client_secret=os.environ["PAW_CLIENT_SECRET"],
    cache="keyring",  # or "in_memory" (default), or a TokenCache
)
oauth.login()  # opens the browser, or refreshes silently from the cache

with TM1Service(
        base_url="https://<paw-host>/api/v1/tm1/<DatabaseName>",
        access_token=oauth.access_token,  # the method itself, not its result
        keep_authorization_header=True) as tm1:
    print(tm1.server.get_product_version())
```
