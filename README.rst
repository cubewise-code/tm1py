TM1py
=======================

TM1py is an object oriented interface to the new IBM Cognos TM1 REST API, written in Python.
The module aims to make interaction with the TM1 Server more straightforward.


Features
=======================
TM1py offers cool features to interact with TM1 from python. Such as,

- Retrieve data from a view (in a concise JSON structure)

.. code-block:: python

    >>> from TM1py import TM1Queries as TM1
    >>> tm1 = TM1(ip='localhost', port=8001, user='admin', password='apple', ssl=False)
    >>> content = tm1.get_view_content_structured(cube_name='Plan_BudgetPlan', 
                                                  view_name='High Level Profit And Loss')
    >>> value = content[('[plan_version].[FY 2004 Budget]',
                         '[plan_business_unit].[10000]',
                         '[plan_department].[1000]',
                         '[plan_chart_of_accounts].[Revenue]',
                         '[plan_exchange_rates].[local]',
                         '[plan_source].[budget]',
                         '[plan_time].[Q2-2004]')]
    >>> print(value)
    51966012.14
    >>> tm1.logout()



Contribution
=======================
TM1py is still at an early stage. Contribution is very welcome.

