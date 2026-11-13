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

## Filtering, limiting and sorting on the server

Methods that return lists of names or objects accept the keyword-only
arguments `filter`, `top` and `order_by`. They are sent to TM1 as the OData
options `$filter`, `$top` and `$orderby`, so only the requested entries are
transferred:

```python
names = tm1.cubes.get_all_names(
    filter="startswith(Name,'Sales')",
    top=10,
    order_by="Name desc",
)
```

`filter` and `order_by` are unencoded OData expressions; TM1py takes care of
the URL encoding. `top` is a non-negative integer, `top=0` is retained.

If a method already filters on its own, the supplied filter is combined with
`and`, so both conditions apply:

```python
# processes that are no control processes AND start with 'Load'
tm1.processes.get_all_names(skip_control_processes=True, filter="startswith(Name,'Load')")

# consolidated elements on a level greater than 1
tm1.elements.get_element_names("Region", "Region", element_type="consolidated", filter="Level gt 1")
```

The arguments are available on:

| Service | Methods |
|---|---|
| `cubes` | `get_all_names`, `get_all_names_with_rules`, `get_all_names_without_rules` |
| `dimensions` | `get_all_names` |
| `hierarchies` | `get_all_names` |
| `processes` | `get_all`, `get_all_names` |
| `elements` | `get_elements`, `get_element_names`, `get_leaf_elements`, `get_leaf_element_names`, `get_consolidated_elements`, `get_consolidated_element_names` |
| `chores` | `get_all_names` |
| `subsets` | `get_all_names` |
| `views` | `get_all_names` (applied to private and public views separately) |
| `security` | `get_all_user_names`, `get_all_groups` |

## Additional GET query parameters

For other endpoints or query options, pass a `params` dictionary directly to
`RestService.GET`:

```python
response = tm1._tm1_rest.GET(
    "/Cubes",
    params={"$select": "Name", "$filter": "Name eq 'Sales'", "$top": 10},
)
cubes = response.json()["value"]
```

Use full parameter names, including the `$` for OData system options. Supply
unencoded values; spaces are encoded as `%20`. Write OData lists as
comma-separated strings, such as `{"$select": "Name,Rules"}`. Python booleans
are sent as lowercase `true`/`false`. The dictionary must have string keys and
is not modified. Entries with a `None` value are omitted; `$top=0` is retained.

A parameter that is already present in the URL raises `ValueError` before the
HTTP request, even if its value is identical:

```python
# Raises ValueError because the URL already contains $select:
tm1._tm1_rest.GET("/Cubes?$select=Name", params={"$select": "Name"})
```

Names are compared case-sensitively after decoding existing URL parameter names,
so `%24select` also conflicts with `$select`. Existing filters and expansions
are neither merged nor replaced. Options inside a nested `$expand` do not
conflict with options at the outer query level.

`params` is only supported for GET. `POST`, `PATCH`, `PUT` and `DELETE` raise a
`TypeError` when `params` is passed. The original parameters are retained for
retries and the initial async request; async polling does not inherit them.
