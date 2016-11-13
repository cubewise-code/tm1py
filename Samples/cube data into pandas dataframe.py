from TM1py import TM1pyQueries as TM1, TM1pyLogin
from pandas import pandas as pd

login = TM1pyLogin.native('admin', 'apple')

# connect to TM1
with TM1(ip='', port=8001, login=login, ssl=False) as tm1:
    # get data from P&L cube
    pnl_data = tm1.get_view_content(cube_name='Plan_BudgetPlan',
                                    view_name='Budget Input Detailed',
                                    cell_properties=['Ordinal', 'Value'],
                                    private=False)

    # restructure data
    pnl_data_clean = {}
    for coordinates, cell in pnl_data.items():
        coordinates_clean = tuple([unique_name[unique_name.find('].[') + 3:-1] for unique_name in coordinates])
        pnl_data_clean[coordinates_clean] = cell['Value']

    # create index
    names = tm1.get_dimension_order('Plan_BudgetPlan')
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

