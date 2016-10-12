from TM1py import TM1pyQueries as TM1, TM1pyLogin
from pandas import pandas as pd

login = TM1pyLogin.native('admin', 'apple')

# connect to TM1
with TM1(ip='', port=8001, login=login, ssl=False) as tm1:
    # get data from P&L cube
    pnl_data = tm1.get_view_content(cube_name='Plan_BudgetPlan',
                                    view_name='High Level Profit And Loss',
                                    cell_properties=['Ordinal', 'Value'])

    # restructure data
    pnl_data_clean = {}
    for item in pnl_data:
        coordinates = []
        for entry in item:
            coordinates.append(entry[entry.find('].[')+3:-1])
        pnl_data_clean[tuple(coordinates)] = pnl_data[item]['Value']

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
    print(df.mean())
    print(df.median())


