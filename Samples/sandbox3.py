from TM1py import TM1pyLogin, TM1pyQueries as TM1

login = TM1pyLogin.native('admin', 'Number22!')
tm1 = TM1(ip='', port=8543, login=login, ssl=False)



nv = tm1.get_native_view('Sales Cube', 'test_Marius')


data = tm1.get_view_content('Sales Cube', 'test_Marius', cell_properties=['Value', 'Status', 'Ordinal'], top=3)



print(data)

tm1.logout()