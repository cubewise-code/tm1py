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

- Read data from cubes through cubeviews and MDX Queries
- Write data into cubes
- Migrate TM1 objects
- Execute processes and chores
- Execute loose statements of TI
- CRUD features for TM1 objects (cubes, dimensions, subsets, etc.)
- Query and kill threads
- Query MessageLog and TransactionLog
- Generate MDX Queries from existing cubeviews

Requirements
=======================
Python 3.5 +

Installation
=======================
To install Requests, simply:

.. code-block:: bash

    pip install TM1py

Usage
=======================
.. code-block:: python

    >>> # Import Service and Objects
    >>> from TM1py.Services import ChoreService
    >>> from TM1py.Services import LoginService
    >>> from TM1py.Services import RESTService

    >>> # Establish Connection to TM1 through the RESTService
    >>> login = LoginService.native('admin', 'apple')
    >>> with RESTService(ip='', port=8001, login=login, ssl=False) as tm1_rest:
    >>>     chore_service = ChoreService(tm1_rest)
    >>>     # Get all Chores
    >>>     for chore in chore_service.get_all():
    >>>         # Reschedule each Chore by one hour
    >>>         chore.reschedule(hours=-1)
    >>>         chore_service.update(chore)

Documentation
=======================
Work in progress

FAQ
=======================
How do I install Python 3?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
download the installer and click through the wizard
https://www.python.org/downloads/

How do I install TM1py?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Open the commandline and type: pip install TM1py

.. code-block:: bash

    pip install TM1py

Do I have to change something in tms.cfg
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Yes. You have to assign an HTTPPortNumber to TM1.

.. code-block:: bash

    HTTPPortNumber=8002

I found a Bug. What do I do?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Sign up in Github and open an Issue in this repository
