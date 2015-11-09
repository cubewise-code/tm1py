TM1py
=======================

TM1py is an object oriented interface to the new IBM Cognos TM1 REST API, written in Python, for humans.
The module aims to make communication with the TM1 Server more easy.

.. code-block:: python

    >>> q = TM1Queries(ip='', port=8008, user='admin', password='apple', ssl=True)
    >>> s = Subset(dimension_name='plan_business_unit', subset_name='Hi_Im_a_subset',
                   elements=['10110', '10300', '10210', '10000'])
    >>> q.create_subset(s)
    {"@odata.context":"../../$metadata#Dimensions('plan_business_unit')/Hierarchies('plan_business_unit')\
    /Subsets/$entity","Name":"Hi_Im_a_subset","UniqueName":"[plan_business_unit].[Hi_Im_a_subset]",\
    "Expression":null}
    ...

This module is still an early stage. Contribution is very welcome.
