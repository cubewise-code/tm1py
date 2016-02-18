import uuid
from TM1py import Subset, TM1Queries as TM1

random_string1 = str(uuid.uuid4())
random_string2 = str(uuid.uuid4())

tm1 = TM1(ip='localhost', port=8001, user='admin', password='apple', ssl=False)

# create dynamic subset
s = Subset(dimension_name='plan_business_unit', subset_name='TM1py_' + random_string1,
           expression='{ HIERARCHIZE( {TM1SUBSETALL( [plan_business_unit] )} ) }')
tm1.create_subset(s)

# create static subset
s = Subset(dimension_name='plan_business_unit', subset_name='TM1py_' + random_string2,
           elements=['10000', '10000', '10000', '10000', '10000', '10000', '10000', '10000', '10000'])
tm1.create_subset(s)

# delete subset
tm1.delete_subset(dimension_name='plan_business_unit', subset_name='TM1py_' + random_string1)
tm1.delete_subset(dimension_name='plan_business_unit', subset_name='TM1py_' + random_string2)

# logout
tm1.logout()
