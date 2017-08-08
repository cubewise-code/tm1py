import pandas as pd

from TM1py.Services import CubeService
from TM1py.Services import DataService
from TM1py.Services import LoginService
from TM1py.Services import RESTService

login = LoginService.native('admin', 'apple')

with RESTService(ip='', port=8001, login=login, ssl=False) as tm1_rest:
    # Services for interaction with TM1
    data_service = DataService(tm1_rest)
    cube_service = CubeService(tm1_rest)

    # get data from P&L cube
    pnl_data = data_service.get_view_content(cube_name='Plan_BudgetPlan',
                                             view_name='Budget Input Detailed',
                                             cell_properties=['Ordinal', 'Value'],
                                             private=False)

    # restructure data
    pnl_data_clean = {}
    for coordinates, cell in pnl_data.items():
        coordinates_clean = tuple([unique_name[unique_name.find('].[') + 3:-1] for unique_name in coordinates])
        pnl_data_clean[coordinates_clean] = cell['Value']

    # create index
    names = cube_service.get_dimension_names('Plan_BudgetPlan')
    keylist = list(pnl_data_clean.keys())
    multiindex = pd.MultiIndex.from_tuples(keylist, names=names)

    # create DataFrame
    values = list(pnl_data_clean.values())
    df = pd.DataFrame(values, index=multiindex)

    # print DataFrame
    print(df)

    # print mean and median
    print("Mean: " + str(df.mean()))
    print("Median: " + str(df.median()))
