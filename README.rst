TM1py
=======================
By wrapping the IBM Planning Analytics (TM1) REST API in a concise Python framework, TM1py facilitates Python developments for TM1.

Interacting with TM1 programmatically has never been easier.

.. code-block:: Python

    >>> login = LoginService.native('admin', 'apple')
    >>> with RESTService(ip='', port=8001, login=login, ssl=False) as tm1_rest:
    >>>     subset_service = SubsetService(tm1_rest)
    >>>     subset = Subset(dimension_name='Month', subset_name='Q1', elements=['Jan', 'Feb', 'Mar'])
    >>>     subset_service.create(subset, private=True)

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
Python
~~~~~~~~~~~~~~~~~~~~~~~
The TM1py libraries will run on all Python versions >= 3.3
Several samples (run processes in parallel, write data in parallel) require the asyncio module though (Python 3.5)!
Python can be downloaded at

https://www.Python.org/downloads/

Python (3.5, 3.6) installation walkthrough on Youtube:

https://www.youtube.com/watch?v=dX2-V2BocqQ

Instead of installing pure Python you can install the Anaconda distribution of Python

https://www.continuum.io/downloads

It comes with 400+ packages (Pandas, Numpy, SciPy, etc.) for Data Analysis in Python.
This is the preferable option if you want to use TM1py for Data Analysis.

Either way, you want to check the "Add Python 3.6 to PATH" Checkbox in the installation!
So can you run Python stuff more easily in the future through the command-line.

To check if the installation was successful just type

 .. code-block:: bash

    Python

into the command-line.
This will print out the installed version of Python and switch into an interactive mode where you can code Python.

If you didn't check the checkbox during the installation you can type

 .. code-block:: bash

    C:\Python35\python.exe

or (in case you decided to use the Anaconda distribution)

 .. code-block:: bash

    C:\Anaconda3\python.exe

TM1
~~~~~~~~~~~~~~~~~~~~~~~
TM1py requires at least TM1 version 10.2.2 FP5.
If you consider using the REST API in production it is recommended to upgrade to TM1 10.2.2 FP 7 or TM1 11, due to minor bugs in earlier versions.

E.g. GET http://localhost:8001/api/v1/Users('Admin')/Password

In order to be able to communicate with TM1 through HTTP, you have to assign an HTTP port number to TM1 in the tm1s.cfg file

.. code-block:: bash

    HTTPPortNumber=8002

The parameter will only be effective after restarting the TM1 instance.

Installation
=======================
To install TM1py, simply:

.. code-block:: bash

    pip install TM1py

pip (the Python package management system) will download the TM1py package and its requirements from PyPI
and store it at in the third party module folder ..Python\\Lib\\site-packages\\TM1py

If Python is installed correctly it should work without issues. Otherwise try:

.. code-block:: bash

    C:\Python35\Scripts\pip.exe TM1py

resp.

.. code-block:: bash

    C:\Anaconda3\Scripts\pip.exe TM1py

If that doesn't work either, try reinstalling Python from scratch.

As a fallback you can download the latest release from GitHub and place it in the \site-packages folder manually
This is not recommended though, as it doesn't take care of the dependencies!

Check Connectivity to TM1
~~~~~~~~~~~~~~~~~~~~~~~
In order to check if TM1py works fine with your TM1 instances,
copy any of the samples (e.g. find unused groups) from Github MariusWirtz-cubewise/TM1py/Samples,
adjust the

- Port
- Address
- SSL (True or False, as stated in the TM1s.cfg)
- User
- Password
parameters in the file and run it with Python

.. code-block:: bash

    python "find unused groups.py"

All the samples are based on the Planning Sample TM1 model, that comes with the installation of TM1.
The samples potentially contain hard coded references to TM1 objects (e.g. cube names).
Make sure to adjust those references if you are not testing against the Planning Sample!

If this doesn't work, feel free to open an issue in Github.

Other
=======================

Python Tutorial
~~~~~~~~~~~~~~~~~~~~~~~
If you are not familiar with the Python programming language you might want to look into some basic tutorials,
before starting with TM1py.
thenewboston offers awesome (and free) Python tutorials on his Youtube Channel
https://www.youtube.com/playlist?list=PL6gx4Cwl9DGAcbMi1sH6oAMk4JHw91mC_

IDE
~~~~~~~~~~~~~~~~~~~~~~~
PyCharm is likely the best IDE for Python. It offers intelligent code completion, on-the-fly error checking and heaps of other features.
It allows you to save time and be more productive.
IntelliJ offers a free Community Edition of PyCharm
https://www.jetbrains.com/pycharm/

Usage
=======================

.. code-block:: Python

    >>> from TM1py.Services import ChoreService
    >>> from TM1py.Services import LoginService
    >>> from TM1py.Services import RESTService

    >>> login = LoginService.native('admin', 'apple')
    >>> with RESTService(ip='', port=8001, login=login, ssl=False) as tm1_rest:
    >>>     chore_service = ChoreService(tm1_rest)
    >>>     for chore in chore_service.get_all():
    >>>         chore.reschedule(hours=-1)
    >>>         chore_service.update(chore)


Documentation
=======================
Work in progress

Issues
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
If you find issues, sign up in Github and open an Issue in this repository
