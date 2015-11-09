TM1py
=======================

TMpy is a object oriented interface to the new IBM Cognos TM1 REST API.

.. code-block:: python

    >>> q = TM1Queries(ip='', port=8008, user='admin', password='apple', ssl=True)
    >>> s = Subset(dimension_name='plan_business_unit', subset_name='Hi_Im_a_subset',
                   elements=['10110', '10300', '10210', '10000'])
    >>> q.create_subset(s)
    {"@odata.context":"../../$metadata#Dimensions('plan_business_unit')/Hierarchies('plan_business_unit')\
    /Subsets/$entity","Name":"Hi_Im_a_subset","UniqueName":"[plan_business_unit].[Hi_Im_a_subset]",\
    "Expression":null}
    ...
