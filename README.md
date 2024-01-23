
<img src="https://s3-ap-southeast-2.amazonaws.com/downloads.cubewise.com/web_assets/CubewiseLogos/TM1py-logo.png" style="width: 70%; height: 70%;text-align: center"/>


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

- python (3.7 or higher)
- requests
- requests_negotiate_sspi
- TM1 11 


Optional Requirements
=======================

- pandas

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
    print(tm1.server.get_product_Version())
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
    print(tm1.server.get_product_Version())
```


> TM1 12 PAaaS

``` python
with TM1Service(
        address="us-east-2.aws.planninganalytics.ibm.com",
        api_key="AB4VfG7T8wPM-912uFKeYG5PGh0XbS80MVBAt7SEG6xn",
        iam_url="https://iam.cloud.ibm.com/identity/token",
        tenant="YA9A2T8BS2ZU",
        database="Database") as tm1:
    print(tm1.server.get_product_Version())
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

    print(tm1.server.get_product_Version())
```




Documentation
=======================

https://tm1py.readthedocs.io/en/master/


Issues
=======================

If you find issues, sign up in Github and open an Issue in this repository


Contribution
=======================

TM1py is an open source project. It thrives on contribution from the TM1 community.
If you find a bug or feel like you can contribute please fork the repository, update the code and then create a pull request so we can merge in the changes.
