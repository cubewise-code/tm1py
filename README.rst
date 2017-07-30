TM1py
=======================
By wrapping the IBM Planning Analytics (TM1) REST API in a concise Python framework, TM1py facilitates Python developments for TM1. 

Interacting with TM1 programmatically has never been so easy

.. code-block:: python

    >>> login = LoginService.native('admin', 'apple')
    >>> with RESTService(ip='', port=8001, login=login, ssl=False) as tm1_rest:
    >>>     subset_service = SubsetService(tm1_rest)
    >>>     subset = Subset(dimension_name='Month', subset_name='Q1', elements=['Jan', 'Feb', 'Mar'])
    >>>     subset_service.create(subset, private=True)

Features
=======================
TM1py offers handy features to interact with TM1 from Python, such as

- Read data from cubes through cubeviews and MDX queries
- Write data into cubes
- Migrate TM1 objects
- Execute processes and chores
- Execute loose statements of TI
- CRUD features for TM1 objects (cubes, dimensions, subsets, etc.)
- Query and kill threads
- Query MessageLog and TransactionLog
- Generate MDX queries from existing cubeviews

Requirements
=======================
http://docs.python-requests.org/en/master/

Installation
=======================
Download TM1py and place it in your project folder
