import uuid
from TM1py import Subset, TM1pyQueries as TM1, TM1pyLogin

random_string1 = str(uuid.uuid4())
random_string2 = str(uuid.uuid4())

login = TM1pyLogin.native('admin', 'apple')
tm1 = TM1(ip='', port=8001, login=login, ssl=False)

# create dynamic subset
s = Subset(dimension_name='plan_business_unit', subset_name='TM1py_' + random_string1, alias='',
           expression='{ HIERARCHIZE( {TM1SUBSETALL( [plan_business_unit] )} ) }')
tm1.create_subset(s)

# create static subset
s = Subset(dimension_name='plan_business_unit', subset_name='TM1py_' + random_string2, alias='',
           elements=['10000', '10100', '10110', '10120', '10200', '10210', '10220', '10300', '10400'])
tm1.create_subset(s)

# delete subset
tm1.delete_subset(dimension_name='plan_business_unit', subset_name='TM1py_' + random_string1)
tm1.delete_subset(dimension_name='plan_business_unit', subset_name='TM1py_' + random_string2)

# logout
tm1.logout()
