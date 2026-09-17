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

## Additional GET query parameters

Pass a `params` dictionary to service methods that forward keyword arguments to
`RestService.GET`. For example, with a connected `tm1` instance:

```python
names = tm1.cubes.get_all_names(
    params={"$top": 10, "$orderby": "Name"}
)
```

This keeps the method's existing `$select=Name` option and adds `$top` and
`$orderby`. For a direct request, use the REST service:

```python
response = tm1._tm1_rest.GET(
    "/Cubes",
    params={"$select": "Name", "$filter": "Name eq 'Sales'", "$top": 10},
)
cubes = response.json()["value"]
```

Use full parameter names, including the `$` for OData system options. Supply
unencoded values; `requests` handles URL encoding. Write OData lists as
comma-separated strings, such as `{"$select": "Name,Rules"}`, and OData boolean
literals as strings, such as `{"$count": "true"}`. Other value encoding follows
`requests.params`. The dictionary must have string keys and is not modified.
Entries with a `None` value are omitted; `$top=0` is retained.

A parameter that is already present in the URL raises `ValueError` before the
HTTP request, even if its value is identical:

```python
# Raises ValueError because get_all_names already requests $select=Name:
tm1.cubes.get_all_names(params={"$select": "Name"})
```

Names are compared case-sensitively after decoding existing URL parameter names,
so `%24select` also conflicts with `$select`. Existing filters and expansions
are neither merged nor replaced. Options inside a nested `$expand` do not
conflict with options at the outer query level.

This support is limited to GET. Service methods expose it through their existing
keyword-argument forwarding; a method with multiple internal GET requests may
apply the parameters to each request. Choose options supported by the endpoint
that preserve the response fields needed by the service method. The original
parameters are retained for retries and the initial async request; async polling
does not inherit them.
