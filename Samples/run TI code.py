from TM1py import TM1pyQueries as TM1, TM1pyLogin

login = TM1pyLogin.native('admin', 'apple')

with TM1(ip='', port=8001, login=login, ssl=False) as tm1:
    ti_statements = [
        "DimensionCreate ( 'TM1py' );",
        "DimensionElementInsert ( 'TM1py' , '' , 'tm1' , 'N');",
        "DimensionElementInsert ( 'TM1py' , '' , 'is' , 'N');",
        "DimensionElementInsert ( 'TM1py' , '' , 'awesome' , 'N');"
    ]
    tm1.execute_TI_code(lines_prolog=ti_statements, lines_epilog=[])

    ti_statements = [
        "SaveDataAll;",
        "DeleteAllPersistentFeeders;",
        "SecurityRefresh;",
        "CubeProcessFeeders('Plan_BudgetPlan');"
    ]
    tm1.execute_TI_code(lines_prolog=ti_statements, lines_epilog=[])
