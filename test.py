from TM1py import TM1Service


config = {
    'address': 'GNG-CW2',
    'port': 8106,
    'user': "admin",
    'password': "apple",
    'ssl': False
}
with TM1Service(**config) as tm1:
    dimension_name = 'TM1py_unittest_element_dimension_6b5b8ac4_353c_11ef_a15d_e470b874d1c2'
    tm1.elements.element_unlock(dimension_name=dimension_name, 
                                       hierarchy_name=dimension_name, 
                                       element_name='1991')
    print(tm1.server.get_admin_host())