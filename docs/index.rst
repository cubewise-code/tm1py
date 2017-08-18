TM1py
=================================


By wrapping the IBM Planning Analytics (TM1) REST API in a concise Python framework, TM1py facilitates Python developments for TM1.

Interacting with TM1 programmatically has never been easier.

.. code-block:: Python

   pip install TM1py

.. code-block:: Python

   from TM1py.Services import TM1Service

   with TM1Service(address='', port=8001, user='admin', password='apple', ssl=False) as tm1:
      subset = Subset(dimension_name='Month',
                      subset_name='Q1',
                      elements=['Jan', 'Feb', 'Mar'])
      tm1.subsets.create(subset, private=True)

Features
----------------------------------

TM1py offers handy features to interact with TM1 from Python, such as

- Read data from cubes through cube views and MDX Queries
- Write data into cubes
- Execute processes and chores
- Execute loose statements of TI
- CRUD features for TM1 objects (cubes, dimensions, subsets, etc.)
- Query and kill threads
- Query MessageLog and TransactionLog
- Generate MDX Queries from existing cube views

Usage
----------------------------------
.. code-block:: Python

   from TM1py.Services import TM1Service

   with TM1Service(address='', port=8001, user='admin', password='apple', ssl=False) as tm1:
      for chore in tm1.chores.get_all():
         chore.reschedule(hours=-1)
         tm1.chores.update(chore)


API Documentation
-----------------

If you are looking for information on a specific function, class, or method,
this part of the documentation is for you.

.. toctree::
   api


Issues
------

If you encounter any problems, please open an Issue in Github


About TM1py
--------------

TM1py was created by Marius Wirtz

Distributed under the MIT license.
