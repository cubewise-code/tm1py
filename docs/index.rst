

.. image:: https://s3-ap-southeast-2.amazonaws.com/downloads.cubewise.com/web_assets/CubewiseLogos/TM1py-logo.png

By wrapping the IBM Planning Analytics (TM1) REST API in a concise Python framework, TM1py facilitates Python developments for TM1.

Interacting with TM1 programmatically has never been easier.


.. code-block:: python

    with TM1Service(address='localhost', port=8001, user='admin', password='apple', ssl=True) as tm1:
        subset = Subset(dimension_name='Month', subset_name='Q1', elements=['Jan', 'Feb', 'Mar'])
        tm1.subsets.create(subset, private=True)

Features
=======================

TM1py offers handy features to interact with TM1 from Python, such as

- Read data from cubes through cube views and MDX Queries
- Write data into cubes
- Execute processes and chores
- Execute loose statements of TI
- CRUD features for TM1 objects (cubes, dimensions, subsets, etc.)
- Query and kill threads
- Query MessageLog, TransactionLog and AuditLog
- Generate MDX Queries from existing cube views

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

without pandas

.. code-block:: python

    pip install tm1py

with pandas

.. code-block:: python

    pip install "tm1py[pandas]"


Usage
=======================

on-premise

.. code-block:: python

    from TM1py.Services import TM1Service

    with TM1Service(address='localhost', port=8001, user='admin', password='apple', ssl=True) as tm1:
        for chore in tm1.chores.get_all():
            chore.reschedule(hours=-1)
            tm1.chores.update(chore)

IBM cloud

.. code-block:: python

    with TM1Service(
            base_url='https://mycompany.planning-analytics.ibmcloud.com/tm1/api/tm1/',
            user="non_interactive_user",
            namespace="LDAP",
            password="U3lSn5QLwoQZY2",
            ssl=True,
            verify=True,
            async_requests_mode=True) as tm1:
        for chore in tm1.chores.get_all():
            chore.reschedule(hours=-1)
            tm1.chores.update(chore)



API Documentation
-----------------

If you are looking for information on a specific function, class, or method,
this part of the documentation is for you.

.. toctree::
   :maxdepth: 2

   api

