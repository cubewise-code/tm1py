TM1py
=======================
TM1py is an object oriented interface to the new IBM Cognos TM1 REST API, written in Python.
The module aims to make interaction with the TM1 Server more straightforward.


Features
=======================
TM1py offers handy features to interact with TM1 from Python. Such as,

- Retrieve data from cubes (in concise JSON structure)

.. code-block:: python

    >>> from TM1py import TM1Queries as TM1
    >>> tm1 = TM1(ip='localhost', port=8001, user='admin', password='apple', ssl=False)
    >>> data = tm1.get_view_content(cube_name='Plan_BudgetPlan', 
                                    view_name='High Level Profit And Loss')
    >>> value = data[('[plan_version].[FY 2004 Budget]',
                      '[plan_business_unit].[10000]',
                      '[plan_department].[1000]',
                      '[plan_chart_of_accounts].[Revenue]',
                      '[plan_exchange_rates].[local]',
                      '[plan_source].[budget]',
                      '[plan_time].[Q2-2004]')]
    >>> print(value)
    51966012.14
    >>> tm1.logout()

- Write data into cubes

.. code-block:: python

    >>> from TM1py import TM1Queries as TM1
    >>> tm1 = TM1(ip='localhost', port=8001, user='admin', password='apple', ssl=False)
    >>> cube_name = 'Plan_BudgetPlan'
    >>> coordinates_and_values = {
            ('FY 2004 Budget', 'Germany', 'IT', 'Web Site', 'local', 'input', 'Oct-2005'): 5320,
            ('FY 2004 Budget', 'Germany', 'IT', 'Web Site', 'local', 'input', 'Nov-2005'): 6190,
            ('FY 2004 Budget', 'Germany', 'IT', 'Web Site', 'local', 'input', 'Dec-2005'): 5790
        }
    >>> tm1.write_values(cube_name, coordinates_and_values)
    >>> tm1.logout()
    
- Trigger execution of TI processes from Python

.. code-block:: python

    >>> from TM1py import TM1Queries as TM1
    >>> tm1 = TM1(ip='localhost', port=8001, user='admin', password='apple', ssl=False)
    >>> parameters = {
            "Parameters": [{ 
                "Name": "legal_entity", 
                "Value": "UK01" 
            }] 
        }
    >>> tm1.execute_process(name_process='import_actuals', parameters=parameters)
    >>> tm1.logout()

- Deploy TM1 objects

.. code-block:: python

    >>> from TM1py import TM1Queries as TM1
    >>> tm1_source = TM1(ip='localhost', port=8001, user='admin', password='apple', ssl=False)
    >>> tm1_target = TM1(ip='localhost', port=56912, user='admin', password='apple', ssl=False)
    >>> p = tm1_source.get_process('new')
    >>> tm1_target.create_process(p)
    >>> tm1_source.logout()
    >>> tm1_target.logout()

- Execute lines of TI code

.. code-block:: python

    >>> from TM1py import TM1Queries as TM1
    >>> tm1 = TM1(ip='localhost', port=8081, user='admin', password='apple', ssl=False)
    >>> lines_prolog = [
    >>>     "AddCLient ( 'Chewbacca' );"
    >>> ]
    >>> lines_epilog = [
    >>>     "AssignClientPassword ( 'Chewbacca', 'apple' );",
    >>>     "AssignClientToGroup ( 'Chewbacca', 'ADMIN' );",
    >>>     "SecurityRefresh;"
    >>> ]
    >>> tm1.execute_TI_code(lines_prolog=lines_prolog, lines_epilog=lines_epilog)
    >>> tm1.logout()

Requirements
=======================
http://docs.python-requests.org/en/master/

Installation
=======================
download TM1py.py file and copy it into your project folder.

Contribution
=======================
TM1py is still at an early stage. Contribution is very welcome.

