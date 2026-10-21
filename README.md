<h1 align="center">
<img src="https://raw.githubusercontent.com/cubewise-code/tm1py/master/Images/Logo.svg" style="width: 70%; height: 70%; text-align: center"/>

![PyPI - License](https://img.shields.io/pypi/l/TM1py)
![PyPI - Version](https://img.shields.io/pypi/v/TM1py)
![Pepy Total Downloads](https://img.shields.io/pepy/dt/TM1py)
</h1>

TM1py is the python package for IBM Planning Analytics (TM1).

``` python
with TM1Service(address='localhost', port=8001, user='admin', password='apple', ssl=True) as tm1:
    subset = Subset(dimension_name='Month', subset_name='Q1', elements=['Jan', 'Feb', 'Mar'])
    tm1.subsets.create(subset, private=True)
```

Features
=======================

TM1py offers handy features to interact with TM1 from Python, such as

- Functions to read data from cubes through cube views or MDX queries (e.g. `tm1.cells.execute_mdx`)
- Functions to write data to cubes (e.g. `tm1.cells.write`)
- Functions to update dimensions and hierarchies (e.g. `tm1.hierarchies.get`)
- Functions to update metadata, clear or write to cubes directly from pandas dataframes  (e.g. `tm1.elements.get_elements_dataframe`)
- Async functions to easily parallelize your read or write operations (e.g. `tm1.cells.write_async`)
- Functions to execute TI process or loose statements of TI (e.g. `tm1.processes.execute_with_return`)
- CRUD features for all TM1 objects (cubes, dimensions, subsets, etc.)

Requirements
=======================

- [Python](https://www.python.org/downloads/) (3.7 or higher)
- [TM1/Planning Analytics](https://www.ibm.com/products/planning-analytics) (v11 or higher)

Optional Python Packages
=======================

- pandas
- networkx

Install
=======================

> without pandas

    pip install tm1py
    
> with pandas

    pip install "tm1py[pandas]"

Usage
=======================

> TM1 11 on-premise

``` python
from TM1py.Services import TM1Service

with TM1Service(address='localhost', port=8001, user='admin', password='apple', ssl=True) as tm1:
    print(tm1.server.get_product_version())
```

> TM1 11 on IBM cloud

``` python
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

> TM1 12 PAaaS

``` python
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

> TM1 12 on-premise & Cloud Pak For Data

``` python
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

> TM1 12 on-premise with access token

``` python
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

> Accessing TM1 REST APIs through Planning Analytics Workspace

PAW serves the TM1 REST API at `https://<PawHost>/api/v1/tm1/<DatabaseName>` and authenticates every request with an
OAuth access token. `access_token` also accepts a function that returns the token. TM1py calls it before every request, so your code can
refresh the token (e.g. a PAW OAuth access token) mid-session, without a failed request or a new TM1 session.
Obtaining, refreshing and storing the token stay in your code; TM1py never opens a browser or stores tokens.

``` python
from TM1py import TM1Service


def get_token() -> str:
    # return a valid access token: a cached one while it is valid, a refreshed one when it is about to expire
    return my_oauth_client.get_access_token()


with TM1Service(
        base_url="https://<PawHost>/api/v1/tm1/<DatabaseName>",
        access_token=get_token) as tm1:  # the function itself, not get_token()
    print(tm1.server.get_product_version())
```

The function is called on every request, possibly from several threads, so it should return a cached token quickly
and be thread-safe. 

Documentation
=======================

<https://tm1py.org/>

Issues
=======================

If you find issues, sign up in GitHub and open an Issue in this repository

Contribution
=======================

TM1py is an open source project. It thrives on contribution from the TM1 community.
If you find a bug or feel like you can contribute please fork the repository, update the code and then create a pull request so we can merge in the changes.
