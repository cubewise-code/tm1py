

.. image:: https://s3-ap-southeast-2.amazonaws.com/downloads.cubewise.com/web_assets/CubewiseLogos/TM1py-logo.png
    :align: center

By wrapping the IBM Planning Analytics (TM1) REST API in a concise Python framework, TM1py facilitates Python developments for TM1.

Interacting with TM1 programmatically has never been easier.


.. code-block:: Python

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
- Query MessageLog and TransactionLog
- Generate MDX Queries from existing cube views

Requirements
=======================

- Python    (3.5 or higher)
- TM1       (10.2.2 FP 5 or higher)

Usage
=======================

 .. code-block:: Bash

    pip install TM1py


.. code-block:: Python

    from TM1py.Services import TM1Service

    with TM1Service(address='localhost', port=8001, user='admin', password='apple', ssl=True) as tm1:
        for chore in tm1.chores.get_all():
            chore.reschedule(hours=-1)
            tm1.chores.update(chore)

Samples:
https://github.com/cubewise-code/TM1py-samples


Documentation
=======================

Code Documentation:
http://tm1py.readthedocs.io/en/latest/

Detailed Installation instructions and Samples:
https://github.com/cubewise-code/TM1py-samples


Issues
=======================

If you find issues, sign up in Github and open an Issue in this repository


Contribution
=======================

TM1py is an open source project. It thrives on contribution from the TM1 community.
If you find a bug or feel like you can contribute please fork the repository, update the code and then create a pull request so we can merge in the changes.
