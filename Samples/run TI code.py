from TM1py import TM1pyQueries as TM1, TM1pyLogin


tm1 = TM1('', 8001, TM1pyLogin.native('admin', 'apple'), ssl=False)

ti_statements = [
    "DimensionCreate ( 'TM1py' );",
    "DimensionElementInsert ( 'TM1py' , '' , 'tm1' , 'N');",
    "DimensionElementInsert ( 'TM1py' , '' , 'is' , 'N');",
    "DimensionElementInsert ( 'TM1py' , '' , 'awesome' , 'N');"
]

tm1.execute_TI_code(lines_prolog=ti_statements, lines_epilog=[])

tm1.logout()
