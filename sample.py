from TM1py import Utils, RESTService, DataService, ViewService

mdx = "SELECT {[Measure].[EBIT],[Measure].[Revenue]} on ROWS, " \
      "{[Month].[01]:[Month].[12]} on COLUMNS  " \
      "FROM [PnL Cube] " \
      "WHERE ([Year].[2016],[Version].[ACT],[Currency].[EUR],[BU].[UK]) "

with RESTService(address='', port=8001, user='admin', password='apple', ssl=False) as tm1_rest:
    data_service = DataService(tm1_rest)

    cellset = data_service.execute_mdx(mdx)
    df = Utils.build_pandas_dataframe_from_cellset(cellset)

    print(df.groupby("Month").median())